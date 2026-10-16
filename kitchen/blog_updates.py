"""Helpers for rewriting the stored HTML of blog posts section by section.

The posts were pasted from a word processor, so their HTML is full of nested <span> styling.
Everything here works on whole top-level blocks (headings, paragraphs, lists, tables), never on
individual words, so the styling inside untouched blocks is left exactly as it is.
"""
import re
from html import unescape
from html.parser import HTMLParser

BLOCK_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'table', 'blockquote', 'div', 'pre'}


class BlockError(Exception):
    """The HTML is not in a shape the updater understands; nothing should be changed."""


def norm(text):
    """Comparable form of a heading or sentence (case, curly quotes, spacing, trailing punctuation)."""
    text = unescape(re.sub(r'<[^>]+>', ' ', text or ''))
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    text = text.replace(' ', ' ')
    return ' '.join(text.split()).lower().rstrip(' :?.!')


def plain(html):
    """Readable text of an HTML fragment."""
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', html)).replace(' ', ' ').split())


class Block:
    def __init__(self, tag, html):
        self.tag = tag
        self.html = html

    @property
    def text(self):
        return plain(self.html)

    def is_heading(self, level=None):
        return self.tag in ('h2', 'h3') if level is None else self.tag == level

    def __repr__(self):
        return f'<{self.tag}> {self.text[:60]}'


class _Splitter(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = [0]
        for match in re.finditer('\n', source):
            self.line_starts.append(match.end())
        self.depth = 0
        self.top_tag = None
        self.start = 0
        self.spans = []

    def _pos(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            if self.depth == 0:
                self.top_tag = tag
                self.start = self._pos()
            if tag == self.top_tag or self.depth > 0:
                self.depth += 1

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS and self.depth > 0:
            self.depth -= 1
            if self.depth == 0:
                end = self._pos() + len(f'</{tag}>')
                self.spans.append((self.top_tag, self.start, end))
                self.top_tag = None


def split_blocks(source):
    """Return the top-level blocks of `source`. Raises BlockError if text sits outside any block."""
    splitter = _Splitter(source)
    splitter.feed(source)
    splitter.close()
    blocks, cursor = [], 0
    for tag, start, end in splitter.spans:
        stray = source[cursor:start]
        if stray.strip():
            raise BlockError(f'text outside any block near: {plain(stray)[:80]!r}')
        blocks.append(Block(tag, source[start:end]))
        cursor = end
    if source[cursor:].strip():
        raise BlockError(f'text after the last block: {plain(source[cursor:])[:80]!r}')
    return blocks


def join_blocks(blocks):
    return '\n\n'.join(block.html for block in blocks) + '\n'


# ── Building blocks of new HTML ──────────────────────────────────────────────

def _esc(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def h2(text):
    return Block('h2', f'<h2>{_esc(text)}</h2>')


def p(text):
    return Block('p', f'<p>{_esc(text)}</p>')


def quick(text):
    return Block('p', f'<p><strong>Quick answer:</strong> {_esc(text)}</p>')


def ol(items):
    return Block('ol', '<ol>\n' + '\n'.join(f'<li>{_esc(i)}</li>' for i in items) + '\n</ol>')


def links(items):
    """A list of (text, path) pairs as clickable links."""
    return Block('ul', '<ul>\n' + '\n'.join(f'<li><a href="{path}">{_esc(text)}</a></li>' for text, path in items) + '\n</ul>')


# ── Operations on a post's blocks. Each returns (blocks, note) or raises BlockError. ────

def _starts_with(block, label):
    return norm(block.text).startswith(label)


def _is_keeper(block):
    """Blocks at the very end of a section that must survive a rewrite of that section."""
    return block.text == '' or _starts_with(block, 'editorial note')


def _find_heading(blocks, heading, tags=('h2',)):
    hits = [i for i, b in enumerate(blocks) if b.tag in tags and norm(b.text) == norm(heading)]
    return hits


def replace_intro(blocks, lead, new_blocks):
    """Replace the opening paragraphs and the quick-answer paragraph (everything between the
    `lead` blocks, such as a title line, and the first H2 after them)."""
    if len(blocks) <= lead:
        raise BlockError('post is shorter than expected')
    if blocks[lead].html == new_blocks[0].html:
        return blocks, 'already applied'
    end = next((i for i in range(lead, len(blocks)) if blocks[i].tag == 'h2'), None)
    if end is None or end == lead:
        raise BlockError('could not find where the introduction ends')
    region = blocks[lead:end]
    if not any(_starts_with(b, 'quick answer') for b in region):
        raise BlockError('the introduction region has no "Quick answer" paragraph, so it is not the right region')
    if any(b.tag != 'p' for b in region):
        raise BlockError('the introduction region contains something other than paragraphs')
    return blocks[:lead] + new_blocks + blocks[end:], f'replaced {len(region)} block(s) with {len(new_blocks)}'


def replace_section(blocks, old_heading, new_blocks):
    """Replace a whole section (its heading and everything up to the next H2), keeping any trailing
    empty paragraph or editorial note. `new_blocks[0]` is the new heading."""
    new_heading = new_blocks[0].text
    if _find_heading(blocks, new_heading) and not _find_heading(blocks, old_heading):
        return blocks, 'already applied'
    hits = _find_heading(blocks, old_heading)
    if len(hits) != 1:
        raise BlockError(f'heading "{old_heading}" found {len(hits)} times (expected exactly 1)')
    i = hits[0]
    j = next((k for k in range(i + 1, len(blocks)) if blocks[k].tag == 'h2'), len(blocks))
    while j - 1 > i and _is_keeper(blocks[j - 1]):
        j -= 1
    return blocks[:i] + new_blocks + blocks[j:], f'replaced {j - i} block(s) with {len(new_blocks)}'


def replace_under_heading(blocks, heading, first, count, new_blocks):
    """Replace `count` blocks that start `first` blocks after a heading (the heading itself stays)."""
    hits = _find_heading(blocks, heading)
    if len(hits) != 1:
        raise BlockError(f'heading "{heading}" found {len(hits)} times (expected exactly 1)')
    start = hits[0] + 1 + first
    end = start + count
    if blocks[start].html == new_blocks[0].html:
        return blocks, 'already applied'
    target = blocks[start:end]
    if len(target) != count or any(b.tag != 'p' for b in target):
        raise BlockError(f'expected {count} paragraph(s) under "{heading}"')
    return blocks[:start] + new_blocks + blocks[end:], f'replaced {count} paragraph(s) with {len(new_blocks)}'


def replace_paragraph_containing(blocks, heading, needle, new_block):
    hits = _find_heading(blocks, heading)
    if len(hits) != 1:
        raise BlockError(f'heading "{heading}" found {len(hits)} times (expected exactly 1)')
    i = hits[0]
    j = next((k for k in range(i + 1, len(blocks)) if blocks[k].tag == 'h2'), len(blocks))
    if any(b.html == new_block.html for b in blocks[i:j]):
        return blocks, 'already applied'
    found = [k for k in range(i + 1, j) if blocks[k].tag == 'p' and norm(needle) in norm(blocks[k].text)]
    if len(found) != 1:
        raise BlockError(f'paragraph containing "{needle}" found {len(found)} times (expected exactly 1)')
    return blocks[:found[0]] + [new_block] + blocks[found[0] + 1:], 'replaced 1 paragraph'


def rename_toc_entry(blocks, old, new):
    """Rename one entry of the plain-text table of contents (a list right after the "Table of Contents" heading)."""
    hits = _find_heading(blocks, 'Table of Contents')
    if len(hits) != 1 or hits[0] + 1 >= len(blocks) or blocks[hits[0] + 1].tag != 'ol':
        raise BlockError('table of contents not found')
    toc = blocks[hits[0] + 1]
    if new in toc.text and old not in toc.text:
        return blocks, 'already applied'
    if toc.html.count(old) != 1:
        raise BlockError(f'table of contents entry "{old}" not found as plain text')
    blocks = list(blocks)
    blocks[hits[0] + 1] = Block('ol', toc.html.replace(old, new))
    return blocks, 'renamed 1 entry'


# ── Planning an update for one post ──────────────────────────────────────────

FIELDS = ('title', 'excerpt', 'seo_title', 'seo_description')


class PostPlan:
    """What would change for one post. Nothing is saved here."""

    def __init__(self, slug):
        self.slug = slug
        self.field_changes = {}      # field -> (old, new)
        self.operations = []         # (name, status, note)
        self.new_content = None
        self.error = None
        self.old_words = self.new_words = 0

    @property
    def ok(self):
        return self.error is None


def plan_post(slug, current, update):
    """`current` is a dict with the post's fields and content; `update` is its entry in POST_UPDATES."""
    plan = PostPlan(slug)
    for field in FIELDS:
        new = update['fields'][field]
        if (current.get(field) or '') != new:
            plan.field_changes[field] = (current.get(field) or '', new)
    try:
        blocks = split_blocks(current['content'])
    except BlockError as exc:
        plan.error = f'could not read the article HTML: {exc}'
        return plan
    plan.old_words = len(plain(current['content']).split())
    for name, operation in update['operations']:
        try:
            blocks, note = operation(blocks)
        except BlockError as exc:
            plan.operations.append((name, 'FAILED', str(exc)))
            plan.error = f'"{name}": {exc}'
            return plan
        plan.operations.append((name, 'already done' if note == 'already applied' else 'will change', note))
    plan.new_content = join_blocks(blocks)
    plan.new_words = len(plain(plan.new_content).split())
    return plan
