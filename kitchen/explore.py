"""Example emoji combinations for the "Explore Combinations" section of the mixer.

Every pair here is checked against the real dataset when the page is built, so a pair that
is not in the data is dropped instead of shown. kitchen/tests.py also fails if one goes missing.
"""
import unicodedata
from functools import lru_cache

from . import views

# (slug, label, icon, [(first emoji, second emoji), ...])
EXPLORE_CATEGORIES = [
    ('faces', 'Faces', '😀', [
        ('😂', '💀'), ('😍', '🔥'), ('🥰', '🌸'), ('😎', '🌈'), ('🤯', '🚀'), ('😱', '👻'),
    ]),
    ('hearts', 'Hearts', '❤️', [
        ('❤️', '🔥'), ('💙', '🌊'), ('💗', '🌸'), ('💘', '🎀'), ('💕', '🌈'), ('💔', '🌧️'),
    ]),
    ('animals', 'Animals', '🐱', [
        ('🐱', '🔥'), ('🦄', '🌈'), ('🐸', '☕'), ('🐙', '🍕'), ('🐰', '🌸'), ('🦋', '🌺'),
    ]),
    ('food', 'Food', '🍕', [
        ('🍕', '🔥'), ('🍩', '🌈'), ('🍪', '☕'), ('🍿', '🎬'), ('🧁', '🌈'), ('🍒', '🌸'),
    ]),
    ('nature', 'Nature', '🌈', [
        ('🌈', '⭐'), ('🔥', '💧'), ('🌊', '🌴'), ('🌷', '🦋'), ('🌟', '🌈'), ('🌋', '🔥'),
    ]),
]


# Unicode names that read badly in alt text, replaced with the everyday name
NAME_OVERRIDES = {
    '\u2764': 'red heart',
    '\U0001F970': 'smiling face with hearts',
    '\U0001F92F': 'exploding head',
    '\U0001F60D': 'heart-eyes face',
    '\U0001F327': 'rain cloud',
    '\U0001F30A': 'water wave',
    '\u2615': 'hot drink',
    '\u2B50': 'star',
    '\U0001F355': 'pizza',
    '\U0001F631': 'screaming face',
}


def emoji_name(char):
    """Plain-English name of an emoji, for image alt and title text."""
    base = char.replace('\ufe0f', '')
    if base in NAME_OVERRIDES:
        return NAME_OVERRIDES[base]
    return unicodedata.name(base, 'emoji').lower()


@lru_cache(maxsize=1)
def explore_groups():
    groups = []
    for slug, label, icon, pairs in EXPLORE_CATEGORIES:
        items = []
        for first, second in pairs:
            url = views.combo_image_url(first, second)
            if url:
                items.append({'emoji1': first, 'emoji2': second, 'url': url,
                              'name1': emoji_name(first), 'name2': emoji_name(second)})
        if items:
            groups.append({'slug': slug, 'label': label, 'icon': icon, 'items': items})
    return groups
