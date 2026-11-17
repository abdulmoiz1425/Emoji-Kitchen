"""Shared helpers for blog seed commands.

Cover files are stored under a content-addressed name so a swapped
image changes the public URL, busts caches, and trips the existing
IndexNow filename comparison.

Inbound-link paragraphs that seed commands append to related posts are
treated as allowed suffixes. When a seed compares a post to its fixture,
those suffixes are ignored so a later seed's links are not mistaken for
body drift. If the fixture body really does need a rewrite, any existing
inbound paragraphs are preserved and reattached after the new body.
"""

import hashlib
from pathlib import Path

from django.core.files.base import ContentFile


# Exact HTML appended by seed_blog_crawl_links. Imported by that command too
# so the helper and the command share one definition.
CRAWL_LINKS_HTML = (
    '<p><span style="font-size:13pt"><span style="font-family:Arial,sans-serif">'
    '<span style="color:#000000">Looking for ready-made text sets instead of '
    'sticker mashups? Browse <a href="/emoji-combos/love/">love emoji combos</a>, '
    '<a href="/emoji-combos/funny/">funny emoji combos</a>, and '
    '<a href="/emoji-combos/pink/">pink emoji combos</a>, or copy single characters '
    'from the <a href="/emoji-keyboard/">online emoji keyboard</a>.</span></span></span></p>'
)


def inbound_link_snippets():
    """Exact HTML snippets that any blog seed may append as an inbound link."""
    # Lazy imports: the seed modules must not import this helper at module level
    # in a way that would cycle, and the crawl HTML lives in this file.
    from kitchen.blog_seed_discord import INBOUND_HTML as discord_html
    from kitchen.blog_seed_google_messages import INBOUND_HTML as google_messages_html
    from kitchen.blog_seed_instagram import INBOUND_HTML as instagram_html
    from kitchen.blog_seed_not_working import INBOUND_HTML as not_working_html
    from kitchen.blog_seed_on_pc import INBOUND_HTML as on_pc_html

    from kitchen.blog_seed_combo_links import combo_link_snippets

    return (
        discord_html,
        google_messages_html,
        instagram_html,
        not_working_html,
        on_pc_html,
        CRAWL_LINKS_HTML,
        *combo_link_snippets(),
    )


def split_allowed_inbound_suffix(content):
    """Split ``content`` into (core_body, inbound_suffix).

    The suffix is zero or more known inbound-link paragraphs at the end of
    the string, including the whitespace that separates them from the body.
    Paragraphs are recognized by their exact HTML (leading/trailing
    whitespace on the snippet itself is ignored).
    """
    original = content or ''
    core = original
    snippets = tuple(snippet.strip() for snippet in inbound_link_snippets() if snippet and snippet.strip())
    while True:
        stripped = core.rstrip()
        match = next((snippet for snippet in snippets if stripped.endswith(snippet)), None)
        if not match:
            break
        core = stripped[:-len(match)]
    suffix = original[len(core):]
    return core, suffix


def attach_inbound_suffix(fixture_html, suffix):
    """Join a fixture body with a previously extracted inbound suffix."""
    if not suffix or not suffix.strip():
        return fixture_html
    body = (fixture_html or '').rstrip()
    if suffix.startswith('\n'):
        return body + suffix
    return body + '\n' + suffix


def desired_seed_content(fixture_html, current_content=''):
    """Return the content a seed should write, preserving inbound suffixes.

    If the current core (known inbound suffixes stripped) already matches
    the fixture, ignoring trailing whitespace, the current content is
    returned unchanged so a no-op rerun does not rewrite links or bump
    ``updated_at``. Otherwise the fixture is used as the new body and any
    existing inbound-link paragraphs are reattached.
    """
    current = current_content or ''
    core, suffix = split_allowed_inbound_suffix(current)
    if current and core.rstrip() == (fixture_html or '').rstrip():
        return current
    return attach_inbound_suffix(fixture_html, suffix)


# ── Versioned featured covers ─────────────────────────────────────────────────

def cover_versioned_filename(cover_filename, image_bytes):
    """Return ``<stem>-<first 8 hex of sha256>.<ext>`` for ``cover_filename``.

    The name is a pure function of the fixture bytes, so a rerun with the
    same PNG always targets the same path and stays a no-op.
    """
    name = Path(cover_filename).name
    stem, ext = (name.rsplit('.', 1) + ['png'])[:2] if '.' in name else (name, 'png')
    digest = hashlib.sha256(image_bytes).hexdigest()[:8]
    return f'{stem}-{digest}.{ext}'


def _is_this_cover_name(stored_name, cover_filename):
    """True when ``stored_name`` is this post's unversioned or versioned cover.

    The stem must match. The extension may be the current fixture extension
    or a legacy ``.png`` / ``.webp``, so a format change still clears a stale
    ``og_image``.
    """
    if not stored_name:
        return False
    base = Path(stored_name).name
    stem = Path(cover_filename).stem
    exts = {Path(cover_filename).suffix or '.png', '.png', '.webp'}
    for ext in exts:
        if base == f'{stem}{ext}':
            return True
        prefix = f'{stem}-'
        if base.startswith(prefix) and base.endswith(ext) and len(base) == len(prefix) + 8 + len(ext):
            return True
    return False


def cover_is_current(post, image_bytes, cover_filename):
    """True when featured_image already has these bytes under the versioned name.

    Also requires ``og_image`` to be unset, or not a leftover copy of this
    cover, so a later rerun can clear a stale og_image.
    """
    if not post or not post.featured_image:
        return False
    desired = cover_versioned_filename(cover_filename, image_bytes)
    if Path(post.featured_image.name).name != desired:
        return False
    if post.og_image and _is_this_cover_name(post.og_image.name, cover_filename):
        return False
    try:
        post.featured_image.open('rb')
        try:
            current = post.featured_image.read()
        finally:
            post.featured_image.close()
    except (FileNotFoundError, OSError, ValueError):
        return False
    return current == image_bytes


def assign_versioned_cover(post, image_bytes, cover_filename):
    """Attach ``image_bytes`` as featured_image under the versioned name.

    Does not call ``post.save()``. Deletes the previous featured file and
    any ``og_image`` that is just a copy of this cover, so ``og_image_display``
    falls back to the new featured file and no orphan is left in storage.
    """
    desired = cover_versioned_filename(cover_filename, image_bytes)
    storage = post.featured_image.storage
    dest = post.featured_image.field.generate_filename(post, desired)

    if post.featured_image:
        post.featured_image.delete(save=False)
    if post.og_image and _is_this_cover_name(post.og_image.name, cover_filename):
        post.og_image.delete(save=False)
        post.og_image = None

    if storage.exists(dest):
        storage.delete(dest)
    post.featured_image.save(desired, ContentFile(image_bytes), save=False)
    return post.featured_image.name



def featured_is_current(post, image_bytes, cover_filename):
    """True when featured_image already has these bytes under the versioned name."""
    if not post or not post.featured_image:
        return False
    desired = cover_versioned_filename(cover_filename, image_bytes)
    if Path(post.featured_image.name).name != desired:
        return False
    try:
        post.featured_image.open('rb')
        try:
            current = post.featured_image.read()
        finally:
            post.featured_image.close()
    except (FileNotFoundError, OSError, ValueError):
        return False
    return current == image_bytes


def og_is_current(post, image_bytes, og_filename):
    """True when og_image already has these bytes under the versioned name."""
    if not post or not post.og_image:
        return False
    desired = cover_versioned_filename(og_filename, image_bytes)
    if Path(post.og_image.name).name != desired:
        return False
    try:
        post.og_image.open('rb')
        try:
            current = post.og_image.read()
        finally:
            post.og_image.close()
    except (FileNotFoundError, OSError, ValueError):
        return False
    return current == image_bytes


def assign_versioned_og_image(post, image_bytes, og_filename):
    """Attach ``image_bytes`` as og_image under the versioned JPEG name.

    Does not call ``post.save()`` and does not touch ``featured_image``.
    Older seeds that call ``assign_versioned_cover`` leave a ``.jpg``
    og_image alone, because leftover-copy detection only matches
    ``.png`` / ``.webp``.
    """
    desired = cover_versioned_filename(og_filename, image_bytes)
    storage = post.og_image.storage
    dest = post.og_image.field.generate_filename(post, desired)

    if post.og_image:
        post.og_image.delete(save=False)

    if storage.exists(dest):
        storage.delete(dest)
    post.og_image.save(desired, ContentFile(image_bytes), save=False)
    return post.og_image.name
