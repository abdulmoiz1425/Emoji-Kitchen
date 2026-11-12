"""IndexNow submissions for Bing and other participating search engines.

Pings are skipped when the key is empty, when DEBUG is true, or when
INDEXNOW_ENABLED is false (the default under the test runner). Exceptions
are logged and never raised, so a failed ping cannot block a blog save.
"""
import logging
import threading
from urllib.parse import urlparse, urlunparse

import requests
from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = 'https://api.indexnow.org/indexnow'
INDEXNOW_HOST = 'emojikitchenhub.com'
INDEXNOW_TIMEOUT = 5
INDEXNOW_BATCH_SIZE = 10_000
ALLOWED_INDEXNOW_HOSTS = frozenset({INDEXNOW_HOST, f'www.{INDEXNOW_HOST}'})

# Fields that appear on the public post page, listing, or in meta/og tags.
# A published save pings IndexNow only when one of these changes (or the
# post is newly visible). updated_at and admin-only keyword fields are
# ignored, so a no-op re-save does not ping.
VISIBLE_BLOG_POST_FIELDS = (
    'title',
    'slug',
    'author',
    'featured_image',
    'excerpt',
    'content',
    'category_id',
    'reading_time',
    'status',
    'is_featured',
    'publish_date',
    'seo_title',
    'seo_description',
    'seo_keywords',
    'canonical_url',
    'meta_robots',
    'og_title',
    'og_description',
    'og_image',
)


def configured_key():
    return (getattr(settings, 'INDEXNOW_KEY', '') or '').strip()


def key_location(key=None):
    key = configured_key() if key is None else key
    return f'https://{INDEXNOW_HOST}/{key}.txt'


def should_submit(*, force=False):
    """True when a request should be sent.

    force=True is for the management command (and tests that opt in). It
    still requires a key, but ignores DEBUG and INDEXNOW_ENABLED.
    """
    if not configured_key():
        return False
    if force:
        return True
    if getattr(settings, 'DEBUG', False):
        return False
    return bool(getattr(settings, 'INDEXNOW_ENABLED', False))


def absolute_site_url(path_or_url):
    value = (path_or_url or '').strip()
    if value.startswith('http://') or value.startswith('https://'):
        return value
    if not value.startswith('/'):
        value = '/' + value
    return f'https://{INDEXNOW_HOST}{value}'


def normalize_indexnow_url(path_or_url):
    """Return a canonical https://emojikitchenhub.com URL, or None if invalid.

    Relative site paths are allowed. Absolute http(s) URLs are accepted only
    when the host is emojikitchenhub.com or www.emojikitchenhub.com, and are
    normalized to the apex https host used in the IndexNow payload.
    """
    value = (path_or_url or '').strip()
    if not value:
        return None
    if value.startswith('//'):
        value = 'https:' + value
    if value.startswith('http://') or value.startswith('https://'):
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https'):
            return None
        if parsed.username or parsed.password:
            return None
        host = (parsed.hostname or '').lower()
        if host not in ALLOWED_INDEXNOW_HOSTS:
            logger.warning('IndexNow skipped foreign-host URL: %s', value)
            return None
        path = parsed.path or '/'
        return urlunparse(('https', INDEXNOW_HOST, path, '', parsed.query, ''))
    if not value.startswith('/'):
        value = '/' + value
    return f'https://{INDEXNOW_HOST}{value}'


def collect_sitemap_urls():
    """Absolute production URLs from the Django sitemap classes, no HTTP."""
    from kitchen.sitemaps import BlogPostSitemap, StaticViewSitemap

    urls = []
    seen = set()
    for sitemap_cls in (StaticViewSitemap, BlogPostSitemap):
        sitemap = sitemap_cls()
        for item in sitemap.items():
            url = normalize_indexnow_url(sitemap.location(item))
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def build_payload(urls, key=None):
    key = configured_key() if key is None else key
    return {
        'host': INDEXNOW_HOST,
        'key': key,
        'keyLocation': key_location(key),
        'urlList': list(urls),
    }


def submit_urls(urls, *, force=False, timeout=INDEXNOW_TIMEOUT):
    """POST urls to IndexNow. Never raises. Returns the payload if sent.

    Foreign-host URLs are ignored; only emojikitchenhub.com URLs are sent.
    """
    cleaned = []
    seen = set()
    for url in urls or []:
        absolute = normalize_indexnow_url(url)
        if absolute and absolute not in seen:
            seen.add(absolute)
            cleaned.append(absolute)
    if not cleaned or not should_submit(force=force):
        return None
    payload = build_payload(cleaned)
    try:
        requests.post(INDEXNOW_ENDPOINT, json=payload, timeout=timeout)
    except Exception:
        logger.exception('IndexNow submit failed')
        return None
    return payload


def _start_daemon(target, args=()):
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()
    return thread


def schedule_urls(urls):
    """Submit after the current transaction commits, in a daemon thread."""
    snapshot = list(urls or [])
    if not snapshot or not should_submit():
        return

    def _run():
        try:
            _start_daemon(submit_urls, args=(snapshot,))
        except Exception:
            logger.exception('IndexNow thread failed to start')

    try:
        transaction.on_commit(_run)
    except Exception:
        logger.exception('IndexNow schedule failed')


def _plain_value(post, field_name):
    value = getattr(post, field_name)
    if hasattr(value, 'name') and not isinstance(value, (str, bytes)):
        return value.name or ''
    return value


def public_blog_post_snapshot(post):
    """Comparable values of the fields that appear on the public page."""
    return {field: _plain_value(post, field) for field in VISIBLE_BLOG_POST_FIELDS}


def snapshot_blog_post_before_save(sender, instance, **kwargs):
    """pre_save: remember the public fields as they currently exist in the DB."""
    try:
        instance._indexnow_prior_snapshot = None
        if instance.pk is None:
            return
        prior = sender.objects.filter(pk=instance.pk).first()
        if prior is None:
            return
        instance._indexnow_prior_snapshot = public_blog_post_snapshot(prior)
        instance._indexnow_prior_visible = bool(prior.is_visible)
    except Exception:
        logger.exception('IndexNow pre_save snapshot failed')
        try:
            instance._indexnow_prior_snapshot = None
        except Exception:
            pass


def should_ping_blog_post(instance, *, created, prior=None, was_visible=None):
    """True when this save should notify IndexNow of the post URL."""
    is_visible = bool(getattr(instance, 'is_visible', False))
    if created:
        return is_visible
    if not is_visible:
        return False
    if prior is None:
        # No snapshot (new pk, or pre_save could not load the row). Ping
        # only when the saved row is visible, matching the previous hook.
        return True
    if not was_visible:
        return True
    return public_blog_post_snapshot(instance) != prior


def on_blog_post_save(sender, instance, **kwargs):
    """post_save hook: ping when a visible post is created or publicly changed.

    A no-op re-save of a published post does not ping. A slug change pings
    only the new URL. Failures are logged and never raised.
    """
    try:
        created = kwargs.get('created', False)
        prior = getattr(instance, '_indexnow_prior_snapshot', None)
        was_visible = getattr(instance, '_indexnow_prior_visible', None)
        if not should_ping_blog_post(
            instance,
            created=created,
            prior=prior,
            was_visible=was_visible,
        ):
            return
        url = normalize_indexnow_url(instance.get_absolute_url())
        if url:
            schedule_urls([url])
    except Exception:
        logger.exception('IndexNow blog post hook failed')


def key_file(request, key):
    """Serve /<INDEXNOW_KEY>.txt; any other *.txt key is a 404."""
    expected = configured_key()
    if not expected or key != expected:
        raise Http404()
    return HttpResponse(expected, content_type='text/plain')
