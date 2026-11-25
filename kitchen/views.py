import json
import logging
import os
import random as _random

from django.contrib.sitemaps.views import sitemap as django_sitemap
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse
from urllib.parse import quote, urlencode

from .models import BlogPost
from .combo_counts import distinct_set_count, floor_hundreds
from .combo_pages import COMBO_PAGES
from . import mood as mood_engine
from . import stickers
from .combo_search import clean_query, matching_tag_pages, search_sets
from .combo_tags import TAG_PAGES
from .seo import (
    absolute_media_url, absolute_site_url, article_json_ld, clean_canonical, faq_json_ld, faq_pairs_from_html, share_image_meta,
    site_origin,
)

logger = logging.getLogger(__name__)


# ── Emoji combo lookup ──────────────────────────────────────────────────────────

with open(os.path.join(os.path.dirname(__file__), 'data', 'emoji_combos.json'), encoding='utf-8') as _f:
    EMOJI_COMBOS = json.load(_f)

# Pre-build a flat list of pair keys once at startup (O(1) random.choice later)
_PAIR_KEYS = list(EMOJI_COMBOS['pairs'].keys())
# Same loaded file the mixer uses. Do not hardcode this.
COMBO_COUNT = len(_PAIR_KEYS)


def _cp_to_emoji(codepoints):
    return ''.join(chr(int(part, 16)) for part in codepoints.split('-'))


def _count_partners():
    """How many other emojis each emoji can be mixed with, keyed by the emoji character."""
    counts = {}
    for key in _PAIR_KEYS:
        for cp in set(key.split(',')):   # a pair of an emoji with itself counts once
            counts[cp] = counts.get(cp, 0) + 1
    result = {}
    for cp, n in counts.items():
        try:
            result[_cp_to_emoji(cp)] = n
        except (ValueError, OverflowError):
            continue
    return result


# emoji -> number of emojis it pairs with (built once at startup)
SUPPORTED_EMOJI_COUNTS = _count_partners()


# ── Static content ────────────────────────────────────────────────────────────

FAQS = [
    {
        'question': 'What is Emoji Kitchen?',
        'answer': "Emoji Kitchen is Google's feature that mixes two emojis into one sticker-style image, mainly through Gboard on Android. Emoji Kitchen Hub is an unofficial website that lets you mix supported pairs in a browser.",
    },
    {
        'question': 'Is Emoji Kitchen Hub free?',
        'answer': 'Yes. The tool is free to use in your browser, and no sign-up is needed.',
    },
    {
        'question': 'Do I need to install an app?',
        'answer': 'No. Emoji Kitchen Hub is a website that runs in your browser.',
    },
    {
        'question': 'Can I combine any two emojis?',
        'answer': 'No. Only supported pairs produce a result, and the tool combines two emojis at a time. If a combination is not available, try changing one of the emojis.',
    },
    {
        'question': 'Are the results real Unicode emojis?',
        'answer': 'No. The results are sticker-style images, not new Unicode characters. For standard emoji characters that you can type as text, use the online emoji keyboard.',
    },
    {
        'question': 'Can I use the tool on my phone?',
        'answer': 'Yes. The mixer works in a mobile browser. Copying an image can vary by browser and app, so use the Download button if pasting does not work.',
    },
    {
        'question': 'Can I use Emoji Kitchen on iPhone?',
        'answer': "Gboard's built-in mashup suggestions are mainly an Android feature. On iPhone, you can open Emoji Kitchen Hub in Safari or another browser, mix two emojis, then download the image and send it in your chat app.",
    },
    {
        'question': 'Why is Emoji Kitchen not showing on my keyboard?',
        'answer': 'Mashup suggestions need Gboard, and they appear only in supported apps, for supported emoji pairs. Update Gboard, check that emoji suggestions are turned on, and try another pair. You can also make mashups on this website in any browser.',
    },
    {
        'question': 'Can I download my emoji mashup?',
        'answer': 'Yes. When a supported result appears, use the Download image button. It saves your mashup as a 512 × 512 image '
                  'with a see-through background and a white outline (a WebP file under 100 KB), which also works in WhatsApp and Telegram '
                  'sticker apps. If an app does not accept WebP, use the PNG link under the buttons. Copy image pastes the picture straight into a '
                  'chat, and on phones Send image opens the share menu.',
    },
    {
        'question': 'Can I save favourite combinations?',
        'answer': 'Combinations you create appear in My Combos, which keeps up to six recent ones in your browser. They are stored on your device, so they may disappear if you clear your browser data.',
    },
    {
        'question': 'Is Emoji Kitchen Hub operated by Google?',
        'answer': "No. Emoji Kitchen Hub is an independent website and is not operated by Google. Google's Emoji Kitchen feature, available through supported Google products such as Gboard, is a separate service.",
    },
]

FEATURES = [
    {
        'icon': '🌐',
        'title': 'Simple Browser-Based Tool',
        'description': 'Open the tool in your browser with no app to install. To create and customize your own design, use the <a href="/emoji-maker/" style="text-decoration:underline;text-underline-offset:3px">Emoji Maker</a>. For an instant or random mashup, try the <a href="/emoji-generator/" style="text-decoration:underline;text-underline-offset:3px">Emoji Generator</a>.',
    },
    {
        'icon': '⚡',
        'title': 'Quick Results',
        'description': 'When a pair is supported, the result usually appears within a few seconds. If nothing appears, try a different pair.',
    },
    {
        'icon': '📋',
        'title': 'Copy and Download Options',
        'description': 'Copy the result to paste into apps that accept images, or download it as a sticker file. If pasting does not work in an app, download the sticker and attach it instead.',
    },
    {
        'icon': '🔍',
        'title': 'Explore Different Combinations',
        'description': 'Browse the Explore Combinations section or press the 🎲 button for a random pair. For ready-made text sets, see the <a href="/emoji-combos/" style="text-decoration:underline;text-underline-offset:3px">emoji combos</a> collections.',
    },
    {
        'icon': '🎨',
        'title': 'No Separate Design Software',
        'description': 'Create a sticker-style image from two emojis without opening an editor. The tool combines existing emoji designs and does not edit photos or draw new artwork.',
    },
    {
        'icon': '⭐',
        'title': 'Save Favourite Combinations',
        'description': 'Combinations you create are listed under My Combos, which keeps up to six recent ones in your browser. They are stored on your device, so they can disappear if you clear browser data or switch devices.',
    },
]

CREATE_STEPS = [
    {
        'num': '1',
        'icon': '😀',
        'title': 'Choose Your First Emoji',
        'description': 'Pick an emoji that expresses the main idea.',
    },
    {
        'num': '2',
        'icon': '🔥',
        'title': 'Add a Second Emoji',
        'description': 'Choose another emoji to add emotion, humour, or contrast.',
    },
    {
        'num': '3',
        'icon': '⬇️',
        'title': 'Preview and Share',
        'description': 'Check the generated image. If the result looks right, copy or download it using the available controls.',
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
        'description': 'Focus on a calm look or matching theme. Try stars, moons, flowers, clouds, hearts, and simple faces. They suit captions, profile posts, gentle messages, or picture-based social content.',
        'bg': '#EDE7F6',
        'border': '#CE93D8',
        'examples': ['🌸', '⭐', '🌙', '🌈'],
        'url': '/emoji-combos/aesthetic/',
    },
    {
        'icon': '🎲',
        'title': 'Random Combinations',
        'description': 'Press the 🎲 Surprise me button in the mixer to load a random supported pair. Like the result? Copy or download it, or press the button again for a new surprise. Random results are also saved to My Combos in your browser.',
        'bg': '#E8F5E9',
        'border': '#A5D6A7',
        'examples': ['🎲', '🦄', '🍄', '🚀'],
        'url': '#kitchen',
        'cta': 'Try the 🎲 button →',
    },
]

HOW_TO_WEB = [
    'Open the mixer on this page.',
    'Choose an emoji in the first selection area.',
    'Choose a second emoji.',
    'Check whether a result is available for the selected pair.',
    'If no result appears, change one emoji and try again.',
    'Use the available copy or download control if it is supported by the current tool and works in your browser.',
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
    {
        'question': 'When should I use an emoji combo instead of one emoji?',
        'answer': 'Use a short combo when one character does not carry the mood you want, for example a soft reply, a bio accent, or a caption decoration. Keep the set short enough to read on a phone.',
    },
    {
        'question': 'How do I copy and paste emoji combos on iPhone or Android?',
        'answer': 'Tap the Copy button beside a set, open your app, press and hold in the text field and choose Paste. The sets are text, so they paste like any typed message.',
    },
    {
        'question': 'Can I turn two emojis into one image?',
        'answer': 'Sometimes. Open the Emoji Kitchen mixer on the home page, pick two emojis and, if that pair has a mashup, the preview appears and you can copy or download it. Not every pair is supported.',
    },
    {
        'question': 'Which emoji combos work for an Instagram or TikTok bio?',
        'answer': 'Two to four emojis per line are usually enough. The emoji combos for bio page sorts sets by interest, such as creator, student, gamer, fitness and travel.',
    },
]

EMOJI_GENERATOR_FAQS = [
    {
        'question': 'Is this emoji generator free?',
        'answer': 'Yes. You can use the generator in your browser at no cost, and no account is needed.',
    },
    {
        'question': 'How do I generate a random emoji mashup?',
        'answer': 'Press the random (dice) button in the generator. It loads a supported pair automatically so you can preview an instant mashup, then copy or download it, or press the button again for another pair.',
    },
    {
        'question': 'Can the generator combine any two emojis?',
        'answer': 'No. It works only with supported pairs, so some selections will not produce a mashup. Emojis that are greyed out in the second picker have no sticker with your first choice. The random button always loads a pair that is supported.',
    },
    {
        'question': 'Is this an AI emoji generator?',
        'answer': 'No. You choose two emojis, or generate a random supported pair, instead of typing a description. The tool is not an AI image generator.',
    },
    {
        'question': 'Can I use the emoji generator on my phone or computer?',
        'answer': 'Yes. It runs in mobile and desktop browsers, with no app to install. If a copied image does not paste into an app, download it and attach the file instead.',
    },
    {
        'question': 'Does it create new keyboard emojis?',
        'answer': 'No. The result is an image-style mashup, not a character you can add to your keyboard. For typing, use the online emoji keyboard.',
    },
]

EMOJI_MAKER_FAQS = [
    {
        'question': 'What does an emoji maker do?',
        'answer': 'An emoji maker creates a custom emoji-style image. This one lets you choose two compatible emojis and combine them into a sticker-style result when the pair is supported.',
    },
    {
        'question': 'Can I make my own emoji for free?',
        'answer': 'Yes. You can create a custom sticker from supported pairs in your browser, with no sign-up. The result is an image, not a new keyboard emoji.',
    },
    {
        'question': 'Can I customize facial features or upload a photo?',
        'answer': 'No. You cannot change eyes, mouths, or other details, and you cannot upload a photograph. You only choose which two emojis to combine.',
    },
    {
        'question': 'Does this emoji maker use AI?',
        'answer': 'No. The tool combines existing emoji designs. It does not generate artwork from text prompts.',
    },
    {
        'question': "Why doesn't my emoji combination work?",
        'answer': 'Only supported pairs produce a result. If a pair is unavailable, change one emoji. If supported pairs also fail to load, refresh the page and try again.',
    },
    {
        'question': 'How do I use my custom emoji in messages and apps?',
        'answer': 'Copy the image and paste it into an app that accepts images, or download the file and attach it. Steps differ by app; the Instagram, Discord, iPhone, and PC guides on this site walk through common cases.',
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
        'answer': 'The text combinations on this page can be copied without signing up. Individual Unicode characters are not owned by anyone, and copying a sequence does not make it a new official emoji.',
    },
    {
        'question': 'What is the difference between an emoji combination and an Emoji Kitchen sticker?',
        'answer': 'An emoji combination contains separate text characters, such as 🐰🍓🤍. An Emoji Kitchen sticker visually merges two selected emojis into one image-based result that is shared as a picture.',
    },
    {
        'question': 'How many emojis should a combination contain?',
        'answer': 'Two to four emojis work well for most messages and bios. Longer sequences can suit decorative profile layouts, borders, captions, or wallpapers where more visual decoration is expected.',
    },
    {
        'question': 'When do cute emoji combos work best?',
        'answer': 'They suit friendly messages, thank-you notes, birthday captions, and approachable bios. Prefer two or three symbols in tight spaces, and preview the paste before posting.',
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


EMOJI_KEYBOARD_PC_FAQS = [
    {
        'question': 'How do I open the emoji keyboard for PC?',
        'answer': 'Click inside a text field and press Windows + . (period). You can also press Windows + ; (semicolon) to open the Windows emoji panel.',
    },
    {
        'question': 'What is the shortcut for emojis on Windows?',
        'answer': 'Use Windows + . as the main shortcut. Microsoft also lists Windows + ; as an alternative shortcut for the emoji panel.',
    },
    {
        'question': 'How do I type emojis on a computer?',
        'answer': 'Place your cursor in a supported text field, open the Windows emoji panel, then select an emoji. You can also copy an emoji from a browser-based picker and paste it.',
    },
    {
        'question': 'Can I use emojis without a touchscreen?',
        'answer': 'Yes. A touchscreen is not required. You can open the panel with the keyboard shortcut and use the mouse or keyboard to select an emoji. Microsoft documents keyboard navigation for the panel.',
    },
    {
        'question': 'Why is my Windows emoji keyboard not showing?',
        'answer': 'Make sure your cursor is inside a text field, then try both Windows shortcuts. If the panel still does not appear, test another app and check for Windows updates.',
    },
    {
        'question': 'Can I copy several emojis at once?',
        'answer': 'Yes. Browser-based emoji pickers can let you select multiple characters and copy them as one sequence. Emoji Kitchen Hub supports multi-emoji selection and copying.',
    },
    {
        'question': 'Do emojis look different on Windows and phones?',
        'answer': 'Yes. Different platforms use different artwork for the same Unicode characters. The character can stay the same while the design changes.',
    },
    {
        'question': 'Can I make custom emoji images on a PC?',
        'answer': 'Yes. Custom emoji images are different from standard Unicode emojis. You can use an emoji maker to create a sticker-style image when you want something beyond a normal text character.',
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
    {
        'question': 'When should I use pink emoji combos?',
        'answer': 'Pink sets fit aesthetic bios, soft captions, and colour-matched profile accents. Shorter sequences read better in usernames; preview colours because platforms draw pink symbols differently.',
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
        'answer': 'Gen Z combinations often use exaggeration, irony and dramatic reactions, like 😭😭💀 for "I am crying laughing", 💀📴 for "this ended me", or ✨🧠🌈 for delulu mode. Meanings can shift quickly with context.',
    },
    {
        'question': 'How many emojis should a funny combination have?',
        'answer': 'Two to four emojis work best. One leads the joke, the others support or extend it. Longer sequences can wrap or look crowded in a bio or caption field.',
    },
    {
        'question': 'When should I use a funny emoji combo?',
        'answer': 'Funny sets work well in casual chats and light captions where a quick reaction is enough. Keep replies short in busy threads, and check that the joke fits the audience.',
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
    {
        'question': 'When should I use aesthetic emoji combos?',
        'answer': 'Use them when you want a bio or caption to feel visually consistent. Stay with one mood or palette, keep sets short in names, and drop symbols that crowd a narrow phone layout.',
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
        'answer': 'Try 🫵💙🫶, 🤍🫂🔐, or Boyfriend 🧸💙🔐. Choose a style that matches how you normally speak to him. Soft, playful, or romantic all work.',
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
    {
        'question': 'When should I send a love emoji combo?',
        'answer': 'Use one when a single heart feels too generic for the moment. Match the intensity to the relationship, keep bios short, and preview the sequence in the same app you will send from.',
    },
]


# ── Views ─────────────────────────────────────────────────────────────────────

def public_sitemap(request, sitemaps, **kwargs):
    """Serve sitemap.xml without Django's default X-Robots-Tag: noindex."""
    response = django_sitemap(request, sitemaps, **kwargs)
    if 'X-Robots-Tag' in response:
        del response['X-Robots-Tag']
    return response


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        '',
        f'Sitemap: {site_origin()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def ads_txt(request):
    return HttpResponse(
        'google.com, pub-3200425003686406, DIRECT, f08c47fec0942fa0',
        content_type='text/plain',
    )


def indexnow_key_file(request, key):
    from kitchen.indexnow import key_file
    return key_file(request, key)


def privacy(request):
    return render(request, 'kitchen/privacy.html')


def about(request):
    return render(request, 'kitchen/about.html')


def cookie_policy(request):
    return render(request, 'kitchen/cookie_policy.html')


def disclaimer(request):
    return render(request, 'kitchen/disclaimer.html')


def terms(request):
    return render(request, 'kitchen/terms.html')


def contact(request):
    return render(request, 'kitchen/contact.html')


def home(request):
    faq_entities = [
        {
            '@type': 'Question',
            'name': item['question'],
            'acceptedAnswer': {'@type': 'Answer', 'text': item['answer']},
        }
        for item in FAQS
    ]
    faq_json_ld = json.dumps(
        {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': faq_entities},
        ensure_ascii=False,
    ).replace('<', '\\u003c')
    context = {
        'faqs': FAQS,
        'features': FEATURES,
        'create_steps': CREATE_STEPS,
        'popular_combos': POPULAR_COMBOS,
        'how_to_web': HOW_TO_WEB,
        'comparison_rows': COMPARISON_ROWS,
        'faq_json_ld': faq_json_ld,
        'combo_count_display': f'{COMBO_COUNT:,}',
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


EMOJI_ART_EDITOR_FAQS = [
    {
        'question': 'What is an emoji art editor?',
        'answer': 'It is a grid where you place emojis one cell at a time to build a picture, then copy the picture as text. '
                  'Each row of the grid becomes one line of emojis.',
    },
    {
        'question': 'How do I copy my emoji art into a message?',
        'answer': 'Press Copy, open the app you want to use, and paste. The art pastes as ordinary text with one line per row, '
                  'so it works best in apps that keep line breaks and use a similar width for every emoji.',
    },
    {
        'question': 'Why does my emoji art look crooked after pasting?',
        'answer': 'Some apps change the spacing or wrap long lines. Try a smaller grid, choose a different empty-cell character, '
                  'or paste into a place that does not reflow text.',
    },
    {
        'question': 'Can I pick up an emoji I already drew?',
        'answer': 'Yes. Hold Ctrl (or Cmd on a Mac) and click a filled cell to make that emoji your brush.',
    },
    {
        'question': 'Is my drawing saved or uploaded?',
        'answer': 'No. The editor runs in your browser and nothing is sent to the server. Copy or download your art before you close the page.',
    },
]

DOT_ART_GENERATOR_FAQS = [
    {
        'question': 'What is dot art?',
        'answer': 'Dot art is a picture made from Braille characters. Each character holds a small grid of raised dots, '
                  'so a block of them can show an image as plain text.',
    },
    {
        'question': 'How do I turn a picture into dot art?',
        'answer': 'Choose an image, pick a mode and size, then copy the result. Dither keeps shading, Threshold gives a '
                  'black-and-white look, and Line art traces the edges.',
    },
    {
        'question': 'Is my image uploaded to a server?',
        'answer': 'No. The picture is read and converted in your browser, and it never leaves your device.',
    },
    {
        'question': 'Why do some apps show the dot art with gaps or the wrong width?',
        'answer': 'Apps use different fonts, and some collapse blank Braille characters. Keep the option that avoids blank '
                  'characters switched on, and try a smaller width if lines wrap.',
    },
    {
        'question': 'Which pictures work best?',
        'answer': 'Simple images with strong contrast, such as a logo, a face or a silhouette, convert most clearly. '
                  'Raise the contrast slider for flat or dark photos.',
    },
]


MOOD_FAQS = [
    {
        'question': 'How does the emoji mood finder work?',
        'answer': 'It reads the feeling words in what you write, such as tired, excited or heartbroken, and matches them to '
                  'emoji sets. It then mixes the emojis of those moods into fresh combos and adds ready-made sets from this site.',
    },
    {
        'question': 'Is the mood finder an AI chatbot?',
        'answer': 'No. It is a simple word-matching tool, so it is fast and gives the same answer for the same words. '
                  'It understands common feelings and phrases but not every sentence.',
    },
    {
        'question': 'Can I describe more than one feeling?',
        'answer': 'Yes. Try something like "tired but happy it is Friday". The finder picks up to three moods and blends their emojis.',
    },
    {
        'question': 'Is what I type saved?',
        'answer': 'What you type is used only to build the results and is not stored in the site database or linked to you.',
    },
    {
        'question': 'Why did it not recognise my mood?',
        'answer': 'It may not know the word you used. Try a simpler feeling word, or tap one of the mood buttons. '
                  'When nothing matches, it shows friendly all-round picks instead.',
    },
]


def emoji_combos_mood(request):
    """Describe a mood, get emoji combos. The page without a query is indexable; result pages are not."""
    text = mood_engine.clean_text(request.GET.get('mood', ''))
    try:
        shuffle = int(request.GET.get('shuffle', '0'))
    except ValueError:
        shuffle = 0
    shuffle = max(0, min(shuffle, mood_engine.MAX_SHUFFLE))
    result = mood_engine.find_combos(text, shuffle) if text else None
    context = {
        'faqs': MOOD_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_mood')),
        'text': text,
        'result': result,
        'sticker_version': stickers.STICKER_VERSION,
    }
    if result:
        result['mashups'] = mashup_links(result['mashups'])
        next_shuffle = shuffle + 1 if shuffle < mood_engine.MAX_SHUFFLE else 0
        context['shuffle_url'] = f"{reverse('emoji_combos_mood')}?{urlencode({'mood': text, 'shuffle': next_shuffle})}"
    return render(request, 'kitchen/emoji_combos_mood.html', context)


def emoji_art_editor(request):
    context = {
        'faqs': EMOJI_ART_EDITOR_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_art_editor')),
    }
    return render(request, 'kitchen/emoji_art_editor.html', context)


def dot_art_generator(request):
    context = {
        'faqs': DOT_ART_GENERATOR_FAQS,
        'canonical_url': absolute_site_url(reverse('dot_art_generator')),
    }
    return render(request, 'kitchen/dot_art_generator.html', context)


THANKSGIVING_POST_SLUG = 'thanksgiving-emoji-combos'
THANKSGIVING_COMBO_CTA = (
    'Hosting Thanksgiving first? Copy '
    '<a href="/blog/thanksgiving-emoji-combos/">Thanksgiving emoji combos</a>. '
)


def thanksgiving_blog_is_published():
    """True when the Thanksgiving blog post is live, so combo pages can link to it."""
    return BlogPost.objects.filter(
        slug=THANKSGIVING_POST_SLUG,
        status=BlogPost.STATUS_PUBLISHED,
    ).exists()


READY_MADE_TEMPLATE = 'ready_made_emoji_combo.html'

EMOJI_COMBOS_HUB_TITLE = 'Emoji Combos: Browse Categories and Ready Made Sets'
EMOJI_COMBOS_HUB_META = (
    'Browse emoji combos by theme: cute, aesthetic, love, funny, pink, birthday and more. '
    'Open the Ready Made Emoji Combo page to copy sets in one tap.'
)

# (url name, label, one-line blurb) for the theme links on the /emoji-combos/ hub.
EMOJI_COMBOS_HUB_CATEGORIES = [
    ('emoji_combos_cute', 'Cute', 'Animals, bows, flowers and soft faces.'),
    ('emoji_combos_aesthetic', 'Aesthetic', 'Sets built around one mood or palette.'),
    ('emoji_combos_love', 'Love', 'Hearts and flowers for romantic messages.'),
    ('emoji_combos_funny', 'Funny', 'Unexpected faces and reactions for chats.'),
    ('emoji_combos_pink', 'Pink', 'Pink hearts, bows and pastel sets.'),
    ('emoji_combos_birthday', 'Birthday', 'Wishes, party sets and belated notes.'),
    ('emoji_combos_friendship', 'Friendship', 'Sets for besties and group chats.'),
    ('emoji_combos_sad', 'Sad', 'Rainy and heartbreak sets for low moods.'),
    ('emoji_combos_dark', 'Dark', 'Gothic, witchy and dark academia looks.'),
    ('emoji_combos_christmas', 'Christmas', 'Cozy, festive and funny holiday sets.'),
    ('emoji_combos_bio', 'Bio', 'Sets sorted by interest for your profile.'),
]


def ready_made_emoji_combo_copy(count):
    """Title and meta for /ready-made-emoji-combo/. A '100+' style number is used only when the real count supports it."""
    floor = floor_hundreds(count)
    lead = f'{floor}+ ' if floor else ''
    title = f'Ready Made Emoji Combo: {lead}Sets to Copy & Paste'
    meta = (
        f'Tap to copy {lead}emoji combos for bios, captions and chats: cute, aesthetic, love, funny and pink sets. '
        'Want an image? Mix emojis with Emoji Kitchen.'
    )
    return title, meta


def emoji_combos(request):
    """Short hub: links to the Ready Made Emoji Combo page and to every theme page."""
    context = {
        'canonical_url': absolute_site_url(reverse('emoji_combos')),
        'page_title': EMOJI_COMBOS_HUB_TITLE,
        'page_meta': EMOJI_COMBOS_HUB_META,
        'categories': [
            {'href': reverse(url_name), 'label': label, 'blurb': blurb}
            for url_name, label, blurb in EMOJI_COMBOS_HUB_CATEGORIES
        ],
        'keywords': [
            {'href': reverse('emoji_combos_tag', kwargs={'slug': slug}), 'label': page['label'],
             'icon': page['badge'].split(' ', 1)[0]}
            for slug, page in TAG_PAGES.items()
        ],
    }
    return render(request, 'kitchen/emoji_combos.html', context)


def ready_made_emoji_combo(request):
    combo_count = distinct_set_count(READY_MADE_TEMPLATE)
    page_title, page_meta = ready_made_emoji_combo_copy(combo_count)
    context = {
        'faqs': EMOJI_COMBOS_PAGE_FAQS,
        'canonical_url': absolute_site_url(reverse('ready_made_emoji_combo')),
        'page_title': page_title,
        'page_meta': page_meta,
        'combo_count': combo_count,
        'thanksgiving_post_live': thanksgiving_blog_is_published(),
    }
    return render(request, f'kitchen/{READY_MADE_TEMPLATE}', context)


def emoji_combos_love(request):
    context = {
        'faqs': LOVE_EMOJI_COMBOS_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_love')),
        'combo_count': distinct_set_count('emoji_combos_love.html'),
    }
    return render(request, 'kitchen/emoji_combos_love.html', context)


def emoji_combos_cute(request):
    context = {
        'faqs': CUTE_EMOJI_COMBOS_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_cute')),
        'combo_count': distinct_set_count('emoji_combos_cute.html'),
    }
    return render(request, 'kitchen/emoji_combos_cute.html', context)


def emoji_combos_funny(request):
    context = {
        'faqs': FUNNY_EMOJI_COMBOS_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_funny')),
        'combo_count': distinct_set_count('emoji_combos_funny.html'),
    }
    return render(request, 'kitchen/emoji_combos_funny.html', context)


def emoji_combos_pink(request):
    context = {
        'faqs': PINK_EMOJI_COMBOS_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_pink')),
        'combo_count': distinct_set_count('emoji_combos_pink.html'),
    }
    return render(request, 'kitchen/emoji_combos_pink.html', context)


def emoji_combos_aesthetic(request):
    context = {
        'faqs': AESTHETIC_EMOJI_COMBOS_FAQS,
        'canonical_url': absolute_site_url(reverse('emoji_combos_aesthetic')),
        'combo_count': distinct_set_count('emoji_combos_aesthetic.html'),
    }
    return render(request, 'kitchen/emoji_combos_aesthetic.html', context)


def mashup_links(pairs):
    """[(emoji1, emoji2, href)] for the mixer. A pair with no sticker in the data is dropped, so no link can be dead."""
    links = []
    for first, second in pairs:
        if combo_image_url(first, second):
            href = f'/?emoji1={quote(first)}&emoji2={quote(second)}#kitchen'
            links.append({'first': first, 'second': second, 'href': href, 'image': combo_image_url(first, second)})
    return links


def category_combos(page):
    """The page's copyable sets as dicts, with a count of distinct sets computed from the data."""
    combos = [{'cat': cat, 'label': label, 'emoji': emoji} for cat, label, emoji in page['combos']]
    return combos, len({c['emoji'] for c in combos})


def emoji_combos_category(request, slug):
    page = COMBO_PAGES.get(slug)
    if page is None:
        raise Http404('No such emoji combo page')
    if slug == 'christmas' and thanksgiving_blog_is_published():
        page = {**page, 'siblings_cta': THANKSGIVING_COMBO_CTA + page['siblings_cta']}
    return render_combo_page(request, page, reverse(f'emoji_combos_{slug}'))


def render_combo_page(request, page, path):
    """Render a data-driven combo page (category or keyword) with the shared copy-and-filter tool."""
    combos, combo_count = category_combos(page)
    context = {
        'page': page,
        'faqs': [{'question': q, 'answer': a} for q, a in page['faqs']],
        'canonical_url': absolute_site_url(path),
        'combos': combos,
        'combos_json': combos,
        'combo_count': combo_count,
        'featured': combos[:12],
        'filters': [{'key': key, 'label': label} for key, label in page['filters']],
        'mashups': mashup_links(page['mashups']),
    }
    return render(request, 'kitchen/emoji_combos_category.html', context)


def emoji_combos_tag(request, slug):
    """Keyword page, e.g. /emoji-combos/kawaii/. Unknown keywords are a normal 404."""
    page = TAG_PAGES.get(slug)
    if page is None:
        raise Http404('No such emoji combo keyword')
    return render_combo_page(request, page, reverse('emoji_combos_tag', kwargs={'slug': slug}))


def emoji_combos_search(request):
    """Search every copyable set on the site. Results pages are kept out of the index."""
    query = clean_query(request.GET.get('q', ''))
    results, total = search_sets(query)
    context = {
        'canonical_url': absolute_site_url(reverse('emoji_combos_search')),
        'query': query,
        'results': results,
        'total': total,
        'shown': len(results),
        'tag_links': matching_tag_pages(query),
        'suggestions': [{'label': p['label'], 'href': reverse('emoji_combos_tag', kwargs={'slug': s})}
                        for s, p in list(TAG_PAGES.items())[:8]],
    }
    return render(request, 'kitchen/emoji_combos_search.html', context)


def emoji_keyboard(request):
    context = {
        'faqs': EMOJI_KEYBOARD_FAQS,
    }
    return render(request, 'kitchen/emoji_keyboard.html', context)


def emoji_keyboard_for_pc(request):
    context = {
        'faqs': EMOJI_KEYBOARD_PC_FAQS,
        'faq_json_ld': _faq_json_ld(EMOJI_KEYBOARD_PC_FAQS),
    }
    return render(request, 'kitchen/emoji_keyboard_for_pc.html', context)


def emoji_kitchen_guide(request):
    context = {'canonical_url': absolute_site_url(reverse('emoji_kitchen_guide'))}
    return render(request, 'kitchen/emoji_kitchen_guide.html', context)


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

    canonical_url = clean_canonical(
        request,
        post.canonical_url,
        post.get_absolute_url(),
        current_slug=post.slug,
    )
    share_image, share_w, share_h, share_type = share_image_meta(
        request, post.og_image_display
    )
    context = {
        'post': post,
        'related_posts': related_posts,
        'canonical_url': canonical_url,
        'share_image': share_image,
        'share_image_width': share_w,
        'share_image_height': share_h,
        'share_image_type': share_type,
        'article_json_ld': article_json_ld(
            post, canonical_url, absolute_site_url('/'), share_image,
            image_width=share_w, image_height=share_h,
        ),
        'post_faqs': [{'question': q, 'answer': a} for q, a in faq_pairs_from_html(post.content)],
    }
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


def get_sticker(request):
    """Download a supported mashup as a sticker: 512 x 512, transparent, white outline (WebP by default)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'GET only'}, status=405)
    emoji1 = request.GET.get('emoji1', '').strip()
    emoji2 = request.GET.get('emoji2', '').strip()
    fmt = request.GET.get('format', 'webp').strip().lower()

    if not emoji1 or not emoji2:
        return JsonResponse({'error': 'Two emojis required'}, status=400)
    if len(emoji1) > 32 or len(emoji2) > 32:
        return JsonResponse({'error': 'Invalid emoji characters'}, status=400)
    if fmt not in stickers.FORMATS:
        return JsonResponse({'error': 'format must be webp or png'}, status=400)

    url = combo_image_url(emoji1, emoji2)
    if not url:
        return JsonResponse({'error': 'No Emoji Kitchen mashup exists for this pair'}, status=404)

    try:
        data = stickers.make_sticker(url, fmt)
    except stickers.StickerError as exc:
        logger.warning('Sticker failed for %s + %s: %s', emoji1, emoji2, exc)
        return JsonResponse({'error': 'Could not make the sticker. Please try again.'}, status=502)

    first, second = sorted([_emoji_to_codepoints(emoji1), _emoji_to_codepoints(emoji2)])
    response = HttpResponse(data, content_type=f'image/{fmt}')
    response['Content-Disposition'] = f'attachment; filename="emoji-kitchen-sticker-{first}-{second}.{fmt}"'
    response['Cache-Control'] = 'public, max-age=86400'
    return response


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


def get_supported_emojis(request):
    """Every emoji that has at least one Kitchen pair, with how many partners it has.

    The mixer uses this to tell visitors which emojis have no sticker pairs and to suggest
    alternatives."""
    response = JsonResponse({'emojis': SUPPORTED_EMOJI_COUNTS})
    response['Cache-Control'] = 'public, max-age=3600'
    return response


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




# ── Helpers ───────────────────────────────────────────────────────────────────

def _faq_json_ld(faqs):
    """FAQPage structured data for a list of {'question', 'answer'} dicts."""
    return faq_json_ld(faqs)


def combo_image_url(emoji1, emoji2):
    """Image URL for a supported pair, or None when the pair has no sticker."""
    cp1 = _emoji_to_codepoints(emoji1)
    cp2 = _emoji_to_codepoints(emoji2)
    if not cp1 or not cp2:
        return None
    a, b = sorted([cp1, cp2])
    entry = EMOJI_COMBOS['pairs'].get(f'{a},{b}')
    if not entry:
        return None
    date_idx, swap = entry
    date = EMOJI_COMBOS['dates'][date_idx]
    left, right = (b, a) if swap else (a, b)
    left_part = _codepoints_to_url_part(left)
    right_part = _codepoints_to_url_part(right)
    return (
        f'https://www.gstatic.com/android/keyboard/emojikitchen/'
        f'{date}/{left_part}/{left_part}_{right_part}.png'
    )


def _emoji_to_codepoints(emoji: str) -> str:
    codepoints = [hex(ord(char))[2:].lower() for char in emoji]
    return '-'.join(codepoints)


def _codepoints_to_url_part(codepoints: str) -> str:
    return '-'.join(f'u{part}' for part in codepoints.split('-'))
