"""Counts of the copyable sets that the older hand-written combo pages ship in their inline JS.

Those pages keep their sets in a ``const COMBOS = [...]`` array inside the template.
Any number shown in a title, meta description or heading is computed from that
array at render time (and checked by tests), so the copy cannot drift from the data.
"""
import re
from functools import lru_cache
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates' / 'kitchen'
_ARRAY = re.compile(r'const COMBOS = \[(.*?)\n\s*\];', re.DOTALL)
_EMOJI = re.compile(r"emoji:\s*'([^']*)'")


@lru_cache(maxsize=None)
def template_sets(template_name):
    """Every set string in the page's COMBOS array, in order (duplicates included)."""
    source = (TEMPLATE_DIR / template_name).read_text(encoding='utf-8')
    match = _ARRAY.search(source)
    if not match:
        raise ValueError(f'{template_name} has no COMBOS array')
    return tuple(_EMOJI.findall(match.group(1)))


def distinct_set_count(template_name):
    """Number of different sets on the page (the number shown to visitors)."""
    return len(set(template_sets(template_name)))


def floor_hundreds(count):
    """Largest multiple of 100 not above ``count`` (0 when the count is under 100), for '100+' style claims."""
    return (count // 100) * 100
