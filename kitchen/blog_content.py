"""The new text for the four blog posts, from the "Remaining Content Updates" document.

Two sentences in the document were notes to the editor ("should not be described as ...");
they are written here as ordinary statements for visitors.
"""
from functools import partial

from . import blog_updates as bu
from .blog_updates import h2, links, ol, p, quick

HOME = '/'
GBOARD = '/blog/emoji-kitchen-gboard/'
SAMSUNG = '/blog/emoji-kitchen-samsung/'
IPHONE = '/blog/emoji-kitchen-iphone/'
WHATSAPP = '/blog/emoji-kitchen-whatsapp/'

POST_UPDATES = {
    # ───────────────────────────────────────────────────────────────── Gboard
    'emoji-kitchen-gboard': {
        'fields': {
            'title': 'How to Use Emoji Kitchen in Gboard on Android',
            'excerpt': 'Learn how to access Emoji Kitchen through Gboard on supported Android devices, choose available '
                       'emoji combinations and troubleshoot missing suggestions. For iPhone or WhatsApp-specific '
                       'instructions, see the relevant dedicated guide.',
            'seo_title': 'How to Use Emoji Kitchen in Gboard on Android',
            'seo_description': 'Learn how to use Emoji Kitchen through Gboard on Android, find supported emoji mashups '
                               'and troubleshoot missing sticker suggestions.',
        },
        'operations': [
            ('introduction and quick answer', partial(bu.replace_intro, lead=1, new_blocks=[
                p("Google's Emoji Kitchen lets users explore sticker-style combinations through supported Gboard "
                  "experiences on Android. The feature is different from placing two ordinary emoji characters next "
                  "to each other in a text message."),
                p('This guide focuses on accessing the feature through Gboard, selecting available combinations and '
                  'troubleshooting situations where suggestions do not appear. The exact interface can vary by device, '
                  'app and software version.'),
                quick('Open a compatible application on an Android device and make sure Gboard is the active keyboard. '
                      'Open its emoji interface, choose an emoji and check for supported combination suggestions. If no '
                      'suitable result appears, try a different pair and confirm that the keyboard and application are '
                      'up to date.'),
            ])),
            ('cross-device section', partial(bu.replace_section, old_heading='Gboard Emoji Kitchen on iPhone and Other Devices', new_blocks=[
                h2('Using Emoji Kitchen on Other Devices'),
                p('This article focuses on the Gboard workflow on Android. The browser-based mixer on Emoji Kitchen Hub '
                  'is a separate option for exploring supported combinations without relying on the same keyboard interface.'),
                p('For Apple-device instructions, use the dedicated iPhone guide. For sharing a mashup through WhatsApp, '
                  'consult the WhatsApp-specific guide.'),
                links([('iPhone guide', IPHONE), ('WhatsApp guide', WHATSAPP)]),
                p('The browser tool and Gboard can differ in supported combinations, controls, output and saving behavior. '
                  'Follow the instructions for the product you are actually using.'),
            ])),
            ('final call to action', partial(bu.replace_section, old_heading='Make Your Next Gboard Emoji Mashup', new_blocks=[
                h2('Try Emoji Kitchen on Your Android Device'),
                p('Once Gboard is active, choose a compatible emoji pair and check whether a sticker-style suggestion '
                  "appears. If no result is available, try a different pair and check the application's behavior before "
                  'assuming the feature is broken.'),
                p('If you need a browser-based alternative, explore the Emoji Kitchen Hub mixer. Use the dedicated WhatsApp '
                  'guide when you need help sharing the result in a conversation.'),
                links([('Open the mixer', HOME), ('Read the WhatsApp guide', WHATSAPP)]),
            ])),
        ],
    },
    # ──────────────────────────────────────────────────────────────── Samsung
    'emoji-kitchen-samsung': {
        'fields': {
            'title': 'How to Use Emoji Kitchen on Samsung Galaxy Phones',
            'excerpt': "Learn how Google's Emoji Kitchen through Gboard differs from Samsung Keyboard, how to select the "
                       'relevant keyboard and what to check when combination suggestions are missing.',
            'seo_title': 'How to Use Emoji Kitchen on Samsung Galaxy Phones',
            'seo_description': "Learn the difference between Gboard and Samsung Keyboard, how to access Google's Emoji "
                               'Kitchen on a Galaxy phone, and how to troubleshoot missing suggestions.',
        },
        'operations': [
            ('introduction and quick answer', partial(bu.replace_intro, lead=1, new_blocks=[
                p("Samsung Galaxy phones can provide more than one keyboard experience, so it is important to distinguish "
                  "Samsung Keyboard from Google's Gboard. Google's Emoji Kitchen is associated with supported Gboard "
                  "experiences, while Samsung's own emoji and sticker tools may have different features."),
                p("This guide explains what to check when you want to use Google's Emoji Kitchen on a Samsung phone. The "
                  'exact settings and menus can vary by device model and software version.'),
                quick("If you want to use Google's Emoji Kitchen on a supported Samsung Galaxy phone, check whether Gboard "
                      'is installed, enabled and selected as the active keyboard. Then open a compatible application and '
                      'look for available emoji combination suggestions. If the feature is missing, try another supported '
                      'pair and check the current keyboard settings.'),
            ])),
            ('"Does Samsung Have Emoji Kitchen?" explanation', partial(bu.replace_under_heading,
                heading='Does Samsung Have Emoji Kitchen?', first=0, count=2, new_blocks=[
                p("Samsung Galaxy phones can use Google's Emoji Kitchen through supported Gboard experiences. Samsung "
                  'Keyboard is a separate application with its own emoji and sticker features. Although some features may '
                  'look similar, they are not the same product.'),
                p("If you want Google's Emoji Kitchen, check the active keyboard and follow the current Gboard "
                  'instructions for your device.'),
            ])),
            ('final summary', partial(bu.replace_section, old_heading='Conclusion', new_blocks=[
                h2('Choosing the Right Emoji Workflow on Samsung'),
                p("Use Gboard when you specifically want to access Google's Emoji Kitchen on a supported Android setup. "
                  'Use Samsung Keyboard when you prefer its own features and controls.'),
                p("If the expected combination does not appear, check the active keyboard, try another emoji pair and "
                  "review the instructions for your device's software version. You can also explore the separate "
                  'browser-based mixer when you want to test available combinations outside the keyboard workflow.'),
                links([('Open the browser-based mixer', HOME)]),
            ])),
        ],
    },
    # ───────────────────────────────────────────────────────────────── iPhone
    'emoji-kitchen-iphone': {
        'fields': {
            'title': 'How to Use Emoji Kitchen on iPhone',
            'excerpt': 'Learn how to explore supported emoji mashups on iPhone through a browser-based workflow. Find '
                       'practical guidance for checking results, saving images where supported and sharing them with '
                       'compatible applications.',
            'seo_title': 'How to Use Emoji Kitchen on iPhone',
            'seo_description': 'Learn how to explore supported emoji mashups on iPhone through a browser-based workflow, '
                               'then understand how to save or share the result where supported.',
        },
        'operations': [
            ('introduction and quick answer', partial(bu.replace_intro, lead=0, new_blocks=[
                p('The standard iPhone emoji keyboard inserts emoji characters into text. A sticker-style mashup is a '
                  'different format, so its creation and sharing workflow may differ.'),
                p('You can explore supported emoji combinations on iPhone through a browser-based mixer. The available '
                  'actions depend on the current tool, iOS version, browser and destination application.'),
                quick('Open the browser-based mixer, select two supported emojis and check whether a result appears. Use '
                      'the available copy or download control if it is supported. A sticker-style mashup is an image, not '
                      'a new emoji character added to the iPhone keyboard.'),
            ])),
            ('keyword-list paragraph', partial(bu.replace_paragraph_containing,
                heading='Can You Use Emoji Kitchen on iPhone?', needle='kitchen emoji iPhone', new_block=p(
                'The main question is how to create and use an image-based mashup on an Apple device. A browser-based tool '
                'provides a separate workflow from the standard iPhone emoji keyboard, which is designed for ordinary '
                'text characters.'))),
            ('final summary', partial(bu.replace_section, old_heading='Make Your Next Emoji Mix on iPhone', new_blocks=[
                h2('Using Emoji Kitchen on iPhone'),
                p('A browser-based mixer is a separate way to explore supported emoji combinations on iPhone. Select a '
                  'pair, check the result and use the available output options if they work with your browser and '
                  'destination application.'),
                p('For standard emoji characters, use the iPhone emoji keyboard. For instructions about sending a mashup '
                  'through WhatsApp, see the dedicated WhatsApp guide.'),
                links([('WhatsApp guide', WHATSAPP)]),
            ])),
            ('table of contents entry', partial(bu.rename_toc_entry, old='Make Your Next Emoji Mix on iPhone',
                                                new='Using Emoji Kitchen on iPhone')),
        ],
    },
    # ─────────────────────────────────────────────────────────────── WhatsApp
    'emoji-kitchen-whatsapp': {
        'fields': {
            'title': 'How to Share Emoji Kitchen Stickers in WhatsApp',
            'excerpt': 'Learn how to share supported emoji mashups in WhatsApp, understand the difference between text '
                       'characters and image-based stickers, and troubleshoot copying or attachment problems.',
            'seo_title': 'How to Share Emoji Kitchen Stickers in WhatsApp',
            'seo_description': 'Learn how to share supported emoji mashups in WhatsApp, understand the difference between '
                               'text and image-based stickers, and troubleshoot sharing problems.',
        },
        'operations': [
            ('introduction and quick answer', partial(bu.replace_intro, lead=1, new_blocks=[
                p('Emoji combinations can be shared in WhatsApp in different ways depending on their source and format. A '
                  'standard emoji is text, while a sticker-style mashup is an image. This difference affects how the '
                  'result can be copied, attached and sent.'),
                p('This guide focuses on sharing a supported mashup in WhatsApp. The exact steps depend on whether the '
                  'result comes from Gboard, a browser-based mixer or another image source.'),
                quick('On a supported Android setup, Gboard may provide Emoji Kitchen suggestions that can be sent through '
                      'compatible applications. A browser-based mixer is another option for exploring supported pairs. Use '
                      'the available copy or download controls only where they are supported, and attach the saved image '
                      'when the destination application requires it.'),
            ])),
            ('"What Is Emoji Kitchen on WhatsApp?" section', partial(bu.replace_section, old_heading='What Is Emoji Kitchen on WhatsApp?', new_blocks=[
                h2('What Is Emoji Kitchen in WhatsApp?'),
                p("Emoji Kitchen is Google's sticker-mixing feature, while WhatsApp is one of the applications in which a "
                  'result may be shared. WhatsApp does not create the mashup itself.'),
                p('A standard emoji appears as a text character, whereas a mashup is a designed image. The available method '
                  'for creating and sharing that image depends on the device, keyboard, browser and application version.'),
            ])),
            ('browser sharing section', partial(bu.replace_section, old_heading='How to Use Emoji Kitchen for WhatsApp in a Browser', new_blocks=[
                h2('How to Share a Browser-Created Mashup in WhatsApp'),
                p('A browser-based mixer is a separate option when the expected keyboard workflow is unavailable or when '
                  'you prefer to explore combinations in a browser.'),
                ol(['Open the Emoji Kitchen Hub mixer.', 'Choose the first emoji.',
                    'Choose a second emoji and check whether a result appears.',
                    'Use the available copy or download control if supported.',
                    'Open WhatsApp and select the intended conversation.',
                    'Paste the copied result if the application accepts it, or attach the saved image where supported.']),
                p("Copying behavior can vary between browsers and applications. If a copied image cannot be pasted, try "
                  "downloading the image and attaching it through WhatsApp's media picker."),
            ])),
            ('final summary', partial(bu.replace_section, old_heading='Create Your Next WhatsApp Sticker', new_blocks=[
                h2('Choose a Sharing Method That Works'),
                p('Use Gboard when you want to explore available Emoji Kitchen suggestions through a supported Android '
                  'workflow. Use a browser-based mixer when you need an alternative way to explore supported pairs.'),
                p('Before sharing, check that the result looks correct and that the destination application accepts the '
                  'chosen format. An image-based mashup and a standard text emoji are different types of content.'),
                links([('For Android keyboard instructions, see the Gboard guide', GBOARD),
                       ('For Samsung-specific keyboard guidance, see the Samsung guide', SAMSUNG)]),
            ])),
        ],
    },
}
