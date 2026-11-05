"""Content for the rewritten iPhone blog post seed command.

Rewritten HTML lives in tests_data/blog/emoji-kitchen-iphone-rewrite.html.
The legacy fixture emoji-kitchen-iphone.html remains for update_blog_posts tests. The management
command updates the existing BlogPost row for slug emoji-kitchen-iphone;
nothing is written unless --apply. Cover image is left unchanged.
"""
from pathlib import Path

SLUG = 'emoji-kitchen-iphone'

FIELDS = {
    'title': 'How to Use Emoji Kitchen on iPhone',
    'excerpt': (
        'Make sticker-style emoji mashups on iPhone in Safari or Chrome. Learn the browser '
        'workflow, when Gboard helps, how to copy or download results, and how to fix common issues.'
    ),
    'seo_title': 'How to Use Emoji Kitchen on iPhone (Browser Guide)',
    'seo_description': (
        'Browser guide for sticker-style emoji mashups on iPhone: pick two emojis, preview, then copy or download. Steps, sharing tips, and fixes.'
    ),
    'focus_keyword_title': 'emoji kitchen iphone',
    'focus_keyword_description': 'emoji kitchen iphone browser',
    'seo_keywords': 'emoji kitchen iphone, emoji mashup iphone, emoji stickers safari',
    'og_title': 'How to Use Emoji Kitchen on iPhone',
    'og_description': (
        'Browser workflow for sticker-style mashups on iPhone: pick two emojis, preview, '
        'then copy or download. Unofficial fan-made guide.'
    ),
}

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'
CONTENT_PATH = _DATA_DIR / f'{SLUG}-rewrite.html'


def content_html():
    return CONTENT_PATH.read_text(encoding='utf-8')
