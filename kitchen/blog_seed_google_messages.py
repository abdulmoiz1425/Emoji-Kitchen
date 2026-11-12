"""Content for the emoji-kitchen-google-messages blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and appends inbound links on related posts;
nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-google-messages'

FIELDS = {
    'title': 'How to Use Emoji Kitchen in Google Messages (Android Guide)',
    'excerpt': (
        'Learn how to send Emoji Kitchen mashups in Google Messages with Gboard, '
        'attach saved mashup images, and fix stickers that don\'t show up or send blurry.'
    ),
    'seo_title': 'How to Use Emoji Kitchen in Google Messages (Android Guide)',
    'seo_description': (
        'Learn how to send Emoji Kitchen mashups in Google Messages with Gboard, '
        'attach saved mashup images, and fix stickers that don\'t show up or send blurry.'
    ),
    'focus_keyword_title': 'emoji kitchen google messages',
    'focus_keyword_description': 'emoji kitchen google messages',
    'seo_keywords': (
        'emoji kitchen google messages, emoji kitchen in messages app, '
        'emoji mashup google messages, gboard emoji kitchen messages, '
        'emoji kitchen stickers text message, '
        'emoji kitchen not showing in google messages, '
        'how to use emoji kitchen in google messages'
    ),
    'og_title': 'How to Use Emoji Kitchen in Google Messages (Android Guide)',
    'og_description': (
        'Learn how to send Emoji Kitchen mashups in Google Messages with Gboard, '
        'attach saved mashup images, and fix stickers that don\'t show up or send blurry.'
    ),
    'canonical_url': 'https://emojikitchenhub.com/blog/emoji-kitchen-google-messages/',
}

# Related posts that should link back to this Google Messages guide.
INBOUND_SLUGS = (
    'emoji-kitchen-gboard',
    'how-to-save-download-emoji-kitchen-stickers',
    'emoji-kitchen-not-working',
    'emoji-kitchen-samsung',
)

INBOUND_MARKER = f'/blog/{SLUG}/'

INBOUND_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">Sending mashups in a text? See how to '
    f'<a href="{INBOUND_MARKER}">use Emoji Kitchen in Google Messages</a>.'
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
