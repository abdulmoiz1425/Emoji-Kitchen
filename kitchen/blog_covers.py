"""Compressed, content-hashed blog cover fixtures.

Each file is a ~1200x675 WebP under 200 KB. Management commands attach
them with ``assign_versioned_cover`` so the public URL changes, caches
bust, and IndexNow sees a filename change.
"""

from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / 'tests_data' / 'blog'

# slug -> unversioned filename in tests_data/blog/
COVER_FILES = {
    'emoji-kitchen-on-pc': 'emoji-kitchen-on-pc-cover.webp',
    'emoji-kitchen-not-working': 'emoji-kitchen-not-working-cover.webp',
    'emoji-kitchen-samsung': 'emoji-kitchen-samsung-cover.webp',
    'emoji-kitchen-gboard': 'emoji-kitchen-gboard-cover.webp',
    'emoji-kitchen-iphone': 'emoji-kitchen-iphone-cover.webp',
    'emoji-kitchen-whatsapp': 'emoji-kitchen-whatsapp-cover.webp',
    'how-to-save-download-emoji-kitchen-stickers': (
        'how-to-save-download-emoji-kitchen-stickers-cover.webp'
    ),
    'emoji-kitchen-discord': 'emoji-kitchen-discord-cover.webp',
    'emoji-kitchen-google-messages': 'emoji-kitchen-google-messages-cover.webp',
    'emoji-kitchen-instagram': 'emoji-kitchen-instagram-cover.webp',
}

MAX_COVER_BYTES = 200 * 1024
COVER_WIDTH = 1200
COVER_HEIGHT = 675


def cover_path(slug):
    return _DATA_DIR / COVER_FILES[slug]


def cover_filename(slug):
    return COVER_FILES[slug]


def cover_bytes(slug):
    return cover_path(slug).read_bytes()
