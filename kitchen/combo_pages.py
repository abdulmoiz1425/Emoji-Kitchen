"""Data for the data-driven emoji combo category pages (/emoji-combos/<slug>/).

Each page is a dict: copyable emoji sets (``combos``), editorial ``sections``,
five FAQs, six Emoji Kitchen mashup pairs and the page's SEO strings. No number
that appears in copy is stored here: counts are derived from the data at render
time (see ``category_context`` in views.py). Mashup pairs are verified against
kitchen/data/emoji_combos.json by the test suite, and every emoji string is
unique inside its page and across all category pages.
"""

COMBO_PAGES = {'birthday': {'slug': 'birthday',
              'label': 'Birthday',
              'badge': '🎂 Birthday Emoji Combos',
              'title': 'Birthday Emoji Combos to Copy & Paste for Wishes',
              'meta': 'Copy and paste birthday emoji combos for wishes, captions and cards: sweet, party, funny and '
                      'belated sets, plus Emoji Kitchen party mashups.',
              'h1': 'Birthday Emoji Combos to Copy and Paste',
              'intro': ['A birthday message lands faster with a few well-chosen emojis. Pick a set below, tap Copy '
                        'and paste it into a wish, a story caption or a group chat.',
                        'The sets are grouped by tone: sweet wishes for family and friends, party sets for the day '
                        'itself, funny ones for friends who like a joke, and quick belated and thank-you sets. In a '
                        'text, two to four emojis is enough to let your words stand out.'],
              'filters': [('wishes', '🎂 Wishes'),
                          ('party', '🥳 Party'),
                          ('funny', '😂 Funny'),
                          ('thanks', '🙏 Belated & thanks')],
              'combos': [('wishes', 'Classic wish', '🎂🎉🎈'),
                         ('wishes', 'From the heart', '🎁💖🥳'),
                         ('wishes', 'Make a wish', '🎂🕯️✨'),
                         ('wishes', 'Flowers and cake', '🌹🎂💐'),
                         ('wishes', 'Bright new year', '🎈💛🌟'),
                         ('wishes', 'Toast to you', '🥂🎂🤍'),
                         ('wishes', 'Sweet day', '🧁🎀💗'),
                         ('wishes', 'Warm wishes', '🎂🫶🌷'),
                         ('wishes', 'Candle glow', '🕯️🧁🌟'),
                         ('wishes', 'Gift of love', '🎁❤️🌸'),
                         ('wishes', 'Sunny birthday', '☀️🎂🌻'),
                         ('wishes', 'Wishing you joy', '🌈🎈💛'),
                         ('wishes', 'Many happy returns', '🎉💐🥰'),
                         ('wishes', 'Pink cake', '🍰🎀🌸'),
                         ('wishes', 'Golden day', '👑🎂✨'),
                         ('wishes', 'Little wish', '🌠🕯️🤞'),
                         ('party', 'Dance floor', '🥳🎊🪩'),
                         ('party', 'Party kit', '🎉🎈🎁'),
                         ('party', 'Karaoke night', '🎤🎶🥳'),
                         ('party', 'Game night', '🍕🎂🎮'),
                         ('party', 'Dessert table', '🎂🍦🍓'),
                         ('party', 'Dancing', '🎊🎶💃'),
                         ('party', 'Pizza party', '🍕🎉🥤'),
                         ('party', 'Confetti pop', '🎊🍾🥳'),
                         ('party', 'Dance all night', '🕺💃🎶'),
                         ('party', 'Photo booth', '📸🥳🎩'),
                         ('party', 'Piñata time', '🪅🎉🍬'),
                         ('party', 'Sparklers', '🎇🎉🔥'),
                         ('party', 'Cake cutting', '🔪🎂📸'),
                         ('funny', 'Getting older', '🎂👴😂'),
                         ('funny', 'Too many candles', '🎂🔥🚒'),
                         ('funny', 'Birthday nap', '🥳🛌😴'),
                         ('funny', 'Cake first', '🍰🏃💨'),
                         ('funny', 'Clown energy', '🤡🎈🎂'),
                         ('funny', 'Silly dance', '🎉🕺🤪'),
                         ('funny', 'Another year', '📅🎂😅'),
                         ('funny', 'Old but gold', '🏆👵😂'),
                         ('funny', 'Wish for pizza', '🕯️🍕🤤'),
                         ('funny', 'Cake smash', '🎂🤪💥'),
                         ('funny', 'Age is a number', '🔢🎂🙄'),
                         ('funny', 'Diet starts tomorrow', '🥗🍰😏'),
                         ('funny', 'Party animal', '🦁🎉🕺'),
                         ('thanks', 'Belated wish', '⏰🎂🙈'),
                         ('thanks', 'Thank you', '🙏🥹💌'),
                         ('thanks', 'Thanks for the gift', '📩🎁🤍'),
                         ('thanks', 'Love you all', '🫶🎂🥰'),
                         ('thanks', 'Late but loving', '🐢🎂💌'),
                         ('thanks', 'Thank you all', '🙏🎉💕'),
                         ('thanks', 'Best day', '🥹📸🎂'),
                         ('thanks', 'Sweet messages', '💬💗🎂'),
                         ('thanks', 'Gift received', '📦🎁😍'),
                         ('thanks', 'Grateful', '🌼🙏🎂')],
              'sections': [('How to Write a Birthday Message With Emojis',
                            ['Say the wish in words first, then let the emojis add the mood. Put the name and one '
                             'warm sentence up front and finish with a set, for example: “Happy birthday, Sam! Hope '
                             'your day is full of cake. 🎂🎉🎈”.',
                             'Match the set to the person. A heart or flower set suits family and close friends, a '
                             'party set suits a group chat, and a joke set is best kept for friends who will get it. '
                             'For a card or a caption that will be read by many people, a short, clear set works '
                             'better than a long one.']),
                           ('What the Common Birthday Emojis Say',
                            ['🎂 is the celebration itself and 🎈 keeps the tone light. 🎁 says you thought of the '
                             'person, 🥳 is the “let’s celebrate” face, and 🕯️ points to the wish. A heart or flower '
                             'next to them makes the message warmer, and a joke emoji makes it playful.'])],
              'mashups': [('🎂', '🥳'), ('🎈', '🎁'), ('🥳', '🎈'), ('😍', '🎂'), ('🥰', '🎂'), ('🥳', '🧁')],
              'mashup_note': 'Mashups are pictures, so send them as an image or sticker rather than pasting them as '
                             'text.',
              'faqs': [('What emoji combo is best for a birthday wish?',
                        '🎂🎉🎈 is a simple starting point. Add a heart or flower for family and close friends, or a '
                        'joke emoji for friends who like humor. The words you write with it matter more than the '
                        'exact set.'),
                       ('Can I paste these into a birthday card or caption?',
                        'Yes. They are text characters, so they paste into captions, stories, cards and chats. Check '
                        'the preview before you post, because each app draws emoji in its own style.'),
                       ('How many emojis should I use in a birthday message?',
                        'Two to four is usually enough. Fewer emojis keep the message easy to read, especially on a '
                        'small screen.'),
                       ('Why does an emoji show up as a box on my friend’s phone?',
                        'Newer emojis such as 🥹 and 🫶 may not display on older devices. If the person has an older '
                        'phone, swap them for a classic emoji such as 🥰 or ❤️.'),
                       ('Can I make a birthday mashup image?',
                        'Sometimes. Emoji Kitchen supports some pairs, for example 🎂 + 🥳, but not every pair has a '
                        'mashup. Open the mixer, pick two emojis and the preview shows whether the pair is '
                        'supported.')],
              'siblings': [('friendship', 'friendship emoji combos'),
                           ('cute', 'cute emoji combos'),
                           ('funny', 'funny emoji combos')],
              'siblings_cta': 'Writing to someone close? See <a href="/emoji-combos/friendship/">friendship emoji '
                              'combos</a>. Want something sweeter? Try <a href="/emoji-combos/cute/">cute emoji '
                              'combos</a>. Planning a joke? Browse <a href="/emoji-combos/funny/">funny emoji '
                              'combos</a>.'},
 'sad': {'slug': 'sad',
         'label': 'Sad',
         'badge': '🥀 Sad Emoji Combos',
         'title': 'Sad Emoji Combos to Copy & Paste for Moods & Captions',
         'meta': 'Copy and paste sad emoji combos for hard days, heartbreak and quiet moods. Rainy, wilted and '
                 'broken-heart sets for captions, statuses and chats.',
         'h1': 'Sad Emoji Combos to Copy and Paste',
         'intro': ['Sometimes a single crying face does not say enough. These sad emoji combos pair faces with rain, '
                   'wilted flowers, hearts and moons to show how you feel in a status, a caption or a message to a '
                   'friend. Tap Copy and paste.',
                   'The sets are sorted by feeling: quietly sad, heartbroken, missing someone, tired, and sad but '
                   'trying to smile. A combo is a small way to signal your mood. If a low mood lasts or feels heavy, '
                   'talking to a friend, a family member or a local support service helps more than any emoji.'],
         'filters': [('quiet', '🌧️ Quiet'),
                     ('heartbreak', '💔 Heartbreak'),
                     ('missing', '🥺 Missing you'),
                     ('tired', '😮\u200d💨 Tired'),
                     ('smile', '🥲 Sad but smiling')],
         'combos': [('quiet', 'Rainy mood', '🌧️😔🤍'),
                    ('quiet', 'Late-night thoughts', '🌙🥺💭'),
                    ('quiet', 'Low light', '🕯️😞🖤'),
                    ('quiet', 'Foggy head', '😶\u200d🌫️☁️🤍'),
                    ('quiet', 'Wilting', '🥀🌧️😢'),
                    ('quiet', 'Staying in', '🛌🌧️😔'),
                    ('quiet', 'Gray sky', '☁️😔🖤'),
                    ('quiet', 'Candle and rain', '🕯️🌧️🥀'),
                    ('quiet', 'Silent room', '🔇🌙😶'),
                    ('quiet', 'Cold tea', '🍵😞🌫️'),
                    ('quiet', 'Blue hour', '🌆💙😔'),
                    ('heartbreak', 'Cried out', '💔😭🖤'),
                    ('heartbreak', 'Wilted love', '🥀💔😢'),
                    ('heartbreak', 'Unsent letter', '💌🥀💔'),
                    ('heartbreak', 'Healing slowly', '🩹💔🤍'),
                    ('heartbreak', 'Pieces', '🧩💔🌧️'),
                    ('heartbreak', 'Torn page', '📄💔🥀'),
                    ('heartbreak', 'Empty chair', '🪑💔🌙'),
                    ('heartbreak', 'Broken mirror', '🪞💔😢'),
                    ('heartbreak', 'Last goodbye', '👋💔🌧️'),
                    ('heartbreak', 'Mending slowly', '❤️\u200d🩹🥺🤍'),
                    ('missing', 'Waiting for a text', '📱🥺💭'),
                    ('missing', 'Miss you tonight', '🌙🤍🥺'),
                    ('missing', 'Far away', '✈️💔🌧️'),
                    ('missing', 'Call me', '📞🥺🤍'),
                    ('missing', 'Need a hug', '🫂🥺🤍'),
                    ('missing', 'Old photos', '📷🥺💭'),
                    ('missing', 'Voice note', '🎙️💭🥺'),
                    ('missing', 'Window seat', '🪟🌧️🥺'),
                    ('missing', 'Across the sea', '🌊💌🥺'),
                    ('missing', 'Miss home', '🏠🥺✈️'),
                    ('tired', 'Running on empty', '😮\u200d💨☕😴'),
                    ('tired', 'Low battery', '🪫😮\u200d💨💤'),
                    ('tired', 'Overthinking', '🫠🧠💭'),
                    ('tired', 'Too much', '😵\u200d💫📚☁️'),
                    ('tired', 'Heavy eyes', '🥱🌙☕'),
                    ('tired', 'Burnt out', '🔥😩🪫'),
                    ('tired', 'Sleep, please', '😴🛏️🌧️'),
                    ('tired', 'Need a break', '🫠📵💤'),
                    ('tired', 'Long week', '📆😮\u200d💨🥱'),
                    ('smile', 'Fine, really', '🥲☕🌧️'),
                    ('smile', 'Ice cream fixes it', '😭🍦💔'),
                    ('smile', 'Smiling through', '🥲🌈✨'),
                    ('smile', 'Tomorrow is new', '🥲🌅🤍'),
                    ('smile', 'Laughing and crying', '😂😭💔'),
                    ('smile', 'Keep going', '🥲💪✨'),
                    ('smile', 'Rain then rainbow', '🌧️🌈🥲'),
                    ('smile', 'Small joys', '🥲🍫🌷'),
                    ('smile', 'Okay-ish', '🙂🌧️🤍')],
         'sections': [('Pick the Right Level of Sad',
                       ['A quiet set such as 🌧️😔🤍 says “low today” without drama. A broken-heart set tells people '
                        'something specific happened. Sets for missing someone work best when the person will read '
                        'them, and tired or overthinking sets fit a status where friends already know the context.',
                        'Mixing one soft symbol, such as 🤍 or 🌙, into a sad set keeps it gentle. Piling on many '
                        'crying faces tends to read as a joke rather than a mood.']),
                      ('What the Common Sad Emojis Say',
                       ['🥺 asks for care, 😢 shows the sadness quietly and 😭 turns it up. 🥀 is a wilted flower, often '
                        'used for faded love, and 💔 is the broken heart. 🌧️ and 🌙 add weather and time of night to '
                        'the mood, and 🤍 softens the whole set.']),
                      ('A Note on Using Sad Emojis',
                       ['Emoji meanings change with the group. A set that reads as sincere to close friends can look '
                        'like a meme in a public caption. Check the tone before you post, and reach out directly to '
                        'a person when you need real support.'])],
         'mashups': [('🥺', '💔'), ('😢', '💔'), ('😭', '🌧️'), ('😔', '🖤'), ('🥀', '💔'), ('😢', '🥀')],
         'mashup_note': 'Mashups are pictures, so send them as an image or sticker rather than pasting them as text.',
         'faqs': [('What are sad emoji combos?',
                   'They are short groups of emojis, such as a crying face with rain or a wilted flower, used to '
                   'show a low or heartbroken mood in a message, status or caption.'),
                  ('Which sad emoji combo is the most gentle?',
                   'Sets that pair a soft face with a calm symbol, such as 🌧️😔🤍 or 🌙🥺💭, read as quiet sadness rather '
                   'than a big reaction.'),
                  ('Can I use these in an Instagram or WhatsApp status?',
                   'Yes. They are text characters, so they paste into statuses, captions, stories and chats. Preview '
                   'them first, because each app draws emoji in its own style.'),
                  ('Are sad emoji combos the same as Emoji Kitchen mashups?',
                   'No. A combo is separate emoji characters in a row. An Emoji Kitchen mashup blends two supported '
                   'emojis into one sticker-style image, and not every pair is supported.'),
                  ('What should I do if I feel very low?',
                   'An emoji can show a mood but it cannot replace support. Talk to someone you trust, or contact a '
                   'local support service.')],
         'siblings': [('aesthetic', 'aesthetic emoji combos'),
                      ('dark', 'dark emoji combos'),
                      ('love', 'love emoji combos')],
         'siblings_cta': 'For softer visuals see <a href="/emoji-combos/aesthetic/">aesthetic emoji combos</a>. For '
                         'moodier sets, browse <a href="/emoji-combos/dark/">dark emoji combos</a>. For the other '
                         'side of a heartbreak, try <a href="/emoji-combos/love/">love emoji combos</a>.'},
 'friendship': {'slug': 'friendship',
                'label': 'Friendship',
                'badge': '🫶 Friendship Emoji Combos',
                'title': 'Friendship Emoji Combos to Copy & Paste for Besties',
                'meta': 'Copy and paste friendship emoji combos for best friends, group chats and long-distance '
                        'friends: sweet, thank-you and funny sets for texts and captions.',
                'h1': 'Friendship Emoji Combos to Copy and Paste',
                'intro': ['Friendship emoji combos cover the things friends actually say: you matter to me, I am '
                          'here, thank you, and I cannot believe you did that. Tap Copy on a set and paste it into a '
                          'text, a caption or a group chat.',
                          'The sets are split by situation: besties, group chats, friends who live far away, '
                          'thank-you messages and chaotic-duo jokes. Friends often pick one matching set to use '
                          'together, which makes it feel like your own.'],
                'filters': [('bestie', '👯 Besties'),
                            ('group', '🍿 Group chat'),
                            ('far', '✈️ Long distance'),
                            ('thanks', '🙏 Thank you'),
                            ('funny', '😂 Funny')],
                'combos': [('bestie', 'Besties', '👯💗✨'),
                           ('bestie', 'Always there', '🤝💛😊'),
                           ('bestie', 'Two flowers', '👭💕🌸'),
                           ('bestie', 'Soft friendship', '🧸🫶🤍'),
                           ('bestie', 'Friends forever', '🧑\u200d🤝\u200d🧑💫♾️'),
                           ('bestie', 'Sunshine friend', '🌻🥰💛'),
                           ('bestie', 'Matching hearts', '💛🤝💛'),
                           ('bestie', 'Day ones', '🥇🫶💫'),
                           ('bestie', 'Soulmates', '🧿👯🤍'),
                           ('bestie', 'Best friends', '🏅💖🧑\u200d🤝\u200d🧑'),
                           ('bestie', 'Ride or die', '🏍️🔥🤝'),
                           ('bestie', 'Little secrets', '🤫💌👭'),
                           ('group', 'Movie night', '🍿🎬👯'),
                           ('group', 'Game night', '🍕🎮😂'),
                           ('group', 'Study buddies', '☕📖🧑\u200d🤝\u200d🧑'),
                           ('group', 'Road trip', '🎤🚗🎶'),
                           ('group', 'Night out', '🥂👯✨'),
                           ('group', 'Weekend plans', '🏖️🎒🌅'),
                           ('group', 'Brunch club', '🥞☕👯'),
                           ('group', 'Picnic day', '🧺🌳🍉'),
                           ('group', 'Concert squad', '🎤🎸🙌'),
                           ('group', 'Holiday crew', '✈️🧳🎉'),
                           ('group', 'Squad goals', '🙌🌟👯'),
                           ('group', 'Sleepover', '🛏️🍿🌙'),
                           ('far', 'Across the miles', '✈️💌🫶'),
                           ('far', 'Same sky', '🌍📱💛'),
                           ('far', 'Time zones apart', '🌙☀️🤝'),
                           ('far', 'Call soon', '📞🫶🤍'),
                           ('far', 'Video call', '💻😊💕'),
                           ('far', 'Letters', '✉️🕊️💛'),
                           ('far', 'Miss you, friend', '🥺🫂🌍'),
                           ('far', 'Count the days', '📅✈️🥰'),
                           ('far', 'Hearts apart', '🌎💞🌏'),
                           ('thanks', 'Thank you', '🙏💛🌷'),
                           ('thanks', 'You mean a lot', '🫶🥹✨'),
                           ('thanks', 'My hero', '🦸💛🙌'),
                           ('thanks', 'Thanks for listening', '👂🤍☕'),
                           ('thanks', 'Appreciate you', '🌷🤍🙏'),
                           ('thanks', 'Always supportive', '🫶📣💛'),
                           ('thanks', 'Sweet gesture', '🍫🎁🥹'),
                           ('thanks', 'Lifesaver', '🛟💛🙌'),
                           ('thanks', 'Thanks for coming', '🏠🥰🙌'),
                           ('funny', 'Chaos duo', '🤪👯😂'),
                           ('funny', 'Partners in snacks', '🍟🤝😋'),
                           ('funny', 'Wild idea', '💡😈🤝'),
                           ('funny', 'Who invited us', '🕶️😎🤝'),
                           ('funny', 'Snack thieves', '🍿🥷😂'),
                           ('funny', 'Trouble twins', '😜😜🔥'),
                           ('funny', 'Matching energy', '🤪🤝🤪'),
                           ('funny', 'Friend tax', '🍔💸😅'),
                           ('funny', 'Inside joke', '🤭🔒😂'),
                           ('funny', 'Bad ideas club', '🧠🚫😆')],
                'sections': [('Choosing a Set for the Friend You Have',
                              ['A close friend can handle a joke set or a sentimental one. A newer friend or a '
                               'coworker you are friendly with is better served by a light, clear set such as 🤝💛😊. '
                               'For a friend who has helped you through something, a thank-you set with a heart says '
                               'more than a row of party emojis.',
                               'Group chats work best with short sets that fit the activity, such as 🍿🎬👯 for a movie '
                               'plan. Use the same set each time and it can become the group’s sign.']),
                             ('What the Common Friendship Emojis Say',
                              ['🤝 usually means a deal or support rather than only friendship, so pair it with a '
                               'heart or smile. 🫶 and 🤍 carry warmth, 👯 is the playful best-friend pair and 🥹 shows '
                               'you are touched. 😂 and 🤪 set a joking tone.'])],
                'mashups': [('🤗', '💕'), ('🥰', '🤗'), ('🤗', '💛'), ('😂', '🥰'), ('😂', '😭'), ('🥰', '💛')],
                'mashup_note': 'Mashups are pictures, so send them as an image or sticker rather than pasting them '
                               'as text.',
                'faqs': [('What emoji combo means friendship?',
                          'There is no single one. 👯💗✨ and 🤝💛😊 are common for close friends. The hug and heart '
                          'emojis carry most of the warmth.'),
                         ('What can I send a friend who lives far away?',
                          'Sets with a plane, a globe or a phone, such as ✈️💌🫶 or 🌍📱💛, say you are thinking of them '
                          'across the distance.'),
                         ('Can I use the same combo with my friends in a group chat?',
                          'Yes. A shared set works like a small sign for the group. Pick something short so it is '
                          'easy to type or paste.'),
                         ('Do these work in WhatsApp and Instagram?',
                          'They are text characters, so they paste into most chat and social apps. The look differs '
                          'by app and device.'),
                         ('Is there a friendship mashup in Emoji Kitchen?',
                          'Some pairs exist, for example 🤗 + 💕, but not every pair is supported. Open the mixer, '
                          'choose two emojis and the preview shows whether the pair works.')],
                'siblings': [('birthday', 'birthday emoji combos'),
                             ('cute', 'cute emoji combos'),
                             ('funny', 'funny emoji combos')],
                'siblings_cta': 'Celebrating someone? See <a href="/emoji-combos/birthday/">birthday emoji '
                                'combos</a>. For sweeter sets, browse <a href="/emoji-combos/cute/">cute emoji '
                                'combos</a>. For jokes between friends, try <a href="/emoji-combos/funny/">funny '
                                'emoji combos</a>.'},
 'bio': {'slug': 'bio',
         'label': 'Bio',
         'badge': '✨ Emoji Combos for Bio',
         'title': 'Emoji Combos for Bio: Instagram, TikTok & Discord Sets',
         'meta': 'Copy and paste emoji combos for your bio on Instagram, TikTok, Discord and WhatsApp, with sets for '
                 'creators, students, gamers, travelers and more.',
         'h1': 'Emoji Combos for Your Bio: Instagram, TikTok, Discord and More',
         'intro': ['A bio gives you a few lines to say who you are, so each emoji has to earn its place. These emoji '
                   'combos for bios are sorted by interest and style. Tap Copy, paste it into your profile and edit '
                   'it to match you.',
                   'Use one emoji as a line starter, two or three as a divider, or a small set at the end of a short '
                   'line. Bio fields have their own length limits that differ by app, so check the limit before you '
                   'paste a long set.'],
         'filters': [('creator', '📸 Creator'),
                     ('student', '📚 Student'),
                     ('gamer', '🎮 Gamer'),
                     ('fitness', '💪 Fitness'),
                     ('travel', '✈️ Travel'),
                     ('food', '🍕 Food'),
                     ('soft', '🤍 Soft'),
                     ('work', '💼 Work')],
         'combos': [('creator', 'Photos', '📸✨🎞️'),
                    ('creator', 'Art', '🎨🖌️🫧'),
                    ('creator', 'Music', '🎧🎶🎹'),
                    ('creator', 'Writer', '✍️📚☕'),
                    ('creator', 'Builder', '💻🚀✨'),
                    ('creator', 'Video maker', '🎬🎥✨'),
                    ('creator', 'Designer', '🖍️📐💫'),
                    ('creator', 'Podcaster', '🎙️🎧💬'),
                    ('student', 'Study mode', '📚✏️🧠'),
                    ('student', 'Grad season', '🎓✨📖'),
                    ('student', 'Late library', '🌙📖🍎'),
                    ('student', 'Exam week', '📝⏰☕'),
                    ('student', 'Notes and highlighters', '🖍️📓🧠'),
                    ('student', 'Campus life', '🏫🎒🍂'),
                    ('gamer', 'Level up', '🎮🔥👾'),
                    ('gamer', 'Night session', '🕹️🌙🎧'),
                    ('gamer', 'Streamer', '🎙️🎮✨'),
                    ('gamer', 'Controller in hand', '🎮🏆😎'),
                    ('gamer', 'Pixel life', '👾🕹️💜'),
                    ('gamer', 'Late-night squad', '🎧🌙🎮'),
                    ('fitness', 'Gym', '🏋️🔥💪'),
                    ('fitness', 'Morning run', '🏃\u200d♀️🌅🥤'),
                    ('fitness', 'Yoga', '🧘🌿🤍'),
                    ('fitness', 'Cardio', '🚴💨💪'),
                    ('fitness', 'Hydrate', '💧🥗🏃'),
                    ('fitness', 'Stretch', '🤸🌞🤍'),
                    ('travel', 'On the road', '✈️🌍📸'),
                    ('travel', 'Trails', '🏔️🎒🌲'),
                    ('travel', 'Beach days', '🏝️🌊🍹'),
                    ('travel', 'Passport ready', '🛂✈️🗺️'),
                    ('travel', 'City break', '🏙️📷🥐'),
                    ('travel', 'Road trip', '🚗🎶🌄'),
                    ('food', 'Foodie', '🍕🍰☕'),
                    ('food', 'Spice lover', '🍜🌶️😋'),
                    ('food', 'Baker', '🧁🍓🤍'),
                    ('food', 'Coffee first', '☕🥐😌'),
                    ('food', 'Home cook', '🍳🥘🌿'),
                    ('food', 'Sweet tooth', '🍩🍫🍓'),
                    ('soft', 'Soft launch', '🤍🕊️✨'),
                    ('soft', 'Moon and mirror', '🌙🪞🫧'),
                    ('soft', 'Garden', '🌷☁️🦋'),
                    ('soft', 'Clouds', '☁️🌸🤍'),
                    ('soft', 'Quiet mind', '🕯️🌙📖'),
                    ('soft', 'Butterfly garden', '🦋🌼🍃'),
                    ('work', 'Open to collabs', '📩🤝💼'),
                    ('work', 'Ideas', '💡📈✅'),
                    ('work', 'Notes', '🧠✏️📍'),
                    ('work', 'Small business', '🛍️💌📦'),
                    ('work', 'Remote work', '💻☕🏡'),
                    ('work', 'Hiring', '📢🤝✨')],
         'sections': [('Three Ways to Lay Out a Bio With Emojis',
                       ['<strong>Line starters:</strong> one emoji at the start of each line, so every line has its '
                        'own label.',
                        '📸 Photos and stories<br>🌍 Always travelling<br>📩 Collabs: send a message',
                        '<strong>Dividers:</strong> a short set between two parts, for example your name and your '
                        'niche. <strong>Closers:</strong> a small set at the end of one line, such as ✨🤍. Pick one '
                        'layout and keep it consistent across your Instagram, TikTok and Discord profiles so people '
                        'recognize you.']),
                      ('Keep It Readable',
                       ['Two to four emojis per line is easier to scan than a long chain. Choose emojis that say '
                        'something about you, not just decoration, and leave out any that you cannot explain in a '
                        'few words. Check your bio on your own phone after saving, since each app and device draws '
                        'emoji its own way.']),
                      ('Emoji Combos for Different Apps',
                       ['The same set works as plain text on Instagram, TikTok, Discord, WhatsApp, X and most other '
                        'profile fields. For a Discord status or server name, keep it short. For a business or '
                        'professional profile, stay with one or two clear symbols such as 📩 or 📍. A mashup from '
                        'Emoji Kitchen is an image, so it cannot go into a bio field.'])],
         'mashups': [('🦋', '🌸'), ('😎', '🔥'), ('🌈', '😎'), ('☕', '😌'), ('🎧', '😌'), ('🌸', '😌')],
         'mashup_note': 'Mashups are images, so use them as a profile picture, story sticker or post, not inside the '
                        'bio text.',
         'faqs': [('How many emojis should I put in my bio?',
                   'Two to four per line is easy to read. A few short lines with one emoji each usually look cleaner '
                   'than one long chain.'),
                  ('Can I paste these into Instagram, TikTok and Discord?',
                   'Yes. They are ordinary emoji characters, so they paste into most bio fields. Check the length '
                   'limit of the app you are using.'),
                  ('Do emojis look the same on every phone?',
                   'No. Apple, Google, Samsung and other makers draw emoji in their own style, and newer emojis may '
                   'show as boxes on older devices. Check your bio on a phone after saving.'),
                  ('What emojis suit a professional bio?',
                   'One or two clear symbols, such as 📩 for contact or 📍 for location, are enough. Skip long '
                   'decorative chains.'),
                  ('Can I put an Emoji Kitchen mashup in my bio?',
                   'No. A mashup is an image, not a text character. Use it as a profile picture, a story or a '
                   'sticker.')],
         'siblings': [('aesthetic', 'aesthetic emoji combos'),
                      ('cute', 'cute emoji combos'),
                      ('dark', 'dark emoji combos')],
         'siblings_cta': 'For a coordinated look, see <a href="/emoji-combos/aesthetic/">aesthetic emoji combos</a>. '
                         'For friendly bios, browse <a href="/emoji-combos/cute/">cute emoji combos</a>. For a '
                         'moodier profile, try <a href="/emoji-combos/dark/">dark emoji combos</a>.'},
 'dark': {'slug': 'dark',
          'label': 'Dark',
          'badge': '🖤 Dark Emoji Combos',
          'title': 'Dark Emoji Combos to Copy & Paste: Gothic & Moody Sets',
          'meta': 'Copy and paste dark emoji combos in gothic, dark academia, witchy and dark feminine styles for '
                  'bios, captions and moody edits. Tap Copy to use one.',
          'h1': 'Dark Emoji Combos to Copy and Paste',
          'intro': ['Dark emoji combos use black hearts, candles, roses, moons, bats and old books to build a moody '
                    'look for a bio, a caption or a profile edit. Tap Copy on a set and paste it where you need it.',
                    'The sets are grouped by style: gothic, dark academia, witchy, dark feminine and edgy. They are '
                    'about atmosphere, so pair them with short text that fits the mood. For jokes, see <a '
                    'href="/emoji-combos/funny/">funny emoji combos</a>, which includes dark humor.'],
          'filters': [('gothic', '🦇 Gothic'),
                      ('academia', '📖 Dark academia'),
                      ('witchy', '🔮 Witchy'),
                      ('feminine', '🍷 Dark feminine'),
                      ('edgy', '⛓️ Edgy')],
          'combos': [('gothic', 'Gothic rose', '🖤🥀🕯️'),
                     ('gothic', 'Midnight castle', '🦇🌙🕸️'),
                     ('gothic', 'Webs', '🕷️🕸️🖤'),
                     ('gothic', 'Graveyard', '🪦🥀🕊️'),
                     ('gothic', 'Dark romance', '🍷🖤🌹'),
                     ('gothic', 'Thorns', '🗡️🥀🖤'),
                     ('gothic', 'Cathedral night', '⛪🌑🕯️'),
                     ('gothic', 'Black lace', '🖤🎀🕸️'),
                     ('gothic', 'Raven', '🐦\u200d⬛🌙🖤'),
                     ('academia', 'Dark academia', '📖🕯️☕'),
                     ('academia', 'Old letters', '🖋️📜🕯️'),
                     ('academia', 'Library rain', '🏛️🍂📚'),
                     ('academia', 'Chess night', '♟️🍷🖤'),
                     ('academia', 'Autumn study', '🍂📚☕'),
                     ('academia', 'Quill and ink', '🪶🖋️📜'),
                     ('academia', 'Oxford rain', '🌧️🏛️☕'),
                     ('academia', 'Candle study', '🕯️📚🌙'),
                     ('academia', 'Old books', '📚🗝️🍂'),
                     ('witchy', 'Mystic', '👁️🔮🌙'),
                     ('witchy', 'Witchy cat', '🐈\u200d⬛🌙🔮'),
                     ('witchy', 'Herb garden', '🌿🕯️🔮'),
                     ('witchy', 'Moon phases', '🌑🌓🌕'),
                     ('witchy', 'Crystal ball', '🔮✨🌙'),
                     ('witchy', 'Potion', '🧪🌿🕯️'),
                     ('witchy', 'Tarot', '🃏🌙🔮'),
                     ('witchy', 'Moon garden', '🌕🌿🦋'),
                     ('feminine', 'Dark feminine', '🖤💋🍷'),
                     ('feminine', 'Queen', '🌹🗡️👑'),
                     ('feminine', 'Mirror', '🪞🖤✨'),
                     ('feminine', 'Red and black', '🍒🖤💄'),
                     ('feminine', 'Red lips', '💄🍷🖤'),
                     ('feminine', 'Rose and thorn', '🌹🖤🗡️'),
                     ('feminine', 'Cherry wine', '🍒🍷🖤'),
                     ('edgy', 'Chains', '⛓️🖤🔥'),
                     ('edgy', 'Night wolf', '🌑🐺⛓️'),
                     ('edgy', 'Skull rose', '💀🌹🖤'),
                     ('edgy', 'Fire and night', '😈🔥🖤'),
                     ('edgy', 'Dark side', '🌑🖤🦇'),
                     ('edgy', 'Lightning', '⚡🖤🌑'),
                     ('edgy', 'Spiked', '⛓️💀🔥'),
                     ('edgy', 'Cold stare', '🥶🖤👁️'),
                     ('edgy', 'Black cat', '🐈\u200d⬛🖤😼'),
                     ('edgy', 'Midnight run', '🏍️🌃🖤'),
                     ('edgy', 'Thunder night', '🌩️🖤🦇')],
          'sections': [('How to Build a Dark Aesthetic Set',
                        ['Start with a color: 🖤 for black, 🍷 or 🌹 for deep red, 🌙 or 🌑 for night. Add one texture '
                         'such as 🕯️ for candlelight or 📖 for paper, and one accent such as 🦇 or 🔮. Three emojis in '
                         'this pattern usually look intentional, while a long mix of unrelated symbols looks messy.',
                         'Keep the text around the set short and quiet. A line of lowercase text next to 🖤🥀🕯️ fits '
                         'the look better than a long, loud caption.']),
                       ('What the Common Dark Emojis Say',
                        ['🖤 is the black heart and often marks a darker or more ironic mood. 🥀 is a wilted flower, '
                         '🕯️ adds candlelight and 🦇 and 🕸️ lean gothic. 🔮 and 🌙 point to the witchy style, while 📖 '
                         'and ♟️ lean dark academia. 🗡️ and ⛓️ read as edgy.'])],
          'mashups': [('🖤', '🔥'), ('💀', '🖤'), ('🦇', '🖤'), ('🥀', '🖤'), ('😈', '🔥'), ('💀', '🌹')],
          'mashup_note': 'Mashups are pictures, so send them as an image or sticker rather than pasting them as '
                         'text.',
          'faqs': [('What are dark emoji combos?',
                    'They are groups of emojis with a moody look, such as a black heart with a wilted rose and a '
                    'candle. People use them in bios, captions and profile edits.'),
                   ('What is the difference between dark academia and gothic sets?',
                    'Dark academia leans on books, candles, coffee and autumn. Gothic sets lean on roses, bats, webs '
                    'and graveyards. Both share black and deep red.'),
                   ('Can I use these in a bio or a username?',
                    'Yes. They are text characters. Some apps limit which characters a username can hold, so test '
                    'the set before you commit.'),
                   ('Are dark emoji combos only for a goth style?',
                    'No. Many people use a single 🖤 or 🕯️ to add a calm, moody touch to an otherwise simple bio.'),
                   ('Is there a dark Emoji Kitchen mashup?',
                    'Some pairs exist, for example 🖤 + 🔥 and 🦇 + 🖤. Not every pair is supported, so check the '
                    'preview in the mixer.')],
          'siblings': [('aesthetic', 'aesthetic emoji combos'),
                       ('sad', 'sad emoji combos'),
                       ('funny', 'funny emoji combos')],
          'siblings_cta': 'For a lighter style, see <a href="/emoji-combos/aesthetic/">aesthetic emoji combos</a>. '
                          'For low-mood sets, browse <a href="/emoji-combos/sad/">sad emoji combos</a>. For dark '
                          'humor, try <a href="/emoji-combos/funny/">funny emoji combos</a>.'},
 'christmas': {'slug': 'christmas',
               'label': 'Christmas',
               'badge': '🎄 Christmas Emoji Combos',
               'title': 'Christmas Emoji Combos to Copy & Paste for Cards & Chats',
               'meta': 'Copy and paste Christmas emoji combos for greetings, captions and group chats: cozy, '
                       'festive, funny and New Year sets. Tap Copy to use any set.',
               'h1': 'Christmas Emoji Combos to Copy and Paste',
               'intro': ['Christmas emoji combos bring trees, gifts, snow and warm drinks together for greetings, '
                         'captions and family group chats. Tap Copy on a set and paste it into your message.',
                         'The sets are grouped by feeling: cozy nights in, festive and bright, funny holiday '
                         'moments, and wishes that bridge into the New Year. A set that matches the words you write '
                         'looks better than a long row of festive symbols.'],
               'filters': [('cozy', '☕ Cozy'),
                           ('festive', '🎄 Festive'),
                           ('funny', '😂 Funny'),
                           ('wishes', '🥂 Wishes')],
               'combos': [('cozy', 'Cozy night', '☕🎄📖'),
                          ('cozy', 'Candlelight', '🕯️🎄🤍'),
                          ('cozy', 'Warm scarf', '🍫☕🧣'),
                          ('cozy', 'Snowed in', '🌨️🏠🕯️'),
                          ('cozy', 'Cold hands', '🥶🧣☕'),
                          ('cozy', 'Cookies and milk', '🍪🥛🎅'),
                          ('cozy', 'Hot chocolate', '🍫☕🧸'),
                          ('cozy', 'Fireplace', '🔥🧦📖'),
                          ('cozy', 'Blanket night', '🛋️🧣🍿'),
                          ('cozy', 'Gingerbread', '🍪🏠🕯️'),
                          ('cozy', 'Cabin snow', '🏔️🏡❄️'),
                          ('festive', 'Tree and gifts', '🎄🎁🌟'),
                          ('festive', 'Snowman', '☃️❄️🧣'),
                          ('festive', 'Reindeer', '🦌🌟🎄'),
                          ('festive', 'Bells', '🔔🎶🎄'),
                          ('festive', 'Red and green', '🎁💚❤️'),
                          ('festive', 'Star on top', '⭐🎄❤️'),
                          ('festive', 'Warm socks', '🧦🎁🔥'),
                          ('festive', 'Candy cane', '🍬❤️🎄'),
                          ('festive', 'Santa’s sleigh', '🛷🎅🌟'),
                          ('festive', 'Gift tags', '🏷️🎁🎀'),
                          ('festive', 'Winter wonderland', '⛄❄️✨'),
                          ('festive', 'Twinkle lights', '💡🎄✨'),
                          ('funny', 'Santa’s cheat day', '🎅🍕😂'),
                          ('funny', 'Tangled lights', '🎄🔌😬'),
                          ('funny', 'Who ate the cookies', '🍪🙈🎅'),
                          ('funny', 'Gift wrapping', '🎁✂️😵\u200d💫'),
                          ('funny', 'Elf on duty', '🧝🎄👀'),
                          ('funny', 'Grinch mood', '😒💚🎄'),
                          ('funny', 'Fruitcake', '🍰😬🎄'),
                          ('funny', 'Ugly sweater', '🧶🎅😂'),
                          ('funny', 'Alarm at dawn', '⏰🎁🏃'),
                          ('wishes', 'Merry Christmas', '🎅🎄❤️'),
                          ('wishes', 'Family time', '👨\u200d👩\u200d👧\u200d👦🎄🤍'),
                          ('wishes', 'Peace and joy', '🕊️🌟🎄'),
                          ('wishes', 'Merry and bright', '✨🎄🎁'),
                          ('wishes', 'New Year toast', '🥂🎆✨'),
                          ('wishes', 'Fresh start', '🎆🥂🤍'),
                          ('wishes', 'Season’s greetings', '❄️🤍🎄'),
                          ('wishes', 'Warm holidays', '🏠❤️🎁'),
                          ('wishes', 'Joy to the world', '🌍🎶🕊️'),
                          ('wishes', 'Happy holidays', '⛄🎁✨'),
                          ('wishes', 'Christmas Eve', '🌙🎄🕯️'),
                          ('wishes', 'Cheers to next year', '🥂🌟🎇')],
               'sections': [('Writing a Christmas Greeting With Emojis',
                             ['Lead with the words and let two or three emojis finish the line, for example: “Merry '
                              'Christmas, everyone! Wishing you a warm and happy holiday. 🎄🎁✨”. For a group that '
                              'celebrates different holidays, a general greeting such as “happy holidays” with ❄️ or '
                              '✨ keeps it open to everyone.',
                              'For a card or a caption, pick one theme, such as cozy or festive, and stay with it. A '
                              'tree, a gift and a star make a complete set on their own.']),
                            ('What the Common Christmas Emojis Say',
                             ['🎄 and 🎁 are the core of the season, 🎅 adds the Santa and cookies jokes, and ☃️ and ❄️ '
                              'set the winter scene. ☕, 🍫 and 🧣 bring in warmth and coziness. 🥂 and 🎆 turn the '
                              'greeting toward the New Year.']),
                            ('Christmas Mashups in Emoji Kitchen',
                             ['Emoji Kitchen does not have mashups for 🎄, 🎅, ☃️ or ❄️. It does have pairs with 🎁, so '
                              'you can make gift-themed stickers. Pairs vary, so check the preview in the mixer.'])],
               'mashups': [('🎁', '❤️'), ('🎁', '🥰'), ('🎁', '🥳'), ('🎁', '🌟'), ('🎁', '💝'), ('🎁', '☕')],
               'mashup_note': 'These are gift-based pairs because Emoji Kitchen has no mashups for 🎄, 🎅, ☃️ or ❄️. '
                              'Mashups are pictures, so send them as an image or sticker.',
               'faqs': [('What emoji combo is good for a Christmas greeting?',
                         '🎄🎁✨ is a simple choice. Add ❤️ for family, 🎅 for kids and a joke, or 🥂 to look ahead to '
                         'the New Year.'),
                        ('Can I paste these into a Christmas card or a family chat?',
                         'Yes. They are text characters, so they paste into cards, captions and chats. Check the '
                         'preview first, because each app draws emoji in its own style.'),
                        ('What if my group celebrates different holidays?',
                         'Use a general greeting such as “happy holidays” with a neutral symbol like ❄️ or ✨, and '
                         'keep Christmas sets for people who celebrate it.'),
                        ('Why do some emojis show as boxes?',
                         'Newer emojis may not display on older devices. If a friend has an old phone, use classic '
                         'ones such as 🎄, 🎁 and ⭐.'),
                        ('Does Emoji Kitchen have Christmas mashups?',
                         'Not for 🎄, 🎅, ☃️ or ❄️. It does have pairs with 🎁, so you can mix a gift with a heart, a '
                         'face or a star.')],
               'siblings': [('birthday', 'birthday emoji combos'),
                            ('friendship', 'friendship emoji combos'),
                            ('cute', 'cute emoji combos')],
               'siblings_cta': 'Planning a party? See <a href="/emoji-combos/birthday/">birthday emoji combos</a>. '
                               'Sending to friends? Browse <a href="/emoji-combos/friendship/">friendship emoji '
                               'combos</a>. For sweeter sets, try <a href="/emoji-combos/cute/">cute emoji '
                               'combos</a>.'}}
