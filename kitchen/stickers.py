"""Turn an Emoji Kitchen mashup into a messaging-app sticker.

The plain mashup image is a loose PNG. A sticker is a 512 x 512 file with a transparent background, the artwork centred
with a small margin, and a white die-cut outline around it. That is the format WhatsApp (static stickers, WebP, under
100 KB) and Telegram expect, so the file can be imported into a sticker-maker app as it is.

The work happens on the server because Safari on iPhone cannot create WebP files in the browser, and doing it here means
every phone gets the same file. The source image is only ever fetched from Google's Emoji Kitchen address built by
``views.combo_image_url`` from a validated pair, never from a URL the visitor supplies.
"""
import io
from functools import lru_cache

import requests
from PIL import Image, ImageChops, ImageFilter

# Bump this whenever the sticker's look changes. The download address carries it (see _mixer.html and main.js), so
# browsers that cached the old sticker for 24 hours ask for the new one instead of showing a stale file.
STICKER_VERSION = 2

STICKER_SIZE = 512
MARGIN = 20                    # transparent space between the outline and the edge of the file
OUTLINE = 10                   # width of the white outline, in pixels
EDGE = 2                       # width of the thin grey line just outside the white outline
EDGE_COLOR = (178, 184, 196)
SHADOW_OFFSET = 4              # the soft shadow sits a little below the sticker
SHADOW_BLUR = 4
SHADOW_OPACITY = 0.38
MAX_WEBP_BYTES = 100 * 1024    # WhatsApp's limit for a static sticker
WEBP_QUALITIES = (92, 86, 80, 74, 68, 60, 52, 44, 36, 28)

ALLOWED_PREFIX = 'https://www.gstatic.com/android/keyboard/emojikitchen/'
MAX_DOWNLOAD_BYTES = 3 * 1024 * 1024
MAX_SOURCE_PIXELS = 4096 * 4096
FETCH_TIMEOUT = (3, 6)         # connect, read (seconds)
FORMATS = ('webp', 'png')


class StickerError(Exception):
    """The sticker could not be made. The message is safe to log, not to show a visitor."""


def fetch_source(url):
    """Download the mashup image. Only Google's Emoji Kitchen address is ever requested."""
    if not url.startswith(ALLOWED_PREFIX) or not url.endswith('.png') or '..' in url:
        raise StickerError(f'refusing to fetch {url!r}')
    try:
        response = requests.get(url, timeout=FETCH_TIMEOUT, stream=True,
                                headers={'User-Agent': 'EmojiKitchenHub-sticker-maker'})
    except requests.RequestException as exc:
        raise StickerError(f'could not reach the image host: {exc}') from exc
    try:
        if response.status_code != 200:
            raise StickerError(f'image host answered {response.status_code}')
        if not response.headers.get('Content-Type', '').startswith('image/'):
            raise StickerError('image host did not return an image')
        body = bytearray()
        for chunk in response.iter_content(65536):
            body.extend(chunk)
            if len(body) > MAX_DOWNLOAD_BYTES:
                raise StickerError('image is larger than expected')
        return bytes(body)
    finally:
        response.close()


def build_sticker_image(source):
    """RGBA 512 x 512 sticker artwork from the bytes of a mashup image."""
    try:
        opened = Image.open(io.BytesIO(source))
        if opened.width * opened.height > MAX_SOURCE_PIXELS:
            raise StickerError('source image is too large')
        art = opened.convert('RGBA')
    except StickerError:
        raise
    except Exception as exc:                       # Pillow raises many types for damaged files
        raise StickerError(f'source is not a readable image: {exc}') from exc

    # Trim the empty border so every sticker fills the same amount of the frame.
    box = art.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    if box is None:
        raise StickerError('source image is empty')
    art = art.crop(box)

    room = STICKER_SIZE - 2 * (MARGIN + OUTLINE)
    scale = room / max(art.size)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)

    canvas = Image.new('RGBA', (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(art, ((STICKER_SIZE - art.width) // 2, (STICKER_SIZE - art.height) // 2))

    # White die-cut outline: grow the shape with a blur and a threshold, then soften the edge.
    shape = canvas.getchannel('A')
    grown = shape.filter(ImageFilter.GaussianBlur(OUTLINE / 2.15)).point(lambda v: 255 if v > 4 else 0)
    grown = grown.filter(ImageFilter.GaussianBlur(1.1))

    # A white outline vanishes on a white page, so the sticker also gets a thin grey edge and a soft shadow.
    # Without them it looks like a plain image everywhere except on a dark background.
    reach = grown.filter(ImageFilter.MaxFilter(2 * EDGE + 1))
    edge_alpha = ImageChops.subtract(reach, grown)
    shadow_alpha = (ImageChops.offset(reach, 0, SHADOW_OFFSET).filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
                    .point(lambda v: int(v * SHADOW_OPACITY)))

    sticker = Image.new('RGBA', canvas.size, (40, 44, 60, 0))
    sticker.putalpha(shadow_alpha)
    for color, alpha in ((EDGE_COLOR, edge_alpha), ((255, 255, 255), grown)):
        layer = Image.new('RGBA', canvas.size, color + (0,))
        layer.putalpha(alpha)
        sticker.alpha_composite(layer)
    sticker.alpha_composite(canvas)
    return sticker


def encode(image, fmt):
    """File bytes for the sticker. WebP is squeezed under WhatsApp's 100 KB limit."""
    if fmt not in FORMATS:
        raise StickerError(f'unknown format {fmt!r}')
    out = io.BytesIO()
    if fmt == 'png':
        image.save(out, 'PNG', optimize=True)
        return out.getvalue()
    data = b''
    for quality in WEBP_QUALITIES:
        out = io.BytesIO()
        image.save(out, 'WEBP', quality=quality, method=4)    # method 6 is about 50x slower for 1 KB less
        data = out.getvalue()
        if len(data) <= MAX_WEBP_BYTES:
            break
    return data


@lru_cache(maxsize=128)
def make_sticker(url, fmt):
    """Sticker file bytes for a mashup address. Cached, so a popular pair is only built once."""
    return encode(build_sticker_image(fetch_source(url)), fmt)
