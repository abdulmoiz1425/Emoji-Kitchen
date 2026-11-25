"""Site-wide search over every copyable emoji set.

The older pages keep their sets in an inline ``const COMBOS = [...]`` array (see combo_counts.py),
the data-driven category pages live in combo_pages.py and the keyword pages in combo_tags.py.
This module reads all three, so one search box finds a set whichever page it lives on.
"""
import re
from functools import lru_cache

from django.urls import reverse

from .combo_counts import _ARRAY, TEMPLATE_DIR
from .combo_pages import COMBO_PAGES
from .combo_tags import TAG_PAGES

MAX_QUERY_LENGTH = 60
DEFAULT_LIMIT = 96

# {cat:'popular', label:'Sweet message', emoji:'❤️🥰✨'}. A value may be single- or double-quoted
# (label:"Valentine's") and may contain escaped quotes, so each value is two alternative groups.
_QUOTED = r"""(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")"""
_ENTRY = re.compile(rf"\{{\s*cat:\s*{_QUOTED}\s*,\s*label:\s*{_QUOTED}\s*,\s*emoji:\s*{_QUOTED}\s*\}}")

# (template file, url name, page label) for the pages whose sets live in a template.
_TEMPLATE_PAGES = (
    ('ready_made_emoji_combo.html', 'ready_made_emoji_combo', 'Ready Made'),
    ('emoji_combos_love.html', 'emoji_combos_love', 'Love'),
    ('emoji_combos_cute.html', 'emoji_combos_cute', 'Cute'),
    ('emoji_combos_aesthetic.html', 'emoji_combos_aesthetic', 'Aesthetic'),
    ('emoji_combos_funny.html', 'emoji_combos_funny', 'Funny'),
    ('emoji_combos_pink.html', 'emoji_combos_pink', 'Pink'),
)


def _unescape(text):
    return text.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')


def _template_entries(template_name):
    source = (TEMPLATE_DIR / template_name).read_text(encoding='utf-8')
    match = _ARRAY.search(source)
    if not match:
        return []
    entries = []
    for found in _ENTRY.findall(match.group(1)):
        # six groups: (single, double) for each of cat, label and emoji; exactly one of each pair is set
        cat, label, emoji = (_unescape(single or double) for single, double in zip(found[0::2], found[1::2]))
        entries.append((cat, label, emoji))
    return entries


@lru_cache(maxsize=1)
def all_sets():
    """Every distinct set once, with the page it lives on. The first page that owns a set wins."""
    rows, seen = [], set()

    def add(emoji, label, cat, page_label, url):
        if emoji in seen:
            return
        seen.add(emoji)
        rows.append({'emoji': emoji, 'label': label, 'cat': cat, 'page': page_label, 'url': url})

    for slug, page in TAG_PAGES.items():
        url = reverse('emoji_combos_tag', kwargs={'slug': slug})
        for cat, label, emoji in page['combos']:
            add(emoji, label, cat, page['label'], url)
    for slug, page in COMBO_PAGES.items():
        url = reverse(f'emoji_combos_{slug}')
        for cat, label, emoji in page['combos']:
            add(emoji, label, cat, page['label'], url)
    for template, url_name, page_label in _TEMPLATE_PAGES:
        url = reverse(url_name)
        for cat, label, emoji in _template_entries(template):
            add(emoji, label, cat, page_label, url)
    return rows


def clean_query(raw):
    return ' '.join((raw or '').split())[:MAX_QUERY_LENGTH]


def search_sets(query, limit=DEFAULT_LIMIT):
    """(results, total_matches). Every word of the query must appear in the set's label, group,
    page name or emoji string, so 'cat sleepy' and a pasted emoji both work."""
    terms = clean_query(query).lower().split()
    if not terms:
        return [], 0
    matches = []
    for row in all_sets():
        haystack = f"{row['label']} {row['cat']} {row['page']} {row['emoji']}".lower()
        if all(term in haystack for term in terms):
            matches.append(row)
    return matches[:limit], len(matches)


def matching_tag_pages(query):
    """Keyword pages whose name matches the query, shown above the results as quick links."""
    term = clean_query(query).lower()
    if not term:
        return []
    found = []
    for slug, page in TAG_PAGES.items():
        if term in page['label'].lower() or term in slug:
            found.append({'label': page['label'], 'icon': page['badge'].split(' ', 1)[0],
                          'href': reverse('emoji_combos_tag', kwargs={'slug': slug})})
    return found
