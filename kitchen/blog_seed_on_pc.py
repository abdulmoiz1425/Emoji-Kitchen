"""Content for the emoji-kitchen-on-pc blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and appends inbound links on related posts;
nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-on-pc'

FIELDS = {
    'title': 'How to Use Emoji Kitchen on PC, Mac, and Chromebook',
    'excerpt': (
        'Want Emoji Kitchen on your computer? Learn how to make, download, and share emoji '
        'mashups on Windows PC, Mac, and Chromebook using a browser, no phone needed.'
    ),
    'seo_title': 'How to Use Emoji Kitchen on PC, Mac, and Chromebook',
    'seo_description': (
        'Want Emoji Kitchen on your computer? Learn how to make, download, and share emoji '
        'mashups on Windows PC, Mac, and Chromebook using a browser, no phone needed.'
    ),
    'focus_keyword_title': 'emoji kitchen on pc',
    'focus_keyword_description': 'emoji kitchen on pc',
    'seo_keywords': (
        'emoji kitchen on pc, emoji kitchen desktop, emoji kitchen windows, emoji kitchen mac, '
        'emoji kitchen chromebook, emoji kitchen laptop, emoji mashup on computer'
    ),
    'og_title': 'How to Use Emoji Kitchen on PC, Mac, and Chromebook',
    'og_description': (
        'Want Emoji Kitchen on your computer? Learn how to make, download, and share emoji '
        'mashups on Windows PC, Mac, and Chromebook using a browser, no phone needed.'
    ),
    'canonical_url': 'https://emojikitchenhub.com/blog/emoji-kitchen-on-pc/',
}

# Related posts that should link back to this desktop guide.
INBOUND_SLUGS = (
    'how-to-save-download-emoji-kitchen-stickers',
    'emoji-kitchen-not-working',
    'emoji-kitchen-gboard',
)

INBOUND_MARKER = f'/blog/{SLUG}/'

INBOUND_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">Want mashups on your computer? See how to '
    f'<a href="{INBOUND_MARKER}">use Emoji Kitchen on PC, Mac, and Chromebook</a>.'
    '</span></span></span></p>'
)

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}.html'
COVER_FILENAME = f'{SLUG}-cover.png'
COVER_PATH = _DATA_DIR / COVER_FILENAME


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')


def cover_bytes():
    return COVER_PATH.read_bytes()
