"""Content for the thanksgiving-emoji-combos blog post seed command.

HTML and the featured cover live in tests_data/blog/. The management command
creates or updates the BlogPost row and attaches the WebP cover plus the JPEG
og:image; nothing is written unless --apply.
"""
from pathlib import Path

SLUG = 'thanksgiving-emoji-combos'

_DESCRIPTION = (
    'Copy and paste Thanksgiving emoji combos for texts, captions, and bios, '
    'plus fall-leaf Emoji Kitchen mashups you can try in the mixer. Free and easy.'
)

FIELDS = {
    'title': 'Thanksgiving Emoji Combos to Copy and Paste (+ Emoji Kitchen Ideas)',
    'excerpt': _DESCRIPTION,
    'seo_title': 'Thanksgiving Emoji Combos to Copy and Paste (+ Emoji Kitchen Ideas)',
    'seo_description': _DESCRIPTION,
    'focus_keyword_title': 'thanksgiving emoji combos',
    'focus_keyword_description': 'thanksgiving emoji combos copy and paste',
    'seo_keywords': (
        'thanksgiving emoji combos, thanksgiving emoji combos copy and paste, '
        'thanksgiving emojis, thanksgiving emoji text, cute thanksgiving emoji combos, '
        'thanksgiving emojis iphone, turkey emoji combo, turkey emoji copy and paste'
    ),
    'og_title': 'Thanksgiving Emoji Combos to Copy and Paste (+ Emoji Kitchen Ideas)',
    'og_description': _DESCRIPTION,
    'canonical_url': 'https://emojikitchenhub.com/blog/thanksgiving-emoji-combos/',
}

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}.html'
COVER_FILENAME = f'{SLUG}-cover.webp'
COVER_PATH = _DATA_DIR / COVER_FILENAME
OG_FILENAME = f'{SLUG}-cover.jpg'
OG_PATH = _DATA_DIR / OG_FILENAME


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')


def cover_bytes():
    return COVER_PATH.read_bytes()


def og_bytes():
    return OG_PATH.read_bytes()
