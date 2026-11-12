"""IndexNow submissions for Bing and other participating search engines.

Pings are skipped when the key is empty, when DEBUG is true, or when
INDEXNOW_ENABLED is false (the default under the test runner). Exceptions
are logged and never raised, so a failed ping cannot block a blog save.
"""
import logging
import threading

import requests
from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = 'https://api.indexnow.org/indexnow'
INDEXNOW_HOST = 'emojikitchenhub.com'
INDEXNOW_TIMEOUT = 5
INDEXNOW_BATCH_SIZE = 10_000


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


def collect_sitemap_urls():
    """Absolute production URLs from the Django sitemap classes, no HTTP."""
    from kitchen.sitemaps import BlogPostSitemap, StaticViewSitemap

    urls = []
    seen = set()
    for sitemap_cls in (StaticViewSitemap, BlogPostSitemap):
        sitemap = sitemap_cls()
        for item in sitemap.items():
            url = absolute_site_url(sitemap.location(item))
            if url not in seen:
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
    """POST urls to IndexNow. Never raises. Returns the payload if sent."""
    cleaned = []
    seen = set()
    for url in urls or []:
        absolute = absolute_site_url(url)
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


def on_blog_post_save(sender, instance, **kwargs):
    """post_save hook: ping a published (or already-visible scheduled) post."""
    try:
        if not getattr(instance, 'is_visible', False):
            return
        url = absolute_site_url(instance.get_absolute_url())
        schedule_urls([url])
    except Exception:
        logger.exception('IndexNow blog post hook failed')


def key_file(request, key):
    """Serve /<INDEXNOW_KEY>.txt; any other *.txt key is a 404."""
    expected = configured_key()
    if not expected or key != expected:
        raise Http404()
    return HttpResponse(expected, content_type='text/plain')
