"""SEO helpers for canonical URLs, share images, and stored blog HTML.

Blog rows (iPhone, Samsung, Gboard, WhatsApp) live in the production database,
not in this repo. These helpers stop bad stored values from being rendered.
"""
import html as html_lib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.urls import Resolver404, resolve

# Hosts this project actually serves. Anything else in a stored canonical is ignored.
CANONICAL_HOST = 'emojikitchenhub.com'
CANONICAL_SCHEME = 'https'
_SITE_HOSTS = {CANONICAL_HOST, f'www.{CANONICAL_HOST}'}


def absolute_blog_canonical(slug):
    """Public canonical for a blog post: https://emojikitchenhub.com/blog/<slug>/."""
    from django.urls import reverse

    return f'{CANONICAL_SCHEME}://{CANONICAL_HOST}{reverse("blog_detail", kwargs={"slug": slug})}'


def absolute_site_url(path):
    """Public absolute URL for a site path, always https on the canonical host."""
    if not path.startswith('/'):
        path = '/' + path
    return f'{CANONICAL_SCHEME}://{CANONICAL_HOST}{path}'


_META_LABEL = re.compile(r'^\s*meta description:\s*', re.IGNORECASE)
_IMG_TAG = re.compile(r'<img\b[^>]*?>', re.IGNORECASE | re.DOTALL)
_SRC_ATTR = re.compile(r"""\bsrc\s*=\s*(['"])(.*?)\1""", re.IGNORECASE | re.DOTALL)

BROKEN_WEBP = 'emoji-kitchen-whatsapp-stickers-android.webp'


def strip_meta_description_label(text):
    """Drop a leading 'Meta Description:' label stored in a CMS field."""
    return _META_LABEL.sub('', (text or '').strip()).strip()


def clean_canonical(request, explicit_url='', fallback_path='/', current_slug=None):
    """Absolute canonical with no query string.

    Blog posts always use the public https://emojikitchenhub.com host so the
    tag matches the sitemap, even when the request is http, www, or a
    local host. Stored canonicals are used only when they resolve to this
    same post (blog_detail with current_slug). Values such as the old
    top-level address /emoji-kitchen-iphone/, another post, or the home
    page fall back to fallback_path. A missing trailing slash is added so
    the canonical matches the site's slash-terminated routes.
    """
    fallback_path = fallback_path or '/'
    if not fallback_path.startswith('/'):
        fallback_path = '/' + fallback_path
    fallback = f'{CANONICAL_SCHEME}://{CANONICAL_HOST}{fallback_path}'

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

    if current_slug:
        # Only this post's own /blog/<slug>/ URL is acceptable. Legacy
        # redirects, the homepage, and other site routes are ignored.
        if match.url_name != 'blog_detail' or match.kwargs.get('slug') != current_slug:
            return fallback
    elif (match.url_name or '').startswith('legacy_'):
        # The old top-level article addresses (/emoji-kitchen-iphone/) now
        # redirect to /blog/<slug>/, so a stored canonical that points at
        # one is a redirect target, not the page itself.
        return fallback

    return f'{CANONICAL_SCHEME}://{CANONICAL_HOST}{path}'


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


# ── Structured data ──────────────────────────────────────────────────────────

def json_ld(data):
    """JSON for a <script type="application/ld+json"> tag; '<' is escaped so the tag cannot be closed early."""
    return json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')


def faq_json_ld(faqs):
    """FAQPage data for a list of {'question', 'answer'} dicts (the questions shown on the page)."""
    entities = [
        {'@type': 'Question', 'name': item['question'],
         'acceptedAnswer': {'@type': 'Answer', 'text': item['answer']}}
        for item in faqs
    ]
    return json_ld({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': entities})


_H2 = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
_H3 = re.compile(r'<h3\b[^>]*>(.*?)</h3>', re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r'<[^>]+>')
_HR = re.compile(r'<hr\b[^>]*/?>', re.IGNORECASE)
_H1_OR_H2 = re.compile(r'<h[12]\b', re.IGNORECASE)
_FAQ_BLOCK = re.compile(
    r'<(p|aside|footer|blockquote)\b[^>]*>.*?</\1>',
    re.IGNORECASE | re.DOTALL,
)
_TRADEMARK = re.compile(r'\btrademarks?\b', re.IGNORECASE)
_AFFILIATION = re.compile(r'\bnot\s+(?:run\s+by\s+or\s+)?affiliated\b', re.IGNORECASE)
_SITE_STATUS = re.compile(r'\bindependent\b|\bfan-?made\b|\bunofficial\b', re.IGNORECASE)
_ITALIC_WRAP = re.compile(r'^<(em|i)\b[^>]*>.*</\1>$', re.IGNORECASE | re.DOTALL)
_DISCLAIMER_ATTR = re.compile(
    r'''\b(?:class|id)\s*=\s*(['"])[^'"]*\bdisclaimer\b''',
    re.IGNORECASE,
)


def _plain(fragment):
    return re.sub(r'\s+', ' ', html_lib.unescape(_TAG.sub(' ', fragment))).strip()


def _strip_outer_tag(block):
    return re.sub(r'^<[^>]+>\s*|\s*</[^>]+>$', '', (block or '').strip(), flags=re.DOTALL)


def _is_wholly_italic(block):
    """True when the block is typographically a footer note (italic or <em>/<i>)."""
    if re.search(r'font-style\s*:\s*italic', block or '', re.IGNORECASE):
        return True
    return bool(_ITALIC_WRAP.fullmatch(_strip_outer_tag(block).strip()))


def _is_disclaimer_block(block):
    """True for a legal/affiliation footer, not a regular FAQ answer paragraph.

    Detection uses markup (italic/em, footer/aside, a disclaimer class) plus
    affiliation or trademark language. It does not depend on one exact sentence,
    so a genuine answer that says the site is unofficial still counts as an answer.
    """
    text = _plain(block)
    if not text:
        return False
    # The footer line on current posts: affiliation language plus a trademark notice.
    if _TRADEMARK.search(text) and _AFFILIATION.search(text):
        return True
    tagged = bool(re.match(r'<(aside|footer)\b', (block or '').strip(), re.IGNORECASE)) or bool(
        _DISCLAIMER_ATTR.search(block or '')
    )
    if (_is_wholly_italic(block) or tagged) and _AFFILIATION.search(text) and _SITE_STATUS.search(text):
        return True
    return False


def _inbound_markers():
    """Exact inbound-link paragraphs that seeds append after a post body."""
    from kitchen.blog_seed_utils import inbound_link_snippets

    return tuple(snippet.strip() for snippet in inbound_link_snippets() if snippet and snippet.strip())


def _faq_section(content, start):
    """HTML after the FAQ heading, cut at the first section boundary.

    The section ends at a following <h1> or <h2>, an <hr>, a disclaimer block,
    or a known inbound-link paragraph. Multi-paragraph answers before that
    boundary are kept.
    """
    rest = content[start:]
    cuts = []
    heading = _H1_OR_H2.search(rest)
    if heading:
        cuts.append(heading.start())
    rule = _HR.search(rest)
    if rule:
        cuts.append(rule.start())
    for snippet in _inbound_markers():
        index = rest.find(snippet)
        if index != -1:
            cuts.append(index)
    for block in _FAQ_BLOCK.finditer(rest):
        if _is_disclaimer_block(block.group(0)):
            cuts.append(block.start())
            break
    end = min(cuts) if cuts else len(rest)
    return rest[:end]


def faq_pairs_from_html(content):
    """(question, answer) pairs from a post's visible FAQ section.

    The section is the <h3>s under the <h2> whose text is FAQ or FAQs. FAQPage
    JSON-LD is built from these pairs at render time; nothing is stored on the
    post. The section stops at a heading of the same or higher level, an <hr>,
    a disclaimer block, or a known inbound-link paragraph.
    """
    content = content or ''
    for heading in _H2.finditer(content):
        if not re.search(r'\bFAQs?\b', _plain(heading.group(1)), re.IGNORECASE):
            continue
        section = _faq_section(content, heading.end())
        questions = list(_H3.finditer(section))
        pairs = []
        for i, question in enumerate(questions):
            end = questions[i + 1].start() if i + 1 < len(questions) else len(section)
            q, a = _plain(question.group(1)), _plain(section[question.end():end])
            if q and a:
                pairs.append((q, a))
        return pairs
    return []


def article_json_ld(post, page_url, site_url, image_url=''):
    """BlogPosting data built only from fields the page already shows."""
    data = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'headline': post.title[:110],
        'description': post.meta_description,
        'datePublished': post.publish_date.isoformat(),
        'dateModified': (post.updated_at or post.publish_date).isoformat(),
        'author': {'@type': 'Organization', 'name': post.author},
        'publisher': {'@type': 'Organization', 'name': 'Emoji Kitchen Hub', 'url': site_url},
        'mainEntityOfPage': {'@type': 'WebPage', '@id': page_url},
        'inLanguage': 'en',
    }
    if image_url:
        data['image'] = [image_url]
    return json_ld(data)

