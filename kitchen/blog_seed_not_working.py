"""Content for the emoji-kitchen-not-working blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and appends inbound links on related posts;
nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-not-working'

FIELDS = {
    'title': 'Emoji Kitchen Not Working? 9 Fixes to Try',
    'excerpt': (
        'Emoji Kitchen not showing up or not pasting? Try these simple fixes for Gboard, '
        'Google Search, and the Emoji Kitchen Hub mixer on Android, iPhone, and desktop.'
    ),
    'seo_title': 'Emoji Kitchen Not Working? 9 Fixes to Try',
    'seo_description': (
        'Emoji Kitchen not showing up or not pasting? Try these simple fixes for Gboard, '
        'Google Search, and the Emoji Kitchen Hub mixer on Android, iPhone, and desktop.'
    ),
    'focus_keyword_title': 'emoji kitchen not working',
    'focus_keyword_description': 'emoji kitchen not working',
    'seo_keywords': (
        'emoji kitchen not working, emoji kitchen not showing, gboard emoji kitchen not working, '
        'emoji kitchen won\'t paste, emoji kitchen combination not available'
    ),
    'og_title': 'Emoji Kitchen Not Working? 9 Fixes to Try',
    'og_description': (
        'Nine simple fixes when Emoji Kitchen is not showing up, not pasting, or a pair is '
        'unavailable. Unofficial fan-made troubleshooting guide.'
    ),
    'canonical_url': 'https://emojikitchenhub.com/blog/emoji-kitchen-not-working/',
}

# Related posts that should link back to this troubleshooting guide.
INBOUND_SLUGS = (
    'emoji-kitchen-gboard',
    'emoji-kitchen-samsung',
    'how-to-save-download-emoji-kitchen-stickers',
)

INBOUND_MARKER = f'/blog/{SLUG}/'

INBOUND_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">If Emoji Kitchen isn\'t working, see our '
    f'<a href="{INBOUND_MARKER}">Emoji Kitchen not working fixes</a>.</span></span></span></p>'
)

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}.html'
COVER_FILENAME = f'{SLUG}-cover.png'
COVER_PATH = _DATA_DIR / COVER_FILENAME


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')


def cover_bytes():
    return COVER_PATH.read_bytes()
