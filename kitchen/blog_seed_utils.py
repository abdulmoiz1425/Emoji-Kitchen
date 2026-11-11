"""Shared helpers for blog seed commands.

Inbound-link paragraphs that seed commands append to related posts are
treated as allowed suffixes. When a seed compares a post to its fixture,
those suffixes are ignored so a later seed's links are not mistaken for
body drift. If the fixture body really does need a rewrite, any existing
inbound paragraphs are preserved and reattached after the new body.
"""

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
    from kitchen.blog_seed_not_working import INBOUND_HTML as not_working_html
    from kitchen.blog_seed_on_pc import INBOUND_HTML as on_pc_html

    return (discord_html, not_working_html, on_pc_html, CRAWL_LINKS_HTML)


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
