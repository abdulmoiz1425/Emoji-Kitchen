"""Example emoji combinations for the "Explore Combinations" section of the mixer.

Every pair here is checked against the real dataset when the page is built, so a pair that
is not in the data is dropped instead of shown. kitchen/tests.py also fails if one goes missing.
"""
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


@lru_cache(maxsize=1)
def explore_groups():
    groups = []
    for slug, label, icon, pairs in EXPLORE_CATEGORIES:
        items = []
        for first, second in pairs:
            url = views.combo_image_url(first, second)
            if url:
                items.append({'emoji1': first, 'emoji2': second, 'url': url})
        if items:
            groups.append({'slug': slug, 'label': label, 'icon': icon, 'items': items})
    return groups
