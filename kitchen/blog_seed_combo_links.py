"""Internal links from blog posts to the emoji combo category pages.

Used by ``seed_combo_page_links``. Each entry is one paragraph for one post.

* ``placement`` ``'end'``: the paragraph is appended after the post body. These
  are the posts whose fixture a seed command can rewrite (Discord, iPhone, save and
  download), so the exact HTML is registered in ``blog_seed_utils`` as a known
  inbound suffix. A later re-run of those older seeds then treats it as a link,
  not as drift, and leaves the post (and its ``updated_at``) alone.
* ``placement`` ``'before:<heading>'``: the paragraph goes directly before that
  ``<h2>`` (the post's closing call to action). If the heading is not found the
  paragraph is appended at the end and the command says so.
"""

_WORD_STYLE_OPEN = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">'
)
_WORD_STYLE_CLOSE = '</span></span></span></p>'


def _word(text):
    return f'{_WORD_STYLE_OPEN}{text}{_WORD_STYLE_CLOSE}'


# slug -> (marker, placement, html)
# marker: an href that identifies "this post already links to the new page"; None means
# only the exact paragraph counts as already applied.
COMBO_LINKS = {
    'emoji-kitchen-discord': (
        '/emoji-combos/bio/',
        'end',
        '<p>Setting up your profile? Copy a ready-made set from '
        '<a href="/emoji-combos/bio/">emoji combos for bio</a>, which also works for a Discord About Me.</p>',
    ),
    'emoji-kitchen-whatsapp': (
        '/emoji-combos/birthday/',
        'before:Create Your Next WhatsApp Sticker',
        _word(
            'Need text for a status or a wish? See '
            '<a href="/emoji-combos/birthday/">birthday emoji combos</a> and '
            '<a href="/emoji-combos/friendship/">friendship emoji combos</a>.'
        ),
    ),
    'emoji-kitchen-iphone': (
        '/emoji-combos/sad/',
        'end',
        '<p>For text sets you can copy on an iPhone, try '
        '<a href="/emoji-combos/bio/">emoji combos for bio</a> or '
        '<a href="/emoji-combos/sad/">sad emoji combos</a> for a low-mood status.</p>',
    ),
    'emoji-kitchen-gboard': (
        None,
        'before:Make Your Next Gboard Emoji Mashup',
        _word(
            'Prefer text over stickers? Copy a ready-made set from '
            '<a href="/emoji-combos/">emoji combos</a> or '
            '<a href="/emoji-combos/aesthetic/">aesthetic emoji combos</a>.'
        ),
    ),
    'emoji-kitchen-samsung': (
        '/emoji-combos/christmas/',
        'before:Conclusion',
        _word(
            'Want something to paste instead of a sticker? Try '
            '<a href="/emoji-combos/cute/">cute emoji combos</a> or '
            '<a href="/emoji-combos/christmas/">Christmas emoji combos</a>.'
        ),
    ),
    'how-to-save-download-emoji-kitchen-stickers': (
        '/emoji-combos/bio/',
        'end',
        '<p>For a caption or bio, text sets are quicker: see '
        '<a href="/emoji-combos/bio/">emoji combos for bio</a>.</p>',
    ),
}

SLUGS = tuple(COMBO_LINKS)


def combo_link_snippets():
    """Exact HTML of every paragraph this seed adds (registered as known inbound suffixes)."""
    return tuple(html for _marker, _placement, html in COMBO_LINKS.values())
