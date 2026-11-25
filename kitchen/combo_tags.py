"""Keyword (tag) pages for emoji combos: /emoji-combos/<tag>/.

Each tag page has the same shape as an entry in ``combo_pages.COMBO_PAGES`` (copyable sets, an
editorial section, FAQs, six Emoji Kitchen mashup pairs and the SEO strings) so it renders through
the same ``emoji_combos_category.html`` template. The tag pages are kept apart from ``COMBO_PAGES``
so the older category pages and their tests are untouched.

All sets and copy are original. No number is written into the title, meta, H1 or intro: counts are
derived from the data at render time. Mashup pairs are verified against kitchen/data/emoji_combos.json
by the test suite, and the sets on a page are unique within that page.
"""

# Url names of the pages that already own a slug, so a tag can never shadow one of them.
RESERVED_SLUGS = frozenset({
    'love', 'cute', 'aesthetic', 'funny', 'pink', 'birthday', 'sad', 'friendship', 'bio', 'dark',
    'christmas', 'search', 'mood', 'tag', 'tags',
})

MASHUP_NOTE = 'Mashups are pictures, so send them as an image or sticker rather than pasting them as text.'


def _meta(label):
    low = label.lower()
    first = (f'Copy and paste {low} emoji combos for bios, captions and chats. Tap Copy on any set, '
             'or turn two emojis into a sticker with Emoji Kitchen.')
    if 140 <= len(first) <= 155:
        return first
    second = (f'Copy and paste {low} emoji combos for bios, captions, comments and chats. Tap Copy on any set, '
              'or turn two emojis into a sticker with Emoji Kitchen.')
    if 140 <= len(second) <= 155:
        return second
    third = (f'Copy and paste {low} emoji combos for bios and captions. Tap Copy on any set, '
             'or turn two emojis into a sticker with Emoji Kitchen.')
    return third


def _page(slug, label, icon, intro, filters, combos, section, faqs, mashups, siblings):
    """Build the full page dict (same keys as COMBO_PAGES entries) from the per-tag essentials."""
    links = ', '.join(
        f'<a href="/emoji-combos/{s}/">{name.lower()} emoji combos</a>' for s, name in siblings
    )
    return {
        'slug': slug,
        'label': label,
        'badge': f'{icon} {label} Emoji Combos',
        'title': f'{label} Emoji Combos to Copy & Paste',
        'meta': _meta(label),
        'h1': f'{label} Emoji Combos to Copy and Paste',
        'intro': intro,
        'filters': filters,
        'combos': combos,
        'sections': [section],
        'mashups': mashups,
        'mashup_note': MASHUP_NOTE,
        'faqs': faqs,
        'siblings': siblings,
        'siblings_cta': f'Looking for something nearby? Browse {links}.',
    }


TAG_PAGES = {}


def _add(*args, **kwargs):
    page = _page(*args, **kwargs)
    TAG_PAGES[page['slug']] = page


_add(
    'adorable', 'Adorable', '🥹',
    ['Adorable emoji combos are the ones that make people say aww. They lean on tiny animals, soft faces, '
     'sweet food and gentle colors, so a message feels warm without a single extra word.',
     'The sets below are grouped by what makes them adorable: little pets, sweet treats and snuggly comfort. '
     'Tap Copy on a set and paste it into a caption, a comment or a reply to someone you want to cheer up.'],
    [('pets', '🐾 Little pets'), ('treats', '🍓 Sweet treats'), ('snug', '🧸 Snuggly')],
    [
        ('pets', 'Sleepy pup', '🐶💤🦴'), ('pets', 'Tiny kitten', '🐱🧶💕'), ('pets', 'Duckling day', '🐥🌼☀️'),
        ('pets', 'Hamster snack', '🐹🌰🤍'), ('pets', 'Puppy love', '🐕💗🎾'), ('pets', 'Bunny nap', '🐰🥕😴'),
        ('pets', 'Baby chick', '🐣🍼💛'), ('pets', 'Paw prints', '🐾🏡💖'),
        ('treats', 'Strawberry milk', '🍓🥛🎀'), ('treats', 'Cupcake smile', '🧁😊🍒'), ('treats', 'Honey bee', '🍯🐝🌸'),
        ('treats', 'Peach fuzz', '🍑☁️💗'), ('treats', 'Cookie night', '🍪🥛🌙'), ('treats', 'Tiny tea', '🍵🧸🌷'),
        ('treats', 'Candy cloud', '🍬☁️🩷'), ('treats', 'Berry basket', '🫐🍓🧺'),
        ('snug', 'Blanket hug', '🧸🛋️🤍'), ('snug', 'Cozy sock', '🧦☕🕯️'), ('snug', 'Teddy and star', '🧸⭐💛'),
        ('snug', 'Warm hug', '🤗🧣❄️'), ('snug', 'Sleepy moon', '🌙🧸💤'), ('snug', 'Pillow fort', '🛏️🧸🌟'),
        ('snug', 'Soft rain', '🌧️☂️🩵'), ('snug', 'Little lamp', '🕯️📖🧸'),
    ],
    ('What Makes a Combo Adorable',
     ['An adorable set is small in feeling as well as in size. A baby animal, a soft food and one gentle symbol '
      'usually do more than a long row of unrelated emojis, so keep the set short and let one character lead.',
      'Match the mood to the person. A sleepy-pup set suits a friend who had a long day, while a strawberry-milk '
      'set fits a sweet caption. If you are unsure, pick the set with the most rounded shapes and the softest colors.']),
    [('What does an adorable emoji combo look like?',
      'It usually pairs a small animal, a sweet food or a cozy object with a heart or a soft color, such as 🐰🥕😴 or 🍓🥛🎀.'),
     ('Can I use adorable emoji combos in a bio?',
      'Yes. Short sets such as 🐾🏡💖 fit in a bio and read clearly even on a small screen.'),
     ('Do adorable emoji combos look the same on every phone?',
      'The characters are the same, but each platform draws its own artwork, so colors and faces can differ a little. '
      'Preview the set in the app you will post from.')],
    [('🥺', '🎀'), ('🥰', '🌸'), ('🐰', '🌸'), ('🥰', '🤗'), ('🐱', '💗'), ('🥺', '💕')],
    [('cute', 'Cute'), ('kawaii', 'Kawaii'), ('cutecore', 'Cutecore')],
)

_add(
    'kawaii', 'Kawaii', '🍡',
    ['Kawaii is the Japanese idea of cute: round shapes, bright pastels, smiling food and tiny characters. '
     'Kawaii emoji combos borrow that look for captions, profiles and chats.',
     'Pick a style below: sweets, happy faces or pastel sparkle. Tap Copy to use a set, or open the mixer to turn '
     'two emojis into a sticker that has the same cheerful feel.'],
    [('sweets', '🍡 Sweets'), ('faces', '😊 Happy faces'), ('pastel', '🌈 Pastel sparkle')],
    [
        ('sweets', 'Dango stick', '🍡🌸🍵'), ('sweets', 'Rice ball', '🍙😊🌸'), ('sweets', 'Soft serve', '🍦🌈⭐'),
        ('sweets', 'Bubble tea', '🧋🫧🩷'), ('sweets', 'Donut sprinkle', '🍩✨🩵'), ('sweets', 'Pudding cup', '🍮🍒🤍'),
        ('sweets', 'Macaron pair', '🍬🎀💜'), ('sweets', 'Taiyaki treat', '🐟🍰💛'),
        ('faces', 'Happy cheeks', '😊🌸💗'), ('faces', 'Sparkly eyes', '🤩✨🍭'), ('faces', 'Blushing smile', '☺️🍓🎀'),
        ('faces', 'Giggle', '😆🌈🫧'), ('faces', 'Shy wave', '🥹👋🌷'), ('faces', 'Wink and star', '😉⭐💕'),
        ('faces', 'Joy burst', '🥳🎈🌟'), ('faces', 'Kiss blown', '😘💌🌸'),
        ('pastel', 'Rainbow cloud', '🌈☁️🩷'), ('pastel', 'Star candy', '⭐🍬🩵'), ('pastel', 'Cotton sky', '☁️💭🩷'),
        ('pastel', 'Ribbon pop', '🎀🫧💜'), ('pastel', 'Flower field', '🌼🌷🌸'), ('pastel', 'Twinkle night', '🌙⭐🩵'),
        ('pastel', 'Magic wand', '🪄✨🎀'), ('pastel', 'Bubble drift', '🫧🦋🩷'),
    ],
    ('How to Get the Kawaii Look With Emoji',
     ['Kawaii design works because everything is soft and a little exaggerated. In emoji form, that means pairing '
      'one cheerful face or snack with a pastel heart, a star or a bubble, then stopping before the set gets crowded.',
      'Food is the easiest way in. A rice ball, a boba cup or a donut already looks friendly, and one sparkle or '
      'ribbon next to it finishes the set.']),
    [('What does kawaii mean?',
      'Kawaii is a Japanese word for cute. It describes round, soft and charming things, from characters to snacks.'),
     ('What is a good kawaii emoji combo?',
      'Sets like 🧋🫧🩷 or 🍡🌸🍵 work well. Combine a sweet or a happy face with a pastel symbol.'),
     ('Can I make a kawaii sticker from two emojis?',
      'Often, yes. Pick two supported emojis in the mixer and it will show the mashup if the pair exists.')],
    [('🥰', '🌸'), ('🍩', '🌈'), ('🧁', '🌈'), ('🍒', '🌸'), ('🦄', '🌈'), ('😍', '🌸')],
    [('cute', 'Cute'), ('pink', 'Pink'), ('cutecore', 'Cutecore')],
)

_add(
    'cutecore', 'Cutecore', '🧸',
    ['Cutecore is an online style built on soft toys, pastel colors, stickers and childhood comfort. Its emoji '
     'combos are gentle and a little nostalgic, perfect for a bio that feels like a favorite bedroom shelf.',
     'The sets are split into plush toys, sweet things and sleepy nights. Tap Copy on any of them and paste it into '
     'a profile, a story caption or a comment.'],
    [('plush', '🧸 Plush toys'), ('sweet', '🍰 Sweet things'), ('sleepy', '🌙 Sleepy nights')],
    [
        ('plush', 'Teddy bow', '🧸🎀🤍'), ('plush', 'Bear and honey', '🐻🍯🌼'), ('plush', 'Plush bunny', '🐰🧸🩷'),
        ('plush', 'Toy box', '🎁🧸🪀'), ('plush', 'Stuffed star', '🧸⭐🩵'), ('plush', 'Patchwork heart', '🧵💗🧸'),
        ('plush', 'Little duck', '🦆🛁🫧'), ('plush', 'Music box', '🎠🎶🧸'),
        ('sweet', 'Cake slice', '🍰🍓🎀'), ('sweet', 'Jam toast', '🍞🍓💗'), ('sweet', 'Milk and cookie', '🥛🍪🧸'),
        ('sweet', 'Lollipop', '🍭🌈🩷'), ('sweet', 'Pink cupcake', '🧁🎀🌸'), ('sweet', 'Apple pie', '🥧🍎☁️'),
        ('sweet', 'Ice cream', '🍨🍒🤍'), ('sweet', 'Sugar star', '🍬⭐🧸'),
        ('sleepy', 'Bedtime bear', '🧸🌙💤'), ('sleepy', 'Night lamp', '🕯️🧸📖'), ('sleepy', 'Cloud bed', '☁️🛏️🧸'),
        ('sleepy', 'Warm cocoa', '☕🧸🧣'), ('sleepy', 'Stars and quilt', '⭐🛌🩵'), ('sleepy', 'Dream catcher', '🌙🪽💭'),
        ('sleepy', 'Sleepy kitten', '🐱🧶💤'), ('sleepy', 'Soft lullaby', '🎶🌙🤍'),
    ],
    ('Building a Cutecore Bio',
     ['Cutecore bios usually use a toy, a sweet and a soft symbol in a row, such as 🧸🍰🎀. The mix feels like a '
      'small shelf of favorite things, so repeating a color or a shape makes it look intentional.',
      'Keep the set short and the colors soft. Pink, cream and baby blue sit together easily, while very dark or '
      'sharp symbols break the mood.']),
    [('What is cutecore?',
      'Cutecore is a style that mixes soft toys, pastel colors and childhood comfort. It is cheerful and gentle.'),
     ('Which emojis suit a cutecore bio?',
      'Teddy bears, ribbons, cakes, bunnies, stars and soft hearts are common. A set like 🧸🍰🎀 is a good start.'),
     ('Is cutecore the same as kawaii?',
      'They overlap, but cutecore leans on plush toys and a nostalgic, cozy mood, while kawaii is a wider Japanese cute style.')],
    [('🥺', '🎀'), ('🐰', '🌸'), ('🥰', '🌸'), ('🧁', '🌈'), ('💗', '🌸'), ('🍒', '🌸')],
    [('cute', 'Cute'), ('kawaii', 'Kawaii'), ('aesthetic', 'Aesthetic')],
)

_add(
    'coquette', 'Coquette', '🎀',
    ['Coquette is a soft, romantic style built on ribbons, lace, pearls, roses and a touch of vintage. Its emoji '
     'combos feel like a handwritten note tied with a bow.',
     'Browse sets by mood: ribbons and bows, romantic flowers or dessert-table treats. Tap Copy and paste one into a '
     'bio, a caption or a message that should feel delicate.'],
    [('ribbon', '🎀 Ribbons and bows'), ('romance', '🌹 Romantic'), ('dessert', '🍰 Dessert table')],
    [
        ('ribbon', 'Pink bow', '🎀🩷🤍'), ('ribbon', 'Ribbon and pearl', '🎀🦪🤍'), ('ribbon', 'Lace and bow', '🕸️🎀🌸'),
        ('ribbon', 'Soft satin', '🎀🪞✨'), ('ribbon', 'Bow and bunny', '🎀🐰🤍'), ('ribbon', 'Dollhouse', '🏠🎀🧸'),
        ('ribbon', 'Ballet slipper', '🩰🎀🤍'), ('ribbon', 'Gift wrap', '🎁🎀💗'),
        ('romance', 'Rose letter', '💌🌹🎀'), ('romance', 'Dried flowers', '🥀📖🤍'), ('romance', 'Cherry blossom', '🌸🕊️🎀'),
        ('romance', 'Candlelit note', '🕯️💌🌷'), ('romance', 'Garden walk', '🌷🌿🕊️'), ('romance', 'Love poem', '📜🖋️💗'),
        ('romance', 'Heart locket', '💗🔐🎀'), ('romance', 'Pearl rose', '🌹🤍✨'),
        ('dessert', 'Cherry cake', '🍰🍒🎀'), ('dessert', 'Tea party', '🫖🍪🌸'), ('dessert', 'Macaron plate', '🍬🎀🩷'),
        ('dessert', 'Strawberry tart', '🍓🥧🤍'), ('dessert', 'Milk and rose', '🥛🌹🎀'), ('dessert', 'Ice cream bow', '🍨🎀🍒'),
        ('dessert', 'Champagne sparkle', '🥂✨🎀'), ('dessert', 'Cupcake frill', '🧁🎀💗'),
    ],
    ('Choosing a Coquette Combo',
     ['The coquette look is about restraint. Choose one ribbon or bow, one romantic symbol such as a rose or a '
      'letter, and one soft color. White, blush pink and cream tend to read as coquette right away.',
      'It pairs well with short captions and quiet bios. Too many bright or loud symbols pull a set away from the '
      'style, so trim anything that does not feel delicate.']),
    [('What is a coquette emoji combo?',
      'It is a short set that uses ribbons, roses, pearls, lace and soft pink or white symbols, such as 🎀🩷🤍.'),
     ('Which colors work for coquette?',
      'Blush pink, white, cream and pale red are the most common. The pink and white hearts do most of the work.'),
     ('Can I use coquette emoji combos in a caption?',
      'Yes. Place the set at the end of a short line, or on its own line, so it reads like a soft sign-off.')],
    [('💘', '🎀'), ('🥰', '🌸'), ('💗', '🌸'), ('🥺', '🎀'), ('🍒', '🌸'), ('💕', '🌈')],
    [('pink', 'Pink'), ('love', 'Love'), ('aesthetic', 'Aesthetic')],
)

_add(
    'preppy', 'Preppy', '🎾',
    ['Preppy style is clean, bright and a little sporty: tennis courts, summer drinks, pastel stripes and well-kept '
     'details. Its emoji combos feel like a fresh outfit with everything matching.',
     'Browse sets for sport and school, summer days and getting ready. Tap Copy on a set to use it in a bio, a '
     'caption or a group chat.'],
    [('sport', '🎾 Sport and school'), ('summer', '🍹 Summer days'), ('ready', '💅 Getting ready')],
    [
        ('sport', 'Tennis court', '🎾👟☀️'), ('sport', 'Varsity day', '📣🏈💙'), ('sport', 'Study date', '📚☕✏️'),
        ('sport', 'Golf morning', '⛳🧢🌤️'), ('sport', 'Swim team', '🏊‍♀️🥇💙'), ('sport', 'Campus walk', '🎒🍂📖'),
        ('sport', 'Match point', '🎾🏆✨'), ('sport', 'Sailing club', '⛵🌊🧭'),
        ('summer', 'Lemonade stand', '🍋🥤☀️'), ('summer', 'Beach club', '🏖️🕶️🍹'), ('summer', 'Poolside', '🏊🍉🌴'),
        ('summer', 'Picnic day', '🧺🍓🌼'), ('summer', 'Pink lemonade', '🍹🩷🍋'), ('summer', 'Boat day', '🛥️🌊☀️'),
        ('summer', 'Sundress', '👗🌻🕶️'), ('summer', 'Ice cream run', '🍦🩴☀️'),
        ('ready', 'Pearl earrings', '🦪💍🤍'), ('ready', 'Fresh nails', '💅🩷✨'), ('ready', 'Hair ribbon', '🎀👱‍♀️💙'),
        ('ready', 'Perfume spritz', '🧴🌸🤍'), ('ready', 'Handbag pick', '👜🕶️🌷'), ('ready', 'Loafers', '👞🧦🍂'),
        ('ready', 'Weekend brunch', '🥐☕🥂'), ('ready', 'Sunday reset', '🕯️🛁🌿'),
    ],
    ('Keeping a Preppy Set Clean',
     ['A preppy set reads well when it stays tidy: one activity, one accessory and one fresh color. Tennis, '
      'lemonade and pearls all fit, while heavy dark symbols do not.',
      'Blue, pink and yellow are easy colors to repeat. Matching two of the three across the set gives it the '
      'coordinated look the style is known for.']),
    [('What is a preppy emoji combo?',
      'It is a bright, tidy set built around sport, summer or getting ready, such as 🎾👟☀️ or 🍋🥤☀️.'),
     ('Which colors suit a preppy bio?',
      'Navy, baby blue, blush pink and yellow are common. Hearts and stars in those colors tie a set together.'),
     ('Do preppy emoji combos work in a username?',
      'Short ones do. Stick to two or three emojis so the name stays readable.')],
    [('😎', '🌈'), ('🥰', '🌸'), ('🌟', '🌈'), ('💙', '🌊'), ('😍', '🔥'), ('🌊', '🌴')],
    [('aesthetic', 'Aesthetic'), ('pink', 'Pink'), ('bio', 'Bio')],
)

_add(
    'anime', 'Anime', '🍥',
    ['Anime emoji combos borrow the visual language of Japanese animation: sparkling eyes, cherry blossoms, ramen '
     'bowls, school rooftops and dramatic power-ups. They suit fan bios, edits and chats about favorite shows.',
     'Pick a mood below: everyday slice of life, action and power, or soft romance. Tap Copy on a set, or open the '
     'mixer to see a sticker made from two emojis.'],
    [('daily', '🍜 Slice of life'), ('action', '⚔️ Action'), ('romance', '🌸 Romance')],
    [
        ('daily', 'Ramen night', '🍜🥢🌙'), ('daily', 'School rooftop', '🏫🌤️🍱'), ('daily', 'Bento lunch', '🍱🌸😋'),
        ('daily', 'Festival evening', '🏮🎆🍡'), ('daily', 'Train window', '🚃🌸🎧'), ('daily', 'Rainy walk', '☔🌧️📖'),
        ('daily', 'Summer cicadas', '🍉🎐☀️'), ('daily', 'Late study', '📚☕🌙'),
        ('action', 'Power up', '⚡🔥💪'), ('action', 'Sword duel', '⚔️🌙✨'), ('action', 'Hero moment', '🦸‍♂️⭐💥'),
        ('action', 'Final battle', '🔥⚔️🌪️'), ('action', 'Dragon wind', '🐉🌪️⚡'), ('action', 'Ninja night', '🥷🌙🍃'),
        ('action', 'Training arc', '🥋💦🔥'), ('action', 'Rival glance', '👀⚡🔥'),
        ('romance', 'Blossom confession', '🌸💌😳'), ('romance', 'Shared umbrella', '☂️💞🌧️'), ('romance', 'Sunset walk', '🌅🚲💗'),
        ('romance', 'Fireworks night', '🎆💕👘'), ('romance', 'Love letter', '💌🌸🥺'), ('romance', 'Sparkle eyes', '🥹✨💗'),
        ('romance', 'Festival date', '🏮💞🍡'), ('romance', 'Moonlit promise', '🌙🤝💫'),
    ],
    ('Using Anime Emoji in Fan Bios and Chats',
     ['Anime fans often use a short row to show a vibe rather than a single show: 🍜🌙📚 for a quiet slice-of-life '
      'mood or ⚡🔥⚔️ for action. The set tells people what kind of story you like.',
      'Keep it to a few emojis and let the caption say the title. If you want a picture instead of a row, the mixer '
      'can make a sticker from supported pairs.']),
    [('What is an anime emoji combo?',
      'It is a short set that suggests an anime mood, such as 🍜🥢🌙 for slice of life or ⚡🔥💪 for action.'),
     ('Which emojis are used for anime fans?',
      'Cherry blossoms, ramen, swords, sparkles and lanterns are popular. Pair two or three for a clear mood.'),
     ('Are these tied to a specific show?',
      'No. They describe a general style and mood and are not taken from any one series.')],
    [('😍', '🔥'), ('🥰', '🌸'), ('🤯', '🚀'), ('😱', '👻'), ('😂', '💀'), ('🔥', '💧')],
    [('funny', 'Funny'), ('aesthetic', 'Aesthetic'), ('kawaii', 'Kawaii')],
)

_add(
    'sparkles', 'Sparkles', '✨',
    ['Sparkle emoji combos add a little shine to a message. They suit compliments, good news, glow-ups and any '
     'caption that deserves a bit of glitter.',
     'Browse sets for glow-ups, celebrations and starry nights. Tap Copy to paste one, or use a single sparkle at '
     'the end of a line for a lighter touch.'],
    [('glow', '💅 Glow up'), ('party', '🎉 Celebrate'), ('night', '🌌 Starry night')],
    [
        ('glow', 'Fresh glow', '✨💅💄'), ('glow', 'Mirror check', '🪞✨😌'), ('glow', 'New hair', '💇‍♀️✨💖'),
        ('glow', 'Soft skin', '🧴✨🌸'), ('glow', 'Golden hour', '🌅✨🧡'), ('glow', 'Main character', '👑✨😎'),
        ('glow', 'Dress up', '👗✨👠'), ('glow', 'Shine on', '💎✨🌟'),
        ('party', 'Confetti pop', '🎉✨🥳'), ('party', 'Champagne toast', '🥂✨🍾'), ('party', 'Big news', '📣✨🎊'),
        ('party', 'Gift shine', '🎁✨🎀'), ('party', 'Dance floor', '🪩✨💃'), ('party', 'Glitter cake', '🎂✨🕯️'),
        ('party', 'Fireworks', '🎆✨🌟'), ('party', 'Trophy sparkle', '🏆✨🙌'),
        ('night', 'Stargazing', '🌌✨🔭'), ('night', 'Moon glow', '🌙✨💫'), ('night', 'Wish upon', '🌠✨🙏'),
        ('night', 'Fairy lights', '🧚✨🌿'), ('night', 'Night swim', '🌊✨🌙'), ('night', 'Lantern sky', '🏮✨🌌'),
        ('night', 'Comet trail', '☄️✨💙'), ('night', 'Magic spell', '🪄✨🔮'),
    ],
    ('When to Add a Sparkle',
     ['A sparkle works as punctuation. Put ✨ after a compliment, a piece of good news or a small win and it adds '
      'warmth without changing what you said.',
      'For a stronger effect, pair the sparkle with one object that explains the occasion, such as a gift, a '
      'trophy or a star. Avoid stacking several sparkle sets in one post, since the shine fades when it is everywhere.']),
    [('What does the sparkles emoji mean?',
      'It usually means something is shiny, new, magical or special. People also use it to add a soft emphasis.'),
     ('Which emoji combos go well with sparkles?',
      'Stars, hearts, gifts and flowers pair well, such as 🎁✨🎀 or 🌙✨💫.'),
     ('Is it fine to use sparkle combos in a work message?',
      'A single sparkle after good news is usually fine. Save longer sets for friends and social posts.')],
    [('🌟', '🌈'), ('🤯', '🚀'), ('🦄', '🌈'), ('😎', '🌈'), ('🥰', '🌸'), ('😍', '🔥')],
    [('aesthetic', 'Aesthetic'), ('cute', 'Cute'), ('star', 'Star')],
)

_add(
    'bunny', 'Bunny', '🐰',
    ['Bunny emoji combos are soft, springy and sweet. They suit Easter posts, pastel bios and anyone who loves '
     'long ears and carrot snacks.',
     'Choose a set below: bunny and garden, bunny and sweets, or bunny and spring. Tap Copy and paste one into a '
     'caption, a nickname or a message.'],
    [('garden', '🥕 Garden'), ('sweets', '🍓 Sweets'), ('spring', '🌷 Spring')],
    [
        ('garden', 'Carrot patch', '🐰🥕🌱'), ('garden', 'Clover luck', '🐇🍀🌿'), ('garden', 'Hop and snack', '🐰🥬🌼'),
        ('garden', 'Garden gate', '🐇🏡🌷'), ('garden', 'Meadow morning', '🐰🌾☀️'), ('garden', 'Burrow home', '🕳️🐰🌱'),
        ('garden', 'Dewdrop', '🐇💧🍃'), ('garden', 'Little sprout', '🌱🐰💚'),
        ('sweets', 'Strawberry bunny', '🐰🍓🎀'), ('sweets', 'Milk bunny', '🐇🥛🤍'), ('sweets', 'Cupcake hop', '🐰🧁🌸'),
        ('sweets', 'Peach bunny', '🐇🍑💗'), ('sweets', 'Cookie ears', '🐰🍪🧸'), ('sweets', 'Honey bunny', '🐇🍯🌼'),
        ('sweets', 'Berry basket', '🐰🫐🧺'), ('sweets', 'Candy bunny', '🐇🍬🩷'),
        ('spring', 'Easter basket', '🐰🧺🥚'), ('spring', 'Flower crown', '🐇🌸👑'), ('spring', 'Painted eggs', '🥚🎨🐰'),
        ('spring', 'Rain boots', '🐇☔🌷'), ('spring', 'Butterfly day', '🐰🦋🌼'), ('spring', 'Spring breeze', '🌬️🐇🌸'),
        ('spring', 'Moon bunny', '🐇🌙⭐'), ('spring', 'Bright morning', '🐰🌞💛'),
    ],
    ('Using Bunny Emoji in Bios and Captions',
     ['The bunny works as a friendly mascot. Put 🐰 at the start of a bio line, or use it with a snack or a flower '
      'to give a post a soft, playful tone.',
      'Spring and Easter posts are the obvious fit, but the bunny also suits pastel profiles all year. Pair it with '
      'pink, white or green symbols for the cleanest look.']),
    [('What is the difference between the rabbit and bunny emoji?',
      'Both are rabbits. 🐰 shows the face and 🐇 shows the whole animal. People use them interchangeably.'),
     ('Which emojis go with a bunny?',
      'Carrots, clovers, flowers, eggs and soft hearts all pair well, such as 🐰🥕🌱 or 🐇🌸👑.'),
     ('Can I use bunny combos outside Easter?',
      'Yes. Bunny sets work for pastel, cute and spring-themed posts at any time of year.')],
    [('🐰', '🌸'), ('🥰', '🌸'), ('🦋', '🌺'), ('🌷', '🦋'), ('🥺', '🎀'), ('💗', '🌸')],
    [('cute', 'Cute'), ('cat', 'Cat'), ('adorable', 'Adorable')],
)

_add(
    'cat', 'Cat', '🐱',
    ['Cat emoji combos suit cat owners, cat lovers and anyone whose mood is best described by a sleepy kitten. '
     'They range from cuddly to cheeky.',
     'Browse sets for cozy cats, playful cats and cat-style sass. Tap Copy to paste one into a bio, a caption or a '
     'reply to a friend with a pet photo.'],
    [('cozy', '😴 Cozy'), ('play', '🧶 Playful'), ('sass', '😼 Sassy')],
    [
        ('cozy', 'Sunbeam nap', '🐱☀️😴'), ('cozy', 'Blanket cat', '🐈🛋️🤍'), ('cozy', 'Warm lap', '🐱☕🧣'),
        ('cozy', 'Moon cat', '🐈‍⬛🌙💤'), ('cozy', 'Window seat', '🐱🪟🌧️'), ('cozy', 'Book and cat', '📖🐈☕'),
        ('cozy', 'Purr time', '🐱💗🎶'), ('cozy', 'Pillow paws', '🐾🛏️🧸'),
        ('play', 'Yarn chase', '🐱🧶🌈'), ('play', 'Fish snack', '🐟🐱😋'), ('play', 'Box fort', '📦🐈✨'),
        ('play', 'Midnight zoomies', '🐱💨🌙'), ('play', 'Laser dot', '🔴🐱👀'), ('play', 'Tiny toy mouse', '🐭🐈🎀'),
        ('play', 'Bell collar', '🔔🐱🎀'), ('play', 'Bird watching', '🐦🐈🌿'),
        ('sass', 'Side eye', '🐱👀🙄'), ('sass', 'Knocked it over', '🐈🥛😼'), ('sass', 'Not today', '😾🚫☕'),
        ('sass', 'Royal cat', '🐱👑😌'), ('sass', 'Judging you', '🐈‍⬛🧐🔥'), ('sass', 'Cat attitude', '😼💅✨'),
        ('sass', 'Hiss', '🙀💥🐾'), ('sass', 'Smug whiskers', '😸😏🐟'),
    ],
    ('Cat Combos for Every Mood',
     ['Cats cover almost every mood, so the set can say a lot with very little. A sunbeam nap set tells people you '
      'are relaxed, while a side-eye set is a quick reply to something silly.',
      'Black cats suit night and mystery sets, and orange or tabby cats suit warm, sunny ones. Pick the cat that '
      'matches the feeling and add one or two supporting symbols.']),
    [('Which emoji combos are good for cat lovers?',
      'Cats with yarn, fish, sunbeams or moons are popular, such as 🐱🧶🌈 or 🐈‍⬛🌙💤.'),
     ('What does a black cat emoji mean?',
      'It can mean luck, mystery or Halloween, depending on the set. It also works as a plain pet emoji.'),
     ('Can I use cat combos as a nickname?',
      'Yes. A short set such as 🐱🌙 works well as a profile name or a bio line.')],
    [('🐱', '🔥'), ('🐱', '💗'), ('😂', '💀'), ('🥰', '🌸'), ('🐰', '🌸'), ('🦋', '🌺')],
    [('cute', 'Cute'), ('bunny', 'Bunny'), ('funny', 'Funny')],
)

_add(
    'heart', 'Heart', '💖',
    ['Heart emoji combos say how you feel in color. Red is love, blue is calm, green is care, and the sparkle or '
     'ribbon next to the heart changes the tone again.',
     'Browse sets for sweet affection, heart color sets and heartbreak. Tap Copy to paste one into a text, a '
     'caption or a note.'],
    [('sweet', '💗 Sweet'), ('colors', '🌈 Heart colors'), ('broken', '💔 Heartbreak')],
    [
        ('sweet', 'Heart and rose', '💗🌹✨'), ('sweet', 'Love letter', '💌💖🕊️'), ('sweet', 'Soft heart', '🩷🤍🌷'),
        ('sweet', 'Heart eyes', '😍💕🌷'), ('sweet', 'Forever', '💞♾️🤍'), ('sweet', 'Warm hug', '🤗💗🧸'),
        ('sweet', 'Kiss and heart', '😘💘🌹'), ('sweet', 'Heart ribbon', '💝🎀🩷'),
        ('colors', 'Rainbow hearts', '❤️🧡💛💚💙💜'), ('colors', 'Blue calm', '💙🌊☁️'), ('colors', 'Green care', '💚🌿🍀'),
        ('colors', 'Purple glow', '💜🔮✨'), ('colors', 'Yellow sun', '💛🌼🌞'), ('colors', 'Orange warmth', '🧡🍊🧣'),
        ('colors', 'Black heart', '🖤🦇🌙'), ('colors', 'White heart', '🤍🕊️☁️'),
        ('broken', 'Heartache', '💔🌧️🥀'), ('broken', 'Mended heart', '❤️‍🩹🌱🌤️'), ('broken', 'Quiet tears', '😢💔🌙'),
        ('broken', 'Letting go', '💔🕊️🌅'), ('broken', 'Missing you', '🥺💭💔'), ('broken', 'Cracked heart', '💔🩹💗'),
        ('broken', 'Night thoughts', '🌙💭🖤'), ('broken', 'Fading rose', '🥀💔🍂'),
    ],
    ('Reading Heart Colors',
     ['Each heart color has a tone. Red and pink are romantic, orange and yellow are warm and friendly, green and '
      'blue are calm and caring, and purple suits a creative or dreamy mood.',
      'Between friends, a colored heart can show how close you feel without sounding too serious. Black and white '
      'hearts carry a quieter, more stylish tone.']),
    [('What do the different heart emoji colors mean?',
      'Red and pink are romantic, orange and yellow are warm, green and blue are caring and calm, and purple is dreamy.'),
     ('Which heart emoji combo is best for a romantic text?',
      'Sets such as 💗🌹✨ or 💌💖🕊️ read as warm and clear.'),
     ('Can I use heart combos with friends?',
      'Yes. Yellow, blue and green hearts are friendly and do not read as romantic.')],
    [('💘', '🎀'), ('💕', '🌈'), ('💗', '🌸'), ('💙', '🌊'), ('😭', '💔'), ('🥰', '🌸')],
    [('love', 'Love'), ('pink', 'Pink'), ('sad', 'Sad')],
)

_add(
    'ribbon', 'Ribbon', '🎀',
    ['Ribbon emoji combos tie a message up in a bow. They suit gifts, pretty bios and anything that should look '
     'neat, soft and a little bit special.',
     'Browse ribbon sets for gifts, soft style and sweet treats. Tap Copy to paste one into a card, a caption or a '
     'profile.'],
    [('gift', '🎁 Gifts'), ('style', '👗 Soft style'), ('treat', '🍰 Treats')],
    [
        ('gift', 'Wrapped gift', '🎁🎀✨'), ('gift', 'Birthday ribbon', '🎂🎀🎈'), ('gift', 'Surprise box', '📦🎀💗'),
        ('gift', 'Thank you bow', '🙏🎀💌'), ('gift', 'Holiday wrap', '🎄🎁🎀'), ('gift', 'Gift tag', '🏷️🎀🌸'),
        ('gift', 'Wedding favor', '💍🎀🕊️'), ('gift', 'Pink package', '🎁🩷🌷'),
        ('style', 'Hair bow', '🎀💇‍♀️🌸'), ('style', 'Ballet bow', '🩰🎀🌙'), ('style', 'Satin dress', '👗🎀💗'),
        ('style', 'Tied shoes', '👟🎀☁️'), ('style', 'Ribbon and pearls', '🎀🦪✨'), ('style', 'Bow tie', '🎀🧸🥂'),
        ('style', 'Sewing day', '🧵🎀🪡'), ('style', 'Vanity table', '🪞🎀💄'),
        ('treat', 'Cake and bow', '🍰🎀🍓'), ('treat', 'Candy ribbon', '🍬🎀🌈'), ('treat', 'Cupcake wrap', '🧁🎀🩷'),
        ('treat', 'Tea and bow', '🫖🎀🌷'), ('treat', 'Cherry bow', '🍒🎀🤍'), ('treat', 'Cookie jar', '🍪🎀🧸'),
        ('treat', 'Chocolate gift', '🍫🎁🎀'), ('treat', 'Honey pot', '🍯🎀🐝'),
    ],
    ('Where a Ribbon Fits',
     ['A ribbon works like a finishing touch. Put 🎀 at the end of a set to make it feel wrapped up and neat, or '
      'at the start of a bio line to set a soft tone.',
      'Pink, red and white ribbons are the usual choices, and one ribbon is enough. A single bow next to a gift or '
      'a flower looks more refined than several bows in a row.']),
    [('What does the ribbon emoji mean?',
      'It stands for gifts, bows, girly style and sweet details. Some people also use it for awareness ribbons.'),
     ('Which emojis go with a ribbon?',
      'Gifts, flowers, cakes, hearts and pearls pair well, such as 🎁🎀✨ or 🍰🎀🍓.'),
     ('Can I use a ribbon combo in a bio?',
      'Yes. A short set like 🎀🌸🤍 fits easily and looks tidy.')],
    [('💘', '🎀'), ('🥺', '🎀'), ('🥰', '🌸'), ('🍒', '🌸'), ('💗', '🌸'), ('🧁', '🌈')],
    [('coquette', 'Coquette'), ('pink', 'Pink'), ('birthday', 'Birthday')],
)

_add(
    'star', 'Star', '⭐',
    ['Star emoji combos shine for wishes, achievements and night skies. They suit a bio that wants a bit of '
     'sparkle or a message that celebrates someone.',
     'Pick a set below for wishes and dreams, praise and success, or the night sky. Tap Copy and paste one into '
     'a caption, a card or a chat.'],
    [('wish', '🌠 Wishes'), ('praise', '🏆 Praise'), ('sky', '🌌 Night sky')],
    [
        ('wish', 'Shooting star', '🌠🙏✨'), ('wish', 'Wish jar', '🫙⭐💭'), ('wish', 'Make a wish', '🕯️🌟🙏'),
        ('wish', 'Dream big', '💭⭐🚀'), ('wish', 'Lucky star', '🍀⭐🤞'), ('wish', 'Star and heart', '⭐💗🌙'),
        ('wish', 'Falling stars', '🌠💫🌌'), ('wish', 'Night prayer', '🌙⭐🕊️'),
        ('praise', 'You are a star', '⭐🙌😍'), ('praise', 'Gold medal', '🥇⭐🎉'), ('praise', 'Top student', '📚⭐🏆'),
        ('praise', 'Bright idea', '💡⭐🧠'), ('praise', 'Standing ovation', '👏⭐🎭'), ('praise', 'Five stars', '⭐⭐⭐⭐⭐'),
        ('praise', 'Team star', '⭐🤝💪'), ('praise', 'Star performer', '🎤⭐🔥'),
        ('sky', 'Starry night', '🌌⭐🌙'), ('sky', 'Telescope', '🔭⭐🪐'), ('sky', 'Camp sky', '⛺⭐🔥'),
        ('sky', 'Milky way', '🌌💫🤍'), ('sky', 'Rocket trip', '🚀⭐🌍'), ('sky', 'Moon and stars', '🌙✨⭐'),
        ('sky', 'Silver star', '🩶⭐🌌'), ('sky', 'Comet', '☄️⭐💙'),
    ],
    ('Star Combos for Praise and Wishes',
     ['A star works as a compliment. Put ⭐ after a name, a result or a piece of good news and it says well done '
      'without needing a sentence.',
      'For wishes, pair the star with a moon, a candle or hands in prayer. For the night sky, add a planet or a '
      'telescope. Keep each set to one idea so the star stays the focus.']),
    [('What does the star emoji mean?',
      'It can mean praise, success, wishes or a bright idea, depending on the set around it.'),
     ('Which emoji combos are good for wishes?',
      'Sets such as 🌠🙏✨ or 🕯️🌟🙏 pair the star with a wish or a prayer.'),
     ('How do I make a star rating with emoji?',
      'Repeat the star emoji in a row. It is plain text, so it pastes into reviews and messages.')],
    [('🌟', '🌈'), ('🤯', '🚀'), ('🌈', '⭐'), ('😎', '🌈'), ('🔥', '💧'), ('🦄', '🌈')],
    [('sparkles', 'Sparkles'), ('aesthetic', 'Aesthetic'), ('cute', 'Cute')],
)

_add(
    'ocean', 'Ocean', '🌊',
    ['Ocean emoji combos bring the sea into a message: waves, shells, sunny beaches and deep blue calm. They suit '
     'summer captions, travel posts and calm bios.',
     'Browse sets for the beach, the deep sea and sailing trips. Tap Copy to paste one into a caption, a story or '
     'a chat about your next holiday.'],
    [('beach', '🏖️ Beach'), ('deep', '🐙 Deep sea'), ('sail', '⛵ Sailing')],
    [
        ('beach', 'Beach day', '🏖️🌊☀️'), ('beach', 'Seashell', '🐚🌊🤍'), ('beach', 'Sand and sun', '🏝️🕶️🍹'),
        ('beach', 'Surf morning', '🏄‍♀️🌊🌅'), ('beach', 'Coconut drink', '🥥🌴🍹'), ('beach', 'Sandcastle', '🏰🪣☀️'),
        ('beach', 'Low tide', '🌊🦀🐚'), ('beach', 'Sunset shore', '🌅🌊🧡'),
        ('deep', 'Dolphin play', '🐬🌊💙'), ('deep', 'Coral reef', '🪸🐠🫧'), ('deep', 'Octopus', '🐙🌊💜'),
        ('deep', 'Whale song', '🐋🎶🌊'), ('deep', 'Sea turtle', '🐢🌊🌿'), ('deep', 'Jellyfish glow', '🪼✨💙'),
        ('deep', 'Pearl dive', '🤿🦪✨'), ('deep', 'Mermaid', '🧜‍♀️🌊🐚'),
        ('sail', 'Sail away', '⛵🌊☀️'), ('sail', 'Lighthouse', '🏝️🌊🔦'), ('sail', 'Boat trip', '🛥️🌅🌊'),
        ('sail', 'Anchor', '⚓🌊🤍'), ('sail', 'Seagull', '🕊️🌊☁️'), ('sail', 'Ship wheel', '🧭⛵🌅'),
        ('sail', 'Fishing day', '🎣🐟🌊'), ('sail', 'Harbor night', '⚓🌙✨'),
    ],
    ('Ocean Combos for Captions',
     ['A good ocean set uses one wave, one sea creature or object, and one light symbol like a sun or a pearl. '
      'The blues and whites of the sea make the set look calm even when it is short.',
      'For travel posts, pair a wave with a boat or a palm tree. For quiet bios, shells, dolphins and pearls give '
      'a softer feel than a busy beach scene.']),
    [('Which emojis are best for the ocean?',
      'Waves, shells, dolphins, whales, boats and palm trees all work, such as 🐬🌊💙 or 🏖️🌊☀️.'),
     ('Can I use ocean combos for a travel caption?',
      'Yes. A set such as ⛵🌊🧭 fits sailing and beach posts well.'),
     ('Which colors go with an ocean combo?',
      'Blue, white and teal-style hearts and symbols match the sea best, with a yellow sun for warmth.')],
    [('💙', '🌊'), ('🌊', '🌴'), ('🌈', '⭐'), ('😎', '🌈'), ('🐸', '☕'), ('🔥', '💧')],
    [('aesthetic', 'Aesthetic'), ('sparkles', 'Sparkles'), ('star', 'Star')],
)

_add(
    'japan', 'Japan', '🗾',
    ['Japan emoji combos pick up the look of Japanese food, festivals, seasons and landmarks. They suit travel '
     'captions, food posts and fan bios.',
     'Browse sets for food, festivals and seasons. Tap Copy to paste one into a caption, a story or a chat about '
     'a trip.'],
    [('food', '🍣 Food'), ('festival', '🏮 Festivals'), ('season', '🌸 Seasons')],
    [
        ('food', 'Sushi set', '🍣🥢🍵'), ('food', 'Ramen bowl', '🍜🥢🔥'), ('food', 'Onigiri', '🍙🌊🌸'),
        ('food', 'Tempura plate', '🍤🍚🥢'), ('food', 'Green tea', '🍵🍡🌸'), ('food', 'Bento box', '🍱😋🌸'),
        ('food', 'Dumplings', '🥟🥢🌶️'), ('food', 'Fish cake', '🍥🍜✨'),
        ('festival', 'Lantern night', '🏮🎆🍵'), ('festival', 'Summer festival', '🎐🍉👘'), ('festival', 'Temple gate', '⛩️🏮🍃'),
        ('festival', 'Fireworks', '🎆👘🌙'), ('festival', 'Wind chime', '🎐🌬️🍃'), ('festival', 'Carp streamer', '🎏🌤️🎋'),
        ('festival', 'New year', '🎍🎌🎉'), ('festival', 'Doll festival', '🎎🌸🍡'),
        ('season', 'Cherry blossom', '🌸🗾🌤️'), ('season', 'Mount Fuji', '🗻🌸☁️'), ('season', 'Autumn leaves', '🍁🍵🏯'),
        ('season', 'Snow country', '❄️♨️🏔️'), ('season', 'Bamboo grove', '🎋🍃🌿'), ('season', 'Rainy season', '☔🐸🌧️'),
        ('season', 'Hot spring', '♨️🌸🍵'), ('season', 'Bullet train', '🚄🗻🌸'),
    ],
    ('Japan Combos for Travel and Food Posts',
     ['A Japan set is easiest when it follows one subject. Food sets pair a dish with chopsticks or tea, festival '
      'sets use lanterns and fireworks, and season sets use blossoms, leaves or snow.',
      'For a trip caption, a landmark plus a season, such as 🗻🌸☁️, says where and when in a few symbols. Keep it '
      'short so the photo does the talking.']),
    [('Which emojis are used for Japan?',
      'Sushi, ramen, cherry blossoms, lanterns, Mount Fuji and the Japan map emoji are common choices.'),
     ('What is a good emoji combo for a Japan trip?',
      'Try 🗻🌸☁️ for spring or 🍁🍵🏯 for autumn, then add the city in your caption.'),
     ('Do these work for Japanese food posts?',
      'Yes. Sets such as 🍣🥢🍵 and 🍜🥢🔥 are easy to read next to a food photo.')],
    [('🍕', '🔥'), ('🍩', '🌈'), ('🥰', '🌸'), ('🍒', '🌸'), ('🌷', '🦋'), ('🌊', '🌴')],
    [('anime', 'Anime'), ('kawaii', 'Kawaii'), ('aesthetic', 'Aesthetic')],
)


# A second editorial section per keyword page, so every page carries real, page-specific guidance.
_SECOND_SECTIONS = {
    'adorable': ('Where Adorable Sets Work Best',
                 ['Adorable sets shine in replies and captions where you want to be kind. Under a friend\'s pet photo, a short '
                  'set like 🐾💗 does more than a long comment, and on a tired Monday a snuggly set can feel like a small gift.',
                  'Keep the picture of the set simple. One animal or one treat, plus a heart, is almost always enough, and the '
                  'result stays easy to read when it appears small in a chat bubble.']),
    'kawaii': ('Pairing Kawaii Sets With Text',
               ['Kawaii sets sit well at the end of a short, cheerful line. A sentence like "snack break" followed by a '
                'boba or dango set feels playful, while the same sentence with no emoji can read flat.',
                'If you also want a picture, open the mixer below and try two of the emojis from your favorite set. A matching '
                'sticker and text set make a profile look planned rather than random.']),
    'cutecore': ('Cutecore Beyond the Bio',
                 ['Cutecore sets are not only for profiles. They work as the sign-off on a message to someone who is having a '
                  'rough day, as a divider between sections of a caption, or as the opening line of a story highlight.',
                  'Because the style is soft and nostalgic, it helps to keep the surrounding text gentle too. Lowercase '
                  'sentences and a single set make the whole post feel like one small, cozy thing.']),
    'coquette': ('Pairing Coquette Sets With Words',
                 ['Coquette captions tend to be short and a little poetic, such as a line about tea, letters or flowers. '
                  'Place the set after the line, or let it stand alone on a second line like a signature.',
                  'Avoid mixing a coquette set with loud, high-energy emojis in the same post. The effect comes from '
                  'consistency, so keep every symbol soft, pale and a little vintage.']),
    'preppy': ('Preppy Sets for Everyday Posts',
               ['Preppy sets suit plans and weekends: a tennis session, a brunch, a day on the water. They read as '
                'organized and upbeat, which makes them a good fit for a group-chat invite or a photo dump caption.',
                'Match the set to the photo. A lemonade set belongs with a summer picture, a campus set with books and '
                'coffee, and a getting-ready set with a mirror shot.']),
    'anime': ('Anime Sets Without Naming a Show',
              ['You do not need a title to show your taste. A row such as 🍜🌙📚 or ⚡🔥⚔️ tells followers whether you '
               'lean toward quiet stories or big battles, and fans of the genre tend to notice.',
               'Use anime sets in bios, edit captions and chats with friends who share the hobby. When you want to name a '
               'character or series, write it in text and let the set carry the mood around it.']),
    'sparkles': ('Sparkle Sets and Tone',
                 ['A sparkle changes the tone of a sentence. "Thank you" with a sparkle sounds warmer, and "new look" with a '
                  'glow-up set sounds proud. The same words without it can feel more neutral.',
                  'Use one sparkle set per post. If you want extra emphasis, pick a set with a clear object, such as a gift, a '
                  'trophy or a moon, so the sparkle has something to light up.']),
    'bunny': ('Bunny Sets for Nicknames and Captions',
              ['A bunny set makes a friendly nickname. Put 🐰 before a name in a bio or a group chat, or add a carrot or '
               'clover to match the mood of the day.',
               'In captions, bunny sets suit gentle photos: a garden, a pastel outfit, a plate of sweets. Keep the colors '
               'light and the set short, and the bunny reads as sweet rather than busy.']),
    'cat': ('Choosing the Right Cat for the Message',
            ['Cats are expressive, so pick the face that matches. A smiling cat suits good news, a side-eye cat answers '
             'something silly, and a sleeping cat tells people you are done for the day.',
             'Pet owners often keep one signature set for their own cat, such as a sunbeam or a yarn set. It becomes a '
             'small, recognizable sign under every photo they post.']),
    'heart': ('Mixing Heart Colors on Purpose',
              ['A single heart color can say a lot, and a row of different colors says something else: variety, a '
               'rainbow mood or a group of friends. Pick the color first, then choose the supporting symbol.',
               'For a bio, two matching hearts with one small symbol look tidy. For a message to someone close, one clear '
               'heart with a flower or a letter feels personal.']),
    'ribbon': ('Ribbon Sets for Messages and Captions',
               ['Ribbon sets work like gift wrap for words. After a thank-you, a congratulation or a birthday line, a '
                'ribbon with a small gift or flower makes the message feel finished.',
                'In bios, a ribbon at the start of a line gives a soft, neat look. Keep to one color family so the ribbon '
                'matches the symbols around it.']),
    'star': ('Star Sets in Captions and Cards',
             ['Stars suit short, warm messages: a thank-you, a congratulation, a good-luck note. Write the line first and '
              'let the star set close it, so the star feels like a small reward.',
              'On cards or notes you plan to print, pick a star set with a clear shape, since a set of simple symbols '
              'stays readable at any size.']),
    'ocean': ('Ocean Sets for Travel and Calm',
              ['Ocean sets pair well with photos of water, but they also work as a mood. A wave and a shell can set a calm '
               'tone for a bio, a playlist title or a note to yourself.',
               'For a holiday caption, name the place in text and add a short ocean set after it. The set tells people '
               'what the trip felt like, and the text tells them where it was.']),
    'japan': ('Japan Sets for Trips and Fans',
              ['Travel captions work best when the set follows the photo: ramen next to a bowl, a lantern set under a '
               'night market picture, a blossom set beside a park. The match makes the set feel earned.',
               'Fans of Japanese food and culture can use these sets as a quiet badge in a bio. Keep it to one subject, '
               'and add the city or dish name in text when you want to be specific.']),
}

for _slug, _section in _SECOND_SECTIONS.items():
    TAG_PAGES[_slug]['sections'].append(_section)
