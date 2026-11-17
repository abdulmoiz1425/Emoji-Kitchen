"""Content for the emoji-kitchen-instagram blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and appends inbound links on related posts;
nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-instagram'

_DESCRIPTION = (
    'Add Emoji Kitchen mashups to Instagram Stories, DMs, and posts on iPhone or Android. '
    'Save a mashup, add it as a photo sticker, and fix common issues.'
)

FIELDS = {
    'title': 'How to Use Emoji Kitchen on Instagram (Stories, DMs & Posts)',
    'excerpt': _DESCRIPTION,
    'seo_title': 'How to Use Emoji Kitchen on Instagram (Stories, DMs & Posts)',
    'seo_description': _DESCRIPTION,
    'focus_keyword_title': 'how to use emoji kitchen on instagram',
    'focus_keyword_description': 'emoji kitchen instagram',
    'seo_keywords': (
        'how to use emoji kitchen on instagram, emoji kitchen instagram, '
        'emoji kitchen instagram story, emoji mashup instagram, '
        'emoji kitchen stickers instagram, emoji kitchen instagram dm, '
        'emoji combos for instagram bio'
    ),
    'og_title': 'How to Use Emoji Kitchen on Instagram (Stories, DMs & Posts)',
    'og_description': _DESCRIPTION,
    'canonical_url': 'https://emojikitchenhub.com/blog/emoji-kitchen-instagram/',
}

# Related posts that should link back to this Instagram guide.
INBOUND_SLUGS = (
    'how-to-save-download-emoji-kitchen-stickers',
    'emoji-kitchen-iphone',
    'emoji-kitchen-whatsapp',
    'emoji-kitchen-gboard',
)

INBOUND_MARKER = f'/blog/{SLUG}/'

INBOUND_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">Sharing mashups on Instagram? See how to '
    f'<a href="{INBOUND_MARKER}">use Emoji Kitchen on Instagram</a>.'
    '</span></span></span></p>'
)

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}.html'
COVER_FILENAME = f'{SLUG}-cover.webp'
COVER_PATH = _DATA_DIR / COVER_FILENAME


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')


def cover_bytes():
    return COVER_PATH.read_bytes()
