"""Compressed, content-hashed blog cover fixtures.

Eight 16:9 covers are 1200x675 WebP. The iPhone and WhatsApp covers keep
their native 3:2 ratio at 1200x800, with no letterbox or crop. All files
are under 200 KB. A matching JPEG of the same dimensions is stored
alongside each WebP for ``og:image``. Management commands attach the
WebP as the on-page cover and the JPEG as ``og_image`` under
content-hashed names, so the public URL changes, caches bust, and
IndexNow sees a filename change.
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

# Native pixel size of the original artwork, used to keep aspect ratio.
COVER_SOURCE_SIZE = {
    'emoji-kitchen-on-pc': (1672, 941),
    'emoji-kitchen-not-working': (1672, 941),
    'emoji-kitchen-samsung': (1672, 941),
    'emoji-kitchen-gboard': (1672, 941),
    'how-to-save-download-emoji-kitchen-stickers': (1672, 941),
    'emoji-kitchen-discord': (1672, 941),
    'emoji-kitchen-google-messages': (1672, 941),
    'emoji-kitchen-instagram': (1672, 941),
    'emoji-kitchen-iphone': (1536, 1024),
    'emoji-kitchen-whatsapp': (1536, 1024),
}

MAX_COVER_BYTES = 200 * 1024
COVER_LONG_EDGE = 1200
COVER_ASPECT_TOLERANCE = 0.01


def cover_path(slug):
    return _DATA_DIR / COVER_FILES[slug]


def cover_filename(slug):
    return COVER_FILES[slug]


def cover_bytes(slug):
    return cover_path(slug).read_bytes()


def og_filename(slug):
    return Path(COVER_FILES[slug]).with_suffix('.jpg').name


def og_path(slug):
    return _DATA_DIR / og_filename(slug)


def og_bytes(slug):
    return og_path(slug).read_bytes()


def expected_cover_size(slug):
    """Return (width, height) with long edge 1200, aspect matching the source."""
    src_w, src_h = COVER_SOURCE_SIZE[slug]
    if src_w >= src_h:
        width = COVER_LONG_EDGE
        height = round(COVER_LONG_EDGE * src_h / src_w)
    else:
        height = COVER_LONG_EDGE
        width = round(COVER_LONG_EDGE * src_w / src_h)
    return width, height
