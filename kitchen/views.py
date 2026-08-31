import json
import os
import random as _random

import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404

from .models import BlogPost


# ── Emoji combo lookup ──────────────────────────────────────────────────────────

with open(os.path.join(os.path.dirname(__file__), 'data', 'emoji_combos.json'), encoding='utf-8') as _f:
    EMOJI_COMBOS = json.load(_f)

# Pre-build a flat list of pair keys once at startup (O(1) random.choice later)
_PAIR_KEYS = list(EMOJI_COMBOS['pairs'].keys())


# ── Static content ────────────────────────────────────────────────────────────

FAQS = [
    {
        'question': 'Is the tool free to use?',
        'answer': 'Yes. Google offers the feature through supported services, and this browser tool lets you make emoji mashups without a paid plan.',
    },
    {
        'question': 'Is the tool an app?',
        'answer': 'It is a feature rather than a separate Google app. You can use it through Gboard on Android or through Google Search in a browser.',
    },
    {
        'question': 'Can I use the tool on iPhone?',
        'answer': 'Yes. iPhone users can search for the tool in a browser and use the Google Search mixer when it appears.',
    },
    {
        'question': 'Can I use the tool on a PC?',
        'answer': 'Yes. Open Google Search on your computer, search for the tool, then mix supported emojis in the on-screen mixer.',
    },
    {
        'question': 'Can I combine three emojis?',
        'answer': 'The tool mainly mixes two emojis at one time. To use three ideas, make one sticker first, then use a separate image editor for extra changes.',
    },
    {
        'question': 'Why is the tool not working?',
        'answer': 'The selected emojis may not support a mix, or your keyboard, browser, or messaging app may need an update. Try another pair or use Google Search.',
    },
    {
        'question': 'Are the results real emojis?',
        'answer': 'No. The results are sticker-style pictures, not new Unicode emojis. They may be sent as images rather than standard keyboard characters.',
    },
    {
        'question': 'Does Emoji Kitchen use AI?',
        'answer': 'Google presents the feature as a set of designed sticker combinations. It does not work like a text-to-image generator that makes a new picture from a written prompt.',
    },
    {
        'question': 'Can I share the stickers in messages?',
        'answer': 'Yes. You can copy, download, or send the sticker through apps that support pictures or Gboard sticker sharing.',
    },
]

FEATURES = [
    {
        'icon': '🆓',
        'title': 'Free Emoji Combiner',
        'description': 'Use the combiner without paying for each mix. Try many ideas, build a sticker collection, and find combinations that fit the exact tone of your message.',
    },
    {
        'icon': '⚡',
        'title': 'Fast Emoji Mixing',
        'description': 'The tool shows your <a href="https://emojikitchenhub.com/emoji-maker/" style="text-decoration:underline;text-underline-offset:3px">emoji mix</a> as soon as you choose both icons — no long prompts, no extra screens, no waiting.',
    },
    {
        'icon': '📋',
        'title': 'Easy Copy & Download',
        'description': 'Copy the sticker for a message you want to send now, or download the image to keep it for future chats, posts, and other media.',
    },
    {
        'icon': '🌐',
        'title': 'Works in Your Browser',
        'description': 'A browser-based tool that works on phones, tablets, and computers — without needing Gboard, an app install, or a large screen.',
    },
    {
        'icon': '🎨',
        'title': 'Creative Combinations',
        'description': 'Related pairs make clear results, while unexpected pairs produce funny or surprising stickers. The right mix says what words sometimes cannot.',
    },
    {
        'icon': '💾',
        'title': 'Save Your Favourites',
        'description': 'Your personal My Combos gallery keeps every creation. Reload and share them again whenever the same mood, joke, or reaction comes up.',
    },
]

CREATE_STEPS = [
    {
        'num': '1',
        'icon': '😀',
        'title': 'Choose Your First Emoji',
        'description': 'Pick the emoji that should lead the design. A face shows the main emotion, while an animal, food item, heart, or object sets the main theme. Start with what you want friends to notice first.',
    },
    {
        'num': '2',
        'icon': '🔥',
        'title': 'Choose Your Second Emoji',
        'description': 'Select a second emoji that adds contrast, humour, warmth, or detail. Pair a smiling face with a heart, mix an animal with food, or combine two random icons to see what kind of sticker appears.',
    },
    {
        'num': '3',
        'icon': '⬇️',
        'title': 'Copy or Download',
        'description': 'When the result appears, use the copy or download button. Copying works well for a message you want to send right now. Downloading saves the picture so you can use it later in chats, posts, or other media.',
    },
]

POPULAR_COMBOS = [
    {
        'icon': '😂',
        'title': 'Funny Combinations',
        'description': 'Turn a plain reply into a small visual joke. Try mixing a laughing face with an animal, a tired face with food, or a surprised face with an object that does not normally match.',
        'bg': '#FFF8E1',
        'border': '#FFE082',
        'examples': ['😂', '🐸', '😴', '🍕'],
        'url': '/emoji-combos/funny/',
    },
    {
        'icon': '🥰',
        'title': 'Cute Combinations',
        'description': 'Often use hearts, smiling faces, flowers, animals, and soft expressions. These stickers fit friendly messages, kind replies, birthday wishes, or chats where a normal heart feels too simple.',
        'bg': '#FCE4EC',
        'border': '#F48FB1',
        'examples': ['🥰', '🌸', '🐱', '❤️'],
        'url': '/emoji-combos/cute/',
    },
    {
        'icon': '🌸',
        'title': 'Aesthetic Combinations',
        'description': 'Focus on a calm look or matching theme. Try stars, moons, flowers, clouds, hearts, and simple faces — ideal for captions, profile posts, gentle messages, or picture-based social content.',
        'bg': '#EDE7F6',
        'border': '#CE93D8',
        'examples': ['🌸', '⭐', '🌙', '🌈'],
        'url': '/emoji-combos/aesthetic/',
    },
    {
        'icon': '🎲',
        'title': 'Random Combinations',
        'description': 'Pick any first emoji, then choose a second one without thinking too much. Odd pairs often produce the funniest and most unexpected creations — great for quick, surprising replies.',
        'bg': '#E8F5E9',
        'border': '#A5D6A7',
        'examples': ['🎲', '🦄', '🍄', '🚀'],
        'url': '/emoji-combos/',
    },
]

HOW_TO_WEB = [
    'Open the kitchen and scroll to the emoji mixer.',
    'Tap the first slot and choose an emoji from the collection.',
    'Pick a second emoji for the second slot.',
    'Your mashup cooks up in a couple of seconds.',
    'Download or copy it, then share anywhere.',
]

HOW_TO_PHONE = [
    'Install Gboard and set it as your default keyboard.',
    'Open a compatible messaging app and tap the text box.',
    'Tap the emoji icon on the keyboard and choose an emoji.',
    'Gboard suggests combined stickers when a compatible pair is chosen.',
    'Tap the sticker to send it instantly inside the chat.',
]

COMPARISON_ROWS = [
    ('Uses one fixed symbol', 'Blends two supported emojis'),
    ('Appears as a keyboard character', 'Often sends as a picture'),
    ('Shows one main idea', 'Can show a more specific reaction'),
]

EMOJI_COMBOS_PAGE_FAQS = [
    {
        'question': 'What is an emoji combo?',
        'answer': 'It is a group of two or more emojis used together to express a mood, topic, reaction, style, or short story.',
    },
    {
        'question': 'How do I copy and paste an emoji combo?',
        'answer': 'Select the Copy button beside a set, open your chosen app, and paste it into a supported text field.',
    },
    {
        'question': 'Are these combinations free?',
        'answer': 'Yes. Emoji Kitchen Hub presents its tools as free and available without sign-up.',
    },
    {
        'question': 'Where can I use emoji combinations?',
        'answer': 'You can use them in texts, captions, comments, bios, status updates, usernames, notes, and most apps that accept standard text.',
    },
    {
        'question': 'How many emojis should I use in a bio?',
        'answer': 'Two to four emojis suit most short bios. Longer decorative sets can work, but they may make a profile harder to scan.',
    },
    {
        'question': 'Should I add spaces between emojis?',
        'answer': 'Spaces are optional. No spaces create a compact look, while spaces can make longer or visually busy combinations easier to read.',
    },
    {
        'question': 'Why do some joined emojis split apart?',
        'answer': 'The device, browser, font, or app may not support that joined sequence. The system then shows its separate parts instead.',
    },
    {
        'question': 'Can a combination have different meanings?',
        'answer': 'Yes. Context, culture, platform design, and the relationship between the sender and reader can change how a set is understood.',
    },
    {
        'question': 'What is the difference between an emoji combo and Emoji Kitchen?',
        'answer': 'An emoji combo uses separate text characters. Emoji Kitchen blends supported emojis into one sticker-style image.',
    },
]

EMOJI_GENERATOR_FAQS = [
    {
        'question': 'Is this emoji generator free?',
        'answer': 'Yes. You can try supported emoji combinations without paying for individual mixes.',
    },
    {
        'question': 'Do I need to sign up?',
        'answer': 'No. This is an emoji generator with no sign-up required. Open the mixer, choose two emojis, and make a supported result.',
    },
    {
        'question': 'How do I use an emoji generator?',
        'answer': 'Choose two compatible emojis, check the result, then copy or download it. Try another pair if your first combination does not produce a mix.',
    },
    {
        'question': 'How do I get the emoji generator on my phone?',
        'answer': 'Open the tool in your mobile browser. You can use the mixer without installing a separate emoji-mixing app.',
    },
    {
        'question': 'Are the results new emojis on my keyboard?',
        'answer': 'No. The results are sticker-style images, not new keyboard emoji characters. You can copy or download them for apps that support images or stickers.',
    },
    {
        'question': 'Why does my emoji mix look different after I share it?',
        'answer': 'Apps can handle copied images, stickers, and previews in different ways. Downloading the result and sending it as an image can help when direct pasting does not work.',
    },
    {
        'question': 'Can I mix three emojis at once?',
        'answer': 'This tool is made for two-emoji combinations. Select two emojis to create one supported sticker-style result.',
    },
    {
        'question': 'Why does my emoji mix not appear?',
        'answer': 'A missing result usually means the selected pair is not supported. Try changing one emoji and test again. Common faces, hearts, animals, and food items are good starting points.',
    },
]

EMOJI_MAKER_FAQS = [
    {
        'question': 'What is an emoji maker?',
        'answer': 'An emoji maker is a tool that helps you create emoji-style images, stickers, or mashups. Emoji Kitchen Hub combines two emoji ideas into one visual reaction.',
    },
    {
        'question': 'How do you make your own emoji online?',
        'answer': 'Choose two emojis, combine them, then copy or download the result. This is an easy way to make your own emoji free without installing an app.',
    },
    {
        'question': 'Can I create custom emojis for free?',
        'answer': 'Yes. A free emoji maker online can help you create custom emojis from supported emoji pairs and save the final sticker image.',
    },
    {
        'question': 'How do I make an emoji with my keyboard?',
        'answer': 'Open your device emoji keyboard and select standard emojis. For a custom mashup, use an online emoji maker, then copy or download the sticker.',
    },
    {
        'question': 'Can I make emojis with a keyboard on Android or iPhone?',
        'answer': 'You can send standard emojis from both Android and iPhone keyboards. Custom mashup options may differ by keyboard, device, selected emojis, and messaging app.',
    },
    {
        'question': 'Is this an AI emoji maker?',
        'answer': 'No. This tool does not use AI prompts to generate emoji art. It creates a sticker-style result by combining existing emojis.',
    },
    {
        'question': 'Can I make an emoji from a photo?',
        'answer': 'No. This is not an emoji maker from photo tool. Use a dedicated photo emoji maker when you want to convert a selfie, pet, or logo into an emoji-style image.',
    },
    {
        'question': 'Can I copy and paste custom emoji stickers?',
        'answer': 'Yes, when the platform supports pasted images or stickers. If it does not, download the emoji and upload it manually.',
    },
    {
        'question': 'Can I use this as a flag emoji maker?',
        'answer': 'No. This tool is not designed as a flag emoji maker. It is made for general emoji mashups and sticker-style combinations.',
    },
    {
        'question': 'Is this an emoji maker game?',
        'answer': 'No. It is not an emoji maker game or a make a emoji game. It is a browser tool for creating and sharing emoji mashups quickly.',
    },
]


CUTE_EMOJI_COMBOS_FAQS = [
    {
        'question': 'What are some cute emoji combos?',
        'answer': 'Popular examples include 🎀🌸✨, 🐰🍓🤍, ☁️🌙🫧, 🧸🍯🤎, and 🌷🦋✨. Choose a set that matches your color, mood, occasion, or profile style.',
    },
    {
        'question': 'How do I copy an emoji combination?',
        'answer': 'Tap the sequence or its Copy button. Open the destination field, then paste it using your phone, tablet, or computer\'s normal paste command.',
    },
    {
        'question': 'Where can I use these emoji sets?',
        'answer': 'You can use them in Instagram and TikTok bios, Discord names, captions, messages, contact names, usernames, comments, documents, and other fields that accept text.',
    },
    {
        'question': 'What are the best combinations for a bio?',
        'answer': 'Short decorative sequences work best because they leave room for your name and description. Try ୨୧‧₊˚🎀˚₊‧୨୧, ☁️⋆｡°‧★, or ♡₊˚ 🦢・₊✧.',
    },
    {
        'question': 'What emojis create a cute aesthetic?',
        'answer': 'Ribbons, hearts, flowers, sparkles, butterflies, clouds, moons, strawberries, bunnies, teddy bears, swans, and pastel-colored hearts are common choices for a cute aesthetic.',
    },
    {
        'question': 'Do emoji combinations work on iPhone and Android?',
        'answer': 'Standard Unicode sequences can be copied on both platforms, but the artwork may look different depending on the device, operating system, app, and installed emoji font.',
    },
    {
        'question': 'Why does an emoji look different on another phone?',
        'answer': 'Unicode defines the character and sequence, while platform vendors create their own visual designs. This can change the color, shape, expression, or small details without changing the basic emoji.',
    },
    {
        'question': 'Are these emoji sets free to use?',
        'answer': 'The text combinations on this page can be copied without signing up. Individual Unicode characters are not owned by anyone — copying a sequence does not make it a new official emoji.',
    },
    {
        'question': 'What is the difference between an emoji combination and an Emoji Kitchen sticker?',
        'answer': 'An emoji combination contains separate text characters, such as 🐰🍓🤍. An Emoji Kitchen sticker visually merges two selected emojis into one image-based result that is shared as a picture.',
    },
    {
        'question': 'How many emojis should a combination contain?',
        'answer': 'Two to four emojis work well for most messages and bios. Longer sequences can suit decorative profile layouts, borders, captions, or wallpapers where more visual decoration is expected.',
    },
]


EMOJI_KEYBOARD_FAQS = [
    {
        'question': 'What is an emoji keyboard?',
        'answer': 'It is an on-screen tool or panel used to find and enter emojis. A browser version copies Unicode characters to your clipboard, while built-in Windows and Mac panels can insert them directly into supported fields.',
    },
    {
        'question': 'Is this tool free?',
        'answer': 'Yes. The browser emoji keyboard is free to use and does not require a paid plan or account.',
    },
    {
        'question': 'Do I need to install an app?',
        'answer': 'No. The browser tool works in any supported web browser, so you do not need to download or install anything.',
    },
    {
        'question': 'How do I open emojis on a Windows keyboard?',
        'answer': 'Click inside a text field and press Windows + . or Windows + ; to open the Windows emoji panel. You can browse with the mouse or keep typing to search.',
    },
    {
        'question': 'How do I open emojis on a Mac?',
        'answer': 'Press Fn/Globe + E, or choose Edit > Emoji & Symbols. This opens the Mac Character Viewer in supported apps.',
    },
    {
        'question': 'Can I copy several emojis at once?',
        'answer': 'Yes. Click multiple emojis to add them to the selection tray, then copy the full sequence into your message in one paste.',
    },
    {
        'question': 'Why do emojis look different on other devices?',
        'answer': 'Platforms use different artwork for the same Unicode characters. Apple, Google, Microsoft, Samsung, and individual apps each design their own emoji visuals. The underlying character is the same, but the appearance can vary.',
    },
    {
        'question': 'Are copied emojis text or images?',
        'answer': 'Standard copied emojis are Unicode text characters or sequences. Emoji mashups and custom stickers created with tools like Emoji Kitchen are image files instead.',
    },
    {
        'question': 'Does the website save what I copy?',
        'answer': 'The copy action places your selected text on your device clipboard only. The website does not store the specific emojis you choose.',
    },
    {
        'question': 'What should I do if the emoji appears as a box or missing symbol?',
        'answer': 'A square or empty box usually means the device, app, or font does not support that character yet. Try updating your operating system or app, or choose an older emoji with wider platform support.',
    },
]


PINK_EMOJI_COMBOS_FAQS = [
    {
        'question': 'What are pink emoji combinations?',
        'answer': 'They are groups of matching hearts, flowers, bows, sweets, fashion items, and symbols arranged around a pink color or mood. People use them in profiles, captions, usernames, comments, and messages.',
    },
    {
        'question': 'How do I copy and paste a pink emoji combination?',
        'answer': 'Select the copy button beside a set, then paste it into your chosen app. You can also highlight the characters manually when a copy button is unavailable.',
    },
    {
        'question': 'Which pink emojis look best together?',
        'answer': '🩷, 🎀, 🌸, 🌷, 💗, 💌, 🩰, 🫧, 🦩, and ✨ pair well because they share soft colors or related themes. Start with two to four symbols.',
    },
    {
        'question': 'Can I use these sets in an Instagram or TikTok bio?',
        'answer': 'Yes. Choose a short set and preview your profile before saving it. Long symbol strings can wrap onto another line or use too much space.',
    },
    {
        'question': 'What does the pink heart emoji mean?',
        'answer': 'The 🩷 emoji commonly suggests affection, care, sweetness, friendship, or romance. The surrounding text and relationship decide the final meaning.',
    },
    {
        'question': 'Why do some decorative symbols show as boxes?',
        'answer': 'The app, font, or device may not support that character. Replace it with a standard emoji or a simpler symbol that displays correctly.',
    },
    {
        'question': 'How many emojis should I use in a bio?',
        'answer': 'Two to four emojis usually keep a bio readable. Longer sets can work as dividers, but they may distract from your name, links, or main description.',
    },
    {
        'question': 'Can I use the same combination in WhatsApp and Discord?',
        'answer': 'Usually, yes. Standard Unicode emojis can be pasted into both apps, though the artwork and spacing may look different on each device.',
    },
    {
        'question': 'Why can the same set look different across devices?',
        'answer': 'The characters stay the same, but platforms draw their own emoji artwork. Colors, shapes, and spacing can change across Apple, Google, Microsoft, Samsung, and social apps. Preview a set in the final app before publishing.',
    },
    {
        'question': 'Are copyable combinations the same as one merged emoji?',
        'answer': 'No. A copyable set contains separate characters you can paste as text. A merged Emoji Kitchen result is a sticker image designed from two selected emojis.',
    },
]


FUNNY_EMOJI_COMBOS_FAQS = [
    {
        'question': 'What are funny emoji combos?',
        'answer': 'They are short sequences of emojis arranged to communicate a joke, reaction, mood or silly situation. Most use two to four symbols so the meaning stays clear.',
    },
    {
        'question': 'What are some funny emoji combinations for texting?',
        'answer': 'Try 👀🍿😂 for drama, 🙂👍🙃 for fake agreement, 🧠❌🐒 for chaos or 📱😳💥 for a shocking message.',
    },
    {
        'question': 'How do I copy and paste a funny emoji combination?',
        'answer': 'Tap the copy button beside the sequence, open the app where you want to use it and paste it into the text field. Preview it before sending.',
    },
    {
        'question': 'What is a good funny emoji combo for friends?',
        'answer': 'Use 😎🤝🔥 for partners in chaos, 📸🧾👀 when you have evidence or 🤦😂🫶 when laughing at a harmless mistake.',
    },
    {
        'question': 'Can I use these combinations in Instagram and TikTok bios?',
        'answer': 'Yes. Choose a short set that fits the available space. Two or three emojis usually look cleaner than a long decorative line.',
    },
    {
        'question': 'What are funny dark humor emoji combinations?',
        'answer': 'They use mild themes such as deadlines, dead batteries, failed plans or Monday mornings. Avoid graphic, threatening or self-harm-related jokes.',
    },
    {
        'question': 'Why do emojis look different after I paste them?',
        'answer': 'Platforms can use different artwork for the same Unicode characters. Faces, colors and small details may therefore appear slightly different across devices.',
    },
    {
        'question': 'Are funny emoji combinations the same as Emoji Kitchen mashups?',
        'answer': 'No. A standard combo places separate Unicode emojis side by side as text. An Emoji Kitchen mashup blends compatible emoji artwork into one sticker-style image.',
    },
    {
        'question': 'What are Gen Z funny emoji combos?',
        'answer': 'Gen Z combinations often use exaggeration, irony and dramatic reactions — like 😭😭💀 for "I am crying laughing", 💀📴 for "this ended me", or ✨🧠🌈 for delulu mode. Meanings can shift quickly with context.',
    },
    {
        'question': 'How many emojis should a funny combination have?',
        'answer': 'Two to four emojis work best. One leads the joke, the others support or extend it. Longer sequences can wrap or look crowded in a bio or caption field.',
    },
]


AESTHETIC_EMOJI_COMBOS_FAQS = [
    {
        'question': 'What are aesthetic emoji combos?',
        'answer': 'They are short groups of emojis or decorative symbols chosen to express one visual mood. Common styles include soft, coquette, dark academia, Y2K, vintage, nature, clean girl and colour-based themes.',
    },
    {
        'question': 'How many emojis should I use in one combination?',
        'answer': 'Two to five characters work well for most bios, captions and usernames. Use fewer characters in a display name, and use a slightly longer set when the caption has more space.',
    },
    {
        'question': 'How do I copy and paste an emoji set?',
        'answer': 'Press the Copy button beside the set, open the app where you want to use it, then paste it into the chosen field. Preview the result before saving.',
    },
    {
        'question': 'Which combinations work best for an Instagram bio?',
        'answer': 'Short sets such as ☁️🫧🤍, 🎀🩷✨ or 🌙🪐⭐ fit well because they create a mood without taking over the bio. Match the set to your profile colours and content.',
    },
    {
        'question': 'Can I use these sets on TikTok, Discord and WhatsApp?',
        'answer': 'Yes. Standard emojis work in most apps, though their artwork may differ by platform. Decorative text symbols can also depend on font support.',
    },
    {
        'question': 'Why do emojis look different on iPhone and Android?',
        'answer': 'Platforms draw their own artwork for standard Unicode characters. The meaning stays broadly consistent, but colour, shape and detail can differ.',
    },
    {
        'question': 'Why does a symbol appear as a square?',
        'answer': 'The device, operating system, app or font may not support that character. Replace it with a common symbol, update the software where appropriate, or use an emoji-only set.',
    },
    {
        'question': 'What is the difference between a combo and an Emoji Kitchen mashup?',
        'answer': 'A combo keeps several emojis as separate text characters. An Emoji Kitchen mashup blends two supported emojis into one image, which behaves more like a sticker than editable text.',
    },
    {
        'question': 'Can I mix emojis, symbols and kaomoji?',
        'answer': 'Yes. Keep the set readable and test it on mobile. One kaomoji with one or two matching emojis often looks cleaner than a long row of decorative characters.',
    },
    {
        'question': 'What makes an emoji combination look aesthetic?',
        'answer': 'A strong set feels intentional. Choose one mood, pick a focal emoji such as a bow, moon or flower, add two supporting characters that match by colour or meaning, and keep the overall palette controlled.',
    },
]


LOVE_EMOJI_COMBOS_FAQS = [
    {
        'question': 'What are the best romantic emoji combinations?',
        'answer': 'The best option matches the message and recipient. ❤️🥰✨ suits a sweet everyday text, while 💌🌹❤️ works better for a romantic note or love letter.',
    },
    {
        'question': 'How do I copy and paste an emoji sequence?',
        'answer': 'Tap the combination you want, open the app where you want to use it, and select Paste. Check the preview before sending or posting so you can remove any symbol that does not display correctly.',
    },
    {
        'question': 'Which emoji sets should I send to my boyfriend?',
        'answer': 'Try 🫵💙🫶, 🤍🫂🔐, or Boyfriend 🧸💙🔐. Choose a style that matches how you normally speak to him — soft, playful, or romantic all work.',
    },
    {
        'question': 'Which romantic combinations work for a girlfriend?',
        'answer': 'Try 🌹💌💗, 🫵🩷🫶, or Girlfriend 🎀💞🔐. Romantic, soft, and playful options can all work depending on your relationship style.',
    },
    {
        'question': 'What is a good aesthetic romantic sequence?',
        'answer': '☁️🩷🎀, 🌷🤍🫧, and 🦢💌✨ are balanced options. Short combinations of two or three emojis work best in profile bios where space is limited.',
    },
    {
        'question': 'Can I use these combinations on Instagram and TikTok?',
        'answer': 'Standard Unicode emojis can usually be pasted into supported text fields on any platform. Always preview them first because decorative symbols and spacing may change between apps.',
    },
    {
        'question': 'Why do emojis look different after I paste them?',
        'answer': 'Apps and operating systems use their own emoji artwork. The underlying Unicode characters stay the same, but their visual design can change on Apple, Google, Samsung, or Microsoft platforms.',
    },
    {
        'question': 'Why does an emoji show as a square or empty box?',
        'answer': 'The device, operating system, app, or font may not support that character. Remove the unsupported symbol or replace it with a more widely supported emoji.',
    },
    {
        'question': 'Are love emoji combos the same as Emoji Kitchen stickers?',
        'answer': 'No. These are plain text sequences made of standard Unicode characters. Emoji Kitchen combines two emoji designs into a single sticker-style image, which is different from a text combination.',
    },
    {
        'question': 'Can I add words to an emoji combination?',
        'answer': 'Yes. Short phrases such as "love you," "miss you," or "my person" placed next to the emojis can make the meaning clearer without making the message too long.',
    },
]


# ── Views ─────────────────────────────────────────────────────────────────────

def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        '',
        f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def ads_txt(request):
    return HttpResponse(
        'google.com, pub-3200425003686406, DIRECT, f08c47fec0942fa0',
        content_type='text/plain',
    )


def home(request):
    context = {
        'faqs': FAQS,
        'features': FEATURES,
        'create_steps': CREATE_STEPS,
        'popular_combos': POPULAR_COMBOS,
        'how_to_web': HOW_TO_WEB,
        'how_to_phone': HOW_TO_PHONE,
        'comparison_rows': COMPARISON_ROWS,
    }
    return render(request, 'kitchen/home.html', context)


def emoji_maker(request):
    context = {
        'faqs': EMOJI_MAKER_FAQS,
    }
    return render(request, 'kitchen/emoji_maker.html', context)


def emoji_generator(request):
    context = {
        'faqs': EMOJI_GENERATOR_FAQS,
    }
    return render(request, 'kitchen/emoji_generator.html', context)


def emoji_combos(request):
    context = {
        'faqs': EMOJI_COMBOS_PAGE_FAQS,
    }
    return render(request, 'kitchen/emoji_combos.html', context)


def emoji_combos_love(request):
    context = {
        'faqs': LOVE_EMOJI_COMBOS_FAQS,
    }
    return render(request, 'kitchen/emoji_combos_love.html', context)


def emoji_combos_cute(request):
    context = {
        'faqs': CUTE_EMOJI_COMBOS_FAQS,
    }
    return render(request, 'kitchen/emoji_combos_cute.html', context)


def emoji_combos_funny(request):
    context = {
        'faqs': FUNNY_EMOJI_COMBOS_FAQS,
    }
    return render(request, 'kitchen/emoji_combos_funny.html', context)


def emoji_combos_pink(request):
    context = {
        'faqs': PINK_EMOJI_COMBOS_FAQS,
    }
    return render(request, 'kitchen/emoji_combos_pink.html', context)


def emoji_combos_aesthetic(request):
    context = {
        'faqs': AESTHETIC_EMOJI_COMBOS_FAQS,
    }
    return render(request, 'kitchen/emoji_combos_aesthetic.html', context)


def emoji_keyboard(request):
    context = {
        'faqs': EMOJI_KEYBOARD_FAQS,
    }
    return render(request, 'kitchen/emoji_keyboard.html', context)


def blog(request):
    posts = BlogPost.objects.visible().select_related('category').prefetch_related('tags')
    featured_post = posts.filter(is_featured=True).first()
    other_posts = posts.exclude(pk=featured_post.pk) if featured_post else posts
    context = {
        'featured_post': featured_post,
        'blog_posts': other_posts,
    }
    return render(request, 'kitchen/blog.html', context)


def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost.objects.select_related('category').prefetch_related('tags'),
        slug=slug,
    )
    if not post.is_visible:
        raise Http404('Post not found')

    related_posts = BlogPost.objects.none()
    if post.category:
        related_posts = (
            BlogPost.objects.visible()
            .filter(category=post.category)
            .exclude(pk=post.pk)
            .select_related('category')[:3]
        )

    context = {'post': post, 'related_posts': related_posts}
    return render(request, 'kitchen/blog_detail.html', context)


def get_combo(request):
    emoji1 = request.GET.get('emoji1', '').strip()
    emoji2 = request.GET.get('emoji2', '').strip()

    if not emoji1 or not emoji2:
        return JsonResponse({'error': 'Two emojis required'}, status=400)

    cp1 = _emoji_to_codepoints(emoji1)
    cp2 = _emoji_to_codepoints(emoji2)

    if not cp1 or not cp2:
        return JsonResponse({'error': 'Invalid emoji characters'}, status=400)

    a, b = sorted([cp1, cp2])
    entry = EMOJI_COMBOS['pairs'].get(f'{a},{b}')

    urls = []
    if entry:
        date_idx, swap = entry
        date = EMOJI_COMBOS['dates'][date_idx]
        left, right = (b, a) if swap else (a, b)
        left_part = _codepoints_to_url_part(left)
        right_part = _codepoints_to_url_part(right)
        urls.append(
            f'https://www.gstatic.com/android/keyboard/emojikitchen/'
            f'{date}/{left_part}/{left_part}_{right_part}.png'
        )

    return JsonResponse({'urls': urls, 'emoji1': emoji1, 'emoji2': emoji2})


def get_combos_for_emoji(request):
    """Return all available Kitchen combos that include the given emoji."""
    emoji = request.GET.get('emoji', '').strip()
    if not emoji:
        return JsonResponse({'error': 'emoji required'}, status=400)

    cp = _emoji_to_codepoints(emoji)
    if not cp:
        return JsonResponse({'error': 'Invalid emoji'}, status=400)

    results = []
    seen_partners = set()

    for key, entry in EMOJI_COMBOS['pairs'].items():
        parts = key.split(',')
        if len(parts) != 2:
            continue
        a, b = parts

        if a == cp:
            partner_cp = b
        elif b == cp:
            partner_cp = a
        else:
            continue

        if partner_cp in seen_partners:
            continue
        seen_partners.add(partner_cp)

        date_idx, swap = entry
        date = EMOJI_COMBOS['dates'][date_idx]
        left, right = (b, a) if swap else (a, b)
        left_part = _codepoints_to_url_part(left)
        right_part = _codepoints_to_url_part(right)
        url = (
            f'https://www.gstatic.com/android/keyboard/emojikitchen/'
            f'{date}/{left_part}/{left_part}_{right_part}.png'
        )

        try:
            partner_emoji = ''.join(chr(int(c, 16)) for c in partner_cp.split('-'))
        except ValueError:
            continue

        results.append({'emoji2': partner_emoji, 'url': url})

    return JsonResponse({'combos': results})


def get_random_combo(request):
    """Return one random valid Emoji Kitchen combo pair with its image URL.

    Tries up to MAX_TRIES random pairs from the dataset, decoding codepoints
    to emoji characters each time.  Returns the first pair that decodes without
    error.  The image URL is constructed from the same data used everywhere
    else, so it is always structurally valid.  The frontend independently
    verifies the image loads before showing it.
    """
    MAX_TRIES = 60

    for _ in range(MAX_TRIES):
        key = _random.choice(_PAIR_KEYS)
        parts = key.split(',')
        if len(parts) != 2:
            continue
        a, b = parts

        try:
            emoji1 = ''.join(chr(int(c, 16)) for c in a.split('-'))
            emoji2 = ''.join(chr(int(c, 16)) for c in b.split('-'))
        except (ValueError, OverflowError):
            continue

        date_idx, swap = EMOJI_COMBOS['pairs'][key]
        date = EMOJI_COMBOS['dates'][date_idx]
        left, right = (b, a) if swap else (a, b)
        left_part  = _codepoints_to_url_part(left)
        right_part = _codepoints_to_url_part(right)
        url = (
            f'https://www.gstatic.com/android/keyboard/emojikitchen/'
            f'{date}/{left_part}/{left_part}_{right_part}.png'
        )
        return JsonResponse({'emoji1': emoji1, 'emoji2': emoji2, 'url': url})

    return JsonResponse({'error': 'Could not find a valid combo'}, status=500)


def download_combo(request):
    url = request.GET.get('url', '')
    if not url.startswith('https://www.gstatic.com/android/keyboard/emojikitchen/'):
        return HttpResponse('Invalid URL', status=400)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            response = HttpResponse(resp.content, content_type='image/png')
            response['Content-Disposition'] = 'attachment; filename="emoji_mashup.png"'
            return response
        return HttpResponse('Image not found', status=404)
    except requests.RequestException:
        return HttpResponse('Error fetching image', status=500)


def proxy_image(request):
    url = request.GET.get('url', '')
    if not url.startswith('https://www.gstatic.com/android/keyboard/emojikitchen/'):
        return HttpResponse('Invalid URL', status=400)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            response = HttpResponse(resp.content, content_type='image/png')
            response['Access-Control-Allow-Origin'] = '*'
            return response
        return HttpResponse('Image not found', status=404)
    except requests.RequestException:
        return HttpResponse('Error fetching image', status=500)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _emoji_to_codepoints(emoji: str) -> str:
    codepoints = [hex(ord(char))[2:].lower() for char in emoji]
    return '-'.join(codepoints)


def _codepoints_to_url_part(codepoints: str) -> str:
    return '-'.join(f'u{part}' for part in codepoints.split('-'))
