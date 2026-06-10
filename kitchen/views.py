import requests
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse


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

BLOG_POSTS = [
    {
        'category': 'GUIDE',
        'title': "10 emoji combos people can't stop sending",
        'description': "A round-up of the most-loved mashups and the moods they're perfect for.",
        'read_time': '5 min read',
        'emoji_header': '🔥❤️',
        'coming_soon': True,
        'bg_color': '#F5E6D3',
    },
    {
        'category': 'HOW-TO',
        'title': 'Using Emoji Kitchen on WhatsApp & iMessage',
        'description': 'Step-by-step setup so your custom stickers work in every chat app.',
        'read_time': '4 min read',
        'emoji_header': '📱✨',
        'coming_soon': True,
        'bg_color': '#D3E8E8',
    },
    {
        'category': 'FUN',
        'title': 'The weirdest mashups we found this week',
        'description': 'Some combos are adorable, some are chaos. Here are our favourites.',
        'read_time': '3 min read',
        'emoji_header': '🐱🍰',
        'coming_soon': True,
        'bg_color': '#E0D3F0',
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
        'description': 'The tool shows your emoji mix as soon as you choose both icons — no long prompts, no extra screens, no waiting.',
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
    },
    {
        'icon': '🥰',
        'title': 'Cute Combinations',
        'description': 'Often use hearts, smiling faces, flowers, animals, and soft expressions. These stickers fit friendly messages, kind replies, birthday wishes, or chats where a normal heart feels too simple.',
        'bg': '#FCE4EC',
        'border': '#F48FB1',
        'examples': ['🥰', '🌸', '🐱', '❤️'],
    },
    {
        'icon': '🌸',
        'title': 'Aesthetic Combinations',
        'description': 'Focus on a calm look or matching theme. Try stars, moons, flowers, clouds, hearts, and simple faces — ideal for captions, profile posts, gentle messages, or picture-based social content.',
        'bg': '#EDE7F6',
        'border': '#CE93D8',
        'examples': ['🌸', '⭐', '🌙', '🌈'],
    },
    {
        'icon': '🎲',
        'title': 'Random Combinations',
        'description': 'Pick any first emoji, then choose a second one without thinking too much. Odd pairs often produce the funniest and most unexpected creations — great for quick, surprising replies.',
        'bg': '#E8F5E9',
        'border': '#A5D6A7',
        'examples': ['🎲', '🦄', '🍄', '🚀'],
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


# ── Views ─────────────────────────────────────────────────────────────────────

def home(request):
    context = {
        'faqs': FAQS,
        'blog_posts': BLOG_POSTS,
        'features': FEATURES,
        'create_steps': CREATE_STEPS,
        'popular_combos': POPULAR_COMBOS,
        'how_to_web': HOW_TO_WEB,
        'how_to_phone': HOW_TO_PHONE,
        'comparison_rows': COMPARISON_ROWS,
    }
    return render(request, 'kitchen/home.html', context)


def get_combo(request):
    emoji1 = request.GET.get('emoji1', '').strip()
    emoji2 = request.GET.get('emoji2', '').strip()

    if not emoji1 or not emoji2:
        return JsonResponse({'error': 'Two emojis required'}, status=400)

    hex1 = _emoji_to_hex(emoji1)
    hex2 = _emoji_to_hex(emoji2)

    if not hex1 or not hex2:
        return JsonResponse({'error': 'Invalid emoji characters'}, status=400)

    dates = [
        '20230301', '20230126', '20221101', '20220815',
        '20220506', '20220406', '20220203', '20220110',
        '20211115', '20210831', '20210521', '20210218',
        '20201001',
    ]

    BASE = 'https://www.gstatic.com/android/keyboard/emojikitchen'
    urls = []
    for date in dates:
        urls.append(f'{BASE}/{date}/{hex1}/{hex1}_{hex2}.png')
        urls.append(f'{BASE}/{date}/{hex2}/{hex2}_{hex1}.png')

    return JsonResponse({'urls': urls, 'emoji1': emoji1, 'emoji2': emoji2})


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

def _emoji_to_hex(emoji: str) -> str:
    codepoints = []
    for char in emoji:
        cp = ord(char)
        if cp == 0xFE0F:
            continue
        codepoints.append(hex(cp)[2:].lower())
    if not codepoints:
        return ''
    return 'u' + '_u'.join(codepoints)
