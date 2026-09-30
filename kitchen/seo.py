"""SEO helpers for canonical URLs, share images, and stored blog HTML.

Blog rows (iPhone, Samsung, Gboard, WhatsApp) live in the production database,
not in this repo. These helpers stop bad stored values from being rendered.
"""
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.urls import Resolver404, resolve

# Hosts this project actually serves. Anything else in a stored canonical is ignored.
_SITE_HOSTS = {'emojikitchenhub.com', 'www.emojikitchenhub.com'}

_META_LABEL = re.compile(r'^\s*meta description:\s*', re.IGNORECASE)
_IMG_TAG = re.compile(r'<img\b[^>]*?>', re.IGNORECASE | re.DOTALL)
_SRC_ATTR = re.compile(r"""\bsrc\s*=\s*(['"])(.*?)\1""", re.IGNORECASE | re.DOTALL)

BROKEN_WEBP = 'emoji-kitchen-whatsapp-stickers-android.webp'


def strip_meta_description_label(text):
    """Drop a leading 'Meta Description:' label stored in a CMS field."""
    return _META_LABEL.sub('', (text or '').strip()).strip()


def clean_canonical(request, explicit_url='', fallback_path='/', current_slug=None):
    """Absolute canonical with no query string.

    Uses the request scheme (http on runserver, https when nginx sets
    X-Forwarded-Proto). Stored canonicals that are not a real route, including
    /emoji-kitchen-iphone/, fall back to fallback_path. A missing trailing
    slash is added so the canonical matches the site's slash-terminated routes.
    """
    fallback_path = fallback_path or '/'
    if not fallback_path.startswith('/'):
        fallback_path = '/' + fallback_path
    fallback = f'{request.scheme}://{request.get_host()}{fallback_path}'

    raw = (explicit_url or '').strip()
    if not raw:
        return fallback

    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        host = parsed.netloc.split('@')[-1].split(':')[0].lower()
        current = request.get_host().split(':')[0].lower()
        if host not in _SITE_HOSTS and host != current:
            return fallback
        path = parsed.path or '/'
    else:
        path = raw.split('?', 1)[0].split('#', 1)[0]
        if not path.startswith('/'):
            path = '/' + path

    if path != '/' and not path.endswith('/'):
        path = path + '/'

    try:
        match = resolve(path)
    except Resolver404:
        return fallback

    if current_slug and match.url_name == 'blog_detail':
        if match.kwargs.get('slug') != current_slug:
            return fallback

    return f'{request.scheme}://{request.get_host()}{path}'


def _broken_webp_on_disk():
    roots = [
        Path(settings.BASE_DIR) / 'kitchen' / 'static',
        Path(settings.BASE_DIR) / 'static',
        Path(settings.MEDIA_ROOT) if settings.MEDIA_ROOT else None,
    ]
    static_root = getattr(settings, 'STATIC_ROOT', None)
    if static_root:
        roots.append(Path(static_root))
    for root in roots:
        if root and root.is_dir() and any(root.rglob(BROKEN_WEBP)):
            return True
    return False


def image_is_usable(image):
    """False for the known 404 webp (unless the file exists) and edgeone.dev hotlinks."""
    if not image:
        return False
    try:
        name = image.name or ''
        url = image.url or ''
    except Exception:
        return False
    blob = f'{name} {url}'.lower()
    if 'edgeone.dev' in blob:
        return False
    if BROKEN_WEBP in blob and not _broken_webp_on_disk():
        return False
    return True


def absolute_media_url(request, image):
    if not image_is_usable(image):
        return ''
    return request.build_absolute_uri(image.url)


def clean_post_html(html):
    """Remove broken <img> tags from stored post HTML. Other markup is kept."""
    if not html:
        return html

    webp_exists = _broken_webp_on_disk()

    def replacer(match):
        tag = match.group(0)
        src_match = _SRC_ATTR.search(tag)
        src = (src_match.group(2) if src_match else '').lower()
        if 'edgeone.dev' in src:
            return ''
        if BROKEN_WEBP in src and not webp_exists:
            return ''
        return tag

    return _IMG_TAG.sub(replacer, html)
