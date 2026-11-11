"""Content for the emoji-kitchen-discord blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and appends inbound links on related posts;
nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-discord'

FIELDS = {
    'title': 'How to Use Emoji Kitchen Stickers on Discord',
    'excerpt': (
        'Want Emoji Kitchen mashups on Discord? Learn how to send them as images, add them as '
        'custom server emoji or stickers, and fix paste and upload problems.'
    ),
    'seo_title': 'How to Use Emoji Kitchen Stickers on Discord',
    'seo_description': (
        'Want Emoji Kitchen mashups on Discord? Learn how to send them as images, add them as '
        'custom server emoji or stickers, and fix paste and upload problems.'
    ),
    'focus_keyword_title': 'emoji kitchen discord',
    'focus_keyword_description': 'emoji kitchen discord',
    'seo_keywords': (
        'emoji kitchen discord, emoji kitchen discord emoji, emoji mashup discord, '
        'custom discord emoji from emoji kitchen, emoji kitchen stickers discord, '
        'how to add emoji kitchen to discord server'
    ),
    'og_title': 'How to Use Emoji Kitchen Stickers on Discord',
    'og_description': (
        'Want Emoji Kitchen mashups on Discord? Learn how to send them as images, add them as '
        'custom server emoji or stickers, and fix paste and upload problems.'
    ),
    'canonical_url': 'https://emojikitchenhub.com/blog/emoji-kitchen-discord/',
}

# Related posts that should link back to this Discord guide.
INBOUND_SLUGS = (
    'how-to-save-download-emoji-kitchen-stickers',
    'emoji-kitchen-on-pc',
    'emoji-kitchen-not-working',
)

INBOUND_MARKER = f'/blog/{SLUG}/'

INBOUND_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">Want mashups in chat? See how to '
    f'<a href="{INBOUND_MARKER}">use Emoji Kitchen stickers on Discord</a>.'
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
