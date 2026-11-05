"""Content for the save/download stickers blog post seed command.

HTML and the featured cover live in tests_data/blog/ alongside the other post
fixtures. The management command creates or updates the BlogPost row; nothing
is written unless --apply.
"""
from pathlib import Path

SLUG = 'how-to-save-download-emoji-kitchen-stickers'

FIELDS = {
    'title': 'How to Save and Download Emoji Kitchen Stickers',
    'excerpt': (
        'Learn how to save and download sticker-style mashups as images, what to do when '
        'clipboard paste fails, and how to share them in chats or social apps on phone or desktop.'
    ),
    'seo_title': 'How to Save and Download Emoji Kitchen Stickers',
    'seo_description': (
        'Learn how to save and download Emoji Kitchen stickers as images, copy mashups when '
        'paste fails, and share them in chats or social apps on phone or desktop.'
    ),
    'focus_keyword_title': 'save download emoji kitchen stickers',
    'focus_keyword_description': 'save download emoji kitchen stickers',
    'seo_keywords': 'save emoji kitchen stickers, download emoji mashup, emoji kitchen png',
    'og_title': 'How to Save and Download Emoji Kitchen Stickers',
    'og_description': (
        'Save sticker-style mashups as images, recover when paste fails, and share them in '
        'chats or social apps on phone or desktop.'
    ),
}

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}.html'
COVER_FILENAME = f'{SLUG}-cover.png'
COVER_PATH = _DATA_DIR / COVER_FILENAME


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')


def cover_bytes():
    return COVER_PATH.read_bytes()
