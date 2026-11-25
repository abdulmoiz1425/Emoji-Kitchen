"""Mood finder: turn a sentence about how someone feels into emoji combos.

This is a rule-based engine, not an AI model. It reads the feeling words in the text (including phrases such as
"can't wait", negation such as "not happy", and intensifiers such as "so tired"), picks up to three moods, and then:

* returns a few hand-written signature sets for those moods,
* builds new combos by mixing the lead, support and accent emoji of the moods,
* pulls matching sets from the site's existing library (see combo_search.py), and
* suggests Emoji Kitchen mashup pairs.

The output is deterministic for the same text and shuffle number, so a results page can be shared or reloaded.
Nothing is stored. Every emoji in the pools, signature sets and mashup pairs is checked by the test suite.
"""
import random
import re

from . import combo_search

MAX_TEXT_LENGTH = 140
MAX_MOODS = 3
GENERATED_COUNT = 8
LIBRARY_COUNT = 8
MAX_SHUFFLE = 99

MOODS = {}


def _m(key, label, icon, tagline, words, lead, support, accent, sets, mashups, terms, opposite=None):
    MOODS[key] = {
        'key': key, 'label': label, 'icon': icon, 'tagline': tagline,
        'words': words,
        'lead': lead.split(), 'support': support.split(), 'accent': accent.split(),
        'sets': sets, 'mashups': mashups, 'terms': terms, 'opposite': opposite,
    }


_m('happy', 'Happy', '😊', 'Bright and sunny',
   ['happy', 'happiness', 'joy', 'joyful', 'glad', 'cheerful', 'delighted', 'smiling', 'good mood', 'great day',
    'wonderful', 'fantastic', 'awesome', 'yay', 'content', 'pleased', 'feeling good', 'feel good', 'feeling great',
    'sunny', 'good vibes'],
   '😊 😄 🥰 😁 ☺️', '🌞 🌈 🌸 🎈 💛 ✨ 🌻', '✨ 💫 🌟 💛 🎶',
   [('Sunny smile', '😊☀️✨'), ('Sunflower joy', '🌻😄💛'), ('Rainbow day', '🌈😁🎈')],
   [('🥰', '🌸'), ('🌟', '🌈')], ['happy', 'smile', 'sun'], opposite='sad')

_m('excited', 'Excited', '🤩', 'Buzzing with energy',
   ['excited', 'excitement', 'thrilled', 'pumped', 'hyped', "can't wait", 'cant wait', 'stoked', 'eager', 'so ready',
    'big news', 'good news', 'looking forward', 'amazing news'],
   '🤩 🥳 😆 🙌 😍', '🎉 🔥 🚀 🎊 💥 ⚡', '✨ 🌟 💫 🎆 ⭐',
   [('Big news', '🤩🎉✨'), ('Launch mode', '🚀🔥🙌'), ('Confetti burst', '🥳🎊💥')],
   [('🤯', '🚀'), ('😍', '🔥')], ['party', 'confetti', 'fireworks'])

_m('love', 'In love', '🥰', 'Warm and romantic',
   ['love', 'in love', 'crush', 'romantic', 'adore', 'affection', 'sweetheart', 'darling', 'valentine', 'my person',
    'date night', 'babe', 'soulmate', 'smitten', 'butterflies'],
   '🥰 😍 😘 💕 🫶', '🌹 💌 💗 🌷 💞 💘', '✨ 🌸 🕊️ 💖 🎀',
   [('Love letter', '🥰💌🌹'), ('Heart eyes', '😍💗🌷'), ('Soft love', '🫶💞🌸')],
   [('💘', '🎀'), ('💕', '🌈')], ['love', 'heart', 'romantic'], opposite='heartbroken')

_m('sad', 'Sad', '😢', 'Quiet and heavy',
   ['sad', 'unhappy', 'down', 'blue', 'crying', 'cry', 'tears', 'hurt', 'upset', 'depressed', 'gloomy', 'feeling low',
    'not okay', 'miserable', 'low', 'heavy heart', 'rough day', 'bad day'],
   '😢 🥺 😔 😞 😭', '🌧️ 💔 🥀 🌙 ☔ 🩶', '💭 🕊️ 🍂 🤍 🫂',
   [('Rainy mood', '😔🌧️💭'), ('Wilted rose', '🥺🥀🤍'), ('Need a hug', '😭☔🫂')],
   [('😭', '💔'), ('🥺', '🎀')], ['sad', 'rain', 'tears'], opposite='happy')

_m('heartbroken', 'Heartbroken', '💔', 'Aching but healing',
   ['heartbroken', 'breakup', 'broke up', 'broken heart', 'dumped', 'ex', 'heartache', 'ghosted', 'cheated',
    'heartbreak', 'got over', 'moving on'],
   '💔 😭 🥀 😞 🖤', '🌧️ 🥺 🩹 🌙 🍂', '💭 🕊️ 🩹 🤍 🌱',
   [('Heartache', '💔🌧️🥀'), ('Night tears', '😭🖤🌙'), ('Healing slowly', '🥺🩹🤍')],
   [('😭', '💔'), ('💔', '🌧️')], ['heartbreak', 'broken', 'missing'])

_m('angry', 'Angry', '😡', 'Hot and fed up',
   ['angry', 'mad', 'furious', 'annoyed', 'irritated', 'rage', 'pissed', 'frustrated', 'hate', 'fed up', 'so done',
    'livid', 'had enough', 'annoying'],
   '😡 😤 🤬 💢 😠', '🔥 💥 ⚡ 🌋 👊', '💢 🖤 🌪️ ❗ 🚫',
   [('Seeing red', '😡🔥💢'), ('Steam', '😤💥🌋'), ('Storm', '🤬⚡🖤')],
   [('😱', '👻'), ('🔥', '💧')], ['angry', 'fire', 'dark'], opposite='chill')

_m('anxious', 'Anxious', '😰', 'On edge, hoping for calm',
   ['anxious', 'anxiety', 'nervous', 'worried', 'worry', 'scared', 'afraid', 'panic', 'overthinking', 'uneasy',
    'on edge', 'jittery', 'nerve wracking'],
   '😰 😬 😟 🥴 😨', '🌀 💭 🫣 🌪️ 🌧️', '🤞 🕊️ 🫶 🌿 🍀',
   [('Fingers crossed', '😰💭🤞'), ('Spiral', '😬🌀🫶'), ('Grey sky', '😟🌧️🌿')],
   [('😱', '👻'), ('🥺', '🎀')], ['nervous', 'worry', 'calm'], opposite='chill')

_m('stressed', 'Stressed', '😩', 'Overloaded, need a break',
   ['stressed', 'stress', 'overwhelmed', 'pressure', 'deadline', 'burnt out', 'burnout', 'busy', 'exam', 'swamped',
    'too much', 'hectic', 'exams'],
   '😩 🫠 😫 🤯 😵', '📚 ⏰ ☕ 💼 🌀 📝', '🕯️ 🧘 🫶 🍵 🌿',
   [('Study stress', '😩📚☕'), ('Deadline', '🫠⏰💼'), ('Mind blown', '🤯🌀🧘')],
   [('🤯', '🚀'), ('🐸', '☕')], ['study', 'coffee', 'work'], opposite='chill')

_m('tired', 'Tired', '😴', 'Low battery',
   ['tired', 'sleepy', 'exhausted', 'drained', 'sleep', 'nap', 'yawn', 'fatigued', 'lazy', 'no energy', 'worn out',
    'need sleep', 'sleepyhead'],
   '😴 🥱 😪 😌 🛌', '🌙 ☕ 🛏️ 💤 🧸 🕯️', '💤 🌙 ⭐ 🤍 ☁️',
   [('Sleepy moon', '😴🌙💤'), ('Coffee first', '🥱☕🛏️'), ('Cloud nap', '😪🧸☁️')],
   [('🐸', '☕'), ('🥺', '🎀')], ['sleepy', 'nap', 'coffee'], opposite='motivated')

_m('chill', 'Chill', '😌', 'Calm and easy',
   ['chill', 'relaxed', 'calm', 'peaceful', 'relax', 'laid back', 'serene', 'zen', 'mellow', 'taking it easy',
    'vibing', 'vibe', 'at peace'],
   '😌 😎 🙂 🧘', '🌿 🌊 ☁️ 🍃 ☕ 🎧', '✨ 🕊️ 🌅 🤍 🌙',
   [('Soft cloud', '😌🌿☁️'), ('Ocean playlist', '😎🌊🎧'), ('Breathe', '🧘🍃🕊️')],
   [('🌊', '🌴'), ('😎', '🌈')], ['calm', 'chill', 'ocean'])

_m('lonely', 'Lonely', '🥺', 'Missing someone',
   ['lonely', 'alone', 'miss you', 'missing', 'isolated', 'homesick', 'abandoned', 'by myself', 'no one', 'miss'],
   '🥺 😔 🫂 😞 🥹', '🌙 💭 🪟 📱 🌧️', '🤍 🕯️ 💌 ⭐ 🫶',
   [('Late night', '🥺🌙💭'), ('Waiting on a text', '😔📱💌'), ('Warm candle', '🫂🕯️🤍')],
   [('🥺', '🎀'), ('😭', '💔')], ['missing', 'alone', 'night'])

_m('grateful', 'Grateful', '🙏', 'Thankful and warm',
   ['grateful', 'thankful', 'thanks', 'thank you', 'blessed', 'appreciate', 'appreciation', 'gratitude'],
   '🙏 🥹 🤗 😇 💖', '🌸 🌻 🤝 💐 ✨ 🕊️', '💛 🌟 🤍 🌈 🎀',
   [('Thank you', '🙏💛✨'), ('Flowers for you', '🥹💐🤍'), ('Warm hug', '🤗🌻🕊️')],
   [('🥰', '🤗'), ('🤗', '💕')], ['thank', 'grateful', 'flowers'])

_m('proud', 'Proud', '😎', 'Winning energy',
   ['proud', 'accomplished', 'achievement', 'won', 'win', 'winning', 'victory', 'success', 'graduated', 'promotion',
    'nailed', 'did it', 'killed it', 'passed', 'promoted'],
   '😎 🥳 💪 🙌 😁', '🏆 🥇 🎓 🎉 👑 🔥', '✨ 🌟 💯 🎊 ⭐',
   [('Trophy shine', '😎🏆✨'), ('Graduation', '🥳🎓🎉'), ('Gold medal', '💪🥇🔥')],
   [('😎', '🌈'), ('🌟', '🌈')], ['trophy', 'star', 'praise'])

_m('motivated', 'Motivated', '💪', 'Locked in',
   ['motivated', 'determined', 'focused', 'driven', 'productive', 'hustle', 'grind', 'workout', 'gym', 'goals',
    'inspired', "let's go", 'lets go', 'ambitious', 'get it done', 'on a roll'],
   '💪 🔥 😤 🏋️ 🚀', '🎯 📈 ⚡ 🏆 ⏰ 📚', '✨ 💯 🌅 ⭐ 🙌',
   [('Locked in', '💪🔥🎯'), ('Going up', '🚀📈⚡'), ('Gym day', '🏋️🏆💯')],
   [('🤯', '🚀'), ('😍', '🔥')], ['gym', 'goal', 'power'])

_m('silly', 'Silly', '🤪', 'Playful chaos',
   ['silly', 'goofy', 'funny', 'crazy', 'hilarious', 'joke', 'lol', 'lmao', 'haha', 'playful', 'weird', 'chaotic',
    'losing it', 'dying laughing', 'laughing'],
   '🤪 😂 🤣 😜 🥴', '🤡 🎭 🍌 🦄 🙈 🎪', '💀 ✨ 🌈 🎉 🔥',
   [('Clown mode', '🤪🤡🎉'), ('I am dead', '😂💀🙈'), ('Banana brain', '🤣🍌🌈')],
   [('😂', '💀'), ('😂', '🥰')], ['funny', 'joke', 'silly'])

_m('bored', 'Bored', '😐', 'Nothing going on',
   ['bored', 'boring', 'nothing to do', 'meh', 'dull', 'so bored', 'uninterested'],
   '😐 🥱 🙄 😑 🫤', '📱 🛋️ 🍿 ⏳ 🎮 🧩', '💤 🌀 ☁️ 🍕 🎧',
   [('Scrolling', '😐📱🛋️'), ('Waiting', '🥱🍿⏳'), ('Game time', '🙄🎮🧩')],
   [('🍿', '🎬'), ('🐸', '☕')], ['bored', 'snack', 'game'], opposite='excited')

_m('confused', 'Confused', '🤔', 'Wondering what is going on',
   ['confused', 'puzzled', 'unsure', 'thinking', 'wondering', 'lost', 'idk', 'hmm', 'no idea', 'uncertain',
    "what's going on", 'whats going on', 'confusing'],
   '🤔 😕 🧐 🤨 😵', '❓ 💭 🔍 🧩 🌀 📚', '💡 🤷 ✨ 🌫️ 🕯️',
   [('Big question', '🤔💭❓'), ('Missing piece', '😕🧩🔍'), ('Lightbulb soon', '🧐📚💡')],
   [('🤯', '🚀'), ('😱', '👻')], ['think', 'question', 'mystery'])

_m('hungry', 'Hungry', '🍕', 'Snack time',
   ['hungry', 'food', 'starving', 'snack', 'pizza', 'craving', 'dinner', 'lunch', 'breakfast', 'eat', 'eating',
    'foodie', 'so hungry', 'dessert', 'brunch'],
   '🤤 😋 🍕 🍔 🍜', '🍟 🍩 🌮 🍣 🥐 🍰', '😋 ✨ 🔥 🧁 ☕',
   [('Pizza time', '🤤🍕🍟'), ('Noodle night', '😋🍜🥢'), ('Sweet tooth', '🍩🍰☕')],
   [('🍕', '🔥'), ('🍩', '🌈')], ['pizza', 'food', 'sweet'])

_m('cozy', 'Cozy', '🧸', 'Warm and snug',
   ['cozy', 'cosy', 'comfy', 'snug', 'warm', 'blanket', 'hot chocolate', 'winter', 'at home', 'rainy day', 'rain',
    'fireplace', 'candle', 'movie night', 'hygge'],
   '🧸 ☕ 🥰 😌 🛋️', '🧣 🕯️ 🍫 📖 🌧️ 🍂', '🤍 ✨ ❄️ 🔥 🍪',
   [('Warm scarf', '🧸☕🧣'), ('Reading nook', '🕯️📖🛋️'), ('Rainy cocoa', '🍫🌧️🍪')],
   [('🥰', '🌸'), ('🧁', '🌈')], ['cozy', 'warm', 'blanket'])

_m('nostalgic', 'Nostalgic', '🌅', 'Remembering the good old days',
   ['nostalgic', 'nostalgia', 'memories', 'memory', 'remember', 'childhood', 'old days', 'throwback', 'good old',
    'back then', 'those days', 'miss the old'],
   '🥹 🌅 😌 📼 🕰️', '📷 🎞️ 💿 🧸 🌇', '✨ 🤍 🍂 💭 🎶',
   [('Old photos', '🥹📷🎞️'), ('Golden hour', '🌅🕰️💭'), ('Mixtape', '📼💿🎶')],
   [('🥺', '🎀'), ('🌟', '🌈')], ['memory', 'photo', 'sunset'])

_m('hopeful', 'Hopeful', '🌈', 'Looking up',
   ['hopeful', 'hope', 'optimistic', 'wish', 'wishing', 'dream', 'dreams', 'looking forward', 'better days',
    'positive', 'fingers crossed', 'faith'],
   '🌈 🤞 🙏 🌅 🌱', '⭐ 🌠 🕊️ 🌻 🍀 🌤️', '✨ 💫 🤍 🌿 🕯️',
   [('Fingers crossed', '🌈🤞✨'), ('New growth', '🌱🌤️🕊️'), ('Make a wish', '🌠🙏💫')],
   [('🌟', '🌈'), ('🦄', '🌈')], ['wish', 'rainbow', 'star'])

_m('cute', 'Cute', '🐰', 'Soft and sweet',
   ['cute', 'adorable', 'sweet', 'soft', 'kawaii', 'aww', 'pretty', 'so cute', 'precious', 'tiny', 'fluffy'],
   '🥺 🐰 🐱 🥰 🧸', '🎀 🌸 🍓 🍰 🫧 🐾', '💗 ✨ 🤍 🌷 ☁️',
   [('Bow bunny', '🐰🎀🌸'), ('Strawberry bear', '🧸🍓💗'), ('Bubble kitten', '🐱🫧🤍')],
   [('🐰', '🌸'), ('🥺', '🎀')], ['cute', 'adorable', 'kawaii'])

_m('party', 'Celebrating', '🥳', 'Party mode',
   ['party', 'celebrate', 'celebrating', 'celebration', 'birthday', 'congrats', 'congratulations', 'festive',
    'cheers', 'weekend', 'friday', "let's party", 'holiday', 'new year'],
   '🥳 🎉 🤩 🕺 💃', '🎂 🥂 🎈 🪩 🎊 🍾', '✨ 🎁 🔥 🌟 🎶',
   [('Birthday', '🥳🎂🎈'), ('Cheers', '🎉🥂✨'), ('Dance floor', '🕺🪩🎶')],
   [('😍', '🔥'), ('😂', '🥰')], ['party', 'birthday', 'celebrate'])

_m('sick', 'Under the weather', '🤒', 'Rest and tea',
   ['sick', 'ill', 'unwell', 'fever', 'cold', 'flu', 'headache', 'not feeling well', 'nauseous', 'under the weather',
    'coughing', 'cough'],
   '🤒 🤧 🥴 😷 🤢', '🛏️ 🍵 💊 🌡️ 🍲 🧣', '💤 🤍 🌿 🫶 🕯️',
   [('Bed rest', '🤒🛏️🍵'), ('Soup and scarf', '🤧🧣🍲'), ('Medicine', '😷💊🌡️')],
   [('🥺', '🎀'), ('🐸', '☕')], ['sleepy', 'tea', 'soup'])

_m('embarrassed', 'Embarrassed', '😳', 'Awkward blush',
   ['embarrassed', 'embarrassing', 'shy', 'awkward', 'blushing', 'cringe', 'ashamed', 'so awkward', 'flustered'],
   '😳 🙈 😅 🫣 😬', '🙊 🌸 💦 🍅 🫠 🌷', '🤭 ✨ 💗 🙃 🍓',
   [('Red face', '😳🙈💦'), ('Peeking', '😅🫣🍅'), ('Melting', '🫠🌸🤭')],
   [('😱', '👻'), ('🥺', '🎀')], ['shy', 'blush', 'oops'])

_m('vacation', 'Vacation mode', '🏖️', 'Sun, sea and snacks',
   ['vacation', 'holiday', 'beach', 'trip', 'travel', 'summer', 'sunshine', 'road trip', 'getaway', 'flight',
    'airport', 'tropical', 'adventure'],
   '😎 🏖️ ✈️ 🌴 🤩', '🌊 🍹 🧳 🗺️ 🌅 🐚', '☀️ ✨ 🌺 🕶️ 🍍',
   [('Beach day', '😎🏖️🍹'), ('Packed bags', '✈️🧳🌍'), ('Palm sunset', '🌴🌊🌅')],
   [('🌊', '🌴'), ('😎', '🌈')], ['beach', 'ocean', 'travel'])

_m('confident', 'Confident', '💅', 'Main character energy',
   ['confident', 'sassy', 'boss', 'slay', 'slaying', 'queen', 'king', 'fierce', 'baddie', 'glow', 'main character',
    'unstoppable', 'bold', 'glowing'],
   '💅 😎 👑 😏 🔥', '💄 ✨ 💎 👠 🪞 🖤', '💯 🌟 💋 ⚡ 🔥',
   [('Crown on', '💅👑✨'), ('Diamond', '😎💎🔥'), ('Heels', '😏👠🖤')],
   [('😎', '🌈'), ('😍', '🔥')], ['main', 'glow', 'queen'])

_m('creative', 'Creative', '🎨', 'Making something',
   ['creative', 'art', 'drawing', 'painting', 'music', 'writing', 'design', 'craft', 'crafting', 'imagination',
    'making art', 'songwriting'],
   '🎨 🎶 ✍️ 🖌️ 💡', '🌈 🎧 📖 ✂️ 🧵 🎭', '✨ 💫 🌸 🪄 🦋',
   [('Paint box', '🎨🌈✨'), ('Studio', '🎶🎧💫'), ('Story time', '✍️📖🪄')],
   [('🦄', '🌈'), ('🌷', '🦋')], ['art', 'music', 'magic'])

_m('surprised', 'Surprised', '😲', 'Did not see that coming',
   ['surprised', 'shocked', 'wow', 'omg', 'unbelievable', 'speechless', 'no way', "can't believe", 'cant believe',
    'astonished', 'gasp', 'what the', 'shocking'],
   '😲 😱 🤯 😮 🫢', '💥 ❗ 👀 🤭 🌪️ 🎢', '✨ 🔥 💫 🙌 ⚡',
   [('Gasp', '😲💥❗'), ('Mind blown', '🤯👀🔥'), ('Rollercoaster', '😱🎢💫')],
   [('🤯', '🚀'), ('😱', '👻')], ['wow', 'shock', 'mind'])

_m('goodnight', 'Good night', '🌙', 'Time for bed',
   ['good night', 'goodnight', 'bedtime', 'sweet dreams', 'going to bed', 'off to bed', 'nighty', 'night night'],
   '😴 🌙 🥱 😌 🛌', '⭐ 💤 🧸 🕯️ ☁️ 🌌', '🤍 ✨ 💫 🌠 🫶',
   [('Moon and stars', '🌙💤⭐'), ('Teddy dreams', '😴🧸☁️'), ('Night sky', '🌌🕯️🤍')],
   [('🥺', '🎀'), ('🌟', '🌈')], ['night', 'moon', 'sleepy'])

_m('goodmorning', 'Good morning', '🌞', 'Fresh start',
   ['good morning', 'morning', 'sunrise', 'wake up', 'rise and shine', 'new day', 'fresh start', 'woke up'],
   '🌞 😊 ☀️ 🥰 😄', '☕ 🌻 🌅 🥐 🐦 🌈', '✨ 💛 🌼 🌟 🍊',
   [('Coffee sun', '🌞☕🌻'), ('Breakfast', '☀️🥐🐦'), ('Sunrise', '🌅🌈💛')],
   [('😊', '🌈'), ('🌟', '🌈')], ['morning', 'sunrise', 'coffee'])

# Order the moods appear in the one-tap chips shown under the search box.
CHIP_MOODS = ('happy', 'tired', 'love', 'sad', 'excited', 'stressed', 'chill', 'silly', 'hungry', 'cozy')

# An emoji typed into the box counts as a hint for a mood.
EMOJI_HINTS = {
    '😂': 'silly', '🤣': 'silly', '🤪': 'silly', '😭': 'sad', '😢': 'sad', '😞': 'sad', '😔': 'sad',
    '😍': 'love', '🥰': 'love', '😘': 'love', '😡': 'angry', '🤬': 'angry', '😤': 'angry', '😴': 'tired',
    '🥱': 'tired', '🥳': 'party', '🎉': 'party', '😰': 'anxious', '😨': 'anxious', '😊': 'happy', '😄': 'happy',
    '😁': 'happy', '🤩': 'excited', '😎': 'confident', '💔': 'heartbroken', '🤒': 'sick', '🤧': 'sick',
    '🤔': 'confused', '😳': 'embarrassed', '😲': 'surprised', '😱': 'surprised', '😌': 'chill', '🙏': 'grateful',
    '🤤': 'hungry', '🍕': 'hungry', '🥺': 'lonely', '😩': 'stressed', '🫠': 'stressed',
}

# "can't" and "won't" are left out on purpose: "can't stop laughing" is not a negated mood.
NEGATORS = {
    'not', 'no', 'never', 'without', 'hardly', 'barely', "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't",
    "didn't", "ain't", 'isnt', 'arent', 'wasnt', 'dont', 'doesnt', 'didnt',
}
INTENSIFIERS = {'so', 'very', 'really', 'super', 'extremely', 'totally', 'soo', 'sooo', 'too', 'incredibly'}
_WORD = re.compile(r"[a-z0-9']+")


def _forms(word):
    """The word plus the few inflections we accept (love, loved, loving, lovely, worry, worried).

    Suffixes are only added where they make a real word shape, so 'win' never turns into 'wind'
    and 'mad' never turns into 'made'."""
    forms = {word, word + 's', word + 'ly', word + 'ness', word + 'y'}
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        forms.add(word + 'es')
    if word.endswith('e'):
        forms.update({word + 'd', word[:-1] + 'ing'})
    else:
        forms.update({word + 'ed', word + 'ing'})
    if word.endswith('y'):
        forms.update({word[:-1] + 'ied', word[:-1] + 'ies'})
    return forms


# Per mood: single words (with their inflections) and multi-word phrases, built once.
_SINGLE = {}    # token -> [mood keys]
_PHRASE_MOODS = {}   # tuple of tokens -> [mood keys]; a phrase can belong to more than one mood
for _key, _mood in MOODS.items():
    for _word in _mood['words']:
        _tokens = tuple(_WORD.findall(_word.lower().replace('’', "'")))
        if len(_tokens) == 1:
            for _form in _forms(_tokens[0]):
                _SINGLE.setdefault(_form, []).append(_key)
        else:
            _PHRASE_MOODS.setdefault(_tokens, []).append(_key)
_PHRASES = sorted(_PHRASE_MOODS.items(), key=lambda item: -len(item[0]))     # longest phrase first


def clean_text(raw):
    """What the visitor typed, with control characters removed, spaces collapsed and the length capped."""
    text = ''.join(' ' if ch.isspace() else ch for ch in str(raw or '') if ch.isspace() or ch.isprintable())
    return ' '.join(text.split())[:MAX_TEXT_LENGTH]


def _negated(tokens, index):
    return any(t in NEGATORS for t in tokens[max(0, index - 3):index])


def _boosted(tokens, index):
    return any(t in INTENSIFIERS for t in tokens[max(0, index - 2):index])


def detect_moods(text):
    """The moods the text expresses, strongest first (at most three). Empty when nothing is recognised."""
    text = clean_text(text)
    lowered = text.lower().replace('’', "'")
    tokens = _WORD.findall(lowered)
    scores, first_seen = {}, {}
    claimed = set()                      # token positions already used by a longer phrase

    def add(key, weight, position, negated, boosted):
        if negated:
            key = MOODS[key]['opposite']
            if key is None:
                return
        if boosted:
            weight *= 1.5
        scores[key] = scores.get(key, 0) + weight
        first_seen.setdefault(key, position)

    for phrase, phrase_keys in _PHRASES:
        size = len(phrase)
        for i in range(len(tokens) - size + 1):
            if tuple(tokens[i:i + size]) == phrase and not claimed.intersection(range(i, i + size)):
                claimed.update(range(i, i + size))
                for key in phrase_keys:
                    add(key, 3, i, _negated(tokens, i), _boosted(tokens, i))

    for i, token in enumerate(tokens):
        if i in claimed:
            continue
        for key in _SINGLE.get(token, ()):
            add(key, 2, i, _negated(tokens, i), _boosted(tokens, i))

    for position, char in enumerate(text):
        if char in EMOJI_HINTS:
            add(EMOJI_HINTS[char], 1, len(tokens) + position, False, False)

    if not scores:
        return []
    ranked = sorted(scores, key=lambda k: (-scores[k], first_seen[k]))
    top = scores[ranked[0]]
    return [k for k in ranked if scores[k] >= top / 2][:MAX_MOODS]


def _mood_label(keys):
    return ' + '.join(MOODS[k]['label'] for k in keys)


def generate_combos(keys, text, shuffle=0, count=GENERATED_COUNT):
    """New three-emoji sets built from the moods' lead, support and accent emoji. Same input, same output."""
    rng = random.Random(f'{clean_text(text).lower()}|{shuffle}')
    signature = {emoji for key in keys for _label, emoji in MOODS[key]['sets']}
    seen, combos = set(), []
    for _ in range(400):
        if len(combos) >= count:
            break
        primary = keys[0] if len(keys) == 1 or rng.random() < 0.55 else rng.choice(keys)
        secondary = rng.choice(keys)
        lead = rng.choice(MOODS[primary]['lead'])
        support = rng.choice(MOODS[secondary]['support'])
        accent = rng.choice(MOODS[primary]['accent'])
        parts = [lead, support, accent]
        if len(set(parts)) < 3:
            continue
        if rng.random() < 0.25:
            parts = [lead, accent, support]
        combo = ''.join(parts)
        if combo in seen or combo in signature:
            continue
        seen.add(combo)
        label = _mood_label([primary] if primary == secondary else [primary, secondary])
        combos.append({'emoji': combo, 'label': label})
    return combos


def library_matches(keys, text, shuffle=0, exclude=(), count=LIBRARY_COUNT):
    """Ready-made sets from the site's own pages whose labels or groups match the moods."""
    pool, seen = [], set(exclude)
    for key in keys:
        for term in MOODS[key]['terms']:
            for row in combo_search.search_sets(term, limit=40)[0]:
                if row['emoji'] not in seen:
                    seen.add(row['emoji'])
                    pool.append(row)
    rng = random.Random(f'lib|{clean_text(text).lower()}|{shuffle}')
    if len(pool) > count:
        pool = rng.sample(pool, count)
    return pool


def mashup_pairs(keys, limit=3):
    pairs = []
    for key in keys:
        for pair in MOODS[key]['mashups']:
            if pair not in pairs:
                pairs.append(pair)
    return pairs[:limit]


def find_combos(text, shuffle=0):
    """Everything the results page needs for one sentence."""
    text = clean_text(text)
    keys = detect_moods(text)
    matched = bool(keys)
    if not matched:
        keys = ['happy', 'chill']        # nothing recognised: show friendly all-round picks and say so
    picks = [{'emoji': emoji, 'label': label} for key in keys for label, emoji in MOODS[key]['sets']]
    generated = generate_combos(keys, text, shuffle)
    library = library_matches(keys, text, shuffle, exclude={p['emoji'] for p in picks} | {g['emoji'] for g in generated})
    return {
        'text': text,
        'matched': matched,
        'moods': [MOODS[k] for k in keys],
        'picks': picks,
        'generated': generated,
        'library': library,
        'mashups': mashup_pairs(keys),
    }
