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


# Title and alt text for the Explore thumbnails, supplied by the SEO team and used exactly as written.
# A pair that is not listed (cupcake + rainbow) and the fire + droplet alt keep the generated wording.
IMAGE_TEXT = {
    ('😂', '💀'): ('Laughing Face and Skull Emoji Mashup', 'Light gray skull emoji with closed laughing eyes and large blue tears of joy.'),
    ('😍', '🔥'): ('Heart Eyes and Fire Emoji Mashup', 'Smiling yellow emoji face with two flames replacing its heart-shaped eyes.'),
    ('🥰', '🌸'): ('Smiling Face with Cherry Blossom Emoji Mashup', 'Smiling yellow face decorated with three pink cherry blossom flowers.'),
    ('😎', '🌈'): ('Sunglasses and Rainbow Emoji Mashup', 'Smiling face wearing black sunglasses beneath a colorful rainbow with two yellow hearts.'),
    ('🤯', '🚀'): ('Exploding Head and Rocket Emoji Mashup', 'Cartoon rocket with wide eyes, red fins, yellow exhaust, and a colorful explosion above its nose.'),
    ('😱', '👻'): ('Screaming Face and Ghost Emoji Mashup', 'Pale blue and white ghost emoji with wide eyes and an open brown mouth.'),
    ('❤️', '🔥'): ('Heart and Fire Emoji Mashup', 'Large red and orange flame forming a heart-shaped fire emoji design.'),
    ('💙', '🌊'): ('Blue Water Wave Emoji Mashup', 'Large blue ocean wave emoji with light blue foam curling over a dark blue wave.'),
    ('💗', '🌸'): ('Growing Heart and Cherry Blossom Emoji Mashup', 'Layered pink growing heart emoji with a pink cherry blossom flower in the center.'),
    ('💘', '🎀'): ('Heart and Ribbon Bow Emoji Mashup', 'Large red ribbon bow surrounded by multiple floating pink heart emojis.'),
    ('💕', '🌈'): ('Two Hearts and Rainbow Emoji Mashup', 'Two pink heart emojis floating above a colorful rainbow with white clouds.'),
    ('💔', '🌧️'): ('Broken Heart and Rain Cloud Emoji Mashup', 'Broken red heart beneath a gray rain cloud with blue raindrops falling onto it.'),
    ('🐱', '🔥'): ('Cat Face and Fire Emoji Kitchen Mashup', 'Yellow-orange cat face with flaming ears, a tall flame above its head, and fire in its eyes.'),
    ('🦄', '🌈'): ('Unicorn and Rainbow Emoji Mashup', 'Gray unicorn head with a rainbow-colored mane and horn beside a colorful rainbow.'),
    ('🐸', '☕'): ('Frog in a Coffee Cup Emoji Mashup', 'Cute green frog sitting in a white cup filled with a brown hot drink and rising steam.'),
    ('🐙', '🍕'): ('Octopus and Pizza Emoji Mashup', 'Round pepperoni pizza shaped like an orange octopus with eight curved tentacles.'),
    ('🐰', '🌸'): ('Rabbit and Cherry Blossom Emoji Mashup', 'Gray rabbit face with pink inner ears, black eyes, whiskers, and a pink cherry blossom on one ear.'),
    ('🦋', '🌺'): ('Butterfly and Hibiscus Emoji Mashup', 'Butterfly and hibiscus flower emoji combination with colorful wings and tropical floral details.'),
    ('🍕', '🔥'): ('Pizza and Fire Emoji Mashup', 'Pizza and fire emoji combination featuring a pizza surrounded by bright flames.'),
    ('🍩', '🌈'): ('Doughnut and Rainbow Emoji Mashup', 'Doughnut and rainbow emoji mashup with colorful icing and rainbow details.'),
    ('🍪', '☕'): ('Cookie and Hot Drink Emoji Mashup', 'Chocolate chip cookie and steaming hot drink combined into a sweet emoji mashup.'),
    ('🍿', '🎬'): ('Popcorn and Movie Clapperboard Emoji Mashup', 'Popcorn and movie clapperboard emoji combination for a fun cinema-themed sticker.'),
    ('🍒', '🌸'): ('Cherries and Cherry Blossom Emoji Mashup', 'Red cherries combined with delicate pink cherry blossom flowers.'),
    ('🌈', '⭐'): ('Rainbow and Star Emoji Mashup', 'Yellow star and colorful rainbow emoji combination with bright decorative details.'),
    ('🔥', '💧'): ('Fire and Water Droplet Emoji Mashup', None),
    ('🌊', '🌴'): ('Ocean Wave and Palm Tree Emoji Mashup', 'Blue ocean wave and green palm tree emoji combination with a tropical beach theme.'),
    ('🌷', '🦋'): ('Tulip and Butterfly Emoji Mashup', 'Pink tulip and butterfly emoji combination with colorful floral and wing details.'),
    ('🌟', '🌈'): ('Glowing Star and Rainbow Emoji Mashup', 'Glowing yellow star combined with a rainbow emoji and colorful decorative dots.'),
    ('🌋', '🔥'): ('Volcano and Fire Emoji Mashup', 'Erupting volcano emoji combined with fire, showing glowing lava and rising flames.'),
}

@lru_cache(maxsize=1)
def explore_groups():
    groups = []
    for slug, label, icon, pairs in EXPLORE_CATEGORIES:
        items = []
        for first, second in pairs:
            url = views.combo_image_url(first, second)
            if url:
                name1, name2 = emoji_name(first), emoji_name(second)
                title, alt = IMAGE_TEXT.get((first, second), (None, None))
                items.append({'emoji1': first, 'emoji2': second, 'url': url, 'name1': name1, 'name2': name2,
                              'title': title or f'{name1.capitalize()} + {name2} emoji mashup',
                              'alt': alt or f'{name1.capitalize()} and {name2} emoji mashup sticker'})
        if items:
            groups.append({'slug': slug, 'label': label, 'icon': icon, 'items': items})
    return groups
