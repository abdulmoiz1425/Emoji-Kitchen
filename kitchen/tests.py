import json
import io
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core.management import CommandError, call_command
from django.utils.html import escape as django_escape
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import resolve, reverse

from . import views
from emoji_kitchen.envfile import load_env

from . import blog_content, blog_updates, explore

from .combo_tags import RESERVED_SLUGS, TAG_PAGES
from .models import BlogPost
from .sitemaps import ComboPageSitemap, StaticViewSitemap

PC = '/emoji-keyboard-for-pc/'
READY_MADE = '/ready-made-emoji-combo/'   # holds the content that used to be on /emoji-combos/
TAG_PATHS = [f'/emoji-combos/{slug}/' for slug in TAG_PAGES]   # keyword pages (kitchen/combo_tags.py)
WHATSAPP_URL = 'https://whatsapp.com/channel/0029VbELF1pCXC3RhJFkUm25'
POST_SLUGS = [
    'emoji-kitchen-iphone',
    'emoji-kitchen-samsung',
    'emoji-kitchen-gboard',
    'emoji-kitchen-whatsapp',
]
POSTS = [f'/blog/{slug}/' for slug in POST_SLUGS]
LEGACY = {f'/{slug}/' for slug in POST_SLUGS}
HUBS = ['/', '/emoji-maker/', '/emoji-generator/', '/emoji-keyboard/', '/emoji-combos/']
COMBOS = [
    '/emoji-combos/love/',
    '/emoji-combos/cute/',
    '/emoji-combos/aesthetic/',
    '/emoji-combos/funny/',
    '/emoji-combos/pink/',
]
# The data-driven category pages (kitchen/combo_pages.py). Kept apart from COMBOS on purpose:
# the home page links to the five COMBOS pages and only to two of these.
MORE_COMBOS = [
    '/emoji-combos/birthday/',
    '/emoji-combos/sad/',
    '/emoji-combos/friendship/',
    '/emoji-combos/bio/',
    '/emoji-combos/dark/',
    '/emoji-combos/christmas/',
]
LEGAL = ['/about-us/', '/contact/', '/privacy/', '/terms/', '/disclaimer/', '/cookie-policy/']
ALL_PAGES = HUBS + [READY_MADE, PC] + COMBOS + MORE_COMBOS + ['/blog/'] + POSTS + LEGAL
WEAK_ANCHORS = {'click here', 'read more', 'here', 'more', 'learn more'}
# Some page copy links with the full address, so those count as internal too.
SITE_HOSTS = {'testserver', 'emojikitchenhub.com', 'www.emojikitchenhub.com'}

EXPECTED_H2 = [
    'What Is an Emoji Keyboard on a PC?',
    'How to Open the Emoji Keyboard for PC',
    'What Is the Windows Emoji Keyboard Shortcut?',
    'How to Type Emojis on a Windows PC',
    'Windows Emoji Panel vs. Online Emoji Keyboard',
    'Why Is My Emoji Keyboard Not Working?',
    'Can You Use Emojis Without the Windows Key?',
    'Are PC Emojis the Same on Every Device?',
    'FAQs',
    'Choose the Right Emoji Method for Your PC',
]


class _PageParser(HTMLParser):
    """Collects <a> links (with anchor text and attributes) and key page facts."""

    def __init__(self):
        super().__init__()
        self.skip = 0                  # depth inside header / footer / nav
        self.body_links = []           # (href, anchor text, attrs) outside header/footer/nav
        self.footer_social = []        # hrefs inside <div class="footer__social">
        self.h1 = []
        self.h2 = []
        self.details = 0
        self.tables = 0
        self.canonical = None
        self.meta = {}
        self.ld_json = []
        self.title = ''
        self._cur = None
        self._heading = None
        self._in_title = False
        self._in_ld = False
        self._social_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('header', 'footer', 'nav'):
            self.skip += 1
        if tag == 'div' and 'footer__social' in (attrs.get('class') or ''):
            self._social_depth = 1
        elif tag == 'div' and self._social_depth:
            self._social_depth += 1
        if tag == 'a' and attrs.get('href') is not None:
            if self._social_depth:
                self.footer_social.append(attrs['href'])
            if not self.skip:
                self._cur = [attrs['href'], '', attrs]
        if tag in ('h1', 'h2'):
            self._heading = tag
            getattr(self, tag).append('')
        if tag == 'details':
            self.details += 1
        if tag == 'table':
            self.tables += 1
        if tag == 'title':
            self._in_title = True
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content')
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self._in_ld = True
            self.ld_json.append('')

    def handle_endtag(self, tag):
        if tag in ('header', 'footer', 'nav') and self.skip:
            self.skip -= 1
        if tag == 'div' and self._social_depth:
            self._social_depth -= 1
        if tag == 'a' and self._cur:
            self.body_links.append(tuple(self._cur))
            self._cur = None
        if tag in ('h1', 'h2'):
            self._heading = None
        if tag == 'title':
            self._in_title = False
        if tag == 'script':
            self._in_ld = False

    def handle_data(self, data):
        if self._cur:
            self._cur[1] += data
        if self._heading:
            getattr(self, self._heading)[-1] += data
        if self._in_title:
            self.title += data
        if self._in_ld:
            self.ld_json[-1] += data


def _clean(text):
    return ' '.join(text.split())


class PageTestCase(TestCase):
    """Creates the four public blog posts (plus a draft) and gives parsing helpers."""

    @classmethod
    def setUpTestData(cls):
        for slug in POST_SLUGS:
            BlogPost.objects.create(
                title=slug.replace('-', ' ').title(),
                slug=slug,
                content='<p>Body</p>',
                status=BlogPost.STATUS_PUBLISHED,
            )
        BlogPost.objects.create(
            title='Hidden Draft', slug='hidden-draft',
            content='<p>Body</p>', status=BlogPost.STATUS_DRAFT,
        )

    def fetch(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, f'{path} returned {response.status_code}')
        return response.content.decode()

    def parse(self, path):
        parser = _PageParser()
        parser.feed(self.fetch(path))
        return parser

    def body_links(self, path):
        """Map of internal target path -> list of anchor texts, body only (no header/footer/nav)."""
        links = {}
        for href, text, _attrs in self.parse(path).body_links:
            target = urlparse(urljoin('http://testserver' + path, href))
            if target.netloc not in SITE_HOSTS or target.path.startswith(('/static/', '/media/')):
                continue
            links.setdefault(target.path, []).append(_clean(text).lower())
        return links


# ── The "Emoji Keyboard for PC" page ──────────────────────────────────────────

class EmojiKeyboardForPcPageTests(PageTestCase):
    def test_route_and_view(self):
        self.assertEqual(reverse('emoji_keyboard_for_pc'), PC)
        self.assertIs(resolve(PC).func, views.emoji_keyboard_for_pc)
        self.assertIs(resolve('/emoji-keyboard/').func, views.emoji_keyboard)

    def test_missing_slash_redirects_and_wrong_paths_404(self):
        redirect = self.client.get('/emoji-keyboard-for-pc')
        self.assertIn(redirect.status_code, (301, 302))
        self.assertTrue(redirect['Location'].endswith(PC))
        self.assertEqual(self.client.get('/Emoji-Keyboard-For-PC/').status_code, 404)
        self.assertEqual(self.client.get(PC + 'extra/').status_code, 404)

    def test_seo_basics(self):
        page = self.parse(PC)
        self.assertEqual(_clean(page.title), 'Emoji Keyboard for PC - Windows Shortcuts and Help')
        self.assertEqual(
            page.meta['description'],
            'Open the Windows emoji panel, search for a character, and learn how to troubleshoot '
            'common emoji keyboard problems, including shortcuts for Windows PCs.',
        )
        self.assertEqual(urlparse(page.canonical).path, PC)
        self.assertEqual(urlparse(page.meta['og:url']).path, PC)
        self.assertNotIn('noindex', page.meta.get('robots') or '')
        self.assertEqual([_clean(h) for h in page.h1], ['Emoji Keyboard for PC: Shortcuts & How to Use'])

    def test_headings_match_the_article(self):
        page = self.parse(PC)
        h2 = [_clean(h) for h in page.h2 if 'Custom Emoji Sticker' not in h]
        self.assertEqual(h2, EXPECTED_H2)

    def test_tables_faqs_and_schema(self):
        html = self.fetch(PC)
        page = self.parse(PC)
        self.assertEqual(page.tables, 2)
        self.assertEqual(page.details, 8)
        self.assertEqual(len(views.EMOJI_KEYBOARD_PC_FAQS), 8)
        for faq in views.EMOJI_KEYBOARD_PC_FAQS:
            self.assertIn(faq['question'], html)
        schemas = [json.loads(block) for block in page.ld_json]
        faq_pages = [s for s in schemas if s.get('@type') == 'FAQPage']
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]['mainEntity']), 8)
        self.assertNotIn('{{', html)
        self.assertNotIn('{%', html)

    def test_page_is_static_content_without_database_queries(self):
        with self.assertNumQueries(0):
            self.client.get(PC)

    def test_faq_json_ld_helper_escapes_script_close(self):
        payload = views._faq_json_ld([{'question': '</script><b>', 'answer': 'a<b'}])
        self.assertNotIn('<', payload)
        self.assertEqual(json.loads(payload)['mainEntity'][0]['name'], '</script><b>')


# ── Sitemap ───────────────────────────────────────────────────────────────────

class SitemapTests(PageTestCase):
    def locations(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get('X-Robots-Tag'))
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]

    def test_new_page_listed_once(self):
        locs = self.locations()
        self.assertEqual(len([l for l in locs if urlparse(l).path == PC]), 1)
        self.assertEqual(len(locs), len(set(locs)))

    def test_counts_and_drafts(self):
        locs = self.locations()
        self.assertEqual(len(StaticViewSitemap().items()), 16)   # 12 pages + art editor + dot art generator + mood finder + guide
        # hub + ready made + 5 older + 6 category pages + one page per keyword
        self.assertEqual(len(ComboPageSitemap().items()), 13 + len(TAG_PAGES))
        self.assertEqual(len(locs), 16 + 13 + len(TAG_PAGES) + len(POST_SLUGS))
        self.assertFalse(any('hidden-draft' in l for l in locs))

    def test_every_sitemap_url_is_clean(self):
        for loc in self.locations():
            path = urlparse(loc).path
            page = self.parse(path)
            self.assertEqual(urlparse(page.canonical).path, path, f'{path} canonical is not itself')
            self.assertNotIn('noindex', page.meta.get('robots') or '', path)

    def test_robots_txt(self):
        text = self.client.get('/robots.txt').content.decode()
        self.assertIn('Allow: /', text)
        self.assertIn('Sitemap:', text)
        self.assertNotIn('Disallow', text)


# ── WhatsApp footer link ──────────────────────────────────────────────────────

class WhatsAppFooterTests(PageTestCase):
    def test_every_page_has_one_whatsapp_link_as_last_social_icon(self):
        for path in ALL_PAGES:
            html = self.fetch(path)
            page = self.parse(path)
            # the home page also carries the sticky button, so it has the link twice
            self.assertEqual(html.count(WHATSAPP_URL), 2 if path == '/' else 1, path)
            self.assertEqual(len(page.footer_social), 4, path)
            self.assertEqual(page.footer_social[-1], WHATSAPP_URL, path)

    def test_link_opens_safely_in_new_tab(self):
        html = self.fetch('/')
        tag = re.search(r'<a href="' + re.escape(WHATSAPP_URL) + r'"([^>]*)>', html).group(1)
        self.assertIn('target="_blank"', tag)
        self.assertIn('noopener', tag)
        self.assertIn('aria-label="Emoji Kitchen on WhatsApp"', tag)

    def test_footer_keeps_its_side_padding(self):
        css = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/css/style.css').read_text(encoding='utf-8')
        self.assertIn('padding:56px 24px 48px', css)
        self.assertIn('padding:40px 24px 32px', css)


# ── Internal linking ──────────────────────────────────────────────────────────

class InternalLinkTests(PageTestCase):
    # Homepage device guides include two later posts that are not in POST_SLUGS
    # (those four still have the only legacy /<slug>/ redirects).
    EXTRA_HOME_GUIDE_SLUGS = (
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-not-working',
        'emoji-kitchen-instagram',
        'emoji-kitchen-discord',
        'emoji-kitchen-on-pc',
        'emoji-kitchen-google-messages',
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for slug in cls.EXTRA_HOME_GUIDE_SLUGS:
            BlogPost.objects.create(
                title=slug.replace('-', ' ').title(),
                slug=slug,
                content='<p>Body</p>',
                status=BlogPost.STATUS_PUBLISHED,
            )

    def test_new_page_receives_body_links_from_five_pages(self):
        for source in ['/', '/emoji-keyboard/', READY_MADE, '/emoji-maker/', '/emoji-generator/']:
            self.assertIn(PC, self.body_links(source), f'{source} does not link to {PC}')

    def test_new_page_sends_body_links_to_the_blog_posts_and_the_keyboard_page(self):
        links = self.body_links(PC)
        for target in ['/emoji-keyboard/', '/blog/emoji-kitchen-whatsapp/', '/blog/emoji-kitchen-iphone/',
                       '/blog/emoji-kitchen-samsung/', '/blog/emoji-kitchen-gboard/']:
            self.assertIn(target, links, f'{PC} does not link to {target}')
        # the bottom sentence was deliberately left without links to these pages
        for target in ['/emoji-maker/', '/emoji-generator/', '/emoji-combos/']:
            self.assertNotIn(target, links, f'{PC} should not link to {target} in its body')

    def test_required_anchor_texts_for_incoming_links(self):
        self.assertEqual(self.body_links('/')[PC], ['windows emoji keyboard'])
        self.assertEqual(self.body_links('/emoji-keyboard/')[PC], ['windows emoji keyboard'])
        self.assertEqual(self.body_links('/emoji-generator/')[PC], ['emoji keyboard shortcut'])
        self.assertEqual(self.body_links('/emoji-maker/')[PC], ['emoji keyboard for pc'])
        self.assertEqual(self.body_links(READY_MADE)[PC], ['emoji keyboard for pc guide'])

    def test_required_anchor_texts_for_outgoing_links(self):
        links = self.body_links(PC)
        self.assertEqual(links['/emoji-keyboard/'], ['emoji keyboard'])
        self.assertEqual(links['/blog/emoji-kitchen-whatsapp/'], ['emoji kitchen whatsapp'])

    def test_each_page_links_to_the_new_page_only_once(self):
        for source in ['/', '/emoji-keyboard/', READY_MADE, '/emoji-maker/', '/emoji-generator/']:
            self.assertEqual(len(self.body_links(source)[PC]), 1, f'{source} links to {PC} more than once')

    def test_more_than_three_incoming_and_outgoing_internal_links(self):
        incoming = [p for p in ALL_PAGES if p != PC and PC in self.body_links(p)]
        outgoing = [t for t in self.body_links(PC) if t != PC]
        self.assertGreater(len(incoming), 3, incoming)
        self.assertGreater(len(outgoing), 3, outgoing)

    def test_closing_sentence_has_no_links(self):
        html = self.fetch(PC)
        sentence = ('Merge two emojis into one unique image using Emoji Kitchen. It is free and needs no sign-up. '
                    'You can also use the emoji maker, the emoji generator, or browse emoji combos to copy and paste.')
        self.assertIn(f'<p>{sentence}</p>', html)  # plain text, no <a> inside the paragraph
        # the button below it is unchanged
        self.assertIn('<a href="/#kitchen" class="btn btn--primary">Open Emoji Kitchen', html)

    def test_interlinking_words_use_the_link_colour_and_no_underline(self):
        """The site CSS strips link styling, so interlinks carry an explicit colour and no underline."""
        def styled(attrs):
            style = (attrs.get('style') or '').replace(' ', '')
            return 'color:var(--accent-dk)' in style and 'underline' not in style

        # 1. incoming links: the one link on each source page that points to the PC page
        for source in ['/', '/emoji-keyboard/', READY_MADE, '/emoji-maker/', '/emoji-generator/']:
            tags = [(h, t, a) for h, t, a in self.parse(source).body_links if urlparse(h).path == PC]
            self.assertEqual(len(tags), 1, source)
            self.assertTrue(styled(tags[0][2]), f'{source}: "{_clean(tags[0][1])}" is not coloured')
        # 2. outgoing links in the PC page article (the "Open Emoji Kitchen" button is not a text link)
        for href, text, attrs in self.parse(PC).body_links:
            if 'btn' in (attrs.get('class') or ''):
                continue
            self.assertTrue(styled(attrs), f'{PC}: "{_clean(text)}" -> {href} is not coloured')

    def test_added_links_are_plain(self):
        """Internal links to the new page carry no nofollow and no target=_blank."""
        for source in ['/', '/emoji-keyboard/', READY_MADE, '/emoji-maker/', '/emoji-generator/']:
            for href, _text, attrs in self.parse(source).body_links:
                if urlparse(href).path == PC:
                    self.assertNotIn('nofollow', attrs.get('rel') or '', source)
                    self.assertNotIn('target', attrs, source)

    def test_hub_and_combo_structure_rules(self):
        expected = {
            '/': set(HUBS[1:]) | {'/blog/'} | set(COMBOS),
            '/emoji-maker/': set(HUBS) - {'/emoji-maker/'},
            '/emoji-generator/': set(HUBS) - {'/emoji-generator/'},
            '/emoji-keyboard/': set(HUBS) - {'/emoji-keyboard/'},
            '/emoji-combos/': {'/', READY_MADE} | set(COMBOS) | set(MORE_COMBOS),
            READY_MADE: {'/'} | set(COMBOS),
            '/blog/': set(POSTS),
        }
        for combo in COMBOS:
            expected[combo] = {'/emoji-combos/', '/', '/emoji-maker/', '/blog/'}
        for post in POSTS:
            expected[post] = {'/', '/blog/', '/emoji-maker/'}
        for page, needed in expected.items():
            links = self.body_links(page)
            self.assertFalse(needed - set(links), f'{page} is missing links to {sorted(needed - set(links))}')

    def test_combo_pages_link_to_two_siblings(self):
        for combo in COMBOS:
            links = self.body_links(combo)
            siblings = [c for c in COMBOS if c != combo and c in links]
            self.assertGreaterEqual(len(siblings), 2, combo)

    def test_no_weak_anchors_and_no_legacy_redirect_links(self):
        for path in ALL_PAGES:
            for target, anchors in self.body_links(path).items():
                self.assertNotIn(target, LEGACY, f'{path} links to a redirecting URL {target}')
                for anchor in anchors:
                    self.assertNotIn(anchor, WEAK_ANCHORS, f'{path} -> {target}')

    def test_every_internal_link_resolves(self):
        for path in ALL_PAGES:
            for target in self.body_links(path):
                self.assertEqual(self.client.get(target).status_code, 200, f'{path} -> {target}')

    def test_each_page_has_one_h1_and_self_canonical(self):
        for path in ALL_PAGES:
            page = self.parse(path)
            self.assertEqual(len(page.h1), 1, path)
            self.assertEqual(urlparse(page.canonical).path, path, path)


# ── Navigation and sticky WhatsApp button ─────────────────────────────────────

class NavigationTests(PageTestCase):
    def header_html(self, path):
        html = self.fetch(path)
        return html[html.index('<header'):html.index('</header>')]

    def test_new_page_is_in_desktop_nav_and_mobile_drawer_on_every_page(self):
        for path in ALL_PAGES:
            header = self.header_html(path)
            self.assertEqual(header.count(f'href="{PC}"'), 2, f'{path}: expected nav + drawer link')
            self.assertIn('Emoji Keyboard for PC</a>', header, path)

    def test_pc_page_is_inside_the_emoji_keyboard_dropdown_not_a_top_level_item(self):
        for path in ALL_PAGES:
            header = self.header_html(path)
            dropdown = re.search(
                r'<li class="nav__item nav__item--dropdown">\s*<a href="/emoji-keyboard/">Emoji Keyboard</a>'
                r'\s*<ul class="nav__dropdown-menu">(.*?)</ul>', header, re.S)
            self.assertIsNotNone(dropdown, f'{path}: Emoji Keyboard is not a dropdown')
            self.assertEqual(dropdown.group(1).count(f'href="{PC}"'), 1, path)
            # the only other PC link is the indented item in the mobile menu
            self.assertEqual(header.count(f'href="{PC}"'), 2, path)
            self.assertIn(f'<a href="{PC}" class="nav__drawer-link nav__drawer-sublink"', header, path)

    def test_nav_link_sits_next_to_emoji_keyboard(self):
        header = self.header_html('/')
        self.assertLess(header.index('href="/emoji-keyboard/"'), header.index(f'href="{PC}"'))
        self.assertLess(header.index(f'href="{PC}"'), header.index('href="/emoji-combos/"'))


    def test_css_keeps_nav_labels_on_one_line_and_switches_to_menu_before_it_overflows(self):
        css = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/css/style.css').read_text(encoding='utf-8')
        link_rule = re.search(r'\.nav__links a\{(.*?)\}', css, re.S).group(1)
        self.assertIn('white-space:nowrap', link_rule)
        # the seven menu items (with Others) fit on one line from ~1140px; below that the hamburger takes over
        self.assertRegex(css, r'@media\(max-width:1140px\)\{\s*\.nav__links,\.nav__cta\{display:none\}')


class StickyWhatsAppButtonTests(PageTestCase):
    def test_button_is_on_home_page_with_correct_link(self):
        html = self.fetch('/')
        tag = re.search(r'<a href="' + re.escape(WHATSAPP_URL) + r'" class="wa-float"([^>]*)>', html)
        self.assertIsNotNone(tag, 'sticky WhatsApp button missing on home page')
        self.assertIn('target="_blank"', tag.group(1))
        self.assertIn('noopener', tag.group(1))
        self.assertIn('aria-label="Join our WhatsApp channel"', tag.group(1))
        self.assertEqual(html.count('class="wa-float"'), 1)

    def test_button_is_home_page_only(self):
        for path in [p for p in ALL_PAGES if p != '/']:
            self.assertNotIn('wa-float', self.fetch(path), path)

    def test_button_appears_in_the_page_body_after_the_footer(self):
        html = self.fetch('/')
        self.assertGreater(html.index('class="wa-float"'), html.index('</footer>'))

    def test_css_keeps_it_fixed_and_always_visible(self):
        css = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/css/style.css').read_text(encoding='utf-8')
        rule = re.search(r'\.wa-float\{(.*?)\}', css, re.S).group(1)
        self.assertIn('position:fixed', rule)
        self.assertIn('bottom:20px', rule)
        self.assertIn('right:20px', rule)
        self.assertIn('background:#25D366', rule)
        # stays above page content but below the toast (z-index 800)
        z = int(re.search(r'z-index:(\d+)', rule).group(1))
        self.assertTrue(200 < z < 800)
        self.assertIn('prefers-reduced-motion', css)


# ── Home page ad block ────────────────────────────────────────────────────────

class HomeAdTests(PageTestCase):
    def test_ad_unit_is_on_home_page_only(self):
        home = self.fetch('/')
        self.assertIn('pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3200425003686406', home)
        self.assertIn('data-ad-slot="1461359629"', home)
        self.assertIn('data-full-width-responsive="true"', home)
        for path in ['/emoji-maker/', PC, '/blog/']:
            self.assertNotIn('adsbygoogle', self.fetch(path), path)

    def test_ad_wrapper_has_a_width(self):
        """Regression: a zero-width wrapper makes AdSense fail with 'availableWidth=0'."""
        wrapper = re.search(r'<div class="hero__ad" style="([^"]+)"', self.fetch('/')).group(1)
        self.assertIn('width:100%', wrapper)

    def test_ad_sits_after_the_start_mixing_button(self):
        home = self.fetch('/')
        self.assertLess(home.index('Start Mixing'), home.index('class="hero__ad"'))
        self.assertLess(home.index('class="hero__ad"'), home.index('class="stats-bar"'))


# ── Site-wide unofficial / not-affiliated notice ──────────────────────────────

class SiteNoticeTests(PageTestCase):
    NOTICE_PHRASE = 'Emoji Kitchen Hub is not affiliated with, endorsed by, or run by Google'

    def test_notice_appears_on_every_public_page(self):
        for path in ALL_PAGES:
            html = self.fetch(path)
            self.assertIn(self.NOTICE_PHRASE, html, path)
            self.assertIn('class="site-notice"', html, path)
            # Notice sits after the header and before the main footer.
            self.assertLess(html.index('id="site-header"'), html.index('class="site-notice"'), path)
            self.assertLess(html.index('class="site-notice"'), html.index('class="site-footer"'), path)


# ── Existing behaviour that must not regress ──────────────────────────────────

class RegressionTests(PageTestCase):
    def test_all_public_pages_return_200(self):
        for path in ALL_PAGES + ['/robots.txt', '/ads.txt', '/sitemap.xml']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_free_emoji_generator_blog_url_redirects_to_generator(self):
        response = self.client.get('/blog/free-emoji-generator/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/emoji-generator/')

    def test_homepage_share_showcase_uses_live_gstatic_mashup(self):
        html = self.fetch('/')
        self.assertNotIn('kitchen/img/mashups/cherry-blossom-smiling-hearts-emoji-mashup.png', html)
        self.assertIn('u1f338_u1f970.png', html)

    def test_legacy_blog_urls_still_redirect(self):
        for slug in POST_SLUGS:
            response = self.client.get(f'/{slug}/')
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response['Location'], f'/blog/{slug}/')

    def test_unknown_url_is_404(self):
        self.assertEqual(self.client.get('/does-not-exist/').status_code, 404)

    def test_combo_api(self):
        data = self.client.get('/api/combo/', {'emoji1': '😀', 'emoji2': '😍'}).json()
        self.assertTrue(data['urls'])
        self.assertEqual(self.client.get('/api/combo/', {'emoji1': '😀'}).status_code, 400)
        self.assertEqual(self.client.get('/api/random-combo/').status_code, 200)

    def test_download_and_proxy_endpoints_are_removed(self):
        for path in ['/api/download/', '/api/proxy/']:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_mixer_script_fetches_gstatic_directly(self):
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js').read_text(encoding='utf-8')
        self.assertNotIn('/api/download/', js)
        self.assertNotIn('/api/proxy/', js)
        self.assertIn("fetch(comboUrl, { mode: 'cors' })", js)

    def test_legal_pages_show_both_contact_emails_once_each(self):
        emails = ['abdulmannanfiv@gmail.com', 'mannanmaan1425@gmail.com']
        for path in LEGAL:
            html = self.fetch(path)
            for line in [l for l in html.splitlines() if 'mailto:' in l]:
                for email in emails:
                    self.assertEqual(line.count(f'href="mailto:{email}"'), 1, f'{path}: {line[:80]}')

    def test_blog_visibility(self):
        self.assertEqual(self.client.get('/blog/hidden-draft/').status_code, 404)
        self.assertEqual(self.client.get('/blog/emoji-kitchen-iphone/').status_code, 200)


# ── Server settings via .env (so plain `python manage.py runserver` is safe) ───

class EnvFileLoaderTests(SimpleTestCase):
    def write(self, text):
        handle = tempfile.NamedTemporaryFile('w', suffix='.env', delete=False, encoding='utf-8')
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def load(self, text, existing=None):
        path = self.write(text)
        with mock.patch.dict(os.environ, {'DJANGO_ENV_FILE': path, **(existing or {})}):
            for key in ('A_KEY', 'B_KEY', 'C_KEY', 'D_KEY', 'E_KEY', 'DJANGO_DEBUG'):
                if key not in (existing or {}):
                    os.environ.pop(key, None)
            loaded = load_env()
            return loaded, dict(os.environ)

    def test_reads_plain_quoted_export_and_skips_comments_blank_and_bad_lines(self):
        loaded, env = self.load(
            '# comment\n\nA_KEY=plain\nB_KEY="double quoted"\nC_KEY=\'single\'\n'
            'export D_KEY=exported\nnot a pair\nE_KEY=has=equals\n'
        )
        self.assertTrue(loaded)
        self.assertEqual(env['A_KEY'], 'plain')
        self.assertEqual(env['B_KEY'], 'double quoted')
        self.assertEqual(env['C_KEY'], 'single')
        self.assertEqual(env['D_KEY'], 'exported')
        self.assertEqual(env['E_KEY'], 'has=equals')

    def test_real_environment_wins_over_the_file(self):
        _loaded, env = self.load('DJANGO_DEBUG=false\n', existing={'DJANGO_DEBUG': 'true'})
        self.assertEqual(env['DJANGO_DEBUG'], 'true')

    def test_missing_file_is_not_an_error(self):
        with mock.patch.dict(os.environ, {'DJANGO_ENV_FILE': '/nonexistent/path/.env'}):
            self.assertFalse(load_env())


class ManagePyModeTests(SimpleTestCase):
    """Runs the real manage.py in a clean environment, as the server and a laptop would."""

    CODE = ('from django.conf import settings; '
            'print(settings.DEBUG, settings.ALLOWED_HOSTS, settings.SECRET_KEY == "from-env-file")')

    def run_manage(self, env_text=None, extra_env=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith('DJANGO_')}
        if env_text is not None:
            handle = tempfile.NamedTemporaryFile('w', suffix='.env', delete=False, encoding='utf-8')
            handle.write(env_text)
            handle.close()
            self.addCleanup(os.unlink, handle.name)
            env['DJANGO_ENV_FILE'] = handle.name
        else:
            env['DJANGO_ENV_FILE'] = '/nonexistent/path/.env'   # never pick up a developer's real .env
        env.update(extra_env or {})
        result = subprocess.run(
            [sys.executable, 'manage.py', 'shell', '-c', self.CODE],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        return result.stdout.strip().splitlines()[-1]

    def test_with_env_file_manage_py_runs_in_production_mode(self):
        out = self.run_manage('DJANGO_DEBUG=false\nDJANGO_SECRET_KEY=from-env-file\n')
        self.assertEqual(out, "False ['emojikitchenhub.com', 'www.emojikitchenhub.com'] True")

    def test_without_env_file_manage_py_is_local_development_mode(self):
        out = self.run_manage(None)
        self.assertEqual(out, "True ['localhost', '127.0.0.1'] False")

    def test_a_real_environment_variable_still_beats_the_env_file(self):
        out = self.run_manage('DJANGO_DEBUG=false\nDJANGO_SECRET_KEY=from-env-file\n',
                              extra_env={'DJANGO_DEBUG': 'true'})
        self.assertTrue(out.startswith('True '))

    def test_production_mode_refuses_to_start_without_a_secret_key(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('DJANGO_')}
        handle = tempfile.NamedTemporaryFile('w', suffix='.env', delete=False, encoding='utf-8')
        handle.write('DJANGO_DEBUG=false\n')
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        env['DJANGO_ENV_FILE'] = handle.name
        result = subprocess.run([sys.executable, 'manage.py', 'check'], cwd=settings.BASE_DIR,
                                env=env, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY must be set', result.stderr)


# ── Mixer improvements: pair status, swap button, Explore Combinations ────────

MIXER_PAGES = ['/', '/emoji-maker/', '/emoji-generator/']


class SupportedEmojisApiTests(PageTestCase):
    def test_lists_supported_emojis_with_partner_counts(self):
        response = self.client.get('/api/supported-emojis/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('max-age', response['Cache-Control'])
        emojis = response.json()['emojis']
        self.assertGreater(len(emojis), 300)
        self.assertTrue(all(isinstance(n, int) and n >= 1 for n in emojis.values()))

    def test_counts_match_the_combos_for_endpoint(self):
        emojis = self.client.get('/api/supported-emojis/').json()['emojis']
        for emoji in ['😀', '❤️', '🐱', '🔥', '🌈']:
            combos = self.client.get('/api/combos-for/', {'emoji': emoji}).json()['combos']
            self.assertEqual(emojis[emoji], len(combos), emoji)

    def test_emojis_without_pairs_are_not_listed(self):
        emojis = self.client.get('/api/supported-emojis/').json()['emojis']
        picker_only = [e for e in ['🧸', '🐴', '🟤', '🌫️'] if not self.client.get(
            '/api/combos-for/', {'emoji': e}).json()['combos']]
        self.assertTrue(picker_only, 'expected at least one picker emoji with no pairs')
        for emoji in picker_only:
            self.assertNotIn(emoji, emojis)


class ComboImageUrlTests(PageTestCase):
    def test_matches_the_combo_api_in_either_order(self):
        for first, second in [('😀', '😍'), ('😍', '😀'), ('🐱', '🔥')]:
            api = self.client.get('/api/combo/', {'emoji1': first, 'emoji2': second}).json()['urls']
            self.assertEqual([views.combo_image_url(first, second)], api)

    def test_unsupported_pair_has_no_url(self):
        self.assertIsNone(views.combo_image_url('😀', '🟤'))
        self.assertIsNone(views.combo_image_url('', '😀'))


class ExploreCombinationsTests(PageTestCase):
    def test_every_curated_pair_exists_in_the_data(self):
        for slug, label, _icon, pairs in explore.EXPLORE_CATEGORIES:
            for first, second in pairs:
                self.assertIsNotNone(views.combo_image_url(first, second), f'{label}: {first}+{second} is not in the data')

    def test_five_categories_of_six_pairs(self):
        groups = explore.explore_groups()
        self.assertEqual([g['label'] for g in groups], ['Faces', 'Hearts', 'Animals', 'Food', 'Nature'])
        self.assertTrue(all(len(g['items']) == 6 for g in groups))
        urls = [i['url'] for g in groups for i in g['items']]
        self.assertEqual(len(urls), len(set(urls)), 'the same sticker appears twice')

    def test_section_is_on_the_three_mixer_pages_only(self):
        for path in MIXER_PAGES:
            html = self.fetch(path)
            self.assertEqual(html.count('class="explore"'), 1, path)
            self.assertEqual(html.count('class="picker__tab explore-tab'), 5, path)
            self.assertEqual(html.count('class="explore-item"'), 30, path)
        for path in [PC, '/emoji-keyboard/', '/emoji-combos/', READY_MADE, '/blog/']:
            self.assertNotIn('class="explore"', self.fetch(path), path)

    def test_items_carry_what_the_mixer_needs_and_are_accessible(self):
        html = self.fetch('/')
        item = re.search(r'<button type="button" class="explore-item" data-emoji1="([^"]+)" data-emoji2="([^"]+)"'
                         r'\s+data-url="([^"]+)" aria-label="([^"]+)">\s*<img src="([^"]+)" alt="([^"]+)"\s+title="([^"]+)" loading="lazy"'
                         r' width="96" height="96"', html)
        self.assertIsNotNone(item)
        first, second, data_url, label, src, alt, title = item.groups()
        self.assertEqual(data_url, src)
        self.assertEqual(views.combo_image_url(first, second), data_url)
        self.assertTrue(alt.strip() and title.strip())
        self.assertIn('into the mixer', label)

    def test_tabs_and_panels_are_wired_together(self):
        html = self.fetch('/emoji-maker/')
        for slug in ['faces', 'hearts', 'animals', 'food', 'nature']:
            self.assertIn(f'id="explore-tab-{slug}"', html)
            self.assertIn(f'id="explore-panel-{slug}"', html)
        # only the first panel is open
        self.assertEqual(len(re.findall(r'class="explore__grid" id="explore-panel-[a-z]+" role="tabpanel"\s+aria-labelledby="[^"]+" hidden>', html)), 4)


class MixerMarkupTests(PageTestCase):
    def test_swap_button_sits_between_the_two_slots_and_starts_disabled(self):
        for path in MIXER_PAGES:
            html = self.fetch(path)
            self.assertLess(html.index('id="chip1"'), html.index('id="btn-swap"'), path)
            self.assertLess(html.index('id="btn-swap"'), html.index('id="chip2"'), path)
            tag = re.search(r'<button type="button" class="cook__swap" id="btn-swap"([^>]*)>', html).group(1)
            self.assertIn('disabled', tag)
            self.assertIn('aria-label="Swap the first and second emoji"', tag)

    def test_status_line_and_alternatives_area_exist_for_screen_readers(self):
        for path in MIXER_PAGES:
            html = self.fetch(path)
            self.assertIn('id="mixer-status" role="status" aria-live="polite"', html, path)
            self.assertRegex(html, r'id="mixer-alts" hidden>', path)

    def test_slots_are_hidden_from_screen_readers_but_the_swap_button_is_not(self):
        html = self.fetch('/')
        chips = html[html.index('class="cook__chips"'):html.index('id="mixer-status"')]
        self.assertNotIn('class="cook__chips" aria-hidden', chips)
        self.assertEqual(chips.count('aria-hidden="true"'), 4)  # two slots, the plus sign, the swap icon

    def test_script_has_swap_status_and_explore_hooks(self):
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js').read_text(encoding='utf-8')
        for hook in ["getElementById('btn-swap')", "'/api/supported-emojis/'", ".explore-item", ".explore-tab",
                     'offerAlternativesForPair', 'announceFirstEmoji']:
            self.assertIn(hook, js)


# ── Claims that must not come back (unverified, outdated or contradictory) ────

class UnsupportedClaimsTests(PageTestCase):
    BANNED = [
        'genuinely new character',     # a mashup is an image, not a new Unicode character
        'keeps every creation',        # the mixer keeps only the six most recent, in the browser
        'v17.0', 'v18.0',              # outdated Unicode release claims
        'copied most often', 'most copied', 'most popular',   # no usage data backs these
        'data-adtest', 'Ads are shown here',                   # ad test mode and placeholder
    ]

    def test_no_banned_claim_on_any_page(self):
        for path in ALL_PAGES:
            html = self.fetch(path)
            for phrase in self.BANNED:
                self.assertNotIn(phrase, html, f'"{phrase}" is back on {path}')

    def test_home_describes_a_mashup_as_an_image(self):
        self.assertIn('A sticker-style image made from a supported emoji pair, rather than a new Unicode character.',
                      self.fetch('/'))

    def test_home_makes_no_promise_to_save_every_creation(self):
        html = self.fetch('/').lower()
        for phrase in ['save your favourites', 'save your favorites', 'keeps every creation']:
            self.assertNotIn(phrase, html)

    def test_unicode_support_paragraphs_use_the_new_wording(self):
        self.assertIn('Unicode releases and device support do not always arrive at the same time', self.fetch('/emoji-keyboard/'))
        self.assertIn('Unicode emoji specifications are updated periodically', self.fetch(READY_MADE))


# ── Home page: content from the "Emoji Updates" document (Page 1) ─────────────

class HomePageContentTests(PageTestCase):
    def home(self):
        return self.fetch('/')

    def test_title_and_meta_description(self):
        page = self.parse('/')
        self.assertEqual(_clean(page.title), 'Emoji Kitchen Mixer: Mix Two Emojis Free')
        self.assertEqual(page.meta['description'],
                         'Mix two emojis into one sticker with this free Emoji Kitchen mixer. '
                         'Works in your browser on iPhone, Android or PC. Copy or download, no sign-up.')
        self.assertEqual(page.meta['og:title'], 'Emoji Kitchen Mixer: Mix Two Emojis Free')
        self.assertEqual(len(page.h1), 1)
        self.assertEqual(_clean(page.h1[0]), 'Emoji Kitchen Mixer: Mix Two Emojis into Custom Stickers')

    def test_introduction_under_the_h1(self):
        html = self.home()
        for text in [
            'Need a reaction that says more than a single emoji? Emoji Kitchen Hub lets you combine two compatible emojis into a sticker-style image.',
            'The tool works in your browser, so you can experiment with different pairs without installing separate design software.',
        ]:
            self.assertIn(text, html)
        self.assertEqual(html.count('class="hero__subtitle"'), 2)
        for old in ['brings together emoji-related tools', 'The type of result matters:']:
            self.assertNotIn(old, html)

    def test_create_section_and_three_steps(self):
        html = self.home()
        self.assertIn('<h2>Create Your Emoji Combination</h2>', html)
        self.assertIn('Some pairs produce a sticker-style mashup, while others may not be supported.', html)
        self.assertIn('How to Make an Emoji Mashup</h3>', html)
        for title in ['Choose Your First Emoji', 'Add a Second Emoji', 'Preview and Share']:
            self.assertIn(f'<h3 class="create-step__title">{title}</h3>', html)
        self.assertEqual(html.count('class="create-step animate-up"'), 3)
        self.assertNotIn('Three steps to your perfect sticker', html)

    def test_why_use_section_has_six_accurate_points(self):
        html = self.home()
        self.assertIn('<h2>Why Use Emoji Kitchen Hub?</h2>', html)
        for title in ['Simple Browser-Based Tool', 'Quick Results', 'Copy and Download Options',
                      'Explore Different Combinations', 'No Separate Design Software', 'Save Favourite Combinations']:
            self.assertIn(f'<h3>{title}</h3>', html)
        self.assertEqual(html.count('class="feature-card animate-up"'), 6)
        for old in ['Explore Emoji Tools for Different Tasks', 'Copy Standard Emojis', 'Why Use Our Emoji Kitchen Tool?']:
            self.assertNotIn(old, html)
        self.assertIn('keeps up to six recent ones in your browser', html)      # My Combos really caps at 6 (main.js)

    def test_no_two_sections_share_a_heading(self):
        for path in ['/', '/emoji-maker/', '/emoji-generator/']:
            headings = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h2[^>]*>(.*?)</h2>', self.fetch(path), re.S)]
            self.assertEqual(len(headings), len(set(headings)), f'{path}: {headings}')

    def test_no_unsupported_claims(self):
        html = self.home()
        html = re.sub(r'<div class="stats-bar">.*?</div>\s*</div>\s*</div>', '', html, flags=re.S)   # the strip keeps its labels by choice
        for claim in ['60,553', 'Transparent', 'transparent', 'forever', 'Instant results', 'permanently', 'unlimited']:
            self.assertNotIn(claim, html, claim)

    def test_devices_section_covers_desktop_mobile_and_gboard(self):
        html = self.home()
        self.assertIn('<h2>How to Use Emoji Kitchen on Any Device</h2>', html)
        self.assertIn("The browser mixer on this website and Google's Emoji Kitchen feature are separate products", html)
        for h3 in ['Desktop Browsers', 'Mobile Browsers', "Gboard and Google's Emoji Kitchen"]:
            self.assertIn(f'<h3>{h3}</h3>', html)
        self.assertEqual(len(views.HOW_TO_WEB), 6)
        self.assertEqual(html.count('class="step-num"'), 6)
        self.assertNotIn('<h2>How to Use Emoji Kitchen</h2>', html)

    def test_understanding_section_is_gone_and_its_points_live_elsewhere(self):
        html = self.home()
        self.assertNotIn('Understanding Emoji Mashups', html)
        self.assertNotIn('id="limitations"', html)
        self.assertIn('Standard emojis can also look different across devices', html)
        self.assertIn('is not operated by Google', html)
        self.assertLess(html.index('id="how-to"'), html.index('id="faq"'))

    def test_random_combinations_card_points_at_the_real_surprise_button(self):
        html = self.home()
        self.assertIn('id="btn-surprise"', html)                       # the 🎲 button exists in the mixer
        self.assertEqual(self.client.get('/api/random-combo/').status_code, 200)
        card = html[html.index('<h3 class="popular-card__title">Random Combinations</h3>'):]
        card = card[:card.index('</article>')]
        self.assertIn('Surprise me', card)
        self.assertIn('href="#kitchen"', card)
        self.assertIn('Try the 🎲 button', card)

    def test_faqs_are_the_eleven_questions_from_the_brief(self):
        self.assertEqual([f['question'] for f in views.FAQS], [
            'What is Emoji Kitchen?', 'Is Emoji Kitchen Hub free?', 'Do I need to install an app?',
            'Can I combine any two emojis?', 'Are the results real Unicode emojis?', 'Can I use the tool on my phone?',
            'Can I use Emoji Kitchen on iPhone?', 'Why is Emoji Kitchen not showing on my keyboard?',
            'Can I download my emoji mashup?', 'Can I save favourite combinations?',
            'Is Emoji Kitchen Hub operated by Google?'])
        html = self.home()
        self.assertEqual(html.count('class="faq-item animate-up"'), 11)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(\{"@context": "https://schema.org", "@type": "FAQPage".*?)</script>', html).group(1))
        self.assertEqual(len(ld['mainEntity']), 11)
        self.assertEqual(sum(1 for e in ld['mainEntity'] if e.get('@type') == 'Question'), 11)
        self.assertNotIn('Google Search mixer', html)

    def test_closing_call_to_action_follows_the_faqs(self):
        html = self.home()
        self.assertIn('<h2>Ready to Create Your Emoji Mashup?</h2>', html)
        self.assertIn('Choose two emojis, explore the available result, and find a combination that suits your message.', html)
        self.assertIn('>Start Mixing Emojis</a>', html)
        self.assertGreater(html.index('Ready to Create Your Emoji Mashup?'), html.index('id="faq"'))

    def test_home_body_links_love_funny_pink_and_keyboard(self):
        links = self.body_links('/')
        for target in ['/emoji-combos/love/', '/emoji-combos/funny/', '/emoji-combos/pink/', '/emoji-keyboard/']:
            self.assertIn(target, links, f'home missing body link to {target}')

    def test_home_links_to_the_four_tools_from_its_body(self):
        links = self.body_links('/')
        for target in ['/emoji-maker/', '/emoji-generator/', '/emoji-keyboard/', '/emoji-combos/']:
            self.assertIn(target, links, f'Home does not link to {target}')

    def test_existing_sections_are_kept(self):
        html = self.home()
        for kept in ['What Is Emoji Kitchen?', 'Share Emoji Kitchen Stickers with Friends', 'Emoji Kitchen FAQs',
                     'id="kitchen"', 'class="explore"']:
            self.assertIn(kept, html)

    def test_home_links_the_live_device_and_chat_guides(self):
        html = self.home()
        section = html[html.index('<h2>How to Use Emoji Kitchen on Any Device</h2>'):html.index('Share Emoji Kitchen Stickers with Friends')]
        for href in [
            '/blog/emoji-kitchen-iphone/',
            '/blog/how-to-save-download-emoji-kitchen-stickers/',
            '/blog/emoji-kitchen-gboard/',
            '/blog/emoji-kitchen-samsung/',
            '/blog/emoji-kitchen-whatsapp/',
            '/blog/emoji-kitchen-not-working/',
            '/blog/emoji-kitchen-on-pc/',
            '/blog/emoji-kitchen-discord/',
            '/blog/emoji-kitchen-google-messages/',
            '/blog/emoji-kitchen-instagram/',
        ]:
            self.assertIn(f'href="{href}"', section)
        self.assertIn('how to use Emoji Kitchen on a PC', section)
        self.assertIn('Google Messages', section)
        self.assertIn('Instagram', section)
        self.assertIn('custom Discord emoji', section)

    def test_homepage_faq_json_ld_has_eleven_questions(self):
        html = self.home()
        ld = json.loads(re.search(
            r'<script type="application/ld\+json">(\{"@context": "https://schema.org", "@type": "FAQPage".*?)</script>',
            html,
        ).group(1))
        questions = [e for e in ld['mainEntity'] if e.get('@type') == 'Question']
        self.assertEqual(len(questions), 11)
        names = [e['name'] for e in questions]
        for question in [
            'What is Emoji Kitchen?',
            'Can I use Emoji Kitchen on iPhone?',
            'Why is Emoji Kitchen not showing on my keyboard?',
        ]:
            self.assertIn(question, names)


# ── Emoji Maker and Emoji Generator: content from the "Emoji Updates" document ─

EDITOR_NOTES = [   # instructions to the editor in the document; they must never reach visitors
    'should not be described', 'unless that functionality is implemented', 'unless those features are actually implemented',
    'Keep this claim', 'Do not advertise', 'is presented as', 'Do not assume',
]


class MakerAndGeneratorContentTests(PageTestCase):
    MAKER_H2 = ['What Is an Emoji Maker?', 'How to Make Your Own Emoji', 'Choose Emoji Pairs That Express an Idea',
                'Emoji Maker vs. Standard Emoji vs. AI Image Generator', 'Can You Make an Emoji From a Photo?',
                'Can You Create a New Keyboard Emoji?', 'Copying and Sharing Your Custom Emoji', 'Troubleshooting',
                'Emoji Maker FAQs', 'Create Your Next Custom Emoji']
    GENERATOR_H2 = ['What Is an Emoji Generator?', 'How to Use the Emoji Generator', 'Get a Random Emoji Mashup',
                    'How to Choose Better Emoji Combinations', 'Emoji Generator vs. Emoji Keyboard',
                    'Emoji Generator vs. AI Image Generator', 'Where Can You Use Generated Mashups?',
                    'Troubleshooting', 'Emoji Generator FAQs', 'Generate Your Next Emoji Mashup']

    def assertInOrder(self, html, headings):
        positions = [html.index(f'<h2>{h}</h2>') for h in headings]
        self.assertEqual(positions, sorted(positions))

    def test_titles_and_meta(self):
        maker, generator = self.parse('/emoji-maker/'), self.parse('/emoji-generator/')
        self.assertEqual(_clean(maker.title), 'Free Emoji Maker: Create Your Own Custom Emoji')
        self.assertEqual(maker.meta['description'],
                         'Make your own custom emoji sticker in this free emoji maker. '
                         'Choose two emojis, preview the result, then copy or download it. No sign-up needed.')
        self.assertEqual(_clean(generator.title), 'Free Emoji Generator: Instant Random Mashups')
        self.assertEqual(generator.meta['description'],
                         'Generate instant emoji mashups with this free emoji generator. '
                         'Press random for a surprise pair, or choose two emojis, then copy or download the sticker.')

        for page, path in ((maker, '/emoji-maker/'), (generator, '/emoji-generator/')):
            title = _clean(page.title)
            meta = page.meta['description']
            self.assertLessEqual(len(meta), 160)
            self.assertLessEqual(len(title), 60)
            self.assertEqual(len(title), 46 if path == '/emoji-maker/' else 44, path)
            self.assertEqual(len(meta), 144 if path == '/emoji-maker/' else 153, path)
            self.assertEqual(page.meta['og:title'], title)
            self.assertEqual(page.meta['og:description'], meta)
            self.assertEqual(len(page.h1), 1)
            blob = f'{title} {page.h1[0]} {meta}'.lower()
            self.assertNotIn('emoji kitchen', blob)
            self.assertNotIn('emoji mixer', blob)
            self.assertEqual(page.canonical, 'https://emojikitchenhub.com' + path)

    def test_h1s_and_introductions(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertIn('<h1>Free Emoji Maker: Create Your Own Custom Emoji</h1>', maker)
        self.assertIn('<h1>Free Emoji Generator: Instant Random Mashups</h1>', generator)
        self.assertIn('This free emoji maker builds a sticker-style image from two emojis you choose yourself.', maker)
        self.assertIn('Emoji Kitchen Hub is an unofficial, fan-made website and is not made by Google.', maker)
        self.assertIn('This free emoji generator creates sticker-style mashups in your browser and can also serve a random supported pair when you want a surprise.', generator)
        self.assertIn('This generator is part of Emoji Kitchen Hub, an unofficial fan-made site that is not made or endorsed by Google.', generator)
        self.assertNotIn('quick-answer', maker + generator)

    def test_section_headings_follow_the_document(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertInOrder(maker, self.MAKER_H2)
        self.assertInOrder(generator, self.GENERATOR_H2)
        for h3 in ['Start With One Clear Feeling', 'Experiment With Contrasting Ideas', 'Explore Themed Combinations']:
            self.assertIn(f'<h3>{h3}</h3>', generator)
        self.assertEqual(generator.count('<li><strong>'), 9)    # four steps + five idea groups
        self.assertEqual(maker.count('<li><strong>'), 4)    # the four numbered steps
        for h3 in ['Express a Feeling', 'Make a Playful Reaction', 'Create a Themed Sticker', 'Unsupported Combinations',
                   'Loading Problems', 'Copying Failures', 'Download Problems']:
            self.assertIn(f'<h3>{h3}</h3>', maker)

    def test_old_repetitive_sections_are_gone(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        for old in ['What This Emoji Maker Creates', 'AI Emoji Maker, Photo Emoji Maker', 'Emoji Maker Games',
                    'Emoji Maker Online vs Emoji Maker App', 'Free Emoji Maker Online: What You Can Do']:
            self.assertNotIn(old, maker)
        for old in ['Why Use an Emoji Generator Online?', 'Emoji Generator vs. Standard Emoji vs. AI Image Tool',
                    'How to Generate an Emoji Mix', 'How to Choose a Useful Pair', 'Emoji Mix Ideas to Try']:
            self.assertNotIn(old, generator)

    def test_faqs_are_six_each_and_match_faqpage_json_ld(self):
        maker_questions = [
            'What does an emoji maker do?', 'Can I make my own emoji for free?',
            'Can I customize facial features or upload a photo?', 'Does this emoji maker use AI?',
            "Why doesn't my emoji combination work?", 'How do I use my custom emoji in messages and apps?',
        ]
        generator_questions = [
            'Is this emoji generator free?', 'How do I generate a random emoji mashup?',
            'Can the generator combine any two emojis?', 'Is this an AI emoji generator?',
            'Can I use the emoji generator on my phone or computer?', 'Does it create new keyboard emojis?',
        ]
        self.assertEqual([f['question'] for f in views.EMOJI_MAKER_FAQS], maker_questions)
        self.assertEqual([f['question'] for f in views.EMOJI_GENERATOR_FAQS], generator_questions)
        answers = {f['question']: f['answer'] for f in views.EMOJI_MAKER_FAQS + views.EMOJI_GENERATOR_FAQS}
        self.assertEqual(answers['Does this emoji maker use AI?'],
                         'No. The tool combines existing emoji designs. It does not generate artwork from text prompts.')
        self.assertEqual(answers['Can I customize facial features or upload a photo?'],
                         'No. You cannot change eyes, mouths, or other details, and you cannot upload a photograph. You only choose which two emojis to combine.')
        for path, questions in (('/emoji-maker/', maker_questions), ('/emoji-generator/', generator_questions)):
            html = self.fetch(path)
            self.assertEqual(html.count('class="faq-item animate-up"'), 6, path)
            blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(blocks), 1, path)
            entities = [e for e in blocks[0]['mainEntity'] if e.get('@type') == 'Question']
            self.assertEqual(len(entities), 6, path)
            self.assertEqual([e['name'] for e in entities], questions)
            self.assertEqual([e['acceptedAnswer']['text'] for e in entities],
                             [answers[q] for q in questions])

    def test_the_two_pages_no_longer_repeat_each_other(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        for shared in ['Standard Emoji vs. Sticker-Style Mashup', 'Emoji Generator vs. Standard Emojis', 'How to Generate an Emoji Mix']:
            self.assertFalse(shared in maker and shared in generator, shared)
        maker_q = {f['question'] for f in views.EMOJI_MAKER_FAQS}
        self.assertFalse(maker_q & {f['question'] for f in views.EMOJI_GENERATOR_FAQS})
        self.assertNotEqual(self.parse('/emoji-maker/').meta['description'].split('.')[0],
                            self.parse('/emoji-generator/').meta['description'].split('.')[0])

    def test_every_idea_pair_on_the_generator_page_is_a_real_supported_pair(self):
        html = self.fetch('/emoji-generator/')
        ideas = html[html.index('<h3>Explore Themed Combinations</h3>'):html.index('<h2>Emoji Generator vs. Emoji Keyboard</h2>')]
        pairs = re.findall(r'(\S+) \+ (\S+?)(?=[ ,.<])', re.sub(r'<[^>]+>', ' ', ideas).replace('  ', ' '))
        self.assertEqual(len(pairs), 13)
        for first, second in pairs:
            self.assertTrue(views.combo_image_url(first, second), f'{first} + {second} is not supported')

    def test_generator_sections_and_wording(self):
        html = self.fetch('/emoji-generator/')
        self.assertIn('An AI image generator creates artwork from a written prompt. This tool does not.', html)
        self.assertIn('<h2>Generate Your Next Emoji Mashup</h2>', html)
        self.assertIn('<h2>Get a Random Emoji Mashup</h2>', html)
        self.assertIn('Generate My Emoji Mix', html)
        self.assertIn('href="/contact/"', html)
        self.assertEqual(html.count('class="step-num"'), 0)

    def test_maker_and_generator_bodies_do_not_repeat_sentences(self):
        def sentences(path):
            html = self.fetch(path)
            body = html[html.index('class="blog-detail__content"'):html.index('class="section faq-section"')]
            text = re.sub(r'</(?:h[1-6]|p|li|tr)>', '\n', body)           # keep headings apart from the next sentence
            text = re.sub(r'<[^>]+>', ' ', text)
            found = set()
            for line in text.split('\n'):
                for sentence in re.split(r'(?<=[.!?]) ', re.sub(r'[ \t]+', ' ', line).strip()):
                    if len(sentence.strip()) > 50:
                        found.add(sentence.strip())
            return found
        shared = sentences('/emoji-maker/') & sentences('/emoji-generator/')
        self.assertEqual(shared, set())

    def test_maker_comparison_table_and_ai_wording(self):
        html = self.fetch('/emoji-maker/')
        table = html[html.index('<table>'):html.index('</table>')]
        for row in ['Standard emoji keyboard', 'Emoji Kitchen Hub', 'Avatar editors', 'AI image generators']:
            self.assertIn(f'<td>{row}</td>', table)
        self.assertIn('This website does not offer avatar editing or AI image generation.', html)
        self.assertIn('No. The tool combines existing emoji designs. It does not generate artwork from text prompts.', html)

    def test_maker_example_pairs_are_supported_and_differ_from_the_generators(self):
        maker = self.fetch('/emoji-maker/')
        section = maker[maker.index('<h2>Choose Emoji Pairs That Express an Idea</h2>'):maker.index('<h2>Emoji Maker vs.')]
        pairs = re.findall(r'(\S+) \+ (\S+?)(?=[ ,.<])', re.sub(r'<[^>]+>', ' ', section).replace('  ', ' '))
        self.assertEqual(len(pairs), 6)
        generator = self.fetch('/emoji-generator/')
        ideas = generator[generator.index('<h3>Explore Themed Combinations</h3>'):generator.index('<h2>Emoji Generator vs. Emoji Keyboard</h2>')]
        for first, second in pairs:
            self.assertTrue(views.combo_image_url(first, second), f'{first} + {second} is not supported')
            self.assertNotIn(f'{first} + {second}', ideas, 'the Maker and Generator should not share example pairs')

    def test_no_editor_instructions_reach_visitors(self):
        for path in ['/emoji-maker/', '/emoji-generator/']:
            html = self.fetch(path)
            for note in EDITOR_NOTES:
                self.assertNotIn(note, html, f'editor note "{note}" is on {path}')

    def test_internal_links_from_the_documents_list(self):
        maker, generator = self.body_links('/emoji-maker/'), self.body_links('/emoji-generator/')
        for target in [
            '/emoji-keyboard/', '/emoji-combos/', '/emoji-generator/', '/',
            '/blog/how-to-save-download-emoji-kitchen-stickers/',
            '/blog/emoji-kitchen-instagram/',
            '/blog/emoji-kitchen-discord/',
            '/blog/emoji-kitchen-iphone/',
            '/blog/emoji-kitchen-on-pc/',
        ]:
            self.assertIn(target, maker, f'Maker does not link to {target}')
        for target in [
            '/emoji-maker/', '/emoji-keyboard/', '/emoji-combos/', '/',
            '/blog/emoji-kitchen-google-messages/',
            '/blog/emoji-kitchen-gboard/',
            '/blog/how-to-save-download-emoji-kitchen-stickers/',
            '/blog/emoji-kitchen-on-pc/',
        ]:
            self.assertIn(target, generator, f'Generator does not link to {target}')

    def test_links_to_the_pc_page_survive_the_rewrite(self):
        self.assertEqual(self.body_links('/emoji-maker/')[PC], ['emoji keyboard for pc'])
        self.assertEqual(self.body_links('/emoji-generator/')[PC], ['emoji keyboard shortcut'])

    def test_the_mixer_is_untouched_on_both_pages(self):
        for path in ['/emoji-maker/', '/emoji-generator/']:
            html = self.fetch(path)
            for part in ['id="kitchen"', 'id="btn-swap"', 'id="mixer-status"', 'class="explore"', 'id="btn-surprise"']:
                self.assertIn(part, html, f'{part} missing on {path}')

    def test_blog_closer_links_maker_generator_and_homepage_mixer(self):
        html = self.fetch('/blog/emoji-kitchen-iphone/')
        tools = html[html.index('class="blog-detail__tools"'):html.index('</p>', html.index('class="blog-detail__tools"'))]
        self.assertIn('href="/emoji-maker/"', tools)
        self.assertIn('href="/emoji-generator/"', tools)
        self.assertIn('href="/#kitchen"', tools)
        self.assertIn('emoji maker', tools)
        self.assertIn('emoji generator', tools)
        self.assertIn('Emoji Kitchen', tools)


# ── Emoji Keyboard and Emoji Keyboard for PC: content from the "Emoji Updates" document ──

class KeyboardPagesContentTests(PageTestCase):
    def test_keyboard_page_title_and_meta(self):
        page = self.parse('/emoji-keyboard/')
        self.assertEqual(_clean(page.title), 'Emoji Keyboard Online - Search, Copy and Paste')
        self.assertEqual(page.meta['description'], 'Find standard emojis by name or category, select characters and copy them '
                         'for messages, documents, captions and profiles.')
        self.assertEqual(page.meta['og:title'], 'Emoji Keyboard Online - Search, Copy and Paste')
        self.assertEqual(len(page.h1), 1)

    def test_keyboard_page_picker_introduction(self):
        html = self.fetch('/emoji-keyboard/')
        for text in [
            'Use the search box when you know what you want to find.',
            'Select one character for a quick reaction, or select several to create a text sequence.',
            'If copying does not work, check whether the browser supports clipboard access in the current context',
            'An online picker copies standard emoji characters or sequences. It does not create a sticker-style mashup.',
        ]:
            self.assertIn(text, html)
        # the old explanation and the category bullet list are gone
        self.assertNotIn('The fastest method is simple: search for an emoji', html)
        self.assertNotIn('<li>Smileys and emotion</li>', html)
        # the picker itself is untouched
        for part in ['ekCopyTray', 'ek-grid', 'ekResetTray']:
            self.assertIn(part, html)

    def test_keyboard_page_platform_appearance_explanation(self):
        html = self.fetch('/emoji-keyboard/')
        self.assertIn('<h3>Why an Emoji May Look Different After Pasting</h3>', html)
        self.assertIn('Preview an emoji in the destination application when appearance matters.', html)
        self.assertEqual(html.count('Why an Emoji May Look Different After Pasting'), 1)   # replaced, not duplicated
        self.assertNotIn('The Emoji Looks Different After Pasting', html)

    def test_keyboard_page_links(self):
        links = self.body_links('/emoji-keyboard/')
        for target in ['/emoji-maker/', '/emoji-generator/', '/emoji-combos/', PC]:
            self.assertIn(target, links, f'/emoji-keyboard/ does not link to {target}')

    def test_pc_page_closing_section(self):
        html = self.fetch(PC)
        self.assertIn('<h2>Choose the Right Emoji Method for Your PC</h2>', html)
        self.assertNotIn('Use the Right Emoji Method for Your PC', html)
        for text in [
            'Use the built-in Windows emoji panel when you want to insert a standard emoji directly into a text field.',
            'For sticker-style mashups rather than standard text characters, use the Emoji Kitchen mixer.',
            'Keyboard layouts, software versions and application behavior can affect the experience.',
        ]:
            self.assertIn(text, html)
        for old in ['The three key points are easy to remember', 'Try the Windows shortcut first']:
            self.assertNotIn(old, html)

    def test_pc_page_keeps_its_detailed_instructions_and_single_keyboard_link(self):
        html = self.fetch(PC)
        for kept in ['How to Open the Emoji Keyboard for PC', 'What Is the Windows Emoji Keyboard Shortcut?',
                     'Why Is My Emoji Keyboard Not Working?', 'ek-table']:
            self.assertIn(kept, html)
        self.assertEqual(self.body_links(PC)['/emoji-keyboard/'], ['emoji keyboard'])   # still one link per target

    def test_pc_page_still_has_no_links_in_the_closing_sentence(self):
        self.assertIn('<p>Merge two emojis into one unique image using Emoji Kitchen', self.fetch(PC))


# ── Emoji Combos hub and the five combo pages: content from the "Emoji Updates" document ──

COMBO_PAGE_TEXT = {
    # path: (title, meta description, first sentence of the new introduction)
    '/emoji-combos/': (views.EMOJI_COMBOS_HUB_TITLE, views.EMOJI_COMBOS_HUB_META,
                       'Pick a theme below, or open the'),
    READY_MADE: ('Ready Made Emoji Combo: 100+ Sets to Copy & Paste',
                       'Tap to copy 100+ emoji combos for bios, captions and chats: cute, aesthetic, love, funny and pink sets. Want an image? Mix emojis with Emoji Kitchen.',
                       'Emoji combos are groups of two or more emoji characters used together to express a mood, topic or visual style.'),
    '/emoji-combos/love/': ('Love Emoji Combos to Copy & Paste for Texts & Captions',
                            'Copy and paste love emoji combos with hearts, roses and soft faces for romantic texts, anniversaries, captions and bios. Tap Copy to use one.',
                            'Love emoji combos bring hearts, faces, flowers and other symbols together to add tone to a message.'),
    '/emoji-combos/cute/': ('Cute Emoji Combos to Copy & Paste: Bows, Bunnies, Hearts',
                            'Copy and paste cute emoji combos with bows, bunnies, flowers, hearts and soft faces for bios, texts and captions. Tap Copy, then paste anywhere.',
                            'Cute emoji combos often use friendly faces, small animals, hearts, flowers, bows and soft colors.'),
    '/emoji-combos/aesthetic/': ('Aesthetic Emoji Combos to Copy & Paste for Bios, Captions',
                                 'Copy and paste aesthetic emoji combos sorted by mood, color and style, from soft and coquette to dark academia, for bios, captions and stories.',
                                 'Aesthetic emoji combos use a consistent visual mood, such as soft pastels, night skies, flowers, nature, minimal symbols or warm neutral tones.'),
    '/emoji-combos/funny/': ('Funny Emoji Combos to Copy & Paste: Reactions & Memes',
                             'Copy and paste funny emoji combos for reactions, jokes, memes and group chats. Pick a playful set that fits the tone of your message and the moment.',
                             'Funny emoji combos bring faces, objects, animals and symbols together to make a reaction more playful.'),
    '/emoji-combos/pink/': ('Pink Emoji Combos to Copy & Paste: Hearts, Bows, Flowers',
                            'Copy and paste pink emoji combos made of hearts, bows, flowers and pastel symbols for bios, captions, profiles and messages. Tap Copy to use one.',
                            'Pink emoji combos bring together hearts, flowers, bows, ribbons and other symbols that suit a pink or pastel visual theme.'),
}
GUIDES = {   # page -> the guide the document adds before the FAQs
    '/emoji-combos/cute/': 'How to Choose a Cute Emoji Combo',
    '/emoji-combos/aesthetic/': 'How to Build a Consistent Emoji Style',
    '/emoji-combos/funny/': 'Choosing a Funny Emoji Reaction',
    '/emoji-combos/pink/': 'How to Choose a Pink Emoji Combo',
}
# collections that must never shrink: minimum emoji-list items / collection entries per page
COLLECTION_MINIMUMS = {
    READY_MADE: (155, 140), '/emoji-combos/love/': (352, 173), '/emoji-combos/cute/': (202, 185),
    '/emoji-combos/aesthetic/': (90, 194), '/emoji-combos/funny/': (159, 149), '/emoji-combos/pink/': (5, 140),
}


class ComboPagesContentTests(PageTestCase):
    def test_titles_and_meta_descriptions(self):
        for path, (title, meta, _intro) in COMBO_PAGE_TEXT.items():
            page = self.parse(path)
            self.assertEqual(_clean(page.title), title, path)
            self.assertEqual(page.meta['description'], meta, path)
            self.assertEqual(len(page.h1), 1, path)

    def test_introductions_replaced_and_quick_answer_boxes_removed(self):
        for path, (_t, _m, intro) in COMBO_PAGE_TEXT.items():
            html = self.fetch(path)
            self.assertIn(intro, html, path)
            self.assertNotIn('quick-answer', html, path)

    def test_hub_theme_block_replaces_the_repeated_category_paragraphs(self):
        html = self.fetch(READY_MADE)
        self.assertEqual(html.count('<h2>Browse Emoji Combos by Theme</h2>'), 1)
        for theme in ['Cute', 'Aesthetic', 'Love', 'Funny', 'Pink']:
            self.assertIn(f'<h3>{theme} Emoji Combos</h3>', html)
        links = self.body_links(READY_MADE)
        for target in COMBOS:
            self.assertIn(target, links)
        for old in ['Cute sets often use bows, hearts, flowers, animals, fruit', 'Aesthetic sets create a clear visual theme',
                    'Color-based sets are useful for matching profile themes', 'Love-themed sets can show affection',
                    'Mood sets help a short reply feel clearer']:
            self.assertNotIn(old, html)
        self.assertIn('This page is the starting point for browsing.', html)

    def test_love_page_replacements(self):
        html = self.fetch('/emoji-combos/love/')
        self.assertIn('<h2>Soft and Aesthetic Love Combos</h2>', html)
        self.assertIn('<h2>Choose a Love Combo That Fits the Message</h2>', html)
        for old in ['Aesthetic Emoji Sets for Love', 'Find Your Favorite Romantic Emoji Set']:
            self.assertNotIn(old, html)
        # the curated lists that followed the replaced paragraph are still there
        for kept in ['<h3>Soft Aesthetic Sets</h3>', '<h3>Aesthetic Sets for Bios</h3>', '<h3>Aesthetic Sets for Captions</h3>']:
            self.assertIn(kept, html)
        links = self.body_links('/emoji-combos/love/')
        for target in ['/emoji-combos/cute/', '/emoji-combos/aesthetic/', '/emoji-combos/pink/', '/']:
            self.assertIn(target, links)

    def test_selection_guides_sit_before_the_faqs_once(self):
        for path, heading in GUIDES.items():
            html = self.fetch(path)
            self.assertEqual(html.count(f'<h2>{heading}</h2>'), 1, path)
            self.assertLess(html.index(f'<h2>{heading}</h2>'), html.index('Frequently Asked Questions'), path)

    def test_documented_internal_links_in_the_introductions(self):
        expected = {
            '/emoji-combos/cute/': ['/emoji-combos/aesthetic/', '/emoji-combos/love/'],
            '/emoji-combos/aesthetic/': ['/emoji-combos/cute/', '/emoji-combos/love/'],
            '/emoji-combos/pink/': ['/emoji-combos/aesthetic/', '/emoji-combos/love/'],
        }
        for path, targets in expected.items():
            links = self.body_links(path)
            for target in targets:
                self.assertIn(target, links, f'{path} does not link to {target}')

    def test_emoji_collections_were_not_touched(self):
        for path, (min_li, min_entries) in COLLECTION_MINIMUMS.items():
            html = self.fetch(path)
            self.assertGreaterEqual(html.count('<li>'), min_li, path)
            entries = len(re.findall(r"\{cat:'", html)) + html.count('class="ec"')
            self.assertGreaterEqual(entries, min_entries, path)
            self.assertIn('<script>', html)

    def test_no_editor_notes_reach_visitors(self):
        for path in COMBO_PAGE_TEXT:
            html = self.fetch(path)
            for note in EDITOR_NOTES + ['should provide focused collections', 'rather than repeating every item']:
                self.assertNotIn(note, html, f'"{note}" is on {path}')


# ── About, Contact, Disclaimer, Terms, Privacy and Cookie pages ────────────────

class LegalAndSupportPagesTests(PageTestCase):
    def test_about_title_meta_and_introduction(self):
        page = self.parse('/about-us/')
        self.assertEqual(_clean(page.title), 'About Emoji Kitchen Hub - Our Tools and Guides')
        self.assertEqual(page.meta['description'], 'Learn about Emoji Kitchen Hub, its emoji tools and educational resources, '
                         'and how to report corrections or problems with the site or its guides.')
        html = self.fetch('/about-us/')
        self.assertIn('<h2>About Emoji Kitchen Hub</h2>', html)
        self.assertIn('Emoji Kitchen Hub is not an official Google service and is not operated by Google.', html)
        self.assertNotIn('Welcome to EmojiKitchenHub', html)
        self.assertIn('<h2>Independent Website Disclosure</h2>', html)      # the accurate independence statements stay

    def test_about_maintenance_section_sits_before_the_contact_section(self):
        html = self.fetch('/about-us/')
        self.assertEqual(html.count('<h2>Maintaining Our Guides and Tools</h2>'), 1)
        self.assertLess(html.index('Maintaining Our Guides and Tools'), html.index('<h2>Contact Us</h2>'))
        self.assertIn('/contact/', self.body_links('/about-us/'))
        self.assertIn('/privacy/', self.body_links('/about-us/'))
        self.assertIn('you can contact us at <a href="mailto:', html)

    def test_contact_title_meta_and_introduction(self):
        page = self.parse('/contact/')
        self.assertEqual(_clean(page.title), 'Contact Emoji Kitchen Hub')
        self.assertEqual(page.meta['description'], 'Contact Emoji Kitchen Hub to report a tool problem, suggest a correction, '
                         'or ask a question about the website, the guides, or any of the emoji tools.')
        html = self.fetch('/contact/')
        self.assertIn('<h2>Contact Emoji Kitchen Hub</h2>', html)
        self.assertIn('Do not send passwords or other sensitive information in a bug report.', html)
        self.assertIn('<h2>Suggest a Correction</h2>', html)
        self.assertIn('A screenshot can help explain the issue', html)
        self.assertEqual(html.count('<h2>Technical Issues</h2>'), 1)         # existing guidance kept, not duplicated
        self.assertNotIn('<h2>Report a Tool Problem</h2>', html)

    def test_contact_makes_no_response_time_promise(self):
        html = self.fetch('/contact/').lower()
        for promise in ['within 24', 'within 48', 'within 72', 'within one', 'within two', 'business day', 'reply within', 'respond within']:
            self.assertNotIn(promise, html)

    def test_disclaimer_and_terms_openings(self):
        disclaimer, terms = self.fetch('/disclaimer/'), self.fetch('/terms/')
        self.assertIn('Emoji Kitchen Hub provides emoji-related tools, collections and educational information.', disclaimer)
        self.assertIn('By using this website, you acknowledge that information, features, tools, and external resources may change over time.', disclaimer)
        self.assertIn('We do not guarantee that every tool result will be complete, accurate, suitable for every purpose, or continuously available.', disclaimer)
        self.assertIn('Visitors are responsible for choosing how to use the tools', terms)
        for kept in ['<h2>1. Introduction</h2>', '<h2>2. Acceptance of Terms</h2>', '<h2>3. Use of the Website</h2>',
                     'If you do not agree with these Terms, please do not use the website.']:
            self.assertIn(kept, terms)

    def test_policies_do_not_promise_a_last_updated_date_they_do_not_show(self):
        for path in ['/privacy/', '/cookie-policy/']:
            self.assertNotIn('Last Updated', self.fetch(path), path)
            self.assertNotIn('Last updated', self.fetch(path), path)

    def test_cookie_policy_states_what_the_code_verifiably_does(self):
        html = self.fetch('/cookie-policy/')
        self.assertIn('<h2>What This Website Uses Today</h2>', html)
        self.assertIn("up to six) in your browser's local storage", html)
        self.assertIn('does not set its own cookies on its public pages', html)
        self.assertIn('uses Google Analytics 4 to understand how visitors use the site', html)
        self.assertNotIn('does not use a separate analytics service', html)
        self.assertIn('_ga', html)
        self.assertIn('_ga_', html)
        self.assertIn('https://tools.google.com/dlpage/gaoptout', html)
        self.assertIn('https://policies.google.com/technologies/partner-sites', html)
        self.assertIn('https://adssettings.google.com', html)
        privacy = self.fetch('/privacy/')
        self.assertIn('EmojiKitchenHub uses Google AdSense to show advertising on some pages.', privacy)
        self.assertIn('EmojiKitchenHub uses Google Analytics 4 to understand how visitors use the site.', privacy)

    def test_the_facts_stated_in_the_policies_are_still_true(self):
        """If one of these fails, update the Cookie Policy and Privacy Policy as well."""
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js').read_text(encoding='utf-8')
        self.assertIn('persistCombos(combos.slice(0, 6))', js)                  # "up to six"
        self.assertIn("localStorage.setItem(COMBOS_KEY", js)                     # local storage, on the device
        self.assertIn("sessionStorage.setItem(RECENT_KEY", js)                   # session storage
        self.assertNotRegex(js, r'method:\s*[\'"]POST')                           # the saved list is never uploaded
        for path in MIXER_PAGES + [PC, '/emoji-combos/', READY_MADE, '/blog/', '/about-us/', '/contact/', '/privacy/', '/cookie-policy/']:
            self.assertFalse(self.client.get(path).cookies, f'{path} sets a cookie')
        templates = Path(settings.BASE_DIR) / 'kitchen/templates'
        scripts = '\n'.join(p.read_text(encoding='utf-8') for p in templates.rglob('*.html'))
        for tracker in ['clarity.ms', 'hotjar', 'plausible', 'matomo']:
            self.assertNotIn(tracker, scripts, f'a tracking script ({tracker}) was added: update the policies')
        self.assertIn('www.googletagmanager.com/gtag/js', scripts)                # GA4, as the policies say
        self.assertIn("gtag('config'", scripts)
        self.assertIn('fonts.googleapis.com', scripts)                           # Google Fonts, as the Cookie Policy says
        self.assertIn('pagead2.googlesyndication.com', self.fetch('/'))          # AdSense, as the policies say

    def test_all_contact_emails_still_appear_on_the_legal_pages(self):
        for path in LEGAL:
            html = self.fetch(path)
            self.assertIn('mailto:abdulmannanfiv@gmail.com', html, path)
            self.assertIn('mailto:mannanmaan1425@gmail.com', html, path)


# ── "Remaining Content Updates" document: Home, Emoji Maker, Generator, Blog index ──

class RemainingUpdatesTests(PageTestCase):
    def test_home_has_no_speed_badge_or_instant_claim(self):
        html = self.fetch('/')
        self.assertNotIn('Free · No sign-up · Results in seconds', html)       # the badge line was removed on request
        self.assertNotIn('hero__badge', html)
        self.assertNotIn('Instant results', html)

    def test_home_strip_shows_labels_only_without_the_four_big_words(self):
        html = self.fetch('/')
        self.assertNotIn('stat__value', html)
        for word in ['60,553', '>Free<', '>Zero<', '>PNG<']:
            self.assertNotIn(word, html)
        for label in ['Emoji combos', 'Always &amp; forever', 'No sign-up', 'Transparent files']:
            self.assertIn(f'<span class="stat__label">{label}</span>', html)
        self.assertNotIn('Sign-up needed', html)

    def test_home_what_is_section_uses_the_new_explanation(self):
        html = self.fetch('/')
        self.assertIn("Emoji Kitchen is Google's emoji-mixing feature. In Gboard on Android, it turns two emojis into one sticker-style mashup that you can send in chats.", html)
        self.assertIn('Emoji Kitchen Hub is an unofficial, independent website (not made by Google) that lets you mix supported pairs in any browser, including on iPhone and PC.', html)
        self.assertIn('sticker-style images, not newly registered Unicode emoji characters.', html)
        self.assertIn('<h2>What Is Emoji Kitchen?</h2>', html)
        for old in ['Google first introduced the feature through Gboard on Android.', 'through Google Search',
                    'Emoji Kitchen Hub is an unofficial fan-made tool']:
            self.assertNotIn(old, html)
        links = self.body_links('/')
        for target in ['/emoji-keyboard/', '/emoji-combos/', '/blog/', PC]:
            self.assertIn(target, links)

    def test_maker_closing_section(self):
        html = self.fetch('/emoji-maker/')
        self.assertIn('<h2>Create Your Next Custom Emoji</h2>', html)
        self.assertIn('Choose two emojis, preview the result, and copy or download a sticker that matches your message.', html)
        self.assertIn('>Make My Emoji Mashup</a>', html)
        for old in ['Make Your Next Emoji Mashup', 'Make Your Next Custom Emoji', 'save the combinations you want to use again']:
            self.assertNotIn(old, html)

    def test_no_page_promises_that_results_can_be_saved_for_later(self):
        for path in ['/emoji-maker/', '/emoji-generator/', '/']:
            html = self.fetch(path)
            for promise in ['save the results that fit your style', 'save the combinations you want to use again',
                            'save your favourites', 'keeps every creation']:
                self.assertNotIn(promise, html, f'"{promise}" is on {path}')
        self.assertIn('Choose two emojis or press random for an instant pair, then copy or download the result.',
                      self.fetch('/emoji-generator/'))

    def test_my_combos_wording_stays_accurate(self):
        html = self.fetch('/emoji-maker/')
        self.assertIn('Saved favourites and recent mixes', html)
        self.assertIn('id="btn-share"', html)
        for overclaim in ['permanent', 'forever', 'every previous', 'synced', 'on all your devices']:
            self.assertNotIn(overclaim, html.split('id="my-combos"')[1].split('</div>')[0], overclaim)

    def test_blog_index_shows_only_the_heading_and_the_article_cards(self):
        html = self.fetch('/blog/')
        for moved in ('These guides explain practical ways to mix sticker-style mashups', 'unofficial, fan-made website',
                      'What you will find here', 'How to choose a guide', 'About this independent site', 'blog-intro'):
            self.assertNotIn(moved, html, moved)
        self.assertNotIn('Explore practical guides to emoji tools, keyboards, sticker-style mashups and common sharing problems.', html)
        self.assertNotIn('Tips, tricks, and fun discoveries', html)
        self.assertNotIn('From the Blog', html)
        self.assertEqual(len(self.parse('/blog/').h1), 1)
        self.assertIn('<h1>Emoji Kitchen Guides</h1>', html)
        for post in POSTS:
            self.assertIn(f'href="{post}"', html)                           # the article cards stay


class EmojiKitchenGuidePageTests(PageTestCase):
    GUIDE = '/emoji-kitchen-guide/'

    def test_the_page_holds_the_text_that_used_to_sit_above_the_blog_cards(self):
        html = self.fetch(self.GUIDE)
        for text in ('These guides explain practical ways to mix sticker-style mashups', 'unofficial, fan-made website',
                     'What you will find here', 'How to choose a guide', 'Tools and collections alongside the guides',
                     'About this independent site'):
            self.assertIn(text, html, text)
        page = self.parse(self.GUIDE)
        self.assertEqual(len(page.h1), 1)
        self.assertIn('<h1>Emoji Kitchen Guide</h1>', html)
        self.assertEqual(page.canonical, COMBO_SITE + self.GUIDE)
        self.assertEqual(page.meta['og:url'], COMBO_SITE + self.GUIDE)

    def test_it_links_to_the_blog_and_the_pages_the_old_text_linked_to(self):
        html = self.fetch(self.GUIDE)
        for href in ('/blog/', '/emoji-keyboard/', '/', '/emoji-combos/', '/emoji-keyboard-for-pc/', '/about-us/', '/disclaimer/', '/contact/'):
            self.assertIn(f'href="{href}"', html, href)
        self.assertNotIn('featured article below', html)

    def test_title_and_description_are_unique_and_a_sensible_length(self):
        page = self.parse(self.GUIDE)
        self.assertEqual(_clean(page.title), 'Emoji Kitchen Guide: How to Use It on Any Device')
        self.assertLessEqual(len(_clean(page.title)), 60)
        self.assertLessEqual(len(page.meta['description']), 170)
        blog = self.parse('/blog/')
        self.assertNotEqual(_clean(page.title), _clean(blog.title))
        self.assertNotEqual(page.meta['description'], blog.meta['description'])

    def test_the_guide_is_in_the_sitemap(self):
        self.assertIn('/emoji-kitchen-guide/', self.client.get('/sitemap.xml').content.decode())

    def test_ids_stay_unique(self):
        ids = re.findall(r'\sid="([^"]+)"', self.fetch(self.GUIDE))
        self.assertEqual(len(ids), len(set(ids)))


# ── Blog posts: the update command ("Remaining Content Updates" document) ──────

BLOG_SAMPLES = Path(__file__).resolve().parent / 'tests_data' / 'blog'
OLD_TITLES = {   # the titles the live posts had before this update
    'emoji-kitchen-gboard': 'How to Use Emoji Kitchen Gboard on Android, iPhone & Samsung',
    'emoji-kitchen-samsung': 'How to Use Emoji Kitchen Samsung on Galaxy Phones',
    'emoji-kitchen-iphone': 'How to Use Emoji Kitchen on iPhone with Gboard & WhatsApp',
    'emoji-kitchen-whatsapp': 'How to Use Emoji Kitchen WhatsApp on iPhone & Android',
}


# how many of each post's original blocks the document tells us to replace (intro + named sections + one contents entry)
EXPECTED_CHANGED_BLOCKS = {'emoji-kitchen-gboard': 10, 'emoji-kitchen-samsung': 9,
                           'emoji-kitchen-iphone': 9, 'emoji-kitchen-whatsapp': 15}


class BlogUpdateTestCase(TestCase):
    """Four posts whose bodies are real copies of the live ones (pasted-document HTML)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        for slug, title in OLD_TITLES.items():
            BlogPost.objects.create(
                title=title, slug=slug, excerpt='old excerpt', seo_title='old seo title', seo_description='old description',
                content=(BLOG_SAMPLES / f'{slug}.html').read_text(encoding='utf-8'), status=BlogPost.STATUS_PUBLISHED)

    def run_command(self, *args):
        out = io.StringIO()
        call_command('update_blog_posts', *args, '--backup-dir', self.tmp, stdout=out)
        return out.getvalue()

    def post(self, slug):
        return BlogPost.objects.get(slug=slug)

    def fetch(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.content.decode()

    def parse(self, path):
        parser = _PageParser()
        parser.feed(self.fetch(path))
        return parser

    def headings(self, slug, level='h2'):
        return [b.text for b in blog_updates.split_blocks(self.post(slug).content) if b.tag == level]


class BlogUpdateHelpersTests(BlogUpdateTestCase):
    def test_splitting_and_rejoining_keeps_all_the_text(self):
        for slug in OLD_TITLES:
            source = self.post(slug).content
            blocks = blog_updates.split_blocks(source)
            self.assertGreater(len(blocks), 50, slug)
            self.assertEqual(blog_updates.plain(blog_updates.join_blocks(blocks)), blog_updates.plain(source), slug)

    def test_text_outside_a_block_is_refused_not_dropped(self):
        with self.assertRaises(blog_updates.BlockError):
            blog_updates.split_blocks('<p>fine</p> stray words <p>fine</p>')


class BlogUpdateCommandTests(BlogUpdateTestCase):
    def test_dry_run_changes_nothing(self):
        before = {s: (p.title, p.content) for s, p in ((s, self.post(s)) for s in OLD_TITLES)}
        output = self.run_command()
        self.assertIn('DRY RUN: nothing was changed', output)
        self.assertEqual(before, {s: (self.post(s).title, self.post(s).content) for s in OLD_TITLES})
        self.assertEqual(list(Path(self.tmp).glob('*.json')), [])            # not even a backup
        for slug in OLD_TITLES:
            self.assertIn(f'/blog/{slug}/', output)

    def test_apply_updates_titles_excerpts_and_seo_fields_but_never_the_web_address(self):
        self.run_command('--apply')
        for slug, update in blog_content.POST_UPDATES.items():
            post = self.post(slug)
            for field, value in update['fields'].items():
                self.assertEqual(getattr(post, field), value, f'{slug}.{field}')
            self.assertEqual(post.get_absolute_url(), f'/blog/{slug}/')
        self.assertEqual(BlogPost.objects.count(), 4)

    def test_apply_writes_a_backup_with_the_old_text(self):
        old = {s: self.post(s).content for s in OLD_TITLES}
        self.run_command('--apply')
        files = list(Path(self.tmp).glob('blog_posts_*.json'))
        self.assertEqual(len(files), 1)
        backup = json.loads(files[0].read_text(encoding='utf-8'))
        for slug in OLD_TITLES:
            self.assertEqual(backup[slug]['content'], old[slug])
            self.assertEqual(backup[slug]['title'], OLD_TITLES[slug])

    def test_restore_puts_everything_back(self):
        old = {s: (self.post(s).title, self.post(s).excerpt, self.post(s).seo_title, self.post(s).content) for s in OLD_TITLES}
        self.run_command('--apply')
        self.assertNotEqual(self.post('emoji-kitchen-gboard').title, OLD_TITLES['emoji-kitchen-gboard'])
        backup = next(Path(self.tmp).glob('blog_posts_*.json'))
        call_command('update_blog_posts', '--restore', str(backup), stdout=io.StringIO())
        for slug in OLD_TITLES:
            post = self.post(slug)
            self.assertEqual((post.title, post.excerpt, post.seo_title, post.content), old[slug], slug)

    def test_running_it_twice_changes_nothing_the_second_time(self):
        self.run_command('--apply')
        after_first = {s: self.post(s).content for s in OLD_TITLES}
        output = self.run_command()
        self.assertIn('everything is already up to date', output)
        self.assertNotIn('[will change]', output)
        self.run_command('--apply')
        self.assertEqual(after_first, {s: self.post(s).content for s in OLD_TITLES})

    def test_one_unreadable_post_means_nothing_is_changed(self):
        broken = self.post('emoji-kitchen-whatsapp')
        broken.content = broken.content.replace('How to Use Emoji Kitchen for WhatsApp in a Browser', 'Something else entirely')
        broken.save()
        before = {s: self.post(s).content for s in OLD_TITLES}
        with self.assertRaises(CommandError) as ctx:
            self.run_command('--apply')
        self.assertIn('Nothing was changed', str(ctx.exception))
        self.assertEqual(before, {s: self.post(s).content for s in OLD_TITLES})
        self.assertEqual(self.post('emoji-kitchen-gboard').title, OLD_TITLES['emoji-kitchen-gboard'])
        self.assertEqual(list(Path(self.tmp).glob('*.json')), [])

    def test_a_missing_post_means_nothing_is_changed(self):
        self.post('emoji-kitchen-samsung').delete()
        with self.assertRaises(CommandError):
            self.run_command('--apply')
        self.assertEqual(self.post('emoji-kitchen-gboard').title, OLD_TITLES['emoji-kitchen-gboard'])

    def test_a_single_post_can_be_selected(self):
        self.run_command('--apply', '--post', 'emoji-kitchen-iphone')
        self.assertEqual(self.post('emoji-kitchen-iphone').title, 'How to Use Emoji Kitchen on iPhone')
        self.assertEqual(self.post('emoji-kitchen-gboard').title, OLD_TITLES['emoji-kitchen-gboard'])

    def test_reading_time_is_recalculated(self):
        BlogPost.objects.filter(slug='emoji-kitchen-gboard').update(reading_time=99)
        self.run_command('--apply')
        self.assertLess(self.post('emoji-kitchen-gboard').reading_time, 99)


class BlogUpdateContentTests(BlogUpdateTestCase):
    def setUp(self):
        super().setUp()
        self.old = {s: blog_updates.split_blocks(self.post(s).content) for s in OLD_TITLES}
        self.run_command('--apply')

    def test_only_the_named_sections_changed_everything_else_is_byte_for_byte_identical(self):
        for slug, old_blocks in self.old.items():
            old_html = {b.html for b in old_blocks}
            new_blocks = blog_updates.split_blocks(self.post(slug).content)
            new_html = {n.html for n in new_blocks}
            changed = sum(1 for b in old_blocks if b.html not in new_html)
            self.assertEqual(changed, EXPECTED_CHANGED_BLOCKS[slug], f'{slug}: {changed} old blocks changed')
            untouched = len(old_blocks) - changed
            self.assertEqual(sum(1 for b in new_blocks if b.html in old_html), untouched, slug)   # nothing else was rewritten
            self.assertGreaterEqual(len(blog_updates.plain(self.post(slug).content).split()), 1300, slug)   # still full articles

    def test_new_and_old_headings(self):
        expected_new = {
            'emoji-kitchen-gboard': ['Using Emoji Kitchen on Other Devices', 'Try Emoji Kitchen on Your Android Device'],
            'emoji-kitchen-samsung': ['Choosing the Right Emoji Workflow on Samsung'],
            'emoji-kitchen-iphone': ['Using Emoji Kitchen on iPhone'],
            'emoji-kitchen-whatsapp': ['What Is Emoji Kitchen in WhatsApp?', 'How to Share a Browser-Created Mashup in WhatsApp',
                                       'Choose a Sharing Method That Works'],
        }
        expected_gone = {
            'emoji-kitchen-gboard': ['Gboard Emoji Kitchen on iPhone and Other Devices', 'Make Your Next Gboard Emoji Mashup'],
            'emoji-kitchen-samsung': ['Conclusion'],
            'emoji-kitchen-iphone': ['Make Your Next Emoji Mix on iPhone'],
            'emoji-kitchen-whatsapp': ['What Is Emoji Kitchen on WhatsApp?', 'How to Use Emoji Kitchen for WhatsApp in a Browser',
                                       'Create Your Next WhatsApp Sticker'],
        }
        for slug in OLD_TITLES:
            heads = self.headings(slug)
            for new in expected_new[slug]:
                self.assertEqual(heads.count(new), 1, f'{slug}: {new}')
            for gone in expected_gone[slug]:
                self.assertNotIn(gone, heads, f'{slug}: {gone}')

    def test_every_post_has_one_quick_answer_with_the_documents_text(self):
        quick = {
            'emoji-kitchen-gboard': 'Open a compatible application on an Android device and make sure Gboard is the active keyboard.',
            'emoji-kitchen-samsung': "If you want to use Google's Emoji Kitchen on a supported Samsung Galaxy phone",
            'emoji-kitchen-iphone': 'Open the browser-based mixer, select two supported emojis and check whether a result appears.',
            'emoji-kitchen-whatsapp': 'On a supported Android setup, Gboard may provide Emoji Kitchen suggestions',
        }
        for slug, text in quick.items():
            blocks = blog_updates.split_blocks(self.post(slug).content)
            answers = [b for b in blocks if blog_updates.norm(b.text).startswith('quick answer')]
            self.assertEqual(len(answers), 1, slug)
            self.assertIn(text, answers[0].text, slug)

    def test_iphone_keyword_list_is_gone_and_its_replacement_is_there(self):
        text = blog_updates.plain(self.post('emoji-kitchen-iphone').content)
        self.assertNotIn('kitchen emoji iPhone', text)
        self.assertNotIn('emoji iPhone kitchen', text)
        self.assertIn('The main question is how to create and use an image-based mashup on an Apple device.', text)

    def test_iphone_table_of_contents_matches_its_headings(self):
        blocks = blog_updates.split_blocks(self.post('emoji-kitchen-iphone').content)
        toc = next(b for i, b in enumerate(blocks) if blocks[i - 1].text == 'Table of Contents')
        self.assertIn('Using Emoji Kitchen on iPhone', toc.text)
        self.assertNotIn('Make Your Next Emoji Mix on iPhone', toc.text)

    def test_the_whatsapp_independence_note_is_kept(self):
        text = blog_updates.plain(self.post('emoji-kitchen-whatsapp').content)
        self.assertIn('Editorial note: Emoji Kitchen Hub is an independent tool website', text)

    def test_no_editor_instruction_reaches_a_post(self):
        for slug in OLD_TITLES:
            text = blog_updates.plain(self.post(slug).content)
            for note in ['should not be described', 'Do not describe', 'PASTE-READY', 'REPLACE WITH']:
                self.assertNotIn(note, text, f'{slug}: {note}')
        whatsapp = blog_updates.plain(self.post('emoji-kitchen-whatsapp').content)
        self.assertIn('WhatsApp does not create the mashup itself.', whatsapp)
        self.assertIn('they are not the same product.', blog_updates.plain(self.post('emoji-kitchen-samsung').content))

    def test_samsung_replaces_the_first_two_paragraphs_and_keeps_the_third(self):
        text = blog_updates.plain(self.post('emoji-kitchen-samsung').content)
        self.assertNotIn('but it does not come from Samsung Keyboard', text)
        self.assertNotIn('This distinction matters because Samsung also offers', text)
        self.assertIn('Google still identifies Emoji Kitchen as a Gboard feature.', text)

    def test_links_added_to_the_posts_work(self):
        for slug in OLD_TITLES:
            for target in re.findall(r'<a href="(/[^"]*)"', self.post(slug).content):
                self.assertEqual(self.client.get(target).status_code, 200, f'{slug} links to {target}')

    def test_published_pages_show_the_new_titles_meta_and_excerpts(self):
        index = self.fetch('/blog/')
        for slug, update in blog_content.POST_UPDATES.items():
            fields = update['fields']
            page = self.parse(f'/blog/{slug}/')
            self.assertEqual([_clean(h) for h in page.h1], [fields['title']], slug)
            self.assertEqual(_clean(page.title), fields['seo_title'], slug)             # no "— Emoji Kitchen" suffix any more
            self.assertEqual(page.meta['description'], fields['seo_description'], slug)
            self.assertIn(django_escape(fields['title']), index, slug)
            self.assertIn(django_escape(fields['excerpt']), index, slug)
            self.assertLessEqual(len(fields['seo_title']), 70)
            self.assertLessEqual(len(fields['seo_description']), 160)


class ImageSeoTests(TestCase):
    """Every image on a public page needs its own alt text and title."""

    PAGES = ['/', '/emoji-maker/', '/emoji-generator/', '/blog/']

    def imgs(self, path):
        html = self.client.get(path).content.decode()
        return [dict(re.findall(r'([\w-]+)="([^"]*)"', tag)) for tag in re.findall(r'<img\b[^>]*>', html)]

    def test_every_image_has_alt_and_title(self):
        for path in self.PAGES:
            for img in self.imgs(path):
                self.assertTrue(img.get('alt', '').strip(), f'{path}: no alt on {img}')
                self.assertTrue(img.get('title', '').strip(), f'{path}: no title on {img}')

    def test_explore_thumbnails_use_the_seo_teams_text_exactly(self):
        by_src = {i['src']: i for i in self.imgs('/') if i.get('width') == '96'}
        self.assertEqual(len(by_src), 30)
        for pair, (title, alt) in explore.IMAGE_TEXT.items():
            img = by_src[views.combo_image_url(*pair)]
            self.assertEqual(img['title'], title, pair)
            if alt:
                self.assertEqual(img['alt'], alt, pair)
        sample = by_src[views.combo_image_url('\U0001F602', '\U0001F480')]
        self.assertEqual(sample['title'], 'Laughing Face and Skull Emoji Mashup')
        self.assertEqual(sample['alt'], 'Light gray skull emoji with closed laughing eyes and large blue tears of joy.')

    def test_pairs_without_usable_file_text_keep_generated_wording(self):
        by_src = {i['src']: i for i in self.imgs('/') if i.get('width') == '96'}
        cupcake = by_src[views.combo_image_url('\U0001F9C1', '\U0001F308')]      # no entry in the file
        self.assertEqual(cupcake['alt'], 'Cupcake and rainbow emoji mashup sticker')
        droplet = by_src[views.combo_image_url('\U0001F525', '\U0001F4A7')]      # the file's alt repeats another entry
        self.assertEqual(droplet['title'], 'Fire and Water Droplet Emoji Mashup')
        self.assertEqual(droplet['alt'], 'Fire and droplet emoji mashup sticker')

    def test_alt_text_is_plain_readable_and_not_too_long(self):
        for path in self.PAGES:
            for img in self.imgs(path):
                self.assertLessEqual(len(img['alt']), 125, img['alt'])
                self.assertNotRegex(img['alt'], r'[^\x00-\x7f]') if img.get('width') == '96' else None

    def test_home_static_images_use_the_seo_teams_text(self):
        alts = {i['alt']: i['title'] for i in self.imgs('/')}
        self.assertEqual(alts['Orange cat emoji with flaming ears, fire-shaped forehead, and fiery eyes.'], 'Cat and Fire Emoji Mashup')
        self.assertEqual(alts['Cute dog face with floppy brown ears, a heart-shaped outline, and a playful expression.'],
                         'Dog and Heart Emoji Mashup')
        self.assertEqual(alts['Cat and fire emoji mashup displayed inside a chat bubble as a messaging sticker.'],
                         'Cat and Fire Emoji in Chat Bubble')

    def test_alt_text_is_not_repeated_for_different_images_on_one_page(self):
        for path in self.PAGES:
            alts = [i['alt'] for i in self.imgs(path) if i.get('src')]
            self.assertEqual(len(alts), len(set(alts)), path)

    def test_emoji_names(self):
        self.assertEqual(explore.emoji_name('\u2764\ufe0f'), 'red heart')
        self.assertEqual(explore.emoji_name('\U0001F602'), 'face with tears of joy')


class SearchSnippetTests(PageTestCase):
    """Titles and descriptions across the whole site stay within search-result limits and are unique."""

    def test_every_page_has_a_unique_title_and_description_of_a_sensible_length(self):
        titles, descriptions = {}, {}
        for path in [p for p in ALL_PAGES if p not in POSTS]:
            page = self.parse(path)
            title, description = _clean(page.title), page.meta['description']
            self.assertTrue(20 <= len(title) <= 60, f'{path} title is {len(title)} characters: {title}')
            self.assertTrue(80 <= len(description) <= 160, f'{path} description is {len(description)} characters')
            self.assertEqual(page.meta['og:title'] if 'og:title' in page.meta else title, title, path)
            self.assertNotIn(title, titles, f'{path} repeats the title of {titles.get(title)}')
            self.assertNotIn(description, descriptions, f'{path} repeats the description of {descriptions.get(description)}')
            titles[title], descriptions[description] = path, path

    def test_legal_pages_say_what_they_cover_and_no_longer_use_the_placeholder(self):
        for path in LEGAL:
            description = self.parse(path).meta['description']
            self.assertNotIn(' page for Emoji Kitchen Hub', description, path)
            self.assertNotIn('\u2014', _clean(self.parse(path).title), path)

    def test_article_titles_and_descriptions_from_the_update_script(self):
        seen = set()
        for slug, update in blog_content.POST_UPDATES.items():
            fields = update['fields']
            title = fields.get('seo_title') or fields['title']
            self.assertTrue(20 <= len(title) <= 60, f'{slug}: {len(title)} characters')
            self.assertTrue(80 <= len(fields['seo_description']) <= 160, slug)
            self.assertNotIn((title, fields['seo_description']), seen)
            seen.add((title, fields['seo_description']))


# ── Structured data, canonical and share cards ───────────────────────────────

def _ld_blocks(html):
    return [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class SiteWideSeoTests(PageTestCase):
    FAQ_PAGES = HUBS[:1] + ['/emoji-maker/', '/emoji-generator/', '/emoji-keyboard/', READY_MADE, PC] + COMBOS + MORE_COMBOS

    def test_every_json_ld_block_on_every_page_is_valid_json(self):
        for path in [p for p in ALL_PAGES if p not in POSTS]:
            self.assertGreaterEqual(len(_ld_blocks(self.fetch(path))), 1, path)

    def test_faq_markup_matches_the_questions_shown_and_is_not_duplicated(self):
        for path in self.FAQ_PAGES:
            html = self.fetch(path)
            faq_blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(faq_blocks), 1, path)
            shown = len(re.findall(r'<details class="faq-item[ "]', html))
            self.assertGreater(shown, 0, path)
            self.assertEqual(len(faq_blocks[0]['mainEntity']), shown, path)
            for entity in faq_blocks[0]['mainEntity']:
                self.assertIn(django_escape(entity['name']), html, path)

    def test_pages_without_faqs_have_no_faq_markup(self):
        for path in ['/blog/', '/privacy/', '/terms/', '/contact/', '/about-us/']:
            self.assertFalse([b for b in _ld_blocks(self.fetch(path)) if b.get('@type') == 'FAQPage'], path)

    def test_combo_category_pages_have_share_image_and_twitter_card(self):
        for path in COMBOS:
            page = self.parse(path)
            self.assertTrue(page.meta.get('og:image', '').endswith('og-emoji-kitchen-hub.png'), path)
            self.assertEqual(page.meta.get('twitter:card'), 'summary_large_image', path)
            self.assertEqual(page.meta['og:title'], _clean(page.title), path)


class SiteUrlCanonicalTests(PageTestCase):
    """Canonical and og:url use SITE_URL, never the request host or scheme."""

    EXTRA_HOSTS = [
        'testserver',
        'emojikitchenhub.com',
        'www.emojikitchenhub.com',
        'staging.example.com',
    ]
    REQUESTS = (
        {'HTTP_HOST': 'www.emojikitchenhub.com'},
        {'HTTP_HOST': 'staging.example.com', 'HTTP_X_FORWARDED_PROTO': 'http'},
        {'HTTP_HOST': 'emojikitchenhub.com', 'HTTP_X_FORWARDED_PROTO': 'http'},
    )

    def parse_with(self, path, **kwargs):
        response = self.client.get(path + '?utm_source=x', **kwargs)
        self.assertEqual(response.status_code, 200, path)
        parser = _PageParser()
        parser.feed(response.content.decode())
        return parser, response.content.decode()

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS)
    def test_canonical_and_og_url_use_the_fixed_https_origin(self):
        for path in ['/', PC, '/blog/emoji-kitchen-iphone/']:
            expected = 'https://emojikitchenhub.com' + path
            for kwargs in self.REQUESTS:
                page, html = self.parse_with(path, **kwargs)
                self.assertEqual(page.canonical, expected, (path, kwargs))
                self.assertEqual(page.meta['og:url'], expected, (path, kwargs))

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS)
    def test_page_specific_canonical_override_still_wins(self):
        # 404 clears the whole canonical block, so the default SITE_URL tag is not used.
        response = self.client.get('/does-not-exist-for-site-url-canonical/', HTTP_HOST='www.emojikitchenhub.com')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('rel="canonical"', response.content.decode())
        # Blog posts keep their pinned /blog/<slug>/ URL via {% block canonical_href %}.
        page, _ = self.parse_with('/blog/emoji-kitchen-iphone/', HTTP_HOST='www.emojikitchenhub.com')
        self.assertEqual(page.canonical, 'https://emojikitchenhub.com/blog/emoji-kitchen-iphone/')
        # Combo pages still supply their own absolute_site_url override.
        page, _ = self.parse_with('/emoji-combos/love/', HTTP_HOST='staging.example.com',
                                  HTTP_X_FORWARDED_PROTO='http')
        self.assertEqual(page.canonical, 'https://emojikitchenhub.com/emoji-combos/love/')

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS, SITE_URL='https://example.test')
    def test_overridden_site_url_is_honoured(self):
        page, html = self.parse_with('/', HTTP_HOST='www.emojikitchenhub.com')
        self.assertEqual(page.canonical, 'https://example.test/')
        self.assertEqual(page.meta['og:url'], 'https://example.test/')
        website = [b for b in _ld_blocks(html) if b.get('@type') == 'WebSite']
        self.assertEqual(website[0]['url'], 'https://example.test')
        page, html = self.parse_with('/blog/emoji-kitchen-iphone/', HTTP_HOST='staging.example.com')
        self.assertEqual(page.canonical, 'https://example.test/blog/emoji-kitchen-iphone/')
        articles = [b for b in _ld_blocks(html) if b.get('@type') == 'BlogPosting']
        self.assertEqual(articles[0]['publisher']['url'], 'https://example.test/')
        self.assertEqual(articles[0]['mainEntityOfPage']['@id'], page.canonical)

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS, SITE_URL='https://example.test/')
    def test_trailing_slash_on_site_url_is_stripped(self):
        page, _ = self.parse_with('/', HTTP_HOST='www.emojikitchenhub.com')
        self.assertEqual(page.canonical, 'https://example.test/')
        self.assertEqual(page.meta['og:url'], 'https://example.test/')

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS)
    def test_sitemap_locs_use_the_fixed_https_origin(self):
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for kwargs in self.REQUESTS:
            response = self.client.get('/sitemap.xml', **kwargs)
            self.assertEqual(response.status_code, 200, kwargs)
            locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
            self.assertTrue(locs, kwargs)
            for loc in locs:
                self.assertTrue(
                    loc.startswith('https://emojikitchenhub.com/'),
                    (loc, kwargs),
                )

    @override_settings(ALLOWED_HOSTS=EXTRA_HOSTS)
    def test_robots_txt_sitemap_uses_the_fixed_https_origin(self):
        for kwargs in self.REQUESTS:
            text = self.client.get('/robots.txt', **kwargs).content.decode()
            self.assertIn('Sitemap: https://emojikitchenhub.com/sitemap.xml', text)


class ErrorPageSeoTests(TestCase):
    """404/500 pages must be noindex and must not self-canonicalise."""

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
    def test_404_page_is_noindex_without_canonical(self):
        response = self.client.get('/does-not-exist-for-seo-404/')
        self.assertEqual(response.status_code, 404)
        html = response.content.decode()
        self.assertIn('<meta name="robots" content="noindex"', html)
        self.assertNotIn('rel="canonical"', html)

    def test_500_template_is_noindex_without_canonical(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        html = render_to_string('500.html', request=request)
        self.assertIn('<meta name="robots" content="noindex"', html)
        self.assertNotIn('rel="canonical"', html)


class ArticleSeoTests(BlogUpdateTestCase):
    def ld(self, slug):
        return _ld_blocks(self.fetch(f'/blog/{slug}/'))

    def test_old_address_stored_as_canonical_is_ignored(self):
        post = self.post('emoji-kitchen-iphone')
        expected = 'https://emojikitchenhub.com/blog/emoji-kitchen-iphone/'
        for stored in ['https://emojikitchenhub.com/emoji-kitchen-iphone/', '/emoji-kitchen-iphone/', 'emoji-kitchen-iphone']:
            post.canonical_url = stored
            post.save()
            self.assertEqual(self.parse('/blog/emoji-kitchen-iphone/').canonical, expected, stored)

    def test_a_correct_stored_canonical_is_kept(self):
        post = self.post('emoji-kitchen-gboard')
        post.canonical_url = 'https://emojikitchenhub.com/blog/emoji-kitchen-gboard/'
        post.save()
        self.assertEqual(
            self.parse('/blog/emoji-kitchen-gboard/').canonical,
            'https://emojikitchenhub.com/blog/emoji-kitchen-gboard/',
        )

    def test_each_article_has_blogposting_markup_built_from_what_the_page_shows(self):
        for slug in OLD_TITLES:
            post = self.post(slug)
            page = self.parse(f'/blog/{slug}/')
            articles = [b for b in self.ld(slug) if b.get('@type') == 'BlogPosting']
            self.assertEqual(len(articles), 1, slug)
            data = articles[0]
            self.assertEqual(data['headline'], post.title)
            self.assertEqual(data['mainEntityOfPage']['@id'], page.canonical)
            self.assertEqual(data['datePublished'], post.publish_date.isoformat())
            self.assertEqual(data['publisher']['name'], 'Emoji Kitchen Hub')
            for invented in ['aggregateRating', 'review', 'reviewRating']:
                self.assertNotIn(invented, data)

    def test_faq_markup_comes_from_the_questions_in_the_article(self):
        expected = {'emoji-kitchen-gboard': 9, 'emoji-kitchen-samsung': 9, 'emoji-kitchen-iphone': 9, 'emoji-kitchen-whatsapp': 7}
        for slug, count in expected.items():
            html = self.fetch(f'/blog/{slug}/')
            faq = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(faq), 1, slug)
            self.assertEqual(len(faq[0]['mainEntity']), count, slug)
            for entity in faq[0]['mainEntity']:
                self.assertTrue(entity['acceptedAnswer']['text'].strip(), slug)
                self.assertIn(blog_updates.plain(entity['name']), blog_updates.plain(self.post(slug).content), slug)

    def test_a_post_without_an_faq_section_gets_no_faq_markup(self):
        post = self.post('emoji-kitchen-gboard')
        post.content = '<h2>Intro</h2><p>No questions here.</p>'
        post.save()
        self.assertFalse([b for b in self.ld('emoji-kitchen-gboard') if b.get('@type') == 'FAQPage'])
        self.assertEqual(len([b for b in self.ld('emoji-kitchen-gboard') if b.get('@type') == 'BlogPosting']), 1)

    def test_markup_cannot_break_out_of_the_script_tag(self):
        post = self.post('emoji-kitchen-gboard')
        post.title = 'Tricky </script><b>title</b>'
        post.save()
        html = self.fetch('/blog/emoji-kitchen-gboard/')
        self.assertNotIn('</script><b>', html)
        self.assertEqual([b for b in _ld_blocks(html) if b.get('@type') == 'BlogPosting'][0]['headline'], post.title)



# ── Blog crawl-target internal links seed ─────────────────────────────────────

class BlogCrawlLinksSeedTests(TestCase):
    RELATED_MARKER = '/emoji-combos/love/'

    def setUp(self):
        for slug in ['emoji-kitchen-gboard', 'emoji-kitchen-samsung', 'emoji-kitchen-whatsapp']:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without crawl links.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_does_not_write(self):
        call_command('seed_blog_crawl_links', stdout=io.StringIO())
        for post in BlogPost.objects.filter(slug__startswith='emoji-kitchen-'):
            self.assertNotIn(self.RELATED_MARKER, post.content)

    def test_apply_appends_once_and_is_idempotent(self):
        slugs = ['emoji-kitchen-gboard', 'emoji-kitchen-samsung', 'emoji-kitchen-whatsapp']
        call_command('seed_blog_crawl_links', '--apply', stdout=io.StringIO())
        first_content = {}
        first_updated = {}
        for slug in slugs:
            post = BlogPost.objects.get(slug=slug)
            self.assertIn(self.RELATED_MARKER, post.content)
            self.assertIn('/emoji-combos/funny/', post.content)
            self.assertIn('/emoji-combos/pink/', post.content)
            self.assertIn('/emoji-keyboard/', post.content)
            first_content[slug] = post.content
            first_updated[slug] = post.updated_at
        call_command('seed_blog_crawl_links', '--apply', stdout=io.StringIO())
        for slug in slugs:
            post = BlogPost.objects.get(slug=slug)
            self.assertEqual(post.content.count(self.RELATED_MARKER), 1)
            self.assertEqual(post.content, first_content[slug])
            self.assertEqual(post.updated_at, first_updated[slug])


# ── iPhone blog rewrite seed ──────────────────────────────────────────────────

class IphoneBlogSeedTests(TestCase):
    def setUp(self):
        BlogPost.objects.create(
            title='Old iPhone Title',
            slug='emoji-kitchen-iphone',
            excerpt='old',
            content='<p>Old stuffed content with emoji kitchen emoji kitchen emoji kitchen.</p>',
            status=BlogPost.STATUS_PUBLISHED,
            seo_title='Old',
            seo_description='d' * 90,
        )

    def test_dry_run_leaves_content(self):
        call_command('seed_iphone_blog_post', stdout=io.StringIO())
        post = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        self.assertIn('Old stuffed content', post.content)

    def test_apply_rewrites_existing_slug_without_duplicate(self):
        call_command('seed_iphone_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug='emoji-kitchen-iphone').count(), 1)
        post = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('/emoji-combos/love/', post.content)
        self.assertIn('/emoji-keyboard/', post.content)
        self.assertNotIn('Old stuffed content', post.content)
        # density guard: phrase should stay rare in the new body
        plain = re.sub(r'<[^>]+>', ' ', post.content)
        words = re.findall(r"[A-Za-z0-9']+", plain)
        phrase = len(re.findall(r'emoji kitchen', plain, re.I))
        self.assertLess(phrase / max(len(words), 1), 0.02)

    def test_second_apply_leaves_updated_at_and_content_unchanged(self):
        call_command('seed_iphone_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        first_content = first.content
        first_updated = first.updated_at
        call_command('seed_iphone_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug='emoji-kitchen-iphone').count(), 1)
        again = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)


# ── Mixer shareable combo links (P10 MVP) ─────────────────────────────────────

class MixerShareLinkTests(PageTestCase):
    def test_mixer_exposes_share_control_and_query_loader(self):
        html = self.fetch('/emoji-maker/')
        self.assertIn('id="btn-share"', html)
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js').read_text(encoding='utf-8')
        self.assertIn('function shareUrlFor', js)
        self.assertIn("searchParams.set('emoji1'", js)
        self.assertIn('loadComboFromQuery', js)
        self.assertIn('Shareable combo link copied', js)


# ── Not-working blog seed ─────────────────────────────────────────────────────

class NotWorkingBlogSeedTests(TestCase):
    SLUG = 'emoji-kitchen-not-working'
    INBOUND = (
        'emoji-kitchen-iphone',
        'emoji-kitchen-gboard',
        'emoji-kitchen-samsung',
        'how-to-save-download-emoji-kitchen-stickers',
    )
    MARKER = f'/blog/{SLUG}/'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.INBOUND:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without not-working link.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_not_working_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            self.assertNotIn(self.MARKER, BlogPost.objects.get(slug=slug).content)

    def test_apply_creates_post_with_schema_cover_and_unofficial_wording(self):
        call_command('seed_not_working_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'Emoji Kitchen Not Working? 9 Fixes to Try')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_utils import cover_versioned_filename
        from kitchen.blog_seed_not_working import COVER_FILENAME, cover_bytes
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertEqual(
            post.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-not-working/',
        )
        from kitchen.seo import faq_pairs_from_html
        self.assertEqual(len(faq_pairs_from_html(post.content)), 6)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            blocks.append(json.loads(match.group(1)))
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)  # Article-style schema used sitewide
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertIn(self.MARKER.strip('/').split('/')[-1], html)  # page renders
        self.assertIn('rel="canonical"', html)
        self.assertIn('/blog/emoji-kitchen-not-working/', html)

    def test_apply_is_idempotent_and_adds_inbound_links(self):
        call_command('seed_not_working_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()
        inbound_content = {}
        inbound_updated = {}
        for slug in self.INBOUND:
            related = BlogPost.objects.get(slug=slug)
            self.assertIn(self.MARKER, related.content)
            self.assertIn('Emoji Kitchen not working fixes', related.content)
            inbound_content[slug] = related.content
            inbound_updated[slug] = related.updated_at

        call_command('seed_not_working_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        for slug in self.INBOUND:
            related = BlogPost.objects.get(slug=slug)
            self.assertEqual(related.content.count(self.MARKER), 1)
            self.assertEqual(related.content, inbound_content[slug])
            self.assertEqual(related.updated_at, inbound_updated[slug])

    def test_missing_related_posts_do_not_abort_seed(self):
        BlogPost.objects.filter(slug='emoji-kitchen-samsung').delete()
        call_command('seed_not_working_blog_post', '--apply', stdout=io.StringIO())
        self.assertTrue(BlogPost.objects.filter(slug=self.SLUG).exists())
        self.assertIn(self.MARKER, BlogPost.objects.get(slug='emoji-kitchen-gboard').content)
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers').content,
        )
        self.assertFalse(BlogPost.objects.filter(slug='emoji-kitchen-samsung').exists())


# ── On-PC blog seed ───────────────────────────────────────────────────────────

class OnPcBlogSeedTests(TestCase):
    SLUG = 'emoji-kitchen-on-pc'
    INBOUND = (
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-not-working',
        'emoji-kitchen-gboard',
    )
    MARKER = f'/blog/{SLUG}/'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.INBOUND:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without on-pc link.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_on_pc_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            self.assertNotIn(self.MARKER, BlogPost.objects.get(slug=slug).content)

    def test_apply_creates_post_with_schema_cover_and_unofficial_wording(self):
        call_command('seed_on_pc_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'How to Use Emoji Kitchen on PC, Mac, and Chromebook')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertIn('href="/emoji-keyboard-for-pc/"', post.content)
        self.assertIn('href="/"', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_utils import cover_versioned_filename
        from kitchen.blog_seed_on_pc import COVER_FILENAME, cover_bytes
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertEqual(
            post.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-on-pc/',
        )
        from kitchen.seo import faq_pairs_from_html
        self.assertEqual(len(faq_pairs_from_html(post.content)), 6)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            blocks.append(json.loads(match.group(1)))
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)  # Article-style schema used sitewide
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertIn(self.MARKER.strip('/').split('/')[-1], html)  # page renders
        self.assertIn('rel="canonical"', html)
        self.assertIn('/blog/emoji-kitchen-on-pc/', html)
        self.assertIn('/emoji-keyboard-for-pc/', html)
        self.assertIn('href="/"', html)

    def test_apply_is_idempotent_and_adds_inbound_links(self):
        call_command('seed_on_pc_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()
        inbound_content = {}
        inbound_updated = {}
        for slug in self.INBOUND:
            related = BlogPost.objects.get(slug=slug)
            self.assertIn(self.MARKER, related.content)
            self.assertIn('use Emoji Kitchen on PC, Mac, and Chromebook', related.content)
            inbound_content[slug] = related.content
            inbound_updated[slug] = related.updated_at

        call_command('seed_on_pc_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        for slug in self.INBOUND:
            related = BlogPost.objects.get(slug=slug)
            self.assertEqual(related.content.count(self.MARKER), 1)
            self.assertEqual(related.content, inbound_content[slug])
            self.assertEqual(related.updated_at, inbound_updated[slug])

    def test_missing_related_posts_do_not_abort_seed(self):
        BlogPost.objects.filter(slug='emoji-kitchen-gboard').delete()
        call_command('seed_on_pc_blog_post', '--apply', stdout=io.StringIO())
        self.assertTrue(BlogPost.objects.filter(slug=self.SLUG).exists())
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers').content,
        )
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='emoji-kitchen-not-working').content,
        )
        self.assertFalse(BlogPost.objects.filter(slug='emoji-kitchen-gboard').exists())


# ── Save/download stickers blog seed ──────────────────────────────────────────

class SaveDownloadBlogSeedTests(TestCase):
    SLUG = 'how-to-save-download-emoji-kitchen-stickers'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)

    def test_dry_run_writes_nothing(self):
        call_command('seed_save_download_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())

    def test_apply_creates_post_with_cover(self):
        call_command('seed_save_download_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'How to Save and Download Emoji Kitchen Stickers')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_utils import cover_versioned_filename
        from kitchen.blog_seed_save_download import COVER_FILENAME, cover_bytes
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )

    def test_apply_twice_leaves_updated_at_and_content_unchanged(self):
        call_command('seed_save_download_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()

        call_command('seed_save_download_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()


# ── Discord blog seed ─────────────────────────────────────────────────────────

class DiscordBlogSeedTests(TestCase):
    SLUG = 'emoji-kitchen-discord'
    INBOUND = (
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-on-pc',
        'emoji-kitchen-not-working',
    )
    MARKER = f'/blog/{SLUG}/'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.INBOUND:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without discord link.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_discord_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            self.assertNotIn(self.MARKER, BlogPost.objects.get(slug=slug).content)

    def test_apply_creates_post_with_schema_cover_and_unofficial_wording(self):
        call_command('seed_discord_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'How to Use Emoji Kitchen Stickers on Discord')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertIn('href="/"', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_utils import cover_versioned_filename
        from kitchen.blog_seed_discord import COVER_FILENAME, cover_bytes
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertEqual(
            post.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-discord/',
        )
        from kitchen.seo import faq_pairs_from_html
        self.assertEqual(len(faq_pairs_from_html(post.content)), 6)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            blocks.append(json.loads(match.group(1)))
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)  # Article-style schema used sitewide
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertIn(self.MARKER.strip('/').split('/')[-1], html)  # page renders
        self.assertIn('rel="canonical"', html)
        self.assertIn('/blog/emoji-kitchen-discord/', html)
        self.assertIn('href="/"', html)

    def test_apply_is_idempotent_and_adds_inbound_links(self):
        call_command('seed_discord_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()
        for slug in self.INBOUND:
            content = BlogPost.objects.get(slug=slug).content
            self.assertIn(self.MARKER, content)
            self.assertIn('use Emoji Kitchen stickers on Discord', content)

        call_command('seed_discord_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        for slug in self.INBOUND:
            self.assertEqual(BlogPost.objects.get(slug=slug).content.count(self.MARKER), 1)

    def test_missing_related_posts_do_not_abort_seed(self):
        BlogPost.objects.filter(slug='emoji-kitchen-on-pc').delete()
        call_command('seed_discord_blog_post', '--apply', stdout=io.StringIO())
        self.assertTrue(BlogPost.objects.filter(slug=self.SLUG).exists())
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers').content,
        )
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='emoji-kitchen-not-working').content,
        )
        self.assertFalse(BlogPost.objects.filter(slug='emoji-kitchen-on-pc').exists())



# ── Google Messages blog seed ─────────────────────────────────────────────────

class GoogleMessagesBlogSeedTests(TestCase):
    SLUG = 'emoji-kitchen-google-messages'
    INBOUND = (
        'emoji-kitchen-gboard',
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-not-working',
        'emoji-kitchen-samsung',
    )
    MARKER = f'/blog/{SLUG}/'
    CANONICAL = 'https://emojikitchenhub.com/blog/emoji-kitchen-google-messages/'
    EXPECTED_HREFS = (
        '/',
        '/emoji-keyboard/',
        '/blog/emoji-kitchen-samsung/',
        '/blog/emoji-kitchen-gboard/',
        '/blog/how-to-save-download-emoji-kitchen-stickers/',
        '/emoji-maker/',
        '/emoji-generator/',
        '/blog/emoji-kitchen-not-working/',
        '/blog/emoji-kitchen-iphone/',
        '/emoji-combos/',
        '/emoji-combos/love/',
        '/emoji-combos/funny/',
        '/blog/emoji-kitchen-whatsapp/',
    )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.INBOUND:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without google messages link.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )
        # Extra published stubs so every internal blog link in the fixture resolves.
        for slug in ('emoji-kitchen-iphone', 'emoji-kitchen-whatsapp'):
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Related guide.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_google_messages_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            self.assertNotIn(self.MARKER, BlogPost.objects.get(slug=slug).content)

    def test_apply_creates_post_with_schema_cover_and_unofficial_wording(self):
        call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'How to Use Emoji Kitchen in Google Messages (Android Guide)')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertIn('href="/"', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_google_messages import COVER_FILENAME, cover_bytes
        from kitchen.blog_seed_utils import cover_versioned_filename
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertEqual(post.canonical_url, self.CANONICAL)
        from kitchen.seo import faq_pairs_from_html
        self.assertEqual(len(faq_pairs_from_html(post.content)), 6)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            blocks.append(json.loads(match.group(1)))
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)  # Article-style schema used sitewide
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertIn(self.SLUG, html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('/blog/emoji-kitchen-google-messages/', html)
        self.assertIn('href="/"', html)

    def test_apply_is_idempotent_and_adds_inbound_links(self):
        call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()
        for slug in self.INBOUND:
            content = BlogPost.objects.get(slug=slug).content
            self.assertIn(self.MARKER, content)
            self.assertIn('use Emoji Kitchen in Google Messages', content)

        call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        for slug in self.INBOUND:
            self.assertEqual(BlogPost.objects.get(slug=slug).content.count(self.MARKER), 1)

    def test_missing_related_posts_do_not_abort_seed(self):
        BlogPost.objects.filter(slug='emoji-kitchen-samsung').delete()
        call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        self.assertTrue(BlogPost.objects.filter(slug=self.SLUG).exists())
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='emoji-kitchen-gboard').content,
        )
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers').content,
        )
        self.assertIn(
            self.MARKER,
            BlogPost.objects.get(slug='emoji-kitchen-not-working').content,
        )
        self.assertFalse(BlogPost.objects.filter(slug='emoji-kitchen-samsung').exists())

    def test_internal_links_resolve_and_sitemap_includes_the_post(self):
        call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        post = BlogPost.objects.get(slug=self.SLUG)
        hrefs = set(re.findall(r'href="([^"]+)"', post.content))
        self.assertEqual(hrefs, set(self.EXPECTED_HREFS))
        for href in sorted(hrefs):
            self.assertEqual(self.client.get(href).status_code, 200, href)
        self.assertEqual(self.client.get(f'/blog/{self.SLUG}/').status_code, 200)

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        self.assertIn(self.CANONICAL, locs)

    def test_publishing_the_post_pings_indexnow(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as post:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        submitted = [url for call in submit.call_args_list for url in call.args[0]]
        self.assertIn(self.CANONICAL, submitted)
        post.assert_called()

        submit.reset_mock()
        post.reset_mock()
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit2:
            with mock.patch.object(indexnow.requests, 'post') as post2:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_google_messages_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(submit2.call_count, 0)
        post2.assert_not_called()

    def test_cover_swap_versions_filename_and_pings_once(self):
        from kitchen.blog_seed_google_messages import COVER_FILENAME, cover_bytes
        _assert_cover_swap_versions_and_pings(
            self,
            command='seed_google_messages_blog_post',
            cover_filename=COVER_FILENAME,
            image_bytes=cover_bytes(),
        )


class InstagramBlogSeedTests(TestCase):
    SLUG = 'emoji-kitchen-instagram'
    INBOUND = (
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-iphone',
        'emoji-kitchen-whatsapp',
        'emoji-kitchen-gboard',
    )
    MARKER = f'/blog/{SLUG}/'
    CANONICAL = 'https://emojikitchenhub.com/blog/emoji-kitchen-instagram/'
    EXPECTED_HREFS = (
        '/',
        '/emoji-combos/',
        '/emoji-combos/aesthetic/',
        '/emoji-combos/cute/',
        '/emoji-combos/pink/',
        '/emoji-combos/love/',
        '/emoji-combos/funny/',
        '/blog/how-to-save-download-emoji-kitchen-stickers/',
        '/blog/emoji-kitchen-gboard/',
        '/blog/emoji-kitchen-iphone/',
        '/blog/emoji-kitchen-not-working/',
        '/blog/emoji-kitchen-whatsapp/',
        '/blog/emoji-kitchen-samsung/',
        '/emoji-maker/',
        '/emoji-generator/',
    )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.INBOUND:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article without instagram link.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )
        # Extra published stubs so every internal blog link in the fixture resolves.
        for slug in ('emoji-kitchen-not-working', 'emoji-kitchen-samsung'):
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Related guide.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_instagram_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            self.assertNotIn(self.MARKER, BlogPost.objects.get(slug=slug).content)

    def test_apply_creates_post_with_schema_cover_and_unofficial_wording(self):
        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, 'How to Use Emoji Kitchen on Instagram (Stories, DMs & Posts)')
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertIn('href="/"', post.content)
        self.assertTrue(post.featured_image)
        from kitchen.blog_seed_instagram import COVER_FILENAME, cover_bytes
        from kitchen.blog_seed_utils import cover_versioned_filename
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertEqual(post.canonical_url, self.CANONICAL)
        from kitchen.seo import faq_pairs_from_html
        self.assertEqual(len(faq_pairs_from_html(post.content)), 6)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = []
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            blocks.append(json.loads(match.group(1)))
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)  # Article-style schema used sitewide
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertIn(self.SLUG, html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('/blog/emoji-kitchen-instagram/', html)
        self.assertIn('href="/"', html)

    def test_apply_is_idempotent_and_adds_inbound_links(self):
        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first_cover = first.featured_image.read()
        first.featured_image.close()
        for slug in self.INBOUND:
            content = BlogPost.objects.get(slug=slug).content
            self.assertIn(self.MARKER, content)
            self.assertIn('use Emoji Kitchen on Instagram', content)

        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        for slug in self.INBOUND:
            self.assertEqual(BlogPost.objects.get(slug=slug).content.count(self.MARKER), 1)

    def test_missing_related_posts_do_not_abort_seed(self):
        BlogPost.objects.filter(slug='emoji-kitchen-whatsapp').delete()
        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        self.assertTrue(BlogPost.objects.filter(slug=self.SLUG).exists())
        for slug in self.INBOUND:
            if slug == 'emoji-kitchen-whatsapp':
                continue
            self.assertIn(self.MARKER, BlogPost.objects.get(slug=slug).content)
        self.assertFalse(BlogPost.objects.filter(slug='emoji-kitchen-whatsapp').exists())

    def test_faq_schema_has_no_disclaimer_leak(self):
        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = [
            json.loads(m.group(1))
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        ]
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        answers = [e['acceptedAnswer']['text'] for e in faq['mainEntity']]
        self.assertEqual(len(answers), 6)
        self.assertFalse(any(_FAQ_DISCLAIMER_RE.search(a) for a in answers))
        self.assertTrue(answers[-1].endswith('the available pairs can differ.'))

    def test_internal_links_resolve_and_sitemap_includes_the_post(self):
        call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        post = BlogPost.objects.get(slug=self.SLUG)
        hrefs = set(re.findall(r'href="([^"]+)"', post.content))
        self.assertEqual(hrefs, set(self.EXPECTED_HREFS))
        for href in sorted(hrefs):
            self.assertEqual(self.client.get(href).status_code, 200, href)
        self.assertEqual(self.client.get(f'/blog/{self.SLUG}/').status_code, 200)

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        self.assertIn(self.CANONICAL, locs)

    def test_publishing_the_post_pings_indexnow(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as post:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        submitted = [url for call in submit.call_args_list for url in call.args[0]]
        self.assertIn(self.CANONICAL, submitted)
        post.assert_called()

        submit.reset_mock()
        post.reset_mock()
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit2:
            with mock.patch.object(indexnow.requests, 'post') as post2:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_instagram_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(submit2.call_count, 0)
        post2.assert_not_called()

    def test_cover_swap_versions_filename_and_pings_once(self):
        from kitchen.blog_seed_instagram import COVER_FILENAME, cover_bytes
        _assert_cover_swap_versions_and_pings(
            self,
            command='seed_instagram_blog_post',
            cover_filename=COVER_FILENAME,
            image_bytes=cover_bytes(),
        )



class ThanksgivingBlogSeedTests(TestCase):
    SLUG = 'thanksgiving-emoji-combos'
    CANONICAL = 'https://emojikitchenhub.com/blog/thanksgiving-emoji-combos/'
    RELATED = (
        'how-to-save-download-emoji-kitchen-stickers',
        'emoji-kitchen-google-messages',
        'emoji-kitchen-gboard',
        'emoji-kitchen-iphone',
        'emoji-kitchen-whatsapp',
        'emoji-kitchen-instagram',
        'emoji-kitchen-discord',
        'emoji-kitchen-not-working',
    )
    MIXER_HREFS = (
        '/?emoji1=%F0%9F%8D%81&emoji2=%F0%9F%98%8A#kitchen',
        '/?emoji1=%F0%9F%8D%82&emoji2=%F0%9F%A5%B0#kitchen',
        '/?emoji1=%F0%9F%8D%81&emoji2=%F0%9F%98%8D#kitchen',
        '/?emoji1=%F0%9F%8D%82&emoji2=%F0%9F%98%8B#kitchen',
        '/?emoji1=%F0%9F%8D%97&emoji2=%F0%9F%98%8B#kitchen',
        '/?emoji1=%F0%9F%8D%82&emoji2=%F0%9F%98%B4#kitchen',
    )
    EXPECTED_HREFS = (
        '/',
        '/emoji-combos/',
        '/emoji-combos/aesthetic/',
        '/emoji-combos/cute/',
        '/emoji-combos/bio/',
        '/emoji-combos/christmas/',
        '/blog/how-to-save-download-emoji-kitchen-stickers/',
        '/blog/emoji-kitchen-google-messages/',
        '/blog/emoji-kitchen-gboard/',
        '/blog/emoji-kitchen-iphone/',
        '/blog/emoji-kitchen-whatsapp/',
        '/blog/emoji-kitchen-instagram/',
        '/blog/emoji-kitchen-discord/',
        '/blog/emoji-kitchen-not-working/',
        '/emoji-maker/',
        '/emoji-generator/',
    ) + MIXER_HREFS

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.RELATED:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Related guide.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def test_dry_run_writes_nothing(self):
        call_command('seed_thanksgiving_blog_post', stdout=io.StringIO())
        self.assertFalse(BlogPost.objects.filter(slug=self.SLUG).exists())

    def test_apply_creates_post_with_schema_cover_meta_and_unofficial_wording(self):
        from io import BytesIO
        from PIL import Image
        from kitchen.blog_covers import MAX_COVER_BYTES, expected_cover_size
        from kitchen.blog_seed_thanksgiving import (
            COVER_FILENAME,
            FIELDS,
            OG_FILENAME,
            cover_bytes,
            og_bytes,
        )
        from kitchen.blog_seed_utils import cover_versioned_filename
        from kitchen.seo import faq_pairs_from_html

        call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        post = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(post.title, FIELDS['title'])
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertEqual(post.canonical_url, self.CANONICAL)
        self.assertLessEqual(len(post.seo_description), 150)
        self.assertLessEqual(len(post.excerpt), 150)
        self.assertEqual(post.seo_description, FIELDS['seo_description'])
        self.assertEqual(post.excerpt, FIELDS['excerpt'])
        self.assertIn('unofficial, fan-made', post.content)
        self.assertIn('not run by Google', post.content)
        self.assertIn('href="/"', post.content)
        self.assertIn('has no mashups for 🦃, 🥧, 🎃, 🌽, or 🙏', post.content)

        self.assertTrue(post.featured_image)
        self.assertEqual(
            post.featured_image.name,
            'blog/featured/' + cover_versioned_filename(COVER_FILENAME, cover_bytes()),
        )
        self.assertTrue(post.og_image)
        self.assertEqual(
            post.og_image.name,
            'blog/og/' + cover_versioned_filename(OG_FILENAME, og_bytes()),
        )
        post.featured_image.open('rb')
        try:
            webp = post.featured_image.read()
        finally:
            post.featured_image.close()
        post.og_image.open('rb')
        try:
            jpg = post.og_image.read()
        finally:
            post.og_image.close()
        self.assertEqual(webp, cover_bytes())
        self.assertEqual(jpg, og_bytes())
        self.assertLessEqual(len(webp), MAX_COVER_BYTES)
        self.assertLessEqual(len(jpg), MAX_COVER_BYTES)
        width, height = expected_cover_size(self.SLUG)
        self.assertEqual(width, 1200)
        self.assertEqual(height, 675)
        webp_im = Image.open(BytesIO(webp))
        jpg_im = Image.open(BytesIO(jpg))
        self.assertEqual(webp_im.size, (width, height))
        self.assertEqual(jpg_im.size, (width, height))
        self.assertEqual(jpg_im.format, 'JPEG')

        pairs = faq_pairs_from_html(post.content)
        self.assertEqual(len(pairs), 6)
        self.assertFalse(any(_FAQ_DISCLAIMER_RE.search(a) for _, a in pairs))
        mashup_answer = next(a for q, a in pairs if 'mashup' in q.lower())
        self.assertIn('have no Emoji Kitchen mashups', mashup_answer)
        self.assertNotIn('Try pairing 🦃', post.content)

        html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
        blocks = [
            json.loads(match.group(1))
            for match in re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
            )
        ]
        types = {b.get('@type') for b in blocks}
        self.assertIn('BlogPosting', types)
        self.assertIn('FAQPage', types)
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 6)
        answers = [e['acceptedAnswer']['text'] for e in faq['mainEntity']]
        self.assertFalse(any(_FAQ_DISCLAIMER_RE.search(a) for a in answers))
        self.assertTrue(answers[-1].endswith('the available pairs can differ.'))
        self.assertIn('rel="canonical"', html)
        self.assertIn(self.CANONICAL, html)
        og = re.search(r'property="og:image" content="([^"]+)"', html)
        self.assertIsNotNone(og)
        self.assertTrue(og.group(1).endswith('.jpg'), og.group(1))
        self.assertIn(cover_versioned_filename(OG_FILENAME, og_bytes()), og.group(1))
        self.assertEqual(
            re.search(r'property="og:image:width" content="([^"]*)"', html).group(1),
            '1200',
        )
        self.assertEqual(
            re.search(r'property="og:image:height" content="([^"]*)"', html).group(1),
            '675',
        )
        self.assertEqual(
            re.search(r'property="og:image:type" content="([^"]*)"', html).group(1),
            'image/jpeg',
        )
        on_page = re.search(r'<div class="blog-detail__cover">\s*<img\b([^>]*)>', html)
        self.assertIsNotNone(on_page)
        self.assertTrue(re.search(r'src="([^"]+)"', on_page.group(1)).group(1).endswith('.webp'))

    def test_apply_is_idempotent(self):
        call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        first = BlogPost.objects.get(slug=self.SLUG)
        first_pk = first.pk
        first_content = first.content
        first_updated = first.updated_at
        first.featured_image.open('rb')
        try:
            first_cover = first.featured_image.read()
        finally:
            first.featured_image.close()
        first.og_image.open('rb')
        try:
            first_og = first.og_image.read()
        finally:
            first.og_image.close()
        first_cover_name = first.featured_image.name
        first_og_name = first.og_image.name

        call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(BlogPost.objects.filter(slug=self.SLUG).count(), 1)
        again = BlogPost.objects.get(slug=self.SLUG)
        self.assertEqual(again.pk, first_pk)
        self.assertEqual(again.content, first_content)
        self.assertEqual(again.updated_at, first_updated)
        self.assertEqual(again.featured_image.name, first_cover_name)
        self.assertEqual(again.og_image.name, first_og_name)
        again.featured_image.open('rb')
        try:
            self.assertEqual(again.featured_image.read(), first_cover)
        finally:
            again.featured_image.close()
        again.og_image.open('rb')
        try:
            self.assertEqual(again.og_image.read(), first_og)
        finally:
            again.og_image.close()

    def test_internal_links_resolve_mixer_pairs_exist_and_sitemap_gains_the_post(self):
        from urllib.parse import parse_qs, unquote, urlparse
        from kitchen.views import combo_image_url

        before = self.client.get('/sitemap.xml')
        self.assertEqual(before.status_code, 200)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs_before = [u.text for u in ET.fromstring(before.content).findall('s:url/s:loc', ns)]
        self.assertNotIn(self.CANONICAL, locs_before)

        call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        post = BlogPost.objects.get(slug=self.SLUG)
        hrefs = {href.replace('&amp;', '&') for href in re.findall(r'href="([^"]+)"', post.content)}
        self.assertEqual(hrefs, set(self.EXPECTED_HREFS))
        for href in sorted(hrefs):
            path = href.split('#')[0]
            self.assertEqual(self.client.get(path).status_code, 200, href)
        self.assertEqual(self.client.get(f'/blog/{self.SLUG}/').status_code, 200)

        mixer = [href for href in hrefs if href.startswith('/?emoji1=')]
        self.assertEqual(len(mixer), 6)
        for href in mixer:
            query = parse_qs(urlparse(href).query)
            self.assertTrue(
                combo_image_url(unquote(query['emoji1'][0]), unquote(query['emoji2'][0])),
                href,
            )

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        self.assertIn(self.CANONICAL, locs)
        self.assertEqual(len(locs), len(locs_before) + 1)

    def test_combo_pages_link_to_the_post_and_the_homepage_does_not(self):
        call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        christmas = self.client.get('/emoji-combos/christmas/').content.decode()
        self.assertIn('/blog/thanksgiving-emoji-combos/', christmas)
        self.assertIn('Thanksgiving emoji combos', christmas)
        ready_made = self.client.get(READY_MADE).content.decode()
        self.assertIn('/blog/thanksgiving-emoji-combos/', ready_made)
        home = self.client.get('/').content.decode()
        self.assertNotIn('/blog/thanksgiving-emoji-combos/', home)

    def test_publishing_the_post_pings_indexnow_once(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as posted:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        submitted = [url for call in submit.call_args_list for url in call.args[0]]
        self.assertIn(self.CANONICAL, submitted)
        posted.assert_called()

        submit.reset_mock()
        posted.reset_mock()
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit2:
            with mock.patch.object(indexnow.requests, 'post') as posted2:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            call_command('seed_thanksgiving_blog_post', '--apply', stdout=io.StringIO())
        self.assertEqual(submit2.call_count, 0)
        posted2.assert_not_called()


# ── Blog seed inbound-suffix helpers ──────────────────────────────────────────

class BlogSeedUtilsTests(SimpleTestCase):
    def test_split_and_desired_content_ignore_and_preserve_suffixes(self):
        from kitchen.blog_seed_discord import INBOUND_HTML as discord_html
        from kitchen.blog_seed_google_messages import INBOUND_HTML as google_messages_html
        from kitchen.blog_seed_instagram import INBOUND_HTML as instagram_html
        from kitchen.blog_seed_not_working import INBOUND_HTML as not_working_html
        from kitchen.blog_seed_on_pc import INBOUND_HTML as on_pc_html
        from kitchen.blog_seed_utils import desired_seed_content, split_allowed_inbound_suffix

        fixture = '<p>Fixture body of the post.</p>\n'
        current = (
            fixture.rstrip()
            + '\n' + not_working_html + '\n'
            + '\n' + on_pc_html + '\n'
            + '\n' + discord_html + '\n'
            + '\n' + google_messages_html + '\n'
            + '\n' + instagram_html + '\n'
        )
        core, suffix = split_allowed_inbound_suffix(current)
        self.assertEqual(core.rstrip(), fixture.rstrip())
        self.assertIn('/blog/emoji-kitchen-not-working/', suffix)
        self.assertIn('/blog/emoji-kitchen-on-pc/', suffix)
        self.assertIn('/blog/emoji-kitchen-discord/', suffix)
        self.assertIn('/blog/emoji-kitchen-google-messages/', suffix)
        self.assertIn('/blog/emoji-kitchen-instagram/', suffix)
        # No-op when the body already matches the fixture.
        self.assertEqual(desired_seed_content(fixture, current), current)
        # A real body change keeps the inbound paragraphs.
        rewritten = desired_seed_content('<p>New fixture body.</p>\n', current)
        new_core, new_suffix = split_allowed_inbound_suffix(rewritten)
        self.assertEqual(new_core.rstrip(), '<p>New fixture body.</p>')
        self.assertIn('/blog/emoji-kitchen-not-working/', new_suffix)
        self.assertIn('/blog/emoji-kitchen-on-pc/', new_suffix)
        self.assertIn('/blog/emoji-kitchen-discord/', new_suffix)
        self.assertIn('/blog/emoji-kitchen-google-messages/', new_suffix)
        self.assertIn('/blog/emoji-kitchen-instagram/', new_suffix)
        self.assertNotIn('Fixture body of the post.', rewritten)

    def test_cover_versioned_filename_is_deterministic(self):
        from kitchen.blog_seed_utils import cover_versioned_filename
        first = cover_versioned_filename('emoji-kitchen-google-messages-cover.png', b'abc')
        second = cover_versioned_filename('emoji-kitchen-google-messages-cover.png', b'abc')
        other = cover_versioned_filename('emoji-kitchen-google-messages-cover.png', b'abd')
        self.assertEqual(first, second)
        self.assertEqual(first, 'emoji-kitchen-google-messages-cover-ba7816bf.png')
        self.assertNotEqual(first, other)
        self.assertTrue(other.startswith('emoji-kitchen-google-messages-cover-'))
        self.assertTrue(other.endswith('.png'))
        self.assertEqual(len(other), len(first))


# ── Cross-seed inbound links must survive a second apply ──────────────────────

class BlogSeedChainIdempotentTests(TestCase):
    """QA scenario: later seeds append inbound links to earlier posts.

    A second --apply (or running an older seed alone) must not treat those
    suffixes as fixture drift, rewrite the body, or bump updated_at.
    """

    REALISTIC_ORDER = (
        'seed_save_download_blog_post',
        'seed_not_working_blog_post',
        'seed_on_pc_blog_post',
        'seed_discord_blog_post',
        'seed_google_messages_blog_post',
        'seed_instagram_blog_post',
    )
    ALL_SEEDS = REALISTIC_ORDER + (
        'seed_iphone_blog_post',
        'seed_blog_crawl_links',
        'seed_combo_page_links',
    )
    OLDER_SEEDS = (
        'seed_save_download_blog_post',
        'seed_not_working_blog_post',
        'seed_on_pc_blog_post',
        'seed_discord_blog_post',
        'seed_google_messages_blog_post',
    )
    STUB_SLUGS = (
        'emoji-kitchen-gboard',
        'emoji-kitchen-samsung',
        'emoji-kitchen-whatsapp',
        'emoji-kitchen-iphone',
    )
    CONTENT_DRIFT = re.compile(r'content:\s+\d+\s+->\s+\d+\s+words')
    INBOUND_MARKERS = (
        '/blog/emoji-kitchen-not-working/',
        '/blog/emoji-kitchen-on-pc/',
        '/blog/emoji-kitchen-discord/',
        '/blog/emoji-kitchen-google-messages/',
        '/blog/emoji-kitchen-instagram/',
    )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self._media = override_settings(MEDIA_ROOT=self.tmp)
        self._media.enable()
        self.addCleanup(self._media.disable)
        for slug in self.STUB_SLUGS:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Base article used for inbound and crawl-link seeds.</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_title=slug,
                seo_description='d' * 90,
            )

    def _run(self, command, apply=True):
        out = io.StringIO()
        args = (command, '--apply') if apply else (command,)
        call_command(*args, stdout=out)
        return out.getvalue()

    def _run_all(self, commands, apply=True):
        return ''.join(self._run(name, apply=apply) for name in commands)

    def _snapshot(self):
        data = {}
        for post in BlogPost.objects.all().order_by('slug'):
            data[post.slug] = {
                'pk': post.pk,
                'content': post.content,
                'updated_at': post.updated_at,
                'reading_time': post.reading_time,
                'title': post.title,
            }
        return data

    def test_full_chain_second_apply_and_older_seeds_alone_change_nothing(self):
        self._run_all(self.ALL_SEEDS, apply=True)

        save = BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers')
        for marker in self.INBOUND_MARKERS:
            self.assertIn(marker, save.content)
        not_working = BlogPost.objects.get(slug='emoji-kitchen-not-working')
        self.assertIn('/blog/emoji-kitchen-on-pc/', not_working.content)
        self.assertIn('/blog/emoji-kitchen-discord/', not_working.content)
        self.assertIn('/blog/emoji-kitchen-google-messages/', not_working.content)
        on_pc = BlogPost.objects.get(slug='emoji-kitchen-on-pc')
        self.assertIn('/blog/emoji-kitchen-discord/', on_pc.content)
        for slug in ('emoji-kitchen-iphone', 'emoji-kitchen-gboard', 'emoji-kitchen-samsung'):
            related = BlogPost.objects.get(slug=slug)
            self.assertIn('/blog/emoji-kitchen-not-working/', related.content)
            self.assertIn('Emoji Kitchen not working fixes', related.content)
            self.assertEqual(related.content.count('/blog/emoji-kitchen-not-working/'), 1)
        for slug in ('emoji-kitchen-gboard', 'emoji-kitchen-samsung'):
            related = BlogPost.objects.get(slug=slug)
            self.assertIn('/blog/emoji-kitchen-google-messages/', related.content)
            self.assertIn('use Emoji Kitchen in Google Messages', related.content)
            self.assertEqual(related.content.count('/blog/emoji-kitchen-google-messages/'), 1)

        after_first = self._snapshot()

        dry_output = self._run_all(self.ALL_SEEDS, apply=False)
        self.assertIsNone(self.CONTENT_DRIFT.search(dry_output))
        self.assertEqual(self._snapshot(), after_first)

        self._run_all(self.ALL_SEEDS, apply=True)
        self.assertEqual(self._snapshot(), after_first)

        for command in self.OLDER_SEEDS:
            self._run(command, apply=True)
            self.assertEqual(
                self._snapshot(),
                after_first,
                msg=f'{command} alone changed a post after the full apply',
            )

    def test_real_body_change_is_corrected_and_inbound_paragraphs_are_kept(self):
        from kitchen.blog_seed_save_download import content_html
        from kitchen.blog_seed_utils import split_allowed_inbound_suffix

        self._run_all(self.REALISTIC_ORDER, apply=True)
        post = BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers')
        core, suffix = split_allowed_inbound_suffix(post.content)
        self.assertTrue(suffix.strip())
        for marker in self.INBOUND_MARKERS:
            self.assertIn(marker, suffix)

        post.content = core.rstrip() + '\n<p>tampered body that is not in the fixture.</p>\n' + suffix
        post.save()
        self.assertIn('tampered body that is not in the fixture.', post.content)

        self._run('seed_save_download_blog_post', apply=True)
        again = BlogPost.objects.get(slug='how-to-save-download-emoji-kitchen-stickers')
        new_core, new_suffix = split_allowed_inbound_suffix(again.content)
        self.assertEqual(new_core.rstrip(), content_html().rstrip())
        self.assertNotIn('tampered body that is not in the fixture.', again.content)
        for marker in self.INBOUND_MARKERS:
            self.assertIn(marker, again.content)
        self.assertEqual(new_suffix.strip(), suffix.strip())


# ── Blog canonicals, fix command, and not-working footer link ─────────────────

class BlogCanonicalPageTests(PageTestCase):
    """Every blog post page (and the sitemap) uses the public /blog/<slug>/ URL."""

    def test_every_seeded_post_canonical_is_the_absolute_blog_url(self):
        from kitchen.seo import absolute_blog_canonical

        for slug in POST_SLUGS:
            expected = absolute_blog_canonical(slug)
            self.assertEqual(expected, f'https://emojikitchenhub.com/blog/{slug}/')
            self.assertEqual(self.parse(f'/blog/{slug}/').canonical, expected, slug)

    def test_bad_stored_canonical_falls_back_to_the_post_url(self):
        from kitchen.seo import absolute_blog_canonical

        post = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        expected = absolute_blog_canonical('emoji-kitchen-iphone')
        for stored in [
            'https://emojikitchenhub.com/emoji-kitchen-iphone/',
            'https://www.emojikitchenhub.com/emoji-kitchen-iphone',
            'http://emojikitchenhub.com/emoji-kitchen-iphone/',
            '/emoji-kitchen-iphone/',
            'https://emojikitchenhub.com/',
            'https://emojikitchenhub.com/blog/',
            'https://emojikitchenhub.com/blog/emoji-kitchen-gboard/',
            'https://example.com/blog/emoji-kitchen-iphone/',
        ]:
            post.canonical_url = stored
            post.save(update_fields=['canonical_url'])
            self.assertEqual(self.parse('/blog/emoji-kitchen-iphone/').canonical, expected, stored)

    def test_sitemap_blog_urls_equal_canonicals_and_return_200(self):
        from kitchen.seo import absolute_blog_canonical

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        blog_locs = [loc for loc in locs if urlparse(loc).path.startswith('/blog/') and urlparse(loc).path != '/blog/']
        self.assertEqual(len(blog_locs), len(POST_SLUGS))
        for loc in blog_locs:
            path = urlparse(loc).path
            slug = path.strip('/').split('/')[-1]
            expected = absolute_blog_canonical(slug)
            self.assertEqual(loc, expected, loc)
            self.assertEqual(urlparse(loc).scheme, 'https')
            self.assertEqual(urlparse(loc).netloc, 'emojikitchenhub.com')
            self.assertTrue(path.endswith('/'), loc)
            self.assertEqual(self.parse(path).canonical, loc)
            self.assertEqual(self.client.get(path).status_code, 200)


class FixBlogCanonicalsCommandTests(TestCase):
    def setUp(self):
        self.bad = BlogPost.objects.create(
            title='iPhone',
            slug='emoji-kitchen-iphone',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
            canonical_url='https://emojikitchenhub.com/emoji-kitchen-iphone/',
        )
        self.good = BlogPost.objects.create(
            title='Gboard',
            slug='emoji-kitchen-gboard',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
            canonical_url='https://emojikitchenhub.com/blog/emoji-kitchen-gboard/',
        )
        self.empty = BlogPost.objects.create(
            title='Samsung',
            slug='emoji-kitchen-samsung',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
            canonical_url='',
        )

    def test_dry_run_writes_nothing(self):
        before = {
            post.slug: (post.canonical_url, post.updated_at, post.pk)
            for post in BlogPost.objects.all()
        }
        out = io.StringIO()
        call_command('fix_blog_canonicals', stdout=out)
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
        self.assertIn('https://emojikitchenhub.com/emoji-kitchen-iphone/', output)
        self.assertIn('https://emojikitchenhub.com/blog/emoji-kitchen-iphone/', output)
        for post in BlogPost.objects.all():
            stored, updated, pk = before[post.slug]
            self.assertEqual(post.pk, pk)
            self.assertEqual(post.canonical_url, stored)
            self.assertEqual(post.updated_at, updated)

    def test_apply_corrects_only_the_bad_value_and_rerun_is_a_noop(self):
        first = io.StringIO()
        call_command('fix_blog_canonicals', '--apply', stdout=first)
        self.bad.refresh_from_db()
        self.good.refresh_from_db()
        self.empty.refresh_from_db()
        self.assertEqual(
            self.bad.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-iphone/',
        )
        self.assertEqual(
            self.good.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-gboard/',
        )
        self.assertEqual(self.empty.canonical_url, '')
        good_updated = self.good.updated_at
        empty_updated = self.empty.updated_at
        bad_updated = self.bad.updated_at
        bad_pk = self.bad.pk
        self.assertIn('Corrected 1', first.getvalue())

        again = io.StringIO()
        call_command('fix_blog_canonicals', '--apply', stdout=again)
        self.bad.refresh_from_db()
        self.good.refresh_from_db()
        self.empty.refresh_from_db()
        self.assertEqual(self.bad.pk, bad_pk)
        self.assertEqual(
            self.bad.canonical_url,
            'https://emojikitchenhub.com/blog/emoji-kitchen-iphone/',
        )
        self.assertEqual(self.bad.updated_at, bad_updated)
        self.assertEqual(self.good.updated_at, good_updated)
        self.assertEqual(self.empty.updated_at, empty_updated)
        self.assertEqual(self.empty.canonical_url, '')
        self.assertIn('No stored canonicals need fixing', again.getvalue())


class NotWorkingFooterLinkTests(TestCase):
    def setUp(self):
        BlogPost.objects.create(
            title='Emoji Kitchen Not Working? 9 Fixes to Try',
            slug='emoji-kitchen-not-working',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
        )

    def test_footer_link_appears_once_and_resolves(self):
        href = 'href="/blog/emoji-kitchen-not-working/"'
        for path in ('/', '/blog/', '/privacy/', '/emoji-maker/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.content.decode()
            footer = html[html.index('class="footer__nav"'):html.index('class="footer__legal"')]
            self.assertEqual(footer.count(href), 1, path)
            self.assertIn('Emoji Kitchen not working?', footer)
        # Homepage: the footer link plus the devices-section guide link.
        home = self.client.get('/').content.decode()
        self.assertEqual(home.count(href), 2)
        target = self.client.get('/blog/emoji-kitchen-not-working/')
        self.assertEqual(target.status_code, 200)


# ── Google Analytics 4 ────────────────────────────────────────────────────────

GTAG_SRC = 'https://www.googletagmanager.com/gtag/js?id=G-3DKYS4C5DL'
GTAG_CONFIG = "gtag('config', 'G-3DKYS4C5DL')"
ADSENSE_SCRIPT = 'pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3200425003686406'
ADSENSE_META = 'name="google-adsense-account" content="ca-pub-3200425003686406"'


class GoogleAnalyticsTests(TestCase):
    """The gtag snippet is rendered once from base.html when the measurement ID is set."""

    def setUp(self):
        BlogPost.objects.create(
            title='GA4 Test Post',
            slug='ga4-test-post',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
        )

    def _assert_gtag_once(self, html):
        self.assertEqual(html.count(GTAG_SRC), 1)
        self.assertEqual(html.count(GTAG_CONFIG), 1)
        self.assertEqual(html.count('www.googletagmanager.com/gtag/js'), 1)
        self.assertEqual(html.count("gtag('config'"), 1)
        self.assertIn(ADSENSE_META, html)

    def test_gtag_appears_once_on_home_combo_blog_legal_and_404(self):
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        home_html = home.content.decode()
        self._assert_gtag_once(home_html)
        self.assertIn(ADSENSE_SCRIPT, home_html)

        combo = self.client.get('/emoji-combos/love/')
        self.assertEqual(combo.status_code, 200)
        combo_html = combo.content.decode()
        self._assert_gtag_once(combo_html)
        self.assertNotIn('adsbygoogle', combo_html)

        blog = self.client.get('/blog/ga4-test-post/')
        self.assertEqual(blog.status_code, 200)
        blog_html = blog.content.decode()
        self._assert_gtag_once(blog_html)
        self.assertNotIn('adsbygoogle', blog_html)

        legal = self.client.get('/privacy/')
        self.assertEqual(legal.status_code, 200)
        legal_html = legal.content.decode()
        self._assert_gtag_once(legal_html)
        self.assertNotIn('adsbygoogle', legal_html)

        with override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1']):
            missing = self.client.get('/does-not-exist-for-ga4-404/')
        self.assertEqual(missing.status_code, 404)
        missing_html = missing.content.decode()
        self._assert_gtag_once(missing_html)
        self.assertNotIn('adsbygoogle', missing_html)

    @override_settings(GA_MEASUREMENT_ID='')
    def test_empty_measurement_id_omits_gtag(self):
        for path, status in [('/', 200), ('/emoji-combos/love/', 200), ('/blog/ga4-test-post/', 200), ('/privacy/', 200)]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, status, path)
            html = response.content.decode()
            self.assertNotIn('googletagmanager', html, path)
            self.assertNotIn('gtag(', html, path)
            self.assertIn(ADSENSE_META, html, path)

        home = self.client.get('/').content.decode()
        self.assertIn(ADSENSE_SCRIPT, home)

        with override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'], GA_MEASUREMENT_ID=''):
            missing = self.client.get('/does-not-exist-for-ga4-404/')
        self.assertEqual(missing.status_code, 404)
        html = missing.content.decode()
        self.assertNotIn('googletagmanager', html)
        self.assertNotIn('gtag(', html)
        self.assertIn(ADSENSE_META, html)


# ── IndexNow (key file, post-save ping, management command) ───────────────────

INDEXNOW_TEST_KEY = 'c784779f391c5dcf67516cb8179ea325'



def _assert_cover_swap_versions_and_pings(self, *, command, cover_filename, image_bytes):
    """Simulate an older unversioned cover, then assert the seed swaps it once."""
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from kitchen import indexnow
    from kitchen.blog_seed_utils import cover_versioned_filename
    from kitchen.models import BlogPost

    call_command(command, '--apply', stdout=io.StringIO())
    desired = cover_versioned_filename(cover_filename, image_bytes)
    expected_path = f'blog/featured/{desired}'

    post = BlogPost.objects.get(slug=self.SLUG)
    old_bytes = b'\x89PNG\r\n\x1a\n' + b'old-cover-bytes-not-the-fixture'
    post.featured_image.save(cover_filename, ContentFile(old_bytes), save=False)
    post.og_image.save(cover_filename, ContentFile(old_bytes), save=True)
    post = BlogPost.objects.get(slug=self.SLUG)
    old_featured = post.featured_image.name
    old_og = post.og_image.name
    self.assertTrue(old_featured.endswith(cover_filename))
    self.assertTrue(default_storage.exists(old_featured))
    self.assertTrue(default_storage.exists(old_og))
    self.assertTrue(post.og_image)
    updated_before = post.updated_at

    with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
        with mock.patch.object(indexnow.requests, 'post') as posted:
            with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                    with self.captureOnCommitCallbacks(execute=True):
                        call_command(command, '--apply', stdout=io.StringIO())
    submitted = [url for call in submit.call_args_list for url in call.args[0]]
    self.assertEqual(submitted, [self.CANONICAL])
    posted.assert_called()

    post = BlogPost.objects.get(slug=self.SLUG)
    self.assertEqual(post.featured_image.name, expected_path)
    self.assertFalse(post.og_image)
    self.assertEqual(post.og_image_display.name, expected_path)
    self.assertFalse(default_storage.exists(old_featured))
    self.assertFalse(default_storage.exists(old_og))
    post.featured_image.open('rb')
    try:
        self.assertEqual(post.featured_image.read(), image_bytes)
    finally:
        post.featured_image.close()
    self.assertNotEqual(post.updated_at, updated_before)

    html = self.client.get(f'/blog/{self.SLUG}/').content.decode()
    og = re.search(r'property="og:image" content="([^"]+)"', html)
    tw = re.search(r'name="twitter:image" content="([^"]+)"', html)
    self.assertIsNotNone(og)
    self.assertIsNotNone(tw)
    self.assertIn(desired, og.group(1))
    self.assertIn(desired, tw.group(1))
    blocks = [
        json.loads(match.group(1))
        for match in re.finditer(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        )
    ]
    blog = next(b for b in blocks if b.get('@type') == 'BlogPosting')
    image = blog['image']
    if isinstance(image, list):
        image = image[0]
    if isinstance(image, dict):
        image = image.get('url') or image.get('@id') or ''
    self.assertIn(desired, image)
    self.assertNotIn('/' + cover_filename, og.group(1))
    self.assertNotIn('/' + cover_filename, tw.group(1))
    self.assertNotIn('/' + cover_filename, image)

    first_updated = post.updated_at
    first_name = post.featured_image.name
    with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit2:
        with mock.patch.object(indexnow.requests, 'post') as posted2:
            with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                    with self.captureOnCommitCallbacks(execute=True):
                        call_command(command, '--apply', stdout=io.StringIO())
    self.assertEqual(submit2.call_count, 0)
    posted2.assert_not_called()
    again = BlogPost.objects.get(slug=self.SLUG)
    self.assertEqual(again.updated_at, first_updated)
    self.assertEqual(again.featured_image.name, first_name)


def _run_thread_inline(target=None, args=(), kwargs=None, daemon=None):
    """Stand-in for threading.Thread that runs the target immediately."""

    class _Immediate:
        def start(self):
            if target:
                target(*(args or ()), **(kwargs or {}))

        def join(self, timeout=None):
            return None

    return _Immediate()


class IndexNowTests(TestCase):
    def _key_path(self, key=INDEXNOW_TEST_KEY):
        return f'/{key}.txt'

    def test_key_file_returns_the_configured_key(self):
        response = self.client.get(self._key_path())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))
        self.assertEqual(response.content.decode(), INDEXNOW_TEST_KEY)

    def test_wrong_key_and_other_txt_paths_are_404(self):
        self.assertEqual(self.client.get('/not-the-indexnow-key.txt').status_code, 404)
        self.assertEqual(self.client.get('/random.txt').status_code, 404)

    def test_robots_and_ads_txt_are_unchanged(self):
        robots = self.client.get('/robots.txt')
        ads = self.client.get('/ads.txt')
        self.assertEqual(robots.status_code, 200)
        self.assertEqual(ads.status_code, 200)
        self.assertIn('Sitemap:', robots.content.decode())
        self.assertIn('google.com, pub-3200425003686406', ads.content.decode())

    def _save_post(self, status, slug='indexnow-ping-post'):
        from kitchen.models import BlogPost
        return BlogPost.objects.create(
            title='IndexNow Ping Post',
            slug=slug,
            content='<p>Body</p>',
            status=status,
        )

    def _capture_ping(self, status, slug='indexnow-ping-post'):
        from kitchen import indexnow
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as post:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            post_obj = self._save_post(status, slug=slug)
        return post_obj, submit, post

    def test_saving_a_published_post_pings_indexnow_with_the_right_payload(self):
        post_obj, submit, post = self._capture_ping(BlogPost.STATUS_PUBLISHED)
        expected_url = f'https://emojikitchenhub.com{post_obj.get_absolute_url()}'
        submit.assert_called_once_with([expected_url])
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://api.indexnow.org/indexnow')
        payload = kwargs['json']
        self.assertEqual(payload['host'], 'emojikitchenhub.com')
        self.assertEqual(payload['key'], INDEXNOW_TEST_KEY)
        self.assertEqual(
            payload['keyLocation'],
            f'https://emojikitchenhub.com/{INDEXNOW_TEST_KEY}.txt',
        )
        self.assertEqual(payload['urlList'], [expected_url])
        self.assertEqual(kwargs['timeout'], 5)

    def test_saving_a_draft_does_not_ping(self):
        _post_obj, submit, post = self._capture_ping(BlogPost.STATUS_DRAFT, slug='indexnow-draft')
        submit.assert_not_called()
        post.assert_not_called()

    def test_a_ping_exception_does_not_break_the_save(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow.requests, 'post', side_effect=RuntimeError('network down')):
            with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                    with self.assertLogs('kitchen.indexnow', level='ERROR'):
                        with self.captureOnCommitCallbacks(execute=True):
                            post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-error')
        post_obj.refresh_from_db()
        self.assertEqual(post_obj.slug, 'indexnow-error')
        self.assertEqual(post_obj.status, BlogPost.STATUS_PUBLISHED)

    def test_submit_urls_is_skipped_by_default_during_tests(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow.requests, 'post') as post:
            result = indexnow.submit_urls(['https://emojikitchenhub.com/'])
        self.assertIsNone(result)
        post.assert_not_called()

    def test_command_submits_a_url(self):
        with mock.patch('kitchen.management.commands.indexnow_submit.submit_urls', return_value={'ok': True}) as submit:
            output = io.StringIO()
            call_command(
                'indexnow_submit',
                'https://emojikitchenhub.com/blog/emoji-kitchen-discord/',
                stdout=output,
            )
        submit.assert_called_once_with(
            ['https://emojikitchenhub.com/blog/emoji-kitchen-discord/'],
            force=True,
        )
        self.assertIn('Submitted 1 URL(s)', output.getvalue())

    def test_command_sitemap_collects_urls_and_dry_run_does_not_send(self):
        from kitchen import indexnow
        BlogPost.objects.create(
            title='Visible For Sitemap',
            slug='visible-for-sitemap',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
        )
        urls = indexnow.collect_sitemap_urls()
        self.assertGreater(len(urls), 0)
        self.assertIn('https://emojikitchenhub.com/', urls)
        self.assertIn('https://emojikitchenhub.com/blog/visible-for-sitemap/', urls)

        with mock.patch('kitchen.management.commands.indexnow_submit.submit_urls') as submit:
            output = io.StringIO()
            call_command('indexnow_submit', '--sitemap', '--dry-run', stdout=output)
        submit.assert_not_called()
        text = output.getvalue()
        self.assertIn('https://emojikitchenhub.com/', text)
        self.assertIn(f'Would submit {len(urls)} URL(s)', text)

        with mock.patch('kitchen.management.commands.indexnow_submit.submit_urls', return_value={'ok': True}) as submit:
            call_command('indexnow_submit', '--sitemap', stdout=io.StringIO())
        submit.assert_called()
        sent = []
        for args, kwargs in submit.call_args_list:
            sent.extend(args[0])
        self.assertEqual(len(sent), len(urls))
        self.assertGreater(len(sent), 0)
        self.assertEqual(kwargs.get('force'), True)

    def _capture_save(self, callback):
        from kitchen import indexnow
        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as post:
                with mock.patch.object(indexnow.threading, 'Thread', side_effect=_run_thread_inline):
                    with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                        with self.captureOnCommitCallbacks(execute=True):
                            result = callback()
        return result, submit, post

    def test_noop_resave_of_published_post_does_not_ping(self):
        post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-noop')
        _, submit, post = self._capture_save(post_obj.save)
        submit.assert_not_called()
        post.assert_not_called()

    def test_published_unchanged_resave_sends_no_ping(self):
        post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-unchanged')
        post_obj.refresh_from_db()
        _, submit, post = self._capture_save(post_obj.save)
        submit.assert_not_called()
        post.assert_not_called()

    def test_changing_title_of_published_post_sends_one_ping(self):
        post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-title')

        def _update():
            post_obj.title = 'Updated IndexNow Title'
            post_obj.save()
            return post_obj

        _, submit, post = self._capture_save(_update)
        expected_url = f'https://emojikitchenhub.com{post_obj.get_absolute_url()}'
        submit.assert_called_once_with([expected_url])
        post.assert_called_once()

    def test_changing_content_of_published_post_sends_one_ping(self):
        post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-content')

        def _update():
            post_obj.content = '<p>Updated body</p>'
            post_obj.save()
            return post_obj

        _, submit, post = self._capture_save(_update)
        expected_url = f'https://emojikitchenhub.com{post_obj.get_absolute_url()}'
        submit.assert_called_once_with([expected_url])
        post.assert_called_once()

    def test_draft_to_published_sends_one_ping(self):
        post_obj = self._save_post(BlogPost.STATUS_DRAFT, slug='indexnow-publish')

        def _update():
            post_obj.status = BlogPost.STATUS_PUBLISHED
            post_obj.save()
            return post_obj

        _, submit, post = self._capture_save(_update)
        expected_url = f'https://emojikitchenhub.com{post_obj.get_absolute_url()}'
        submit.assert_called_once_with([expected_url])
        post.assert_called_once()

    def test_slug_change_pings_only_the_new_url(self):
        post_obj = self._save_post(BlogPost.STATUS_PUBLISHED, slug='indexnow-old-slug')

        def _update():
            post_obj.slug = 'indexnow-new-slug'
            post_obj.save()
            return post_obj

        _, submit, post = self._capture_save(_update)
        submit.assert_called_once_with(['https://emojikitchenhub.com/blog/indexnow-new-slug/'])
        post.assert_called_once()

    def test_submit_urls_ignores_foreign_host_urls(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow.requests, 'post') as post:
            with self.assertLogs('kitchen.indexnow', level='WARNING'):
                result = indexnow.submit_urls(
                    [
                        'https://example.com/x',
                        'https://www.emojikitchenhub.com/ok/',
                        'http://emojikitchenhub.com/also/',
                    ],
                    force=True,
                )
        post.assert_called_once()
        payload = post.call_args.kwargs['json']
        self.assertEqual(
            payload['urlList'],
            [
                'https://emojikitchenhub.com/ok/',
                'https://emojikitchenhub.com/also/',
            ],
        )
        self.assertEqual(result['urlList'], payload['urlList'])

    def test_submit_urls_ignores_an_all_foreign_list(self):
        from kitchen import indexnow
        with mock.patch.object(indexnow.requests, 'post') as post:
            with self.assertLogs('kitchen.indexnow', level='WARNING'):
                result = indexnow.submit_urls(['https://example.com/x'], force=True)
        self.assertIsNone(result)
        post.assert_not_called()

    def test_command_rejects_a_foreign_host(self):
        with mock.patch('kitchen.management.commands.indexnow_submit.submit_urls') as submit:
            stderr = io.StringIO()
            with self.assertLogs('kitchen.indexnow', level='WARNING'):
                with self.assertRaises(CommandError) as caught:
                    call_command(
                        'indexnow_submit',
                        'https://example.com/x',
                        stdout=io.StringIO(),
                        stderr=stderr,
                    )
        submit.assert_not_called()
        self.assertIn('No valid emojikitchenhub.com URLs', str(caught.exception))
        self.assertIn('example.com', stderr.getvalue())

    def test_command_accepts_apex_and_www_urls(self):
        with mock.patch('kitchen.management.commands.indexnow_submit.submit_urls', return_value={'ok': True}) as submit:
            output = io.StringIO()
            call_command(
                'indexnow_submit',
                'https://emojikitchenhub.com/blog/foo/',
                'https://www.emojikitchenhub.com/blog/bar/',
                stdout=output,
            )
        submit.assert_called_once_with(
            [
                'https://emojikitchenhub.com/blog/foo/',
                'https://emojikitchenhub.com/blog/bar/',
            ],
            force=True,
        )
        self.assertIn('Submitted 2 URL(s)', output.getvalue())


# ── Meta descriptions lengthened for search snippets ──────────────────────────

LENGTHENED_META_PAGES = [
    '/emoji-combos/love/',
    '/emoji-combos/cute/',
    '/emoji-combos/aesthetic/',
    '/emoji-combos/funny/',
    '/emoji-combos/pink/',
    '/emoji-keyboard-for-pc/',
    '/about-us/',
    '/contact/',
]


class LengthenedMetaDescriptionTests(PageTestCase):
    def test_changed_pages_have_meta_descriptions_between_120_and_160(self):
        for path in LENGTHENED_META_PAGES:
            page = self.parse(path)
            description = page.meta['description']
            length = len(description)
            self.assertTrue(
                120 <= length <= 160,
                f'{path} description is {length} characters: {description}',
            )
            self.assertEqual(page.meta.get('og:description'), description, path)
            self.assertEqual(page.meta.get('twitter:description'), description, path)


# ── Emoji combo CTR rewrite and the data-driven category pages ───────────────

import html as _html_lib
import itertools

from . import combo_counts
from .combo_pages import COMBO_PAGES
from .seo import CANONICAL_HOST

COMBO_SITE = f'https://{CANONICAL_HOST}'
EXISTING_COMBO_PAGES = ['/emoji-combos/', READY_MADE] + COMBOS
EXISTING_COMBO_TEMPLATES = {
    READY_MADE: 'ready_made_emoji_combo.html',
    '/emoji-combos/love/': 'emoji_combos_love.html',
    '/emoji-combos/cute/': 'emoji_combos_cute.html',
    '/emoji-combos/aesthetic/': 'emoji_combos_aesthetic.html',
    '/emoji-combos/funny/': 'emoji_combos_funny.html',
    '/emoji-combos/pink/': 'emoji_combos_pink.html',
}
MIN_SETS_PER_NEW_PAGE = 40
ADSENSE_HOME_SLOT = '1461359629'


def _words(text):
    return re.findall(r"[a-z']+", _html_lib.unescape(re.sub(r'<[^>]+>', ' ', text)).lower())


def _shingles(text, size=3):
    words = _words(text)
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def _page_copy(page):
    """All the prose of a category page's data (no emoji sets, no shared boilerplate)."""
    parts = [*page['intro'], page['mashup_note'], page['siblings_cta']]
    for heading, paragraphs in page['sections']:
        parts += [heading, *paragraphs]
    for question, answer in page['faqs']:
        parts += [question, answer]
    return '\n'.join(parts)


def _visible_text(html):
    return re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.DOTALL)


def _emoji_units(emoji_set):
    """The emoji in a set as a sorted tuple, so reordered sets compare equal.

    Variation selectors are ignored, a zero-width joiner glues the next character to the
    emoji before it (family and couple sequences), and skin-tone modifiers and flag pairs stay together.
    """
    units = []
    for char in emoji_set:
        code = ord(char)
        if char == '\ufe0f':
            continue
        if units and (units[-1].endswith('\u200d') or char == '\u200d' or 0x1F3FB <= code <= 0x1F3FF):
            units[-1] += char
        elif units and 0x1F1E6 <= code <= 0x1F1FF and len(units[-1]) == 1 and 0x1F1E6 <= ord(units[-1]) <= 0x1F1FF:
            units[-1] += char
        else:
            units.append(char)
    return tuple(sorted(units))


class ComboCategoryDataTests(SimpleTestCase):
    """The six pages in kitchen/combo_pages.py have real, distinct substance."""

    def test_the_six_pages_exist(self):
        self.assertEqual(sorted(COMBO_PAGES), sorted(p.rsplit('/', 2)[-2] for p in MORE_COMBOS))

    def test_each_page_has_enough_unique_sets(self):
        for slug, page in COMBO_PAGES.items():
            sets = [c[2] for c in page['combos']]
            self.assertGreaterEqual(len(sets), MIN_SETS_PER_NEW_PAGE, slug)
            self.assertEqual(len(sets), len(set(sets)), f'{slug} repeats a set')
            labels = [c[1] for c in page['combos']]
            self.assertEqual(len(labels), len(set(labels)), f'{slug} repeats a label')
            filters = {key for key, _label in page['filters']}
            self.assertTrue({c[0] for c in page['combos']} <= filters, slug)
            for key in filters:
                self.assertGreaterEqual(len([c for c in page['combos'] if c[0] == key]), 3, f'{slug}/{key} is thin')

    def test_sets_are_emoji_only_and_not_on_any_other_page(self):
        seen = {}
        existing = set()
        for name in EXISTING_COMBO_TEMPLATES.values():
            existing |= set(combo_counts.template_sets(name))
        for slug, page in COMBO_PAGES.items():
            for _cat, _label, emoji_set in page['combos']:
                self.assertFalse(emoji_set.isascii(), (slug, emoji_set))
                self.assertFalse(any(ch.isascii() and ch.isalnum() for ch in emoji_set), (slug, emoji_set))
                self.assertFalse(emoji_set.startswith('\ufe0f') or emoji_set.startswith('\u200d'), (slug, emoji_set))
                self.assertNotIn(emoji_set, existing, f'{slug}: {emoji_set} is already on an older combo page')
                self.assertNotIn(emoji_set, seen, f'{slug}: {emoji_set} is also on {seen.get(emoji_set)}')
                seen[emoji_set] = slug

    def test_emoji_units_ignore_order_and_variation_selectors(self):
        self.assertEqual(_emoji_units('\U0001F9C1\U0001F380\U0001F497'), _emoji_units('\U0001F380\U0001F9C1\U0001F497'))
        self.assertEqual(_emoji_units('\U0001F56F\ufe0f\U0001F319'), _emoji_units('\U0001F319\U0001F56F'))
        self.assertEqual(len(_emoji_units('\U0001F468\u200d\U0001F469\u200d\U0001F467\U0001F384')), 2)
        self.assertNotEqual(_emoji_units('\U0001F384\U0001F381'), _emoji_units('\U0001F384\U0001F384'))

    def test_no_new_set_is_a_reordering_of_a_set_on_any_page(self):
        # A set that only reorders the emoji of another page's set is a near-duplicate.
        # Old-page against old-page overlaps are out of scope and not checked here.
        seen = {}
        for name in EXISTING_COMBO_TEMPLATES.values():
            for emoji_set in combo_counts.template_sets(name):
                seen.setdefault(_emoji_units(emoji_set), f'{name}: {emoji_set}')
        for slug, page in COMBO_PAGES.items():
            for _cat, label, emoji_set in page['combos']:
                key = _emoji_units(emoji_set)
                self.assertFalse(key in seen, f'{slug} "{label}" {emoji_set} reorders {seen.get(key)}')
                seen[key] = f'{slug}: {emoji_set}'

    def test_editorial_substance(self):
        for slug, page in COMBO_PAGES.items():
            self.assertEqual(len(page['faqs']), 5, slug)
            self.assertGreaterEqual(len(page['sections']), 2, slug)
            self.assertEqual(len(page['intro']), 2, slug)
            self.assertEqual(len(page['mashups']), 6, slug)
            self.assertGreaterEqual(len(_words(_page_copy(page))), 350, f'{slug} copy is thin')

    def test_every_mashup_pair_exists_in_the_dataset(self):
        for slug, page in COMBO_PAGES.items():
            for first, second in page['mashups']:
                self.assertTrue(views.combo_image_url(first, second), f'{slug}: {first} + {second} has no Emoji Kitchen pair')
            self.assertEqual(len(views.mashup_links(page['mashups'])), 6, slug)

    def test_no_number_is_written_into_the_copy(self):
        for slug, page in COMBO_PAGES.items():
            for field in ('title', 'meta', 'h1', 'badge'):
                self.assertIsNone(re.search(r'\d', page[field]), f'{slug} {field}: {page[field]}')
            for paragraph in page['intro']:
                self.assertIsNone(re.search(r'\d', paragraph), f'{slug}: {paragraph}')

    def test_title_and_meta_lengths(self):
        for slug, page in COMBO_PAGES.items():
            self.assertLessEqual(len(page['title']), 60, slug)
            self.assertGreaterEqual(len(page['title']), 30, slug)
            self.assertTrue(140 <= len(page['meta']) <= 155, f'{slug} meta is {len(page["meta"])}')

    def test_copy_is_distinct_between_the_new_pages(self):
        shingles = {slug: _shingles(_page_copy(page)) for slug, page in COMBO_PAGES.items()}
        for first, second in itertools.combinations(shingles, 2):
            score = len(shingles[first] & shingles[second]) / len(shingles[first] | shingles[second])
            self.assertLess(score, 0.15, f'{first} and {second} copy overlap ({score:.3f})')

    def test_every_page_has_its_own_title_meta_and_h1(self):
        for field in ('title', 'meta', 'h1'):
            values = [page[field] for page in COMBO_PAGES.values()]
            self.assertEqual(len(values), len(set(values)), field)


class ComboCountsTests(SimpleTestCase):
    def test_floor_hundreds(self):
        self.assertEqual([combo_counts.floor_hundreds(n) for n in (0, 99, 100, 138, 199, 200, 345)],
                         [0, 0, 100, 100, 100, 200, 300])

    def test_ready_made_title_and_meta_use_a_number_only_when_the_count_supports_it(self):
        title, meta = views.ready_made_emoji_combo_copy(138)
        self.assertTrue(title.startswith('Ready Made Emoji Combo: 100+ Sets'))
        self.assertIn('Tap to copy 100+ emoji combos', meta)
        title, meta = views.ready_made_emoji_combo_copy(99)
        self.assertIsNone(re.search(r'\d', title + meta))
        self.assertTrue(title.startswith('Ready Made Emoji Combo: Sets to Copy & Paste'))
        self.assertTrue(views.ready_made_emoji_combo_copy(250)[0].startswith('Ready Made Emoji Combo: 200+ '))
        for count in (0, 99, 100, 250):
            title, meta = views.ready_made_emoji_combo_copy(count)
            self.assertLessEqual(len(title), 60, count)
            self.assertTrue(140 <= len(meta) <= 155, (count, len(meta)))

    def test_older_pages_ship_the_counts_the_review_found(self):
        # Entries listed in each COMBOS array. Aesthetic, funny, pink, love and the hub repeat a few sets,
        # so the number shown to visitors is the count of distinct sets.
        listed = {name: len(combo_counts.template_sets(name)) for name in EXISTING_COMBO_TEMPLATES.values()}
        self.assertEqual(listed['emoji_combos_cute.html'], 185)
        self.assertEqual(listed['emoji_combos_aesthetic.html'], 194)
        self.assertEqual(listed['emoji_combos_funny.html'], 149)
        self.assertGreaterEqual(combo_counts.distinct_set_count('ready_made_emoji_combo.html'), 100)


class ComboCategoryPageTests(PageTestCase):
    def slug(self, path):
        return path.rsplit('/', 2)[-2]

    def test_each_new_page_is_a_complete_page(self):
        for path in MORE_COMBOS:
            page_data = COMBO_PAGES[self.slug(path)]
            html = self.fetch(path)
            page = self.parse(path)
            self.assertEqual(len(page.h1), 1, path)
            self.assertEqual(_clean(page.h1[0]), page_data['h1'], path)
            self.assertEqual(_clean(page.title), page_data['title'], path)
            self.assertEqual(page.meta['description'], page_data['meta'], path)
            self.assertEqual(page.canonical, COMBO_SITE + path, path)
            self.assertEqual(page.meta['og:url'], COMBO_SITE + path, path)
            self.assertEqual(page.meta['og:title'], page_data['title'], path)
            self.assertEqual(page.meta['og:description'], page_data['meta'], path)
            self.assertNotIn('noindex', page.meta.get('robots') or '', path)
            faq_blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(faq_blocks), 1, path)
            shown = len(re.findall(r'<details class="faq-item[ "]', html))
            self.assertEqual(shown, 5, path)
            self.assertEqual(len(faq_blocks[0]['mainEntity']), shown, path)
            links = self.body_links(path)
            for needed in ('/emoji-combos/', '/', '/emoji-maker/', '/blog/'):
                self.assertIn(needed, links, f'{path} does not link to {needed}')
            siblings = [t for t in links if t.startswith('/emoji-combos/') and t not in ('/emoji-combos/', path)]
            self.assertGreaterEqual(len(siblings), 2, path)
            self.assertNotIn(path, links, f'{path} links to itself')
            for target, anchors in links.items():
                for anchor in anchors:
                    self.assertNotIn(anchor, WEAK_ANCHORS, f'{path} -> {target}')

    def test_title_meta_and_server_rendered_sets(self):
        for path in MORE_COMBOS:
            data = COMBO_PAGES[self.slug(path)]
            html = self.fetch(path)
            cards = re.findall(r'<div class="combo-card">', _visible_text(html))
            self.assertEqual(len(cards), 12, path)   # first 12 sets exist before any JS runs
            for _cat, _label, emoji_set in data['combos'][:12]:
                self.assertIn(f'data-combo="{emoji_set}"', html, path)

    def test_the_count_shown_is_the_count_in_the_data(self):
        for path in MORE_COMBOS:
            data = COMBO_PAGES[self.slug(path)]
            html = self.fetch(path)
            distinct = len({c[2] for c in data['combos']})
            self.assertIn(f'<span id="combo-count">{distinct}</span> sets', html, path)
            payload = re.search(r'<script id="combos-data" type="application/json">(.*?)</script>', html, re.DOTALL)
            rows = json.loads(payload.group(1))
            self.assertEqual(len(rows), len(data['combos']), path)
            self.assertEqual({r['emoji'] for r in rows}, {c[2] for c in data['combos']}, path)
            self.assertIn("new Set(COMBOS.map(c => c.emoji)).size", html, path)
            # no number is written into the title, meta, H1 or intro of the rendered page
            page = self.parse(path)
            self.assertIsNone(re.search(r'\d', _clean(page.title) + page.meta['description'] + page.h1[0]), path)

    def test_mashup_block_links_resolve_to_the_mixer_with_supported_pairs(self):
        for path in MORE_COMBOS:
            data = COMBO_PAGES[self.slug(path)]
            html = self.fetch(path)
            self.assertIn('<h2>Emoji Kitchen Mashups to Try</h2>', html, path)
            self.assertIn('unofficial fan site, not made or endorsed by Google', html, path)
            mixer = [h for h, _t, _a in self.parse(path).body_links if h.startswith('/?emoji1=')]
            self.assertEqual(len(mixer), 6, path)
            for href in mixer:
                query = dict(part.split('=') for part in urlparse(href).query.split('&'))
                from urllib.parse import unquote
                self.assertTrue(views.combo_image_url(unquote(query['emoji1']), unquote(query['emoji2'])), href)
                self.assertEqual(self.client.get(href.split('#')[0]).status_code, 200)
            self.assertNotIn('gstatic.com/android/keyboard/emojikitchen', html, 'no Google sticker images are embedded')

    def test_ready_made_page_links_to_every_new_page_and_has_the_new_copy(self):
        html = self.fetch(READY_MADE)
        links = self.body_links(READY_MADE)
        for path in MORE_COMBOS:
            self.assertIn(path, links)
        for theme in ['Birthday', 'Friendship', 'Sad', 'Dark', 'Christmas']:
            self.assertIn(f'<h3>{theme} Emoji Combos</h3>', html)
        self.assertIn('<h3>Emoji Combos for Bio</h3>', html)
        self.assertIn('<h2>Want One Image Instead of a Row of Emojis?</h2>', html)
        self.assertLess(html.index('Want One Image Instead'), html.index('Plain Combinations vs. Emoji Kitchen Mashups'))
        self.assertEqual(self.client.get('/emoji-combos/unknown/').status_code, 404)

    def test_ready_made_page_is_titled_ready_made_emoji_combo(self):
        page = self.parse(READY_MADE)
        self.assertEqual(page.h1, ['Ready Made Emoji Combo'])
        self.assertIn('Ready Made Emoji Combo', _clean(page.title))
        self.assertEqual(page.canonical, COMBO_SITE + READY_MADE)

    def test_hub_is_a_short_page_that_links_to_ready_made_and_every_category(self):
        html = self.fetch('/emoji-combos/')
        page = self.parse('/emoji-combos/')
        self.assertEqual(len(page.h1), 1)
        self.assertEqual(_clean(page.h1[0]), 'Emoji Combos')
        links = self.body_links('/emoji-combos/')
        for path in [READY_MADE] + COMBOS + MORE_COMBOS:
            self.assertIn(path, links, f'hub does not link to {path}')
        self.assertEqual(len(re.findall(r'<a href="/emoji-combos/[a-z]+/" class="feature-card', html)),
                         len(COMBOS) + len(MORE_COMBOS))
        self.assertEqual(page.canonical, COMBO_SITE + '/emoji-combos/')
        self.assertIsNone(re.search(r'\d', _clean(page.title) + page.meta['description'] + page.h1[0]))

    def test_hub_no_longer_carries_the_content_that_moved_to_ready_made(self):
        html = self.fetch('/emoji-combos/')
        for gone in ('id="combo-tool"', 'id="combo-grid"', 'id="combo-search"', 'const COMBOS', 'faq-item',
                     'Popular Emoji Combos to Copy and Paste', 'How to Copy and Use a Combination',
                     'Why Emoji May Look Different After Pasting', 'Plain Combinations vs. Emoji Kitchen Mashups',
                     'Frequently Asked Questions', 'Pick a Combo That Fits Your Message'):
            self.assertNotIn(gone, html)
        self.assertFalse([b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage'])

    def test_ready_made_page_keeps_all_the_content_the_hub_used_to_have(self):
        html = self.fetch(READY_MADE)
        for kept in ('id="combo-tool"', 'id="combo-grid"', 'id="combo-search"', 'const COMBOS',
                     'Popular Emoji Combos to Copy and Paste', 'How to Copy and Use a Combination',
                     'Why Emoji May Look Different After Pasting', 'Plain Combinations vs. Emoji Kitchen Mashups',
                     'When and How to Use Emoji Combos', 'Frequently Asked Questions',
                     'Pick a Combo That Fits Your Message'):
            self.assertIn(kept, html)
        self.assertEqual(len(re.findall(r'<details class="faq-item[ "]', html)), len(views.EMOJI_COMBOS_PAGE_FAQS))

    def test_home_links_to_birthday_and_bio_and_still_links_to_the_five_combo_pages(self):
        links = self.body_links('/')
        for path in COMBOS + ['/emoji-combos/birthday/', '/emoji-combos/bio/']:
            self.assertIn(path, links)
        self.assertIn('emoji combos to copy and paste', links['/emoji-combos/'])

    def test_every_number_in_the_older_pages_matches_their_data(self):
        for path, template in EXISTING_COMBO_TEMPLATES.items():
            html = self.fetch(path)
            visible = _visible_text(html)
            distinct = combo_counts.distinct_set_count(template)
            self.assertIn(f'<span id="combo-count">{distinct}</span> sets', html, path)
            self.assertEqual(html.count('id="combo-count"'), 1, path)
            self.assertIn("new Set(COMBOS.map(c => c.emoji)).size", html, path)
            # the false counts the review found must be gone
            for stale in ('200 Cute Emoji', '200+ Aesthetic', '150+ Funny'):
                self.assertNotIn(stale, visible, path)
            page = self.parse(path)
            claims = re.findall(r'(\d[\d,]*)\+?', _clean(page.title) + ' ' + page.meta['description'] + ' ' + page.h1[0])
            for claim in claims:
                self.assertEqual(path, READY_MADE, f'{path} writes the number {claim} into its title/meta/H1')

    def test_ready_made_hundred_plus_claim_is_true(self):
        page = self.parse(READY_MADE)
        distinct = combo_counts.distinct_set_count('ready_made_emoji_combo.html')
        floor = combo_counts.floor_hundreds(distinct)
        self.assertGreaterEqual(floor, 100)
        self.assertTrue(_clean(page.title).startswith(f'Ready Made Emoji Combo: {floor}+ '), page.title)
        self.assertIn(f'copy {floor}+ emoji combos', page.meta['description'])
        self.assertEqual(re.findall(r'\d+', _clean(page.title)), [str(floor)])
        self.assertEqual(re.findall(r'\d+', page.meta['description']), [str(floor)])
        self.assertEqual(re.findall(r'\d+', page.h1[0]), [])

    def test_titles_and_metas_have_sensible_lengths_on_every_combo_page(self):
        for path in EXISTING_COMBO_PAGES + MORE_COMBOS:
            page = self.parse(path)
            title = _clean(page.title)
            meta = page.meta['description']
            self.assertTrue(30 <= len(title) <= 60, f'{path} title is {len(title)}: {title}')
            self.assertTrue(140 <= len(meta) <= 155, f'{path} meta is {len(meta)}: {meta}')
            self.assertEqual(page.meta['og:title'], title, path)
            self.assertEqual(page.meta['og:description'], meta, path)
            self.assertEqual(page.meta['twitter:description'], meta, path)

    def test_new_copy_is_not_a_copy_of_the_older_pages(self):
        older = {path: _shingles(_visible_text(self.fetch(path))) for path in EXISTING_COMBO_PAGES}
        for slug, data in COMBO_PAGES.items():
            mine = _shingles(_page_copy(data))
            for path, theirs in older.items():
                shared = len(mine & theirs) / len(mine)
                self.assertLess(shared, 0.15, f'{slug} copy shares {shared:.3f} of its phrases with {path}')

    @override_settings(ALLOWED_HOSTS=['testserver', 'emojikitchenhub.com', 'www.emojikitchenhub.com'])
    def test_canonicals_are_pinned_to_the_public_https_host(self):
        for path in EXISTING_COMBO_PAGES + MORE_COMBOS:
            for kwargs in ({}, {'HTTP_HOST': 'www.emojikitchenhub.com'}, {'HTTP_HOST': 'testserver:8000'},
                           {'HTTP_HOST': 'emojikitchenhub.com', 'HTTP_X_FORWARDED_PROTO': 'http'}):
                response = self.client.get(path + '?utm_source=x', **kwargs)
                self.assertEqual(response.status_code, 200)
                parser = _PageParser()
                parser.feed(response.content.decode())
                self.assertEqual(parser.canonical, COMBO_SITE + path, (path, kwargs))
                self.assertEqual(parser.meta['og:url'], COMBO_SITE + path, (path, kwargs))

    @override_settings(ALLOWED_HOSTS=['testserver', 'emojikitchenhub.com', 'www.emojikitchenhub.com'])
    def test_sitemap_locs_for_combo_pages_equal_their_canonicals_and_return_200(self):
        response = self.client.get('/sitemap.xml', HTTP_HOST='www.emojikitchenhub.com')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        combo_locs = [loc for loc in locs if '/emoji-combos/' in loc or loc.endswith(READY_MADE)]
        expected = [COMBO_SITE + p for p in EXISTING_COMBO_PAGES + MORE_COMBOS + TAG_PATHS + ['/emoji-combos/mood/']]
        self.assertEqual(sorted(combo_locs), sorted(expected))
        for loc in combo_locs:
            path = urlparse(loc).path
            self.assertEqual(self.parse(path).canonical, loc)
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_indexnow_sitemap_collection_includes_the_new_pages(self):
        from . import indexnow
        urls = indexnow.collect_sitemap_urls()
        for path in MORE_COMBOS:
            self.assertIn(COMBO_SITE + path, urls)

    def test_category_pages_keep_ga4_once_and_adsense_off_the_home_slot(self):
        home = self.fetch('/')
        self.assertIn(ADSENSE_HOME_SLOT, home)
        for path in EXISTING_COMBO_PAGES + MORE_COMBOS:
            html = self.fetch(path)
            self.assertEqual(html.count('googletagmanager.com/gtag/js?id=G-3DKYS4C5DL'), 1, path)
            self.assertEqual(html.count("gtag('config', 'G-3DKYS4C5DL')"), 1, path)
            self.assertEqual(html.count('name="google-adsense-account"'), 1, path)
            self.assertEqual(html.count('ca-pub-3200425003686406'), 1, path)
            self.assertNotIn(ADSENSE_HOME_SLOT, html, path)


class ComboPageLinksSeedTests(TestCase):
    """seed_combo_page_links: dry run by default, guarded save, safe to re-run."""

    def setUp(self):
        from .blog_seed_combo_links import COMBO_LINKS
        self.links = COMBO_LINKS
        bodies = {
            'emoji-kitchen-whatsapp': '<h2>Intro</h2>\n\n<p>Body one.</p>\n\n<h2>Create Your Next WhatsApp Sticker</h2>\n\n<p>Closing.</p>\n',
            'emoji-kitchen-gboard': '<h2>Tips</h2>\n\n<p>Body.</p>\n\n<h2>Make Your Next Gboard Emoji Mashup</h2>\n\n<p>Closing.</p>\n',
            'emoji-kitchen-samsung': '<h2>Tips</h2>\n\n<p>Body.</p>\n\n<h2>Conclusion</h2>\n\n<p>Closing.</p>\n',
        }
        for slug in self.links:
            BlogPost.objects.create(
                title=slug, slug=slug, excerpt='x', content=bodies.get(slug, '<h2>A</h2>\n\n<p>Body.</p>\n'),
                status=BlogPost.STATUS_PUBLISHED, seo_title=slug, seo_description='d' * 90,
            )

    def run_seed(self, apply=True):
        out = io.StringIO()
        call_command(*(('seed_combo_page_links', '--apply') if apply else ('seed_combo_page_links',)), stdout=out)
        return out.getvalue()

    def snapshot(self):
        return {p.slug: (p.content, p.updated_at, p.reading_time) for p in BlogPost.objects.all()}

    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        output = self.run_seed(apply=False)
        self.assertIn('Dry run only', output)
        self.assertEqual(self.snapshot(), before)

    def test_apply_adds_each_paragraph_once_and_a_rerun_changes_nothing(self):
        self.run_seed()
        first = self.snapshot()
        for slug, (_marker, _placement, html) in self.links.items():
            self.assertEqual(first[slug][0].count(html), 1, slug)
        self.run_seed()
        self.assertEqual(self.snapshot(), first)
        self.assertIn('Nothing to change', self.run_seed())

    def test_placement_before_the_closing_heading_and_at_the_end(self):
        self.run_seed()
        whatsapp = BlogPost.objects.get(slug='emoji-kitchen-whatsapp').content
        html = self.links['emoji-kitchen-whatsapp'][2]
        self.assertLess(whatsapp.index(html), whatsapp.index('<h2>Create Your Next WhatsApp Sticker</h2>'))
        self.assertGreater(whatsapp.index(html), whatsapp.index('Body one.'))
        self.assertTrue(whatsapp.endswith('<p>Closing.</p>\n'))
        iphone = BlogPost.objects.get(slug='emoji-kitchen-iphone').content
        self.assertTrue(iphone.rstrip().endswith(self.links['emoji-kitchen-iphone'][2]))

    def test_missing_heading_appends_at_the_end_and_missing_post_is_skipped(self):
        BlogPost.objects.filter(slug='emoji-kitchen-samsung').update(content='<h2>Other</h2>\n\n<p>Body.</p>\n')
        BlogPost.objects.filter(slug='emoji-kitchen-gboard').delete()
        output = self.run_seed()
        self.assertIn('emoji-kitchen-gboard: missing - skip', output)
        self.assertIn('appended at the end instead', output)
        samsung = BlogPost.objects.get(slug='emoji-kitchen-samsung').content
        self.assertTrue(samsung.rstrip().endswith(self.links['emoji-kitchen-samsung'][2]))

    def test_a_post_that_already_links_to_the_new_page_is_left_alone(self):
        BlogPost.objects.filter(slug='emoji-kitchen-iphone').update(
            content='<p>See our <a href="/emoji-combos/sad/">sad emoji combos</a>.</p>')
        before = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        output = self.run_seed()
        self.assertIn('emoji-kitchen-iphone: already has the link - skip', output)
        after = BlogPost.objects.get(slug='emoji-kitchen-iphone')
        self.assertEqual((after.content, after.updated_at), (before.content, before.updated_at))

    def test_new_paragraphs_are_known_inbound_suffixes_for_the_older_seeds(self):
        from .blog_seed_utils import desired_seed_content, split_allowed_inbound_suffix
        for slug in ('emoji-kitchen-discord', 'emoji-kitchen-iphone', 'how-to-save-download-emoji-kitchen-stickers'):
            html = self.links[slug][2]
            core, suffix = split_allowed_inbound_suffix('<p>fixture</p>\n' + html + '\n')
            self.assertEqual(core.strip(), '<p>fixture</p>', slug)
            self.assertEqual(suffix.strip(), html, slug)
            current = '<p>fixture</p>\n' + html + '\n'
            self.assertEqual(desired_seed_content('<p>fixture</p>', current), current, slug)

    def test_links_only_point_at_pages_that_exist(self):
        for _slug, (_marker, _placement, html) in self.links.items():
            for href in re.findall(r'href="(/[^"]*)"', html):
                self.assertEqual(self.client.get(href).status_code, 200, href)


# ── FAQ extractor: footer disclaimer must not leak into FAQPage answers ───────

# Previous extractor: the FAQ section ran to the next <h2> or EOF, so a
# trailing italic disclaimer (and later inbound-link paragraphs) was folded
# into the last answer. Kept only to show that current answers match that
# output once the leaked disclaimer is removed.
_LEGACY_H2 = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
_LEGACY_H3 = re.compile(r'<h3\b[^>]*>(.*?)</h3>', re.IGNORECASE | re.DOTALL)
_LEGACY_TAG = re.compile(r'<[^>]+>')


def _legacy_plain(fragment):
    text = re.sub(r'\s+', ' ', __import__('html').unescape(_LEGACY_TAG.sub(' ', fragment))).strip()
    # Same punctuation clean-up as kitchen.seo._plain, so this comparison
    # isolates the disclaimer change.
    return re.sub(r'\s+([.,;:!?)])', r'\1', text)


def _legacy_faq_pairs(content):
    content = content or ''
    for heading in _LEGACY_H2.finditer(content):
        if not re.search(r'\bFAQs?\b', _legacy_plain(heading.group(1)), re.IGNORECASE):
            continue
        following = _LEGACY_H2.search(content, heading.end())
        section = content[heading.end():following.start() if following else len(content)]
        questions = list(_LEGACY_H3.finditer(section))
        pairs = []
        for i, question in enumerate(questions):
            end = questions[i + 1].start() if i + 1 < len(questions) else len(section)
            q, a = _legacy_plain(question.group(1)), _legacy_plain(section[question.end():end])
            if q and a:
                pairs.append((q, a))
        return pairs
    return []


# Fixtures whose last FAQ answer previously swallowed the italic footer.
AFFECTED_FAQ_FIXTURES = (
    'emoji-kitchen-discord.html',
    'emoji-kitchen-google-messages.html',
    'emoji-kitchen-instagram.html',
    'emoji-kitchen-not-working.html',
    'emoji-kitchen-on-pc.html',
    'thanksgiving-emoji-combos.html',
)

# Counts from the previous extractor; the fix must not drop or invent questions.
FAQ_FIXTURE_COUNTS = {
    'emoji-kitchen-discord.html': 6,
    'emoji-kitchen-gboard.html': 9,
    'emoji-kitchen-google-messages.html': 6,
    'emoji-kitchen-instagram.html': 6,
    'emoji-kitchen-iphone-rewrite.html': 6,
    'emoji-kitchen-iphone.html': 9,
    'emoji-kitchen-not-working.html': 6,
    'emoji-kitchen-on-pc.html': 6,
    'emoji-kitchen-samsung.html': 9,
    'emoji-kitchen-whatsapp.html': 7,
    'how-to-save-download-emoji-kitchen-stickers.html': 6,
    'thanksgiving-emoji-combos.html': 6,
}

# Legal footer language that must not appear in any extracted answer.
_FAQ_DISCLAIMER_RE = re.compile(
    r'\btrademarks?\b|independent, fan-made (?:project|site)',
    re.IGNORECASE,
)


class FaqExtractorDisclaimerTests(SimpleTestCase):
    def _fixtures(self):
        return sorted((BLOG_SAMPLES).glob('*.html'))

    def test_every_fixture_keeps_its_faq_count(self):
        from kitchen.seo import faq_pairs_from_html

        names = {path.name for path in self._fixtures()}
        self.assertEqual(names, set(FAQ_FIXTURE_COUNTS))
        for path in self._fixtures():
            pairs = faq_pairs_from_html(path.read_text(encoding='utf-8'))
            self.assertEqual(len(pairs), FAQ_FIXTURE_COUNTS[path.name], path.name)

    def test_last_answers_do_not_include_the_footer_disclaimer(self):
        from kitchen.seo import faq_pairs_from_html

        for path in self._fixtures():
            pairs = faq_pairs_from_html(path.read_text(encoding='utf-8'))
            if not pairs:
                continue
            last = pairs[-1][1]
            self.assertIsNone(_FAQ_DISCLAIMER_RE.search(last), f'{path.name}: {last}')

    def test_answers_match_the_previous_extractor_once_the_disclaimer_is_gone(self):
        from kitchen.seo import faq_pairs_from_html

        for path in self._fixtures():
            html = path.read_text(encoding='utf-8')
            new_pairs = faq_pairs_from_html(html)
            old_pairs = _legacy_faq_pairs(html)
            self.assertEqual([q for q, _ in new_pairs], [q for q, _ in old_pairs], path.name)
            for index, ((question, new_answer), (_, old_answer)) in enumerate(zip(new_pairs, old_pairs)):
                if new_answer == old_answer:
                    continue
                self.assertEqual(index, len(old_pairs) - 1, f'{path.name} changed an earlier answer: {question}')
                self.assertTrue(old_answer.startswith(new_answer), path.name)
                leftover = old_answer[len(new_answer):].strip()
                self.assertTrue(leftover, path.name)
                self.assertIsNotNone(_FAQ_DISCLAIMER_RE.search(leftover), leftover)
                self.assertIn(path.name, AFFECTED_FAQ_FIXTURES)

        changed = {
            path.name
            for path in self._fixtures()
            if faq_pairs_from_html(path.read_text(encoding='utf-8')) != _legacy_faq_pairs(path.read_text(encoding='utf-8'))
        }
        self.assertEqual(changed, set(AFFECTED_FAQ_FIXTURES))

    def test_multi_paragraph_answers_are_kept_and_the_disclaimer_is_not(self):
        from kitchen.seo import faq_pairs_from_html

        html = (
            '<h2>FAQ</h2>\n'
            '<h3>What is a long answer?</h3>\n'
            '<p>First paragraph of the answer.</p>\n'
            '<p>Second paragraph still belongs to this answer.</p>\n'
            '<h3>And a short one?</h3>\n'
            '<p>Just one paragraph.</p>\n'
            '<p><em>Emoji Kitchen Hub is an independent, fan-made project and is '
            'not affiliated with Google. Gboard is a trademark of Google LLC.</em></p>\n'
        )
        pairs = faq_pairs_from_html(html)
        self.assertEqual(
            pairs,
            [
                (
                    'What is a long answer?',
                    'First paragraph of the answer. Second paragraph still belongs to this answer.',
                ),
                ('And a short one?', 'Just one paragraph.'),
            ],
        )

    def test_section_stops_at_hr_higher_headings_and_inbound_links(self):
        from kitchen.blog_seed_utils import CRAWL_LINKS_HTML
        from kitchen.seo import faq_pairs_from_html

        base = '<h2>FAQ</h2>\n<h3>A question?</h3>\n<p>The real answer.</p>\n'
        self.assertEqual(
            faq_pairs_from_html(base + '<hr>\n<p>After the rule, not a FAQ answer.</p>\n'),
            [('A question?', 'The real answer.')],
        )
        self.assertEqual(
            faq_pairs_from_html(base + '<h1>Next chapter</h1>\n<p>Not in the FAQ.</p>\n'),
            [('A question?', 'The real answer.')],
        )
        self.assertEqual(
            faq_pairs_from_html(base + CRAWL_LINKS_HTML + '\n'),
            [('A question?', 'The real answer.')],
        )
        # A genuine unofficial answer, with no footer markup, is kept in full.
        unofficial = (
            '<h2>FAQs</h2>\n'
            '<h3>Is this official?</h3>\n'
            '<p>No. It is unofficial and fan-made. It is not affiliated with Google or Apple.</p>\n'
        )
        self.assertEqual(
            faq_pairs_from_html(unofficial),
            [(
                'Is this official?',
                'No. It is unofficial and fan-made. It is not affiliated with Google or Apple.',
            )],
        )


class FaqPlainTextPunctuationTests(TestCase):
    """Stripped tags must not leave a space before punctuation in JSON-LD text."""

    def test_no_space_before_punctuation_after_links(self):
        from kitchen.seo import faq_pairs_from_html

        html = (
            '<h2>FAQ</h2><h3>Where?</h3>'
            '<p>See the <a href="/contact/">contact page</a>. Or try '
            '<a href="/emoji-combos/bio/">emoji combos for bio</a>, '
            '<strong>Gboard</strong>; <em>it</em>! (<a href="/">mixer</a>)</p>'
        )
        (_, answer), = faq_pairs_from_html(html)
        self.assertEqual(
            answer,
            'See the contact page. Or try emoji combos for bio, Gboard; it! ( mixer)',
        )

    def test_not_working_fixture_answer_and_visible_body_unchanged(self):
        from kitchen.seo import faq_pairs_from_html

        html = (BLOG_SAMPLES / 'emoji-kitchen-not-working.html').read_text(encoding='utf-8')
        answers = [a for _, a in faq_pairs_from_html(html)]
        self.assertFalse(any(re.search(r'\s[.,;:!?)]', a) for a in answers))
        self.assertTrue(any('contact page.' in a for a in answers))
        post = BlogPost.objects.create(
            title='t', slug='emoji-kitchen-not-working', excerpt='e',
            content=html, status=BlogPost.STATUS_PUBLISHED,
        )
        page = self.client.get('/blog/emoji-kitchen-not-working/').content.decode()
        self.assertIn('contact page</a>.', page)
        self.assertEqual(BlogPost.objects.get(pk=post.pk).content, html)


class FaqSchemaRenderTests(TestCase):
    """FAQPage JSON-LD is computed from the stored body at render time."""

    def test_rendered_schema_strips_the_disclaimer_without_changing_stored_content(self):
        from kitchen.seo import faq_pairs_from_html

        html = (BLOG_SAMPLES / 'emoji-kitchen-google-messages.html').read_text(encoding='utf-8')
        post = BlogPost.objects.create(
            title='How to Use Emoji Kitchen in Google Messages (Android Guide)',
            slug='emoji-kitchen-google-messages',
            excerpt='excerpt',
            content=html,
            status=BlogPost.STATUS_PUBLISHED,
        )
        stored = BlogPost.objects.get(pk=post.pk).content
        self.assertIn('trademarks of Google LLC', stored)

        page = self.client.get('/blog/emoji-kitchen-google-messages/').content.decode()
        blocks = [
            json.loads(match.group(1))
            for match in re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL
            )
        ]
        faq = next(block for block in blocks if block.get('@type') == 'FAQPage')
        answers = [entity['acceptedAnswer']['text'] for entity in faq['mainEntity']]
        expected = faq_pairs_from_html(html)
        self.assertEqual(len(answers), 6)
        self.assertEqual(answers, [answer for _, answer in expected])
        self.assertFalse(any(_FAQ_DISCLAIMER_RE.search(answer) for answer in answers))
        # The body in the database is unchanged; only the schema is cleaned.
        self.assertEqual(BlogPost.objects.get(pk=post.pk).content, stored)


# ── 17 Nov 2026 on-page: homepage links, meta cap, compressed covers ─────────

from kitchen.blog_covers import (
    COVER_ASPECT_TOLERANCE,
    COVER_FILES,
    COVER_LONG_EDGE,
    COVER_SOURCE_SIZE,
    MAX_COVER_BYTES,
    cover_bytes as fixture_cover_bytes,
    cover_filename as fixture_cover_filename,
    cover_path as fixture_cover_path,
    expected_cover_size,
    og_bytes as fixture_og_bytes,
    og_filename as fixture_og_filename,
    og_path as fixture_og_path,
)
from kitchen.blog_content import POST_UPDATES
from kitchen.management.commands.fix_blog_meta_descriptions import META_TARGETS


def _all_seed_meta_descriptions():
    """seo_description values that seed or update commands would write."""
    from kitchen.blog_seed_discord import FIELDS as discord_fields
    from kitchen.blog_seed_google_messages import FIELDS as gm_fields
    from kitchen.blog_seed_instagram import FIELDS as ig_fields
    from kitchen.blog_seed_iphone import FIELDS as iphone_fields
    from kitchen.blog_seed_not_working import FIELDS as not_working_fields
    from kitchen.blog_seed_on_pc import FIELDS as on_pc_fields
    from kitchen.blog_seed_save_download import FIELDS as save_fields
    from kitchen.blog_seed_thanksgiving import FIELDS as thanksgiving_fields

    values = {
        'emoji-kitchen-on-pc': on_pc_fields['seo_description'],
        'emoji-kitchen-not-working': not_working_fields['seo_description'],
        'emoji-kitchen-discord': discord_fields['seo_description'],
        'emoji-kitchen-google-messages': gm_fields['seo_description'],
        'emoji-kitchen-instagram': ig_fields['seo_description'],
        'emoji-kitchen-iphone': iphone_fields['seo_description'],
        'how-to-save-download-emoji-kitchen-stickers': save_fields['seo_description'],
        'thanksgiving-emoji-combos': thanksgiving_fields['seo_description'],
    }
    for slug, plan in POST_UPDATES.items():
        values[f'blog_content:{slug}'] = plan['fields']['seo_description']
    return values


def _all_seed_excerpts():
    """excerpt values that seed or update commands would write."""
    from kitchen.blog_seed_discord import FIELDS as discord_fields
    from kitchen.blog_seed_google_messages import FIELDS as gm_fields
    from kitchen.blog_seed_instagram import FIELDS as ig_fields
    from kitchen.blog_seed_iphone import FIELDS as iphone_fields
    from kitchen.blog_seed_not_working import FIELDS as not_working_fields
    from kitchen.blog_seed_on_pc import FIELDS as on_pc_fields
    from kitchen.blog_seed_save_download import FIELDS as save_fields
    from kitchen.blog_seed_thanksgiving import FIELDS as thanksgiving_fields

    values = {
        'emoji-kitchen-on-pc': on_pc_fields['excerpt'],
        'emoji-kitchen-not-working': not_working_fields['excerpt'],
        'emoji-kitchen-discord': discord_fields['excerpt'],
        'emoji-kitchen-google-messages': gm_fields['excerpt'],
        'emoji-kitchen-instagram': ig_fields['excerpt'],
        'emoji-kitchen-iphone': iphone_fields['excerpt'],
        'how-to-save-download-emoji-kitchen-stickers': save_fields['excerpt'],
        'thanksgiving-emoji-combos': thanksgiving_fields['excerpt'],
    }
    for slug, plan in POST_UPDATES.items():
        values[f'blog_content:{slug}'] = plan['fields']['excerpt']
    return values


class SeededBlogMetaDescriptionTests(SimpleTestCase):
    def test_every_seeded_meta_description_is_at_most_150_characters(self):
        values = _all_seed_meta_descriptions()
        self.assertGreaterEqual(len(values), 10)
        for key, description in values.items():
            length = len(description)
            self.assertLessEqual(
                length,
                150,
                f'{key} is {length} characters: {description}',
            )
            self.assertGreaterEqual(length, 120, key)

    def test_every_seeded_excerpt_is_at_most_150_characters(self):
        values = _all_seed_excerpts()
        self.assertGreaterEqual(len(values), 10)
        for key, excerpt in values.items():
            length = len(excerpt)
            self.assertLessEqual(
                length,
                150,
                f'{key} is {length} characters: {excerpt}',
            )
            self.assertGreaterEqual(length, 120, key)


class FixBlogMetaDescriptionsCommandTests(TestCase):
    OLD_ON_PC = (
        'Want Emoji Kitchen on your computer? Learn how to make, download, and share emoji '
        'mashups on Windows PC, Mac, and Chromebook using a browser, no phone needed.'
    )
    OLD_NOT_WORKING = (
        'Emoji Kitchen not showing up or not pasting? Try these simple fixes for Gboard, '
        'Google Search, and the Emoji Kitchen Hub mixer on Android, iPhone, and desktop.'
    )
    OLD_SAMSUNG = (
        "Learn the difference between Gboard and Samsung Keyboard, how to access Google's Emoji "
        'Kitchen on a Galaxy phone, and how to troubleshoot missing suggestions.'
    )
    OLD_GBOARD_EXCERPT = (
        'Learn how to access Emoji Kitchen through Gboard on supported Android devices, choose '
        'available emoji combinations and troubleshoot missing suggestions. For iPhone or '
        'WhatsApp-specific instructions, see the relevant dedicated guide.'
    )
    OLD_WHATSAPP_EXCERPT = (
        'Learn how to share supported emoji mashups in WhatsApp, understand the difference '
        'between text characters and image-based stickers, and troubleshoot copying or '
        'attachment problems.'
    )
    OLD_IPHONE_EXCERPT = (
        'Make sticker-style emoji mashups on iPhone in Safari or Chrome. Learn the browser '
        'workflow, when Gboard helps, how to copy or download results, and how to fix common issues.'
    )
    OLD_SAVE_EXCERPT = (
        'Learn how to save and download sticker-style mashups as images, what to do when '
        'clipboard paste fails, and how to share them in chats or social apps on phone or desktop.'
    )

    def setUp(self):
        self.posts = {}
        long_excerpts = {
            'emoji-kitchen-on-pc': self.OLD_ON_PC,
            'emoji-kitchen-not-working': self.OLD_NOT_WORKING,
            'emoji-kitchen-samsung': self.OLD_SAMSUNG,
            'emoji-kitchen-gboard': self.OLD_GBOARD_EXCERPT,
            'emoji-kitchen-whatsapp': self.OLD_WHATSAPP_EXCERPT,
            'emoji-kitchen-iphone': self.OLD_IPHONE_EXCERPT,
            'how-to-save-download-emoji-kitchen-stickers': self.OLD_SAVE_EXCERPT,
        }
        for slug in META_TARGETS:
            old = long_excerpts.get(slug, 'x' * 80)
            self.posts[slug] = BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt=old,
                seo_description=old if slug in {
                    'emoji-kitchen-on-pc', 'emoji-kitchen-not-working', 'emoji-kitchen-samsung',
                } else 'd' * 90,
                og_description=old if slug == 'emoji-kitchen-on-pc' else '',
                content='<p>Body</p>',
                status=BlogPost.STATUS_PUBLISHED,
            )

    def test_dry_run_writes_nothing(self):
        before = {
            slug: (post.seo_description, post.excerpt, post.og_description, post.updated_at, post.pk)
            for slug, post in self.posts.items()
        }
        out = io.StringIO()
        call_command('fix_blog_meta_descriptions', stdout=out)
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
        for slug, (seo, excerpt, og, updated, pk) in before.items():
            post = BlogPost.objects.get(slug=slug)
            self.assertEqual(post.pk, pk)
            self.assertEqual(post.seo_description, seo)
            self.assertEqual(post.excerpt, excerpt)
            self.assertEqual(post.og_description, og)
            self.assertEqual(post.updated_at, updated)

    def test_apply_trims_only_the_target_fields_and_rerun_is_a_noop(self):
        first = io.StringIO()
        call_command('fix_blog_meta_descriptions', '--apply', stdout=first)
        self.assertRegex(first.getvalue(), r'Updated \d+')
        for slug, desired in META_TARGETS.items():
            post = BlogPost.objects.get(slug=slug)
            for field, value in desired.items():
                self.assertEqual(getattr(post, field), value, f'{slug}.{field}')
            if 'seo_description' in desired:
                self.assertLessEqual(len(post.meta_description), 150, slug)
            if 'excerpt' in desired:
                self.assertLessEqual(len(post.excerpt), 150, slug)

        updated = {slug: BlogPost.objects.get(slug=slug).updated_at for slug in META_TARGETS}
        pks = {slug: BlogPost.objects.get(slug=slug).pk for slug in META_TARGETS}

        again = io.StringIO()
        call_command('fix_blog_meta_descriptions', '--apply', stdout=again)
        self.assertIn('No meta descriptions or excerpts need fixing', again.getvalue())
        for slug in META_TARGETS:
            post = BlogPost.objects.get(slug=slug)
            self.assertEqual(post.pk, pks[slug])
            self.assertEqual(post.updated_at, updated[slug])


class CompressedBlogCoverTests(TestCase):
    def test_fixture_covers_keep_source_aspect_and_stay_under_200kb(self):
        from PIL import Image
        from io import BytesIO

        self.assertEqual(len(COVER_FILES), 11)
        self.assertEqual(set(COVER_FILES), set(COVER_SOURCE_SIZE))
        for slug in COVER_FILES:
            path = fixture_cover_path(slug)
            self.assertTrue(path.is_file(), slug)
            data = fixture_cover_bytes(slug)
            self.assertLessEqual(len(data), MAX_COVER_BYTES, f'{slug} is {len(data)} bytes')
            self.assertTrue(fixture_cover_filename(slug).endswith('.webp'), slug)
            image = Image.open(BytesIO(data))
            width, height = image.size
            self.assertEqual((width, height), expected_cover_size(slug), slug)
            self.assertEqual(max(width, height), COVER_LONG_EDGE, slug)
            src_w, src_h = COVER_SOURCE_SIZE[slug]
            source_aspect = src_w / src_h
            actual_aspect = width / height
            self.assertLessEqual(
                abs(actual_aspect - source_aspect) / source_aspect,
                COVER_ASPECT_TOLERANCE,
                f'{slug} aspect {actual_aspect} vs source {source_aspect}',
            )
            from kitchen.blog_seed_utils import cover_versioned_filename
            name = cover_versioned_filename(fixture_cover_filename(slug), data)
            self.assertRegex(name, rf'^{re.escape(path.stem)}-[0-9a-f]{{8}}\.webp$')

            jpg_path = fixture_og_path(slug)
            self.assertTrue(jpg_path.is_file(), slug)
            jpg = fixture_og_bytes(slug)
            self.assertLessEqual(len(jpg), MAX_COVER_BYTES, f'{slug} og jpg is {len(jpg)} bytes')
            self.assertTrue(fixture_og_filename(slug).endswith('.jpg'), slug)
            jpg_image = Image.open(BytesIO(jpg))
            self.assertEqual(jpg_image.format, 'JPEG', slug)
            self.assertEqual(jpg_image.size, (width, height), slug)
            jpg_name = cover_versioned_filename(fixture_og_filename(slug), jpg)
            self.assertRegex(jpg_name, rf'^{re.escape(jpg_path.stem)}-[0-9a-f]{{8}}\.jpg$')

    def test_compress_command_is_idempotent_and_writes_hashed_names(self):
        from kitchen import indexnow
        from kitchen.blog_seed_utils import cover_versioned_filename

        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(tmp, ignore_errors=True))
        media = override_settings(MEDIA_ROOT=tmp)
        media.enable()
        self.addCleanup(media.disable)

        for slug in COVER_FILES:
            BlogPost.objects.create(
                title=slug,
                slug=slug,
                excerpt='x',
                content='<p>Body</p>',
                status=BlogPost.STATUS_PUBLISHED,
                seo_description='d' * 90,
            )

        dry = io.StringIO()
        call_command('compress_blog_covers', stdout=dry)
        self.assertIn('DRY RUN', dry.getvalue())
        for slug in COVER_FILES:
            post = BlogPost.objects.get(slug=slug)
            self.assertFalse(post.featured_image)
            self.assertFalse(post.og_image)

        first = io.StringIO()
        call_command('compress_blog_covers', '--apply', stdout=first)
        self.assertIn('Updated 11', first.getvalue())
        updated = {}
        for slug in COVER_FILES:
            post = BlogPost.objects.get(slug=slug)
            desired_webp = cover_versioned_filename(
                fixture_cover_filename(slug), fixture_cover_bytes(slug)
            )
            desired_jpg = cover_versioned_filename(
                fixture_og_filename(slug), fixture_og_bytes(slug)
            )
            self.assertEqual(post.featured_image.name, f'blog/featured/{desired_webp}', slug)
            self.assertEqual(post.og_image.name, f'blog/og/{desired_jpg}', slug)
            post.featured_image.open('rb')
            try:
                self.assertEqual(post.featured_image.read(), fixture_cover_bytes(slug), slug)
            finally:
                post.featured_image.close()
            post.og_image.open('rb')
            try:
                self.assertEqual(post.og_image.read(), fixture_og_bytes(slug), slug)
            finally:
                post.og_image.close()
            self.assertLessEqual(post.featured_image.size, MAX_COVER_BYTES, slug)
            self.assertLessEqual(post.og_image.size, MAX_COVER_BYTES, slug)
            updated[slug] = post.updated_at

            html = self.client.get(f'/blog/{slug}/').content.decode()
            width, height = expected_cover_size(slug)
            og = re.search(r'property="og:image" content="([^"]+)"', html)
            tw = re.search(r'name="twitter:image" content="([^"]+)"', html)
            self.assertIsNotNone(og, slug)
            self.assertIsNotNone(tw, slug)
            self.assertTrue(og.group(1).endswith('.jpg'), og.group(1))
            self.assertTrue(tw.group(1).endswith('.jpg'), tw.group(1))
            self.assertIn(desired_jpg, og.group(1), slug)
            self.assertIn(desired_jpg, tw.group(1), slug)
            og_w = re.search(r'property="og:image:width" content="([^"]*)"', html)
            og_h = re.search(r'property="og:image:height" content="([^"]*)"', html)
            og_t = re.search(r'property="og:image:type" content="([^"]*)"', html)
            self.assertIsNotNone(og_w, slug)
            self.assertIsNotNone(og_h, slug)
            self.assertIsNotNone(og_t, slug)
            self.assertEqual(og_w.group(1), str(width), slug)
            self.assertEqual(og_h.group(1), str(height), slug)
            self.assertEqual(og_t.group(1), 'image/jpeg', slug)

            on_page = re.search(
                r'<div class="blog-detail__cover">\s*<img\b([^>]*)>',
                html,
            )
            self.assertIsNotNone(on_page, slug)
            attrs = on_page.group(1)
            src = re.search(r'src="([^"]+)"', attrs)
            self.assertIsNotNone(src, slug)
            self.assertTrue(src.group(1).endswith('.webp'), src.group(1))
            self.assertIn(desired_webp, src.group(1), slug)
            self.assertIn(f'width="{width}"', attrs, slug)
            self.assertIn(f'height="{height}"', attrs, slug)

            blocks = [
                json.loads(match.group(1))
                for match in re.finditer(
                    r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
                )
            ]
            blog = next(b for b in blocks if b.get('@type') == 'BlogPosting')
            image = blog['image']
            if isinstance(image, list):
                image = image[0]
            if isinstance(image, dict):
                self.assertEqual(image.get('width'), width, slug)
                self.assertEqual(image.get('height'), height, slug)
                image_url = image.get('url') or image.get('@id') or ''
            else:
                image_url = image
            self.assertIn(desired_jpg, image_url, slug)

        with mock.patch.object(indexnow, 'submit_urls', wraps=indexnow.submit_urls) as submit:
            with mock.patch.object(indexnow.requests, 'post') as posted:
                with override_settings(INDEXNOW_ENABLED=True, DEBUG=False):
                    with self.captureOnCommitCallbacks(execute=True):
                        again = io.StringIO()
                        call_command('compress_blog_covers', '--apply', stdout=again)
        self.assertIn('No covers need updating', again.getvalue())
        self.assertEqual(submit.call_count, 0)
        posted.assert_not_called()
        for slug in COVER_FILES:
            post = BlogPost.objects.get(slug=slug)
            self.assertEqual(post.updated_at, updated[slug], slug)

    def test_assign_versioned_cover_leaves_a_jpeg_og_image_in_place(self):
        from django.core.files.base import ContentFile
        from kitchen.blog_seed_utils import (
            assign_versioned_cover,
            assign_versioned_og_image,
            cover_versioned_filename,
        )

        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(tmp, ignore_errors=True))
        media = override_settings(MEDIA_ROOT=tmp)
        media.enable()
        self.addCleanup(media.disable)

        slug = 'emoji-kitchen-iphone'
        post = BlogPost.objects.create(
            title=slug,
            slug=slug,
            excerpt='x',
            content='<p>Body</p>',
            status=BlogPost.STATUS_PUBLISHED,
            seo_description='d' * 90,
        )
        assign_versioned_cover(post, fixture_cover_bytes(slug), fixture_cover_filename(slug))
        assign_versioned_og_image(post, fixture_og_bytes(slug), fixture_og_filename(slug))
        post.save()
        og_name = post.og_image.name
        self.assertTrue(og_name.endswith('.jpg'))

        assign_versioned_cover(post, fixture_cover_bytes(slug), fixture_cover_filename(slug))
        post.save()
        post = BlogPost.objects.get(slug=slug)
        self.assertEqual(post.og_image.name, og_name)
        desired_jpg = cover_versioned_filename(
            fixture_og_filename(slug), fixture_og_bytes(slug)
        )
        self.assertEqual(Path(post.og_image.name).name, desired_jpg)


# ── Keyword pages, site search and the two browser tools ─────────────────────

import json as _json

from . import combo_search

STATIC_JS = Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js'
TOOL_PAGES = ['/emoji-art-editor/', '/dot-art-generator/']


class TagPageDataTests(SimpleTestCase):
    """kitchen/combo_tags.py: original, distinct, valid keyword pages."""

    def test_the_keyword_list_is_not_empty_and_never_shadows_a_fixed_page(self):
        self.assertGreaterEqual(len(TAG_PAGES), 12)
        for slug in TAG_PAGES:
            self.assertRegex(slug, r'^[a-z0-9-]+$')
            self.assertNotIn(slug, RESERVED_SLUGS, slug)
            self.assertNotIn(slug, COMBO_PAGES, f'{slug} is already a category page')

    def test_every_page_has_enough_unique_sets_in_every_filter(self):
        for slug, page in TAG_PAGES.items():
            sets = [c[2] for c in page['combos']]
            labels = [c[1] for c in page['combos']]
            self.assertGreaterEqual(len(sets), MIN_SETS_PER_NEW_PAGE // 2, slug)
            self.assertEqual(len(sets), len(set(sets)), f'{slug} repeats a set')
            self.assertEqual(len(labels), len(set(labels)), f'{slug} repeats a label')
            keys = {key for key, _label in page['filters']}
            self.assertTrue({c[0] for c in page['combos']} <= keys, slug)
            for key in keys:
                self.assertGreaterEqual(len([c for c in page['combos'] if c[0] == key]), 3, f'{slug}/{key} is thin')

    def test_sets_are_emoji_only(self):
        for slug, page in TAG_PAGES.items():
            for _cat, _label, emoji_set in page['combos']:
                self.assertFalse(emoji_set.isascii(), (slug, emoji_set))
                self.assertFalse(any(ch.isascii() and ch.isalnum() for ch in emoji_set), (slug, emoji_set))

    def test_no_set_is_copied_from_another_page_or_repeated_across_keywords(self):
        owned = set()
        for name in EXISTING_COMBO_TEMPLATES.values():
            owned |= set(combo_counts.template_sets(name))
        for page in COMBO_PAGES.values():
            owned |= {c[2] for c in page['combos']}
        seen = {}
        for slug, page in TAG_PAGES.items():
            for _cat, label, emoji_set in page['combos']:
                self.assertNotIn(emoji_set, owned, f'{slug} "{label}" {emoji_set} is already on an older page')
                self.assertNotIn(emoji_set, seen, f'{slug} "{label}" {emoji_set} is also on {seen.get(emoji_set)}')
                seen[emoji_set] = slug

    def test_every_mashup_pair_exists_in_the_dataset(self):
        for slug, page in TAG_PAGES.items():
            self.assertEqual(len(page['mashups']), 6, slug)
            for first, second in page['mashups']:
                self.assertTrue(views.combo_image_url(first, second), f'{slug}: {first} + {second} has no Emoji Kitchen pair')
            self.assertEqual(len(views.mashup_links(page['mashups'])), 6, slug)

    def test_no_number_is_written_into_title_meta_h1_or_intro(self):
        for slug, page in TAG_PAGES.items():
            for field in ('title', 'meta', 'h1', 'badge'):
                self.assertIsNone(re.search(r'\d', page[field]), f'{slug} {field}: {page[field]}')
            for paragraph in page['intro']:
                self.assertIsNone(re.search(r'\d', paragraph), f'{slug}: {paragraph}')

    def test_title_and_meta_lengths_and_uniqueness(self):
        for field in ('title', 'meta', 'h1'):
            values = [page[field] for page in TAG_PAGES.values()]
            self.assertEqual(len(values), len(set(values)), field)
        for slug, page in TAG_PAGES.items():
            self.assertTrue(30 <= len(page['title']) <= 60, f'{slug} title is {len(page["title"])}')
            self.assertTrue(140 <= len(page['meta']) <= 155, f'{slug} meta is {len(page["meta"])}')

    def test_each_page_has_real_copy_and_faqs(self):
        for slug, page in TAG_PAGES.items():
            self.assertEqual(len(page['intro']), 2, slug)
            self.assertGreaterEqual(len(page['faqs']), 3, slug)
            parts = [*page['intro']]
            for heading, paragraphs in page['sections']:
                parts += [heading, *paragraphs]
            for question, answer in page['faqs']:
                parts += [question, answer]
            self.assertEqual(len(page['sections']), 2, slug)
            self.assertGreaterEqual(len(_words('\n'.join(parts))), 240, f'{slug} copy is thin')

    def test_sibling_links_point_at_real_pages(self):
        known = {'love', 'cute', 'aesthetic', 'funny', 'pink'} | set(COMBO_PAGES) | set(TAG_PAGES)
        for slug, page in TAG_PAGES.items():
            self.assertEqual(len(page['siblings']), 3, slug)
            for target, _name in page['siblings']:
                self.assertIn(target, known, f'{slug} links to {target}')
                self.assertNotEqual(target, slug, slug)


class TagPageTests(PageTestCase):
    def test_every_keyword_page_is_a_complete_page(self):
        for path in TAG_PATHS:
            slug = path.rsplit('/', 2)[-2]
            data = TAG_PAGES[slug]
            html = self.fetch(path)
            page = self.parse(path)
            self.assertEqual(len(page.h1), 1, path)
            self.assertEqual(_clean(page.h1[0]), data['h1'], path)
            self.assertEqual(_clean(page.title), data['title'], path)
            self.assertEqual(page.meta['description'], data['meta'], path)
            self.assertEqual(page.canonical, COMBO_SITE + path, path)
            self.assertEqual(page.meta['og:url'], COMBO_SITE + path, path)
            self.assertNotIn('noindex', page.meta.get('robots') or '', path)
            faq_blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(faq_blocks), 1, path)
            shown = len(re.findall(r'<details class="faq-item[ "]', html))
            self.assertEqual(shown, len(data['faqs']), path)
            self.assertEqual(len(faq_blocks[0]['mainEntity']), shown, path)

    def test_count_and_server_rendered_sets_come_from_the_data(self):
        for path in TAG_PATHS:
            data = TAG_PAGES[path.rsplit('/', 2)[-2]]
            html = self.fetch(path)
            distinct = len({c[2] for c in data['combos']})
            self.assertIn(f'<span id="combo-count">{distinct}</span> sets', html, path)
            self.assertEqual(len(re.findall(r'<div class="combo-card">', _visible_text(html))), 12, path)
            for _cat, _label, emoji_set in data['combos'][:12]:
                self.assertIn(f'data-combo="{emoji_set}"', html, path)
            payload = re.search(r'<script id="combos-data" type="application/json">(.*?)</script>', html, re.DOTALL)
            self.assertEqual(len(_json.loads(payload.group(1))), len(data['combos']), path)
            self.assertIn('id="combo-search"', html, path)
            self.assertIn('combo-random-btn', html, path)

    def test_links_in_and_out(self):
        for path in TAG_PATHS:
            links = self.body_links(path)
            for needed in ('/emoji-combos/', '/', '/emoji-maker/', '/blog/'):
                self.assertIn(needed, links, f'{path} does not link to {needed}')
            self.assertNotIn(path, links, f'{path} links to itself')
            siblings = [t for t in links if t.startswith('/emoji-combos/') and t not in ('/emoji-combos/', path)]
            self.assertGreaterEqual(len(siblings), 3, path)
            mixer = [h for h, _t, _a in self.parse(path).body_links if h.startswith('/?emoji1=')]
            self.assertEqual(len(mixer), 6, path)
            for target, anchors in links.items():
                for anchor in anchors:
                    self.assertNotIn(anchor, WEAK_ANCHORS, f'{path} -> {target}')

    def test_unknown_keywords_and_look_alikes_are_404(self):
        for path in ['/emoji-combos/unknown/', '/emoji-combos/tag/', '/emoji-combos/kawaii/extra/', '/emoji-combos/Kawaii/',
                     '/emoji-combos/%3Cscript%3E/']:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_fixed_pages_still_win_over_keywords(self):
        for path in COMBOS + MORE_COMBOS:
            page = self.parse(path)
            self.assertEqual(page.canonical, COMBO_SITE + path, path)
        self.assertEqual(self.client.get('/emoji-combos/search/').status_code, 200)

    def test_hub_lists_every_keyword_and_the_search_box(self):
        html = self.fetch('/emoji-combos/')
        links = self.body_links('/emoji-combos/')
        for path in TAG_PATHS:
            self.assertIn(path, links, path)
        self.assertIn('action="/emoji-combos/search/"', html)
        self.assertIn('name="q"', html)

    def test_keyword_pages_are_in_the_sitemap_with_matching_canonicals(self):
        response = self.client.get('/sitemap.xml')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        for path in TAG_PATHS:
            self.assertIn(COMBO_SITE + path, locs, path)
        self.assertNotIn(COMBO_SITE + '/emoji-combos/search/', locs)

    def test_keyword_pages_keep_ga4_once_and_adsense_off_the_home_slot(self):
        for path in TAG_PATHS:
            html = self.fetch(path)
            self.assertEqual(html.count('googletagmanager.com/gtag/js?id=G-3DKYS4C5DL'), 1, path)
            self.assertEqual(html.count('name="google-adsense-account"'), 1, path)
            self.assertNotIn(ADSENSE_HOME_SLOT, html, path)


class ComboSearchTests(PageTestCase):
    def test_every_inline_array_entry_is_parsed(self):
        for name in EXISTING_COMBO_TEMPLATES.values():
            entries = combo_search._template_entries(name)
            self.assertEqual(len(entries), len(combo_counts.template_sets(name)), name)

    def test_the_index_lists_every_set_once_and_covers_every_source(self):
        rows = combo_search.all_sets()
        emojis = [r['emoji'] for r in rows]
        self.assertEqual(len(emojis), len(set(emojis)))
        owned = set()
        for name in EXISTING_COMBO_TEMPLATES.values():
            owned |= set(combo_counts.template_sets(name))
        for page in COMBO_PAGES.values():
            owned |= {c[2] for c in page['combos']}
        for page in TAG_PAGES.values():
            owned |= {c[2] for c in page['combos']}
        self.assertEqual(set(emojis), owned)
        for row in rows:
            self.assertTrue(row['url'].startswith('/'), row)

    def test_search_page_is_noindex_and_canonical_to_itself(self):
        for url in ['/emoji-combos/search/', '/emoji-combos/search/?q=ocean', '/emoji-combos/search/?q=zzzzzz']:
            html = self.fetch(url)
            page = self.parse(url)
            self.assertEqual(page.canonical, COMBO_SITE + '/emoji-combos/search/', url)
            self.assertIn('noindex', page.meta.get('robots') or '', url)
            self.assertEqual(len(page.h1), 1, url)
            self.assertIn('role="search"', html, url)

    def test_finds_sets_by_word_and_links_to_their_page(self):
        html = self.fetch('/emoji-combos/search/?q=ocean')
        self.assertIn('data-combo="🏖️🌊☀️"', html)
        self.assertIn('href="/emoji-combos/ocean/"', html)
        self.assertIn('combo-card__copy', html)

    def test_every_word_must_match(self):
        both = combo_search.search_sets('cat cozy')[0]
        self.assertTrue(both)
        self.assertIn('🐱☀️😴', [r['emoji'] for r in both])
        self.assertEqual(combo_search.search_sets('cat zzzzzz'), ([], 0))

    def test_finds_by_pasted_emoji(self):
        results, total = combo_search.search_sets('🐰')
        self.assertGreater(total, 5)
        for row in results:
            self.assertIn('🐰', row['emoji'] + row['label'])

    def test_finds_sets_that_only_live_in_the_older_inline_pages(self):
        results, _total = combo_search.search_sets('ribbon blossom')
        self.assertIn('🎀🌸✨', [r['emoji'] for r in results])

    def test_keyword_page_quick_links_appear_for_a_matching_name(self):
        html = self.fetch('/emoji-combos/search/?q=kawai')
        self.assertIn('href="/emoji-combos/kawaii/"', html)

    def test_empty_and_no_match_queries_are_friendly(self):
        for url in ['/emoji-combos/search/', '/emoji-combos/search/?q=', '/emoji-combos/search/?q=%20%20']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        html = self.fetch('/emoji-combos/search/?q=qqqqqqqq')
        self.assertIn('No sets match', html)
        self.assertNotIn('<div class="combo-card">', html)

    def test_results_are_capped_and_say_so(self):
        results, total = combo_search.search_sets('e')
        self.assertLessEqual(len(results), combo_search.DEFAULT_LIMIT)
        self.assertGreater(total, combo_search.DEFAULT_LIMIT)
        html = self.fetch('/emoji-combos/search/?q=e')
        self.assertIn(f'Showing the first {combo_search.DEFAULT_LIMIT} of {total} sets', html)
        self.assertEqual(html.count('<div class="combo-card">'), combo_search.DEFAULT_LIMIT)

    def test_long_queries_are_trimmed_and_input_is_escaped(self):
        html = self.fetch('/emoji-combos/search/?q=' + 'a' * 500)
        self.assertEqual(len(re.search(r'name="q"[^>]*value="([^"]*)"', html).group(1)), combo_search.MAX_QUERY_LENGTH)
        evil = '<script>alert(1)</script>'
        html = self.client.get('/emoji-combos/search/', {'q': evil}).content.decode()
        self.assertNotIn(evil, html)
        self.assertIn('&lt;script&gt;', html)

    def test_search_never_touches_the_database_or_sets_cookies(self):
        with self.assertNumQueries(0):
            response = self.client.get('/emoji-combos/search/?q=cat')
        self.assertFalse(response.cookies)


class ArtToolPageTests(PageTestCase):
    def test_both_pages_are_complete_pages(self):
        for path in TOOL_PAGES:
            html = self.fetch(path)
            page = self.parse(path)
            self.assertEqual(len(page.h1), 1, path)
            self.assertEqual(page.canonical, COMBO_SITE + path, path)
            self.assertEqual(page.meta['og:url'], COMBO_SITE + path, path)
            title = _clean(page.title)
            meta = page.meta['description']
            self.assertTrue(30 <= len(title) <= 60, f'{path} title is {len(title)}: {title}')
            self.assertTrue(140 <= len(meta) <= 155, f'{path} meta is {len(meta)}: {meta}')
            self.assertEqual(page.meta['og:title'], title, path)
            self.assertEqual(page.meta['og:description'], meta, path)
            self.assertNotIn('noindex', page.meta.get('robots') or '', path)
            faq_blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
            self.assertEqual(len(faq_blocks), 1, path)
            shown = len(re.findall(r'<details class="faq-item[ "]', html))
            self.assertGreater(shown, 0, path)
            self.assertEqual(len(faq_blocks[0]['mainEntity']), shown, path)

    def test_pages_link_to_each_other_and_to_the_combo_hub(self):
        editor, generator = self.body_links('/emoji-art-editor/'), self.body_links('/dot-art-generator/')
        self.assertIn('/dot-art-generator/', editor)
        self.assertIn('/emoji-combos/', editor)
        self.assertIn('/emoji-art-editor/', generator)
        self.assertIn('/emoji-combos/', generator)

    def test_nav_and_sitemap_list_both_tools(self):
        html = self.fetch('/')
        header = html[html.index('<header'):html.index('</header>')]
        for path in TOOL_PAGES:
            self.assertEqual(header.count(f'href="{path}"'), 2, f'{path}: expected nav + drawer link')
        response = self.client.get('/sitemap.xml')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        for path in TOOL_PAGES:
            self.assertIn(COMBO_SITE + path, locs, path)

    def test_each_page_loads_its_script_and_the_file_exists(self):
        for path, script in [('/emoji-art-editor/', 'emoji_art_editor.js'), ('/dot-art-generator/', 'dot_art_generator.js')]:
            self.assertIn(f'kitchen/js/{script}', self.fetch(path), path)
            self.assertTrue((STATIC_JS / script).is_file(), script)

    def test_every_element_the_scripts_look_up_exists_in_the_page(self):
        for path, script in [('/emoji-art-editor/', 'emoji_art_editor.js'), ('/dot-art-generator/', 'dot_art_generator.js')]:
            html = self.fetch(path)
            source = (STATIC_JS / script).read_text(encoding='utf-8')
            ids = set(re.findall(r"getElementById\('([^']+)'\)", source))
            self.assertGreater(len(ids), 8, script)
            for element_id in ids:
                self.assertIn(f'id="{element_id}"', html, f'{script} needs #{element_id} on {path}')

    def test_editor_buttons_all_have_a_handler(self):
        html = self.fetch('/emoji-art-editor/')
        source = (STATIC_JS / 'emoji_art_editor.js').read_text(encoding='utf-8')
        actions = set(re.findall(r'data-ea-action="([^"]+)"', html))
        self.assertGreaterEqual(len(actions), 10)
        for action in actions:
            self.assertRegex(source, rf"[\s,{{](?:{re.escape(action)}|'{re.escape(action)}')\s*:", f'no handler for {action}')
        for tool in set(re.findall(r'data-ea-tool="([^"]+)"', html)):
            self.assertIn(f"'{tool}'", source, tool)
        for feature in ('undo', 'redo', 'cropToFit', 'addPadding', 'importText', 'copyArt', 'downloadPng', 'flood', 'ctrlKey'):
            self.assertIn(feature, source, feature)

    def test_generator_modes_and_controls_exist_in_both_page_and_script(self):
        html = self.fetch('/dot-art-generator/')
        source = (STATIC_JS / 'dot_art_generator.js').read_text(encoding='utf-8')
        for mode in ('dither', 'threshold', 'lines'):
            self.assertIn(f'<option value="{mode}"', html, mode)
            self.assertIn(f"'{mode}'", source, mode)
        for slider in ('da-width', 'da-threshold', 'da-contrast', 'da-edge'):
            self.assertIn(f'id="{slider}"', html, slider)
        self.assertIn('0x2800', source)

    def test_images_and_drawings_never_leave_the_browser(self):
        for script in ('emoji_art_editor.js', 'dot_art_generator.js'):
            source = (STATIC_JS / script).read_text(encoding='utf-8')
            for network in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'FormData', 'localStorage', 'document.cookie'):
                self.assertNotIn(network, source, f'{script} uses {network}')
        for path in TOOL_PAGES:
            self.assertFalse(self.client.get(path).cookies, path)
            self.assertNotIn('<form method="post"', self.fetch(path), path)


# ── Mood finder, the "Others" menu and mobile ────────────────────────────────

from . import mood as mood_engine

MOOD_PAGE = '/emoji-combos/mood/'
STYLE_CSS = Path(settings.BASE_DIR) / 'kitchen/static/kitchen/css/style.css'


def _css():
    return STYLE_CSS.read_text(encoding='utf-8')


def _rule(css, selector):
    """The declarations of every plain rule for a selector (base and phone rules together), e.g. '.mood-chip'."""
    found = re.findall(r'(?m)^\s*' + re.escape(selector) + r'\s*\{([^}]*)\}', css)
    assert found, f'no rule for {selector}'
    return ';'.join(found)


class MoodEngineTests(SimpleTestCase):
    def test_every_mood_is_fully_described(self):
        self.assertGreaterEqual(len(mood_engine.MOODS), 25)
        for key, m in mood_engine.MOODS.items():
            self.assertEqual(m['key'], key)
            self.assertTrue(m['label'] and m['icon'] and m['tagline'], key)
            self.assertGreaterEqual(len(m['words']), 6, key)
            self.assertGreaterEqual(len(m['lead']), 4, key)
            self.assertGreaterEqual(len(m['support']), 5, key)
            self.assertGreaterEqual(len(m['accent']), 5, key)
            self.assertEqual(len(m['sets']), 3, key)
            self.assertEqual(len(m['mashups']), 2, key)
            self.assertGreaterEqual(len(m['terms']), 3, key)
            if m['opposite']:
                self.assertIn(m['opposite'], mood_engine.MOODS, key)
                self.assertNotEqual(m['opposite'], key, key)

    def test_pools_sets_and_pairs_are_clean(self):
        for key, m in mood_engine.MOODS.items():
            for pool in ('lead', 'support', 'accent'):
                self.assertEqual(len(m[pool]), len(set(m[pool])), f'{key} {pool} repeats an emoji')
                for emoji in m[pool]:
                    self.assertFalse(emoji.isascii(), (key, pool, emoji))
                    self.assertFalse(emoji.isspace(), (key, pool, emoji))
            labels = [label for label, _ in m['sets']]
            self.assertEqual(len(labels), len(set(labels)), key)
            for _label, emoji_set in m['sets']:
                self.assertFalse(emoji_set.isascii(), (key, emoji_set))
                self.assertFalse(any(ch.isascii() and ch.isalnum() for ch in emoji_set), (key, emoji_set))
            for first, second in m['mashups']:
                self.assertTrue(views.combo_image_url(first, second), f'{key}: {first} + {second} has no Emoji Kitchen pair')

    def test_each_mood_is_reachable_from_every_one_of_its_words(self):
        for key, m in mood_engine.MOODS.items():
            for word in m['words']:
                self.assertIn(key, mood_engine.detect_moods(word), f'"{word}" does not reach {key}')

    def test_the_one_tap_chips_all_work(self):
        self.assertEqual(len(mood_engine.CHIP_MOODS), len(set(mood_engine.CHIP_MOODS)))
        for key in mood_engine.CHIP_MOODS:
            self.assertEqual(mood_engine.detect_moods(key)[0], key, key)

    def test_negation_flips_a_mood_or_drops_it(self):
        self.assertEqual(mood_engine.detect_moods('not happy at all'), ['sad'])
        self.assertEqual(mood_engine.detect_moods("I'm not tired"), ['motivated'])
        self.assertEqual(mood_engine.detect_moods("i don't feel sad"), ['happy'])
        self.assertEqual(mood_engine.detect_moods('no worries'), ['chill'])
        self.assertEqual(mood_engine.detect_moods('not hungry'), [])

    def test_phrases_and_contractions(self):
        self.assertEqual(mood_engine.detect_moods("I can't wait!"), ['excited'])
        self.assertEqual(mood_engine.detect_moods("I can't stop laughing"), ['silly'])
        self.assertEqual(mood_engine.detect_moods('feeling heartbroken after the breakup'), ['heartbroken'])
        self.assertEqual(mood_engine.detect_moods("I’m so done"), ['angry'])     # curly apostrophe and a phrase

    def test_two_moods_and_intensity(self):
        both = mood_engine.detect_moods('tired but happy')
        self.assertEqual(set(both), {'tired', 'happy'})
        self.assertEqual(mood_engine.detect_moods('so tired and happy')[0], 'tired')
        self.assertLessEqual(len(mood_engine.detect_moods('happy sad angry tired hungry silly')), mood_engine.MAX_MOODS)

    def test_inflections_match_but_look_alike_words_do_not(self):
        for text in ('I am worrying', "I'm worried", 'loving this', 'this is lovely', 'so excited', 'feeling cosy'):
            self.assertTrue(mood_engine.detect_moods(text), text)
        for text in ('windy weather', 'madam', 'I made a cake', 'the wind blew', 'saddle up', 'a bluebird'):
            self.assertEqual(mood_engine.detect_moods(text), [], text)

    def test_an_emoji_in_the_text_is_a_hint(self):
        self.assertEqual(mood_engine.detect_moods('😭'), ['sad'])
        self.assertEqual(mood_engine.detect_moods('🥳'), ['party'])
        self.assertEqual(mood_engine.detect_moods('so tired 😭')[0], 'tired')

    def test_nothing_recognised_or_empty_gives_no_mood(self):
        for text in ('', '   ', 'asdfgh qwerty', '12345', '???'):
            self.assertEqual(mood_engine.detect_moods(text), [], text)

    def test_clean_text(self):
        self.assertEqual(mood_engine.clean_text('  happy \n\t  me  '), 'happy me')
        self.assertEqual(mood_engine.clean_text('a\x00b\x07c'), 'abc')
        self.assertEqual(len(mood_engine.clean_text('x' * 1000)), mood_engine.MAX_TEXT_LENGTH)
        self.assertEqual(mood_engine.clean_text(None), '')

    def test_results_are_deterministic_and_shuffle_changes_them(self):
        first = mood_engine.find_combos('tired but happy', 0)
        again = mood_engine.find_combos('tired but happy', 0)
        other = mood_engine.find_combos('tired but happy', 1)
        self.assertEqual(first['generated'], again['generated'])
        self.assertEqual(first['library'], again['library'])
        self.assertNotEqual(first['generated'], other['generated'])
        self.assertEqual(first['picks'], other['picks'])          # the hand-written picks never change

    def test_generated_combos_are_valid_and_from_the_moods(self):
        result = mood_engine.find_combos('tired but happy', 0)
        keys = [m['key'] for m in result['moods']]
        pool = {e for k in keys for p in ('lead', 'support', 'accent') for e in mood_engine.MOODS[k][p]}
        generated = [g['emoji'] for g in result['generated']]
        self.assertEqual(len(generated), mood_engine.GENERATED_COUNT)
        self.assertEqual(len(generated), len(set(generated)))
        picks = {p['emoji'] for p in result['picks']}
        library = {r['emoji'] for r in result['library']}
        self.assertFalse(set(generated) & picks)
        self.assertFalse(set(generated) & library)
        self.assertFalse(picks & library)
        for combo in generated:
            self.assertFalse(combo.isascii(), combo)
            remaining = combo
            for emoji in sorted(pool, key=len, reverse=True):
                remaining = remaining.replace(emoji, '')
            self.assertEqual(remaining, '', f'{combo} uses an emoji outside the chosen moods')

    def test_library_sets_exist_on_the_site(self):
        known = {r['emoji'] for r in combo_search.all_sets()}
        for text in ('tired but happy', 'in love', 'hungry', 'stressed about exams', 'cozy rainy day'):
            result = mood_engine.find_combos(text)
            self.assertTrue(result['library'], text)
            self.assertLessEqual(len(result['library']), mood_engine.LIBRARY_COUNT)
            for row in result['library']:
                self.assertIn(row['emoji'], known, text)

    def test_nothing_recognised_falls_back_to_friendly_picks(self):
        result = mood_engine.find_combos('asdfgh qwerty')
        self.assertFalse(result['matched'])
        self.assertTrue(result['picks'] and result['generated'])
        self.assertTrue(mood_engine.find_combos('so tired')['matched'])

    def test_mashups_are_valid_and_limited(self):
        for text in ('tired but happy', 'in love', 'angry', 'asdfgh'):
            pairs = mood_engine.find_combos(text)['mashups']
            self.assertTrue(1 <= len(pairs) <= 3, text)
            self.assertEqual(len(pairs), len(set(pairs)), text)
            for first, second in pairs:
                self.assertTrue(views.combo_image_url(first, second), (text, first, second))

    def test_hostile_input_is_cheap_and_safe(self):
        import time
        started = time.perf_counter()
        for text in ('happy ' * 200, 'not ' * 200 + 'happy', "'" * 500, '🥳' * 300, '‮' + 'sad' * 100):
            result = mood_engine.find_combos(text)
            self.assertLessEqual(len(result['text']), mood_engine.MAX_TEXT_LENGTH)
            self.assertLessEqual(len(result['moods']), mood_engine.MAX_MOODS)
        self.assertLess(time.perf_counter() - started, 2.0)


class MoodPageTests(PageTestCase):
    def test_landing_page_is_a_complete_indexable_page(self):
        html = self.fetch(MOOD_PAGE)
        page = self.parse(MOOD_PAGE)
        self.assertEqual([_clean(h) for h in page.h1], ['Find an Emoji Combo for Your Mood'])
        title, meta = _clean(page.title), page.meta['description']
        self.assertTrue(30 <= len(title) <= 60, f'title is {len(title)}: {title}')
        self.assertTrue(140 <= len(meta) <= 155, f'meta is {len(meta)}: {meta}')
        self.assertEqual(page.canonical, COMBO_SITE + MOOD_PAGE)
        self.assertEqual(page.meta['og:url'], COMBO_SITE + MOOD_PAGE)
        self.assertNotIn('noindex', page.meta.get('robots') or '')
        faq_blocks = [b for b in _ld_blocks(html) if b.get('@type') == 'FAQPage']
        self.assertEqual(len(faq_blocks), 1)
        self.assertEqual(len(faq_blocks[0]['mainEntity']), len(re.findall(r'<details class="faq-item[ "]', html)))
        self.assertNotIn('class="mood-results"', html)
        self.assertEqual(html.count('class="mood-chip"'), len(mood_engine.CHIP_MOODS))

    def test_results_page_shows_the_moods_and_every_group(self):
        url = MOOD_PAGE + '?mood=tired+but+happy'
        html = self.fetch(url)
        page = self.parse(url)
        self.assertIn('noindex', page.meta.get('robots') or '')
        self.assertEqual(page.canonical, COMBO_SITE + MOOD_PAGE)
        self.assertIn('We picked up:', html)
        self.assertEqual(html.count('class="mood-pill"'), 2)
        for heading in ('Top picks for you', 'Made for your mood', 'More ready-made sets that fit', 'Emoji mashup images for your mood'):
            self.assertIn(heading, html)
        self.assertGreaterEqual(html.count('class="combo-card__copy"'), 20)
        self.assertIn('data-copy-grid', html)
        self.assertEqual(len(re.findall(r'class="mood-mashup" href="/\?emoji1=', html)), 3)
        self.assertIn('value="tired but happy"', html)

    def test_every_set_can_be_copied_as_text_or_as_an_image(self):
        html = self.fetch(MOOD_PAGE + '?mood=tired+but+happy')
        text_buttons = html.count('class="combo-card__copy"')
        image_buttons = len(re.findall(r'<button type="button" class="mood-imgbtn" data-combo-image="', html))
        self.assertGreaterEqual(image_buttons, 20)
        self.assertEqual(text_buttons, image_buttons, 'each set has both a text and an image button')
        self.assertIn('kitchen/js/combo_image.js', html)

    def test_mashups_show_their_picture_with_copy_download_and_mixer_buttons(self):
        html = self.fetch(MOOD_PAGE + '?mood=tired+but+happy')
        cards = re.findall(r'<div class="mood-mashup-card".*?</div>\s*</div>', html, re.S)
        self.assertEqual(len(cards), 3)
        for card in cards:
            self.assertRegex(card, r'<img class="mood-mashup-card__img" src="https://www\.gstatic\.com/android/keyboard/emojikitchen/')
            self.assertIn('data-mashup-action="copy"', card)
            self.assertIn('data-mashup-action="download"', card)
            self.assertRegex(card, r'class="mood-mashup" href="/\?emoji1=')
            self.assertRegex(card, r'data-emoji1="[^"]+" data-emoji2="[^"]+" data-image="https://www\.gstatic\.com/')
        self.assertIn(f'data-sticker-version="{stickers.STICKER_VERSION}"', html)

    def test_the_image_script_never_copies_emojis_as_text_and_sends_nothing_typed(self):
        script = (STATIC_JS / 'combo_image.js').read_text(encoding='utf-8')
        for banned in ('writeText', 'execCommand', 'location.search', 'mood='):
            self.assertNotIn(banned, script, banned)
        for needle in ("'image/png'", 'new ClipboardItem', '/api/sticker/?', "window.isSecureContext === false",
                       'Use Download image instead'):
            self.assertIn(needle, script, needle)

    def test_the_home_mood_box_cannot_grow_wider_than_the_phone(self):
        css = _css()
        self.assertIn('.hero .mood-form{width:100%;max-width:640px;min-width:0', css)
        self.assertIn('.mood-grid .combo-card{width:auto;min-width:0', css)

    def test_results_match_the_engine(self):
        result = mood_engine.find_combos('tired but happy', 0)
        html = self.fetch(MOOD_PAGE + '?mood=tired+but+happy')
        for row in result['picks'] + result['generated'] + result['library']:
            self.assertIn(f'data-combo="{row["emoji"]}"', html)

    def test_shuffle_gives_new_combos_and_a_next_link(self):
        first = self.fetch(MOOD_PAGE + '?mood=happy')
        self.assertRegex(first, r'href="/emoji-combos/mood/\?mood=happy&amp;shuffle=1#results" rel="nofollow"')
        second = self.fetch(MOOD_PAGE + '?mood=happy&shuffle=1')
        for row in mood_engine.find_combos('happy', 1)['generated']:
            self.assertIn(f'data-combo="{row["emoji"]}"', second)
        self.assertNotEqual(first, second)
        self.assertIn('shuffle=2#results', second)

    def test_bad_shuffle_values_are_safe(self):
        for value in ('abc', '-5', '', '1.5', '99999999999999999999'):
            self.assertEqual(self.client.get(MOOD_PAGE, {'mood': 'happy', 'shuffle': value}).status_code, 200, value)
        self.assertIn('shuffle=0#results', self.fetch(MOOD_PAGE + f'?mood=happy&shuffle={mood_engine.MAX_SHUFFLE}'))

    def test_empty_or_blank_query_shows_the_landing_page(self):
        for url in (MOOD_PAGE + '?mood=', MOOD_PAGE + '?mood=%20%20%20', MOOD_PAGE + '?other=1'):
            html = self.fetch(url)
            self.assertNotIn('class="mood-results"', html, url)
            self.assertNotIn('noindex', self.parse(url).meta.get('robots') or '', url)

    def test_unrecognised_text_gets_a_friendly_message_and_still_has_results(self):
        html = self.fetch(MOOD_PAGE + '?mood=asdfgh+qwerty')
        self.assertIn('We could not read a clear mood', html)
        self.assertNotIn('We picked up:', html)
        self.assertGreaterEqual(html.count('class="combo-card__copy"'), 10)

    def test_what_the_visitor_types_is_escaped(self):
        evil = '"><script>alert(1)</script>'
        html = self.client.get(MOOD_PAGE, {'mood': evil}).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_long_text_is_trimmed_in_the_box(self):
        html = self.fetch(MOOD_PAGE + '?mood=' + 'happy+' * 100)
        value = re.search(r'name="mood"[^>]*value="([^"]*)"', html).group(1)
        self.assertLessEqual(len(value), mood_engine.MAX_TEXT_LENGTH)

    def test_no_database_no_cookies_and_nothing_stored(self):
        with self.assertNumQueries(0):
            response = self.client.get(MOOD_PAGE + '?mood=tired+but+happy')
        self.assertFalse(response.cookies)

    def test_the_box_is_on_the_hero_hub_ready_made_and_mood_pages(self):
        for path, field_id in [('/', 'hero-mood-input'), ('/emoji-combos/', 'hub-mood-input'),
                               (READY_MADE, 'ready-mood-input'), (MOOD_PAGE, 'mood-input')]:
            html = self.fetch(path)
            self.assertEqual(html.count('class="mood-form"'), 1, path)
            self.assertIn(f'id="{field_id}"', html, path)
            self.assertIn(f'for="{field_id}"', html, path)
            self.assertIn('action="/emoji-combos/mood/"', html, path)
            self.assertIn('Find an emoji combo according to your mood', html, path)
            self.assertIn(f'maxlength="{mood_engine.MAX_TEXT_LENGTH}"', html, path)
            self.assertIn('Explain your mood', html, path)

    def test_the_homepage_box_sits_inside_the_hero(self):
        html = self.fetch('/')
        hero = html[html.index('<section class="hero">'):html.index('</section>', html.index('<section class="hero">'))]
        self.assertIn('class="mood-form"', hero)
        self.assertLess(hero.index('Start Mixing'), hero.index('class="mood-form"'))

    def test_ids_are_unique_on_every_page_with_the_box(self):
        for path in ['/', '/emoji-combos/', READY_MADE, MOOD_PAGE]:
            ids = re.findall(r'\sid="([^"]+)"', self.fetch(path))
            self.assertEqual(len(ids), len(set(ids)), f'{path} repeats an id: {[i for i in set(ids) if ids.count(i) > 1]}')

    def test_mood_page_is_in_the_sitemap_but_result_urls_are_not(self):
        response = self.client.get('/sitemap.xml')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locs = [u.text for u in ET.fromstring(response.content).findall('s:url/s:loc', ns)]
        self.assertIn(COMBO_SITE + MOOD_PAGE, locs)
        self.assertFalse([loc for loc in locs if 'mood=' in loc])

    def test_mood_is_never_a_keyword_page(self):
        self.assertIn('mood', RESERVED_SLUGS)
        self.assertNotIn('mood', TAG_PAGES)

    def test_links_in_and_out(self):
        links = self.body_links(MOOD_PAGE)
        for needed in ('/emoji-combos/', READY_MADE, '/emoji-art-editor/', '/'):
            self.assertIn(needed, links, needed)
        for anchors in links.values():
            for anchor in anchors:
                self.assertNotIn(anchor, WEAK_ANCHORS)


class OthersMenuTests(PageTestCase):
    def header(self, path):
        html = self.fetch(path)
        return html[html.index('<header'):html.index('</header>')]

    def test_every_page_has_the_others_menu_with_the_ready_made_link(self):
        for path in ALL_PAGES + TAG_PATHS + TOOL_PAGES + [MOOD_PAGE]:
            header = self.header(path)
            self.assertEqual(header.count('id="nav-others-btn"'), 1, path)
            button = re.search(r'<button[^>]*id="nav-others-btn"[^>]*>(.*?)</button>', header, re.S)
            self.assertEqual(button.group(1).strip(), 'Others', path)
            self.assertIn('aria-haspopup="true"', button.group(0), path)
            self.assertIn('aria-expanded="false"', button.group(0), path)
            menu = re.search(r'<ul class="nav__dropdown-menu" id="nav-others-menu"[^>]*>(.*?)</ul>', header, re.S)
            self.assertIsNotNone(menu, path)
            links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', menu.group(1))
            self.assertEqual(links, [(READY_MADE, '🎭 Ready Made Emoji Combos'), ('/emoji-kitchen-guide/', '📖 Emoji Kitchen Guide')], path)

    def test_others_is_the_last_menu_item_after_blog(self):
        header = self.header('/')
        nav = header[header.index('<ul class="nav__links">'):header.index('class="nav__cta')]
        self.assertLess(nav.index('>Blog</a>'), nav.index('id="nav-others-btn"'))
        self.assertEqual(nav.count('nav__item--dropdown'), 3)      # keyboard, combos, others

    def test_mobile_menu_has_an_others_section(self):
        for path in ('/', '/emoji-combos/', READY_MADE, MOOD_PAGE):
            header = self.header(path)
            drawer = header[header.index('id="nav-drawer"'):]
            self.assertIn('<span class="nav__drawer-heading">Others</span>', drawer, path)
            self.assertLess(drawer.index('>📝 Blog</a>'), drawer.index('nav__drawer-heading'), path)
            self.assertRegex(drawer, rf'<a href="{READY_MADE}" class="nav__drawer-link nav__drawer-sublink" data-close-drawer>🎭 Ready Made Emoji Combos</a>')
            self.assertRegex(drawer, r'<a href="/emoji-kitchen-guide/" class="nav__drawer-link nav__drawer-sublink" data-close-drawer>📖 Emoji Kitchen Guide</a>')
            self.assertLess(drawer.index('Ready Made Emoji Combos'), drawer.index('Emoji Kitchen Guide'), path)

    def test_hover_and_click_both_open_it_and_focus_alone_cannot_trap_it_open(self):
        css = _css()
        self.assertIn('.nav__item--others:hover .nav__dropdown-menu', css)
        self.assertIn('.nav__item--others.is-open .nav__dropdown-menu', css)
        self.assertIn('.nav__item--others:focus-within:not(.is-open):not(:hover) .nav__dropdown-menu', css)
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/site.js').read_text(encoding='utf-8')
        for needle in ("'nav-others-btn'", "'is-open'", 'aria-expanded', "'Escape'", 'othersItem.contains(e.target)'):
            self.assertIn(needle, js, needle)

    def test_the_desktop_menu_switches_to_the_hamburger_before_seven_items_overflow(self):
        css = _css()
        self.assertRegex(css, r'@media\(max-width:1140px\)\{\s*\.nav__links,\.nav__cta\{display:none\}')
        self.assertNotRegex(css, r'@media\(max-width:1040px\)\{\s*\.nav__links')
        self.assertIn('white-space:nowrap', _rule(css, '.nav__others'))


class MobileUiTests(PageTestCase):
    def test_every_page_declares_a_mobile_viewport(self):
        for path in ['/', '/emoji-combos/', READY_MADE, MOOD_PAGE, '/emoji-combos/kawaii/', '/emoji-art-editor/']:
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0" />', self.fetch(path), path)

    def test_text_inputs_are_16px_so_iphones_do_not_zoom(self):
        css = _css()
        self.assertRegex(_rule(css, '.mood-form__input'), r'font-size:1rem')
        phones = css[css.rindex('.hero{padding:56px 0 48px}'):]
        for selector in ('.combo-search{font-size:16px', '.ea-num,.ea-select,.ea-textarea,.ea-brushrow .combo-search{font-size:16px'):
            self.assertIn(selector, phones, selector)

    def test_tap_targets_are_at_least_44px_on_the_new_controls(self):
        css = _css()
        for selector, minimum in [('.mood-chip', 44), ('.mood-form__input', 52), ('.mood-form__btn', 52),
                                  ('.mood-mashup', 44), ('.nav__drawer-link', 48), ('.nav__hamburger', 44)]:
            match = re.search(r'min-height:(\d+)px', _rule(css, selector))
            self.assertIsNotNone(match, selector)
            self.assertGreaterEqual(int(match.group(1)), minimum, selector)
        phones = css[css.rindex('.hero{padding:56px 0 48px}'):]
        for needle in ('.combo-card__copy{min-height:44px', '.combo-filter__btn{flex:0 0 auto;min-height:40px',
                       '.combo-random-btn{width:100%;min-height:46px', '.mood-shuffle{width:100%;min-height:44px'):
            self.assertIn(needle, phones, needle)

    def test_chips_and_filters_scroll_sideways_on_phones_instead_of_stacking(self):
        css = _css()
        self.assertIn('overflow-x:auto', _rule(css, '.mood-chips'))
        phones = css[css.rindex('.hero{padding:56px 0 48px}'):]
        self.assertRegex(phones, r'\.combo-filter\{\s*flex-wrap:nowrap;overflow-x:auto')

    def test_the_mood_form_stacks_and_the_grids_use_two_columns_on_phones(self):
        phones = _css()[_css().rindex('.hero{padding:56px 0 48px}'):]
        self.assertIn('.mood-form__row{flex-direction:column}', phones)
        self.assertIn('.mood-form__btn{width:100%}', phones)
        self.assertIn('.mood-grid{grid-template-columns:repeat(2,1fr)', phones)
        self.assertIn('.combo-grid{grid-template-columns:repeat(2,1fr)', phones)

    def test_the_mobile_menu_scrolls_when_it_is_taller_than_the_screen(self):
        rule = _rule(_css(), '.nav__drawer')
        self.assertIn('overflow-y:auto', rule)
        self.assertIn('100dvh', rule)

    def test_the_mood_box_is_usable_without_javascript(self):
        html = self.fetch(MOOD_PAGE)
        form = re.search(r'<form class="mood-form".*?</form>', html, re.S).group(0)
        self.assertIn('method="get"', form)
        self.assertEqual(len(re.findall(r'<a class="mood-chip" href="/emoji-combos/mood/\?mood=[a-z]+">', form)), len(mood_engine.CHIP_MOODS))
        self.assertIn('enterkeyhint="search"', form)
        self.assertIn('autocomplete="off"', form)

    def test_copy_works_on_the_search_and_mood_pages_through_one_shared_script(self):
        script = (STATIC_JS / 'combo_copy.js').read_text(encoding='utf-8')
        for needle in ('navigator.clipboard', 'execCommand', '[data-copy-grid] .combo-card__copy', 'Copied'):
            self.assertIn(needle, script, needle)
        for network in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'localStorage'):
            self.assertNotIn(network, script, network)
        for url in ('/emoji-combos/search/?q=cat', MOOD_PAGE + '?mood=happy'):
            html = self.fetch(url)
            self.assertIn('kitchen/js/combo_copy.js', html, url)
            self.assertIn('data-copy-grid', html, url)
            self.assertNotIn('navigator.clipboard', html, f'{url} should use the shared script, not an inline copy')


# ── Download as a sticker ────────────────────────────────────────────────────

import io as _io
import os as _os
import random as _random
from unittest import mock

from PIL import Image as _Image, ImageDraw as _ImageDraw

from . import stickers

MAIN_JS = Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js'
STICKER_URL = 'https://www.gstatic.com/android/keyboard/emojikitchen/20201001/u1f602/u1f602_u1f480.png'


def _mashup_png(size=(534, 534), box=(60, 80, 470, 440), color=(230, 60, 60, 255), noisy=False, mode='RGBA'):
    """A stand-in for a Google mashup: a coloured blob on a transparent background."""
    image = _Image.new('RGBA', size, (0, 0, 0, 0))
    if noisy:
        grain = _Image.frombytes('RGB', size, _os.urandom(size[0] * size[1] * 3)).convert('RGBA')
        mask = _Image.new('L', size, 0)
        _ImageDraw.Draw(mask).ellipse(box, fill=255)
        image.paste(grain, (0, 0), mask)
    else:
        _ImageDraw.Draw(image).ellipse(box, fill=color)
    if mode == 'P':
        image = image.quantize(colors=16, method=_Image.Quantize.FASTOCTREE)
    out = _io.BytesIO()
    image.save(out, 'PNG')
    return out.getvalue()


def _alpha_box(image, threshold=8):
    return image.getchannel('A').point(lambda v: 255 if v > threshold else 0).getbbox()


class _FakeResponse:
    def __init__(self, body=b'', status=200, content_type='image/png', chunk=65536):
        self.status_code = status
        self.headers = {'Content-Type': content_type}
        self._body, self._chunk = body, chunk
        self.closed = False
        self.chunks_read = 0

    def iter_content(self, size):
        for start in range(0, len(self._body), self._chunk):
            self.chunks_read += 1
            yield self._body[start:start + self._chunk]

    def close(self):
        self.closed = True


class StickerImageTests(SimpleTestCase):
    def test_output_is_a_512_square_with_transparent_corners_and_an_opaque_middle(self):
        art = stickers.build_sticker_image(_mashup_png())
        self.assertEqual(art.size, (512, 512))
        self.assertEqual(art.mode, 'RGBA')
        for corner in [(0, 0), (511, 0), (0, 511), (511, 511)]:
            self.assertEqual(art.getpixel(corner)[3], 0, corner)
        middle = art.getpixel((256, 256))
        self.assertEqual(middle[3], 255)
        self.assertGreater(middle[0], 200)
        self.assertLess(middle[1], 100)

    def test_artwork_is_centred_and_keeps_a_clear_margin(self):
        art = stickers.build_sticker_image(_mashup_png())
        # the opaque sticker (artwork, white outline and grey edge) is centred; the soft shadow is faint and is left out
        left, top, right, bottom = _alpha_box(art, threshold=200)
        self.assertLessEqual(abs((left + right) - 512), 3)
        self.assertLessEqual(abs((top + bottom) - 512), 3)
        self.assertGreaterEqual(min(left, top, 512 - right, 512 - bottom), 12)
        alpha = art.getchannel('A')
        edge = 4    # nothing at all, not even shadow, touches the very edge of the file
        for strip in [(0, 0, 512, edge), (0, 512 - edge, 512, 512), (0, 0, edge, 512), (512 - edge, 0, 512, 512)]:
            self.assertEqual(alpha.crop(strip).getextrema()[1], 0, f'something is drawn in the outer {edge}px strip {strip}')

    def test_there_is_a_white_outline_of_about_the_right_width(self):
        art = stickers.build_sticker_image(_mashup_png())
        row = 256
        pixels = [art.getpixel((x, row)) for x in range(512)]
        first_art = next(x for x, p in enumerate(pixels) if p[3] == 255 and p[0] > 200 and p[1] < 100)
        outside = pixels[first_art - 4]
        self.assertGreater(outside[3], 200)
        self.assertTrue(all(channel > 240 for channel in outside[:3]), outside)
        width = 0
        for p in reversed(pixels[:first_art]):
            if p[3] > 200 and all(channel > 240 for channel in p[:3]):
                width += 1
            else:
                break
        self.assertTrue(stickers.OUTLINE - 3 <= width <= stickers.OUTLINE + 4, f'white outline is {width}px wide')

    def test_the_sticker_is_visibly_a_sticker_on_a_plain_white_page(self):
        # Regression: a white outline on a white page is invisible, which made stickers look like plain images.
        art = stickers.build_sticker_image(_mashup_png())
        page = _Image.new('RGBA', art.size, (255, 255, 255, 255))
        page.alpha_composite(art)
        row = [page.convert('RGB').getpixel((x, 256)) for x in range(512)]
        first_art = next(x for x, p in enumerate(row) if p[0] > 200 and p[1] < 100)
        outline = row[first_art - 12:first_art]
        luminance = [sum(p) / 3 for p in outline]
        self.assertLess(min(luminance), 225, 'no grey edge shows against a white page')
        self.assertGreater(max(luminance), 250, 'the white border itself has gone')
        below = page.convert('RGB')
        bottom = max(y for y in range(512) if art.getpixel((256, y))[3] > 200)
        shadow = [sum(below.getpixel((256, y))) / 3 for y in range(bottom + 1, bottom + 9)]
        self.assertLess(min(shadow), 245, 'no soft shadow shows below the sticker on a white page')
        self.assertGreater(min(shadow), 120, 'the shadow is too heavy')

    def test_the_shadow_is_soft_and_faint(self):
        art = stickers.build_sticker_image(_mashup_png())
        alpha = art.getchannel('A')
        bottom = max(y for y in range(512) if alpha.getpixel((256, y)) > 200)
        # start a few pixels past the sticker's own anti-aliased edge, so only the shadow is measured
        faint = [alpha.getpixel((256, y)) for y in range(bottom + 4, 512) if alpha.getpixel((256, y)) > 0]
        self.assertTrue(faint, 'there is no shadow')
        self.assertLessEqual(max(faint), int(255 * stickers.SHADOW_OPACITY) + 8)
        self.assertEqual(faint, sorted(faint, reverse=True), 'the shadow should fade out smoothly, not stripe')

    def test_wide_tall_and_small_sources_all_fill_the_frame(self):
        for size, box in [((600, 200), (0, 0, 599, 199)), ((200, 600), (0, 0, 199, 599)), ((100, 100), (5, 5, 95, 95))]:
            art = stickers.build_sticker_image(_mashup_png(size=size, box=box))
            left, top, right, bottom = _alpha_box(art)
            longest = max(right - left, bottom - top)
            self.assertTrue(470 <= longest <= 500, f'{size}: longest side is {longest}')

    def test_palette_png_like_googles_works(self):
        art = stickers.build_sticker_image(_mashup_png(mode='P'))
        self.assertEqual(art.getpixel((0, 0))[3], 0)
        self.assertEqual(art.getpixel((256, 256))[3], 255)

    def test_bad_sources_are_rejected(self):
        blank = _io.BytesIO()
        _Image.new('RGBA', (50, 50), (0, 0, 0, 0)).save(blank, 'PNG')
        huge = _io.BytesIO()
        _Image.new('1', (5000, 5000)).save(huge, 'PNG')
        for name, data in [('not an image', b'definitely not an image'), ('empty', b''), ('fully transparent', blank.getvalue()),
                           ('too many pixels', huge.getvalue()), ('truncated', _mashup_png()[:40])]:
            with self.assertRaises(stickers.StickerError, msg=name):
                stickers.build_sticker_image(data)


class StickerEncodeTests(SimpleTestCase):
    def setUp(self):
        self.art = stickers.build_sticker_image(_mashup_png())

    def test_webp_is_a_real_webp_512_square_with_transparency_under_100kb(self):
        data = stickers.encode(self.art, 'webp')
        self.assertEqual(data[:4], b'RIFF')
        self.assertEqual(data[8:12], b'WEBP')
        self.assertLessEqual(len(data), 100 * 1024)
        decoded = _Image.open(_io.BytesIO(data))
        self.assertEqual((decoded.format, decoded.size), ('WEBP', (512, 512)))
        rgba = decoded.convert('RGBA')
        self.assertEqual(rgba.getpixel((0, 0))[3], 0)
        self.assertEqual(rgba.getpixel((256, 256))[3], 255)

    def test_webp_is_squeezed_under_the_limit_even_for_very_detailed_art(self):
        noisy = stickers.build_sticker_image(_mashup_png(noisy=True))
        data = stickers.encode(noisy, 'webp')
        lowest = _io.BytesIO()
        noisy.save(lowest, 'WEBP', quality=stickers.WEBP_QUALITIES[-1], method=4)
        self.assertTrue(len(data) <= stickers.MAX_WEBP_BYTES or len(data) == len(lowest.getvalue()),
                        f'{len(data)} bytes is neither under the limit nor the smallest the encoder can do')

    def test_png_is_a_real_png_with_transparency(self):
        data = stickers.encode(self.art, 'png')
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        decoded = _Image.open(_io.BytesIO(data))
        self.assertEqual((decoded.format, decoded.size, decoded.mode), ('PNG', (512, 512), 'RGBA'))
        self.assertEqual(decoded.getpixel((0, 0))[3], 0)

    def test_unknown_format_is_rejected(self):
        for fmt in ('gif', 'jpg', '', 'WEBP'):
            with self.assertRaises(stickers.StickerError, msg=fmt):
                stickers.encode(self.art, fmt)

    def test_the_spec_numbers_are_what_whatsapp_asks_for(self):
        self.assertEqual(stickers.STICKER_SIZE, 512)
        self.assertEqual(stickers.MAX_WEBP_BYTES, 100 * 1024)
        self.assertEqual(stickers.FORMATS, ('webp', 'png'))


class StickerFetchTests(SimpleTestCase):
    def test_only_googles_emoji_kitchen_addresses_are_ever_requested(self):
        bad = [
            'https://evil.example/android/keyboard/emojikitchen/x.png',
            'http://www.gstatic.com/android/keyboard/emojikitchen/20201001/a/a_b.png',
            'https://www.gstatic.com.evil.example/android/keyboard/emojikitchen/a.png',
            'https://www.gstatic.com/android/keyboard/emojikitchen/../../secret.png',
            'https://www.gstatic.com/android/keyboard/emojikitchen/20201001/a/a_b.jpg',
            'https://www.gstatic.com/other/path.png',
            'file:///etc/passwd', '', 'javascript:alert(1)',
        ]
        with mock.patch.object(stickers.requests, 'get') as get:
            for url in bad:
                with self.assertRaises(stickers.StickerError, msg=url):
                    stickers.fetch_source(url)
            get.assert_not_called()

    def test_a_good_address_is_fetched_with_a_timeout_and_the_connection_is_closed(self):
        response = _FakeResponse(b'png-bytes')
        with mock.patch.object(stickers.requests, 'get', return_value=response) as get:
            self.assertEqual(stickers.fetch_source(STICKER_URL), b'png-bytes')
        self.assertEqual(get.call_args.args[0], STICKER_URL)
        self.assertEqual(get.call_args.kwargs['timeout'], stickers.FETCH_TIMEOUT)
        self.assertTrue(response.closed)

    def test_failures_become_sticker_errors_and_still_close_the_connection(self):
        cases = {
            'host error': _FakeResponse(b'', status=404),
            'server error': _FakeResponse(b'', status=500),
            'not an image': _FakeResponse(b'<html>', content_type='text/html'),
        }
        for name, response in cases.items():
            with mock.patch.object(stickers.requests, 'get', return_value=response):
                with self.assertRaises(stickers.StickerError, msg=name):
                    stickers.fetch_source(STICKER_URL)
            self.assertTrue(response.closed, name)
        with mock.patch.object(stickers.requests, 'get', side_effect=stickers.requests.ConnectionError('down')):
            with self.assertRaises(stickers.StickerError):
                stickers.fetch_source(STICKER_URL)
        with mock.patch.object(stickers.requests, 'get', side_effect=stickers.requests.Timeout('slow')):
            with self.assertRaises(stickers.StickerError):
                stickers.fetch_source(STICKER_URL)

    def test_an_oversized_download_is_cut_off_early(self):
        one_mb = 1024 * 1024
        response = _FakeResponse(b'x' * (10 * one_mb), chunk=one_mb)
        with mock.patch.object(stickers.requests, 'get', return_value=response):
            with self.assertRaises(stickers.StickerError):
                stickers.fetch_source(STICKER_URL)
        self.assertLessEqual(response.chunks_read, 4)
        self.assertTrue(response.closed)


class StickerCacheTests(SimpleTestCase):
    def setUp(self):
        stickers.make_sticker.cache_clear()
        self.addCleanup(stickers.make_sticker.cache_clear)

    def test_a_popular_pair_is_built_once(self):
        with mock.patch.object(stickers, 'fetch_source', return_value=_mashup_png()) as fetch:
            first = stickers.make_sticker(STICKER_URL, 'webp')
            second = stickers.make_sticker(STICKER_URL, 'webp')
            self.assertEqual(first, second)
            self.assertEqual(fetch.call_count, 1)
            stickers.make_sticker(STICKER_URL, 'png')
            self.assertEqual(fetch.call_count, 2)       # a different format is a different file


class StickerEndpointTests(PageTestCase):
    def setUp(self):
        super().setUp()
        stickers.make_sticker.cache_clear()
        self.addCleanup(stickers.make_sticker.cache_clear)
        self.fetched = []

        def fake_fetch(url):
            self.fetched.append(url)
            return _mashup_png()

        patcher = mock.patch.object(stickers, 'fetch_source', side_effect=fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get(self, **params):
        return self.client.get('/api/sticker/', params)

    def test_a_supported_pair_downloads_as_a_webp_sticker(self):
        response = self.get(emoji1='😂', emoji2='💀')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/webp')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="emoji-kitchen-sticker-1f480-1f602.webp"')
        self.assertEqual(response['Cache-Control'], 'public, max-age=86400')
        body = response.content
        self.assertEqual((body[:4], body[8:12]), (b'RIFF', b'WEBP'))
        self.assertLessEqual(len(body), 100 * 1024)
        self.assertEqual(_Image.open(_io.BytesIO(body)).size, (512, 512))
        self.assertFalse(response.cookies)

    def test_the_source_comes_from_the_validated_pair_and_nothing_else(self):
        self.get(emoji1='😂', emoji2='💀')
        self.assertEqual(self.fetched, [views.combo_image_url('😂', '💀')])
        self.assertTrue(self.fetched[0].startswith(stickers.ALLOWED_PREFIX))

    def test_the_order_of_the_two_emojis_does_not_matter(self):
        one, two = self.get(emoji1='😂', emoji2='💀'), self.get(emoji1='💀', emoji2='😂')
        self.assertEqual(one.content, two.content)
        self.assertEqual(one['Content-Disposition'], two['Content-Disposition'])

    def test_png_is_available_and_webp_is_the_default(self):
        png = self.get(emoji1='😂', emoji2='💀', format='png')
        self.assertEqual(png['Content-Type'], 'image/png')
        self.assertTrue(png['Content-Disposition'].endswith('.png"'))
        self.assertEqual(png.content[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(self.get(emoji1='😂', emoji2='💀', format='PNG')['Content-Type'], 'image/png')
        self.assertEqual(self.get(emoji1='😂', emoji2='💀', format='webp')['Content-Type'], 'image/webp')
        self.assertEqual(self.get(emoji1='😂', emoji2='💀')['Content-Type'], 'image/webp')

    def test_a_pair_without_a_mashup_is_a_404_and_nothing_is_fetched(self):
        for first, second in [('abc', 'def'), ('😂', 'x'), ('https://evil.example/a.png', '💀')]:
            response = self.get(emoji1=first, emoji2=second)
            self.assertEqual(response.status_code, 404, (first, second))
            self.assertIn('error', response.json())
        self.assertEqual(self.fetched, [])

    def test_bad_requests_get_a_400(self):
        cases = [{}, {'emoji1': '😂'}, {'emoji2': '💀'}, {'emoji1': '', 'emoji2': ''}, {'emoji1': '  ', 'emoji2': '💀'},
                 {'emoji1': '😂', 'emoji2': '💀', 'format': 'gif'}, {'emoji1': '😂', 'emoji2': '💀', 'format': 'jpg'},
                 {'emoji1': '😂' * 40, 'emoji2': '💀'}]
        for params in cases:
            response = self.get(**params)
            self.assertEqual(response.status_code, 400, params)
            self.assertIn('error', response.json())
        self.assertEqual(self.fetched, [])

    def test_only_get_is_allowed(self):
        for method in (self.client.post, self.client.put, self.client.delete):
            self.assertEqual(method('/api/sticker/', {'emoji1': '😂', 'emoji2': '💀'}).status_code, 405)

    def test_an_upstream_failure_is_a_clean_502_that_leaks_nothing(self):
        with mock.patch.object(stickers, 'fetch_source', side_effect=stickers.StickerError('host answered 500 at 10.0.0.5')):
            with self.assertLogs('kitchen.views', level='WARNING') as logs:
                response = self.get(emoji1='😂', emoji2='💀')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {'error': 'Could not make the sticker. Please try again.'})
        self.assertNotIn('10.0.0.5', response.content.decode())
        self.assertIn('10.0.0.5', logs.output[0])           # the detail is logged for the owner

    def test_a_failure_is_not_cached(self):
        with mock.patch.object(stickers, 'fetch_source', side_effect=stickers.StickerError('boom')):
            self.assertEqual(self.get(emoji1='😂', emoji2='💀').status_code, 502)
        self.assertEqual(self.get(emoji1='😂', emoji2='💀').status_code, 200)

    def test_no_database_is_used(self):
        with self.assertNumQueries(0):
            self.get(emoji1='😂', emoji2='💀')

    def test_the_endpoint_never_takes_a_url_from_the_visitor(self):
        for key in ('url', 'src', 'image', 'u'):
            self.client.get('/api/sticker/', {'emoji1': '😂', 'emoji2': '💀', key: 'https://evil.example/x.png'})
        self.assertTrue(all(url.startswith(stickers.ALLOWED_PREFIX) for url in self.fetched))


class StickerDownloadButtonTests(PageTestCase):
    MIXER_PAGES_WITH_BUTTON = ['/', '/emoji-maker/', '/emoji-generator/']

    def test_the_mixer_offers_a_sticker_download_with_a_png_alternative(self):
        for path in self.MIXER_PAGES_WITH_BUTTON:
            html = self.fetch(path)
            self.assertEqual(html.count('id="btn-download"'), 1, path)
            self.assertEqual(html.count('id="btn-download-png"'), 1, path)
            self.assertEqual(html.count('id="btn-download-label"'), 1, path)
            self.assertRegex(html, r'id="btn-download-label">Download image</span>', path)
            self.assertIn('512 × 512', html, path)
            self.assertIn('Need a PNG instead?', html, path)
            self.assertRegex(html, r'id="btn-download"[^>]*\bdisabled\b', path)
            self.assertRegex(html, r'id="btn-download-png"[^>]*\bdisabled\b', path)
            self.assertNotIn('Download mashup as PNG', html, path)

    def test_the_script_uses_the_sticker_endpoint_and_falls_back_to_the_plain_image(self):
        source = MAIN_JS.read_text(encoding='utf-8')
        for needle in ("/api/sticker/?", "downloadSticker('webp')", "downloadSticker('png')", 'URLSearchParams',
                       'savePlainImage', 'MutationObserver', 'btnDownload.disabled = !comboUrl', 'Content-Disposition',
                       'Sticker service unavailable'):
            self.assertIn(needle, source, needle)
        self.assertEqual(source.count("'emoji_mashup.png'"), 1, 'the plain image is only the fallback now')
        self.assertLess(source.index('async function savePlainImage'), source.index('async function downloadSticker'))

    def test_the_download_address_carries_the_sticker_version_so_old_cached_files_are_skipped(self):
        for path in self.MIXER_PAGES_WITH_BUTTON:
            self.assertIn(f'data-sticker-version="{stickers.STICKER_VERSION}"', self.fetch(path), path)
        source = MAIN_JS.read_text(encoding='utf-8')
        self.assertIn("params.set('v', btnDownload.dataset.stickerVersion)", source)
        # the server ignores v, and the same file comes back for any version
        with mock.patch.object(stickers, 'fetch_source', return_value=_mashup_png()):
            stickers.make_sticker.cache_clear()
            one = self.client.get('/api/sticker/', {'emoji1': '😂', 'emoji2': '💀', 'v': '1'})
            two = self.client.get('/api/sticker/', {'emoji1': '😂', 'emoji2': '💀', 'v': '2'})
            stickers.make_sticker.cache_clear()
        self.assertEqual((one.status_code, two.status_code), (200, 200))
        self.assertEqual(one.content, two.content)

    def test_the_faq_says_the_download_is_a_sticker(self):
        answer = next(f['answer'] for f in views.FAQS if f['question'] == 'Can I download my emoji mashup?')
        for word in ('sticker', '512', 'WebP', 'PNG'):
            self.assertIn(word, answer, word)
        self.assertNotIn('as an image (PNG) file', answer)

    def test_ids_stay_unique_on_the_pages_with_the_button(self):
        for path in self.MIXER_PAGES_WITH_BUTTON:
            ids = re.findall(r'\sid="([^"]+)"', self.fetch(path))
            self.assertEqual(len(ids), len(set(ids)), f'{path}: {[i for i in set(ids) if ids.count(i) > 1]}')

    def test_the_note_is_readable_on_a_phone(self):
        css = _css()
        self.assertIn('.cook__dlnote{', css)
        rule = _rule(css, '.linklike')
        self.assertRegex(rule, r'min-height:(4\d|[5-9]\d)px')
        self.assertIn('cursor:not-allowed', css)


# ── Copy sticker and Send sticker ────────────────────────────────────────────

class StickerCopySendTests(PageTestCase):
    PAGES = ['/', '/emoji-maker/', '/emoji-generator/']

    def source(self):
        return MAIN_JS.read_text(encoding='utf-8')

    def test_the_mixer_has_copy_sticker_and_a_send_sticker_button_that_starts_hidden(self):
        for path in self.PAGES:
            html = self.fetch(path)
            self.assertRegex(html, r'id="btn-copy-label">Copy image</span>', path)
            self.assertRegex(html, r'id="btn-send-label">Send image</span>', path)
            self.assertRegex(html, r'<button[^>]*id="btn-send"[^>]*\bhidden\b[^>]*\bdisabled\b', path)
            self.assertEqual(html.count('id="btn-send"'), 1, path)
            self.assertIn('Copy image</strong> pastes it into a chat', html, path)
            self.assertNotIn('Copy emojis as text', html, path)
            for old in ('Copy sticker', 'Download sticker', 'Send sticker'):
                self.assertNotIn(old, html, f'{path}: {old}')

    def test_send_sticker_stays_out_of_sight_until_the_browser_can_share_files(self):
        self.assertIn('.cook__actions [hidden]{display:none !important}', _css())
        source = self.source()
        for needle in ('function canShareType(type, name)', "const canShareFiles = () => canShareType('image/png', 'sticker.png')",
                       "typeof navigator.share !== 'function'", "typeof navigator.canShare !== 'function'",
                       'if (btnSend && canShareFiles())', 'btnSend.hidden = false'):
            self.assertIn(needle, source, needle)

    def test_copy_copies_the_sticker_png_and_falls_back_in_order(self):
        source = self.source()
        copy = source[source.index('btnCopy.addEventListener'):]
        copy = copy[:copy.index('\n});') + 4]
        self.assertIn("fetchSticker('png')", copy)
        self.assertIn("new ClipboardItem({ 'image/png': pngBlob })", copy)
        self.assertLess(copy.index("fetchSticker('png')"), copy.index('fetch(comboUrl'), 'sticker first, plain image second')
        # the two emojis are never copied as text: the button only ever copies a picture
        for banned in ('writeText', 'fallbackCopy', 'execCommand', 'slot1Emoji + slot2Emoji'):
            self.assertNotIn(banned, copy, banned)
        self.assertIn("window.isSecureContext === false", copy)
        self.assertIn('Use Download image instead', copy)
        # Safari only allows the clipboard write inside the tap, so the promise is created before any await
        self.assertLess(copy.index("fetchSticker('png')"), copy.index('await navigator.clipboard.write'))
        self.assertIn('btnCopy.disabled = !comboUrl', copy)

    def test_send_prepares_the_file_ahead_so_the_share_menu_opens_inside_the_tap(self):
        source = self.source()
        send = source[source.index('async function sendSticker()'):]
        send = send[:send.index('\n}\n') + 3]
        self.assertIn('readyStickerFiles.get(stickerPairKey())', send)
        # with a ready file there is nothing to await between the tap and share()
        self.assertLess(send.index('if (!file) {'), send.index('await navigator.share'))
        self.assertIn('PREFETCH_DELAY_MS = 700', source)
        # loading a saved combo swaps the image without toggling the buttons, so the image itself must be watched
        self.assertIn("if (resultImg) new MutationObserver(scheduleStickerPrefetch).observe(resultImg, { attributes: true, attributeFilter: ['src'] });", source)
        for needle in ("err.name === 'AbortError'", "err.name === 'NotAllowedError'", 'downloadSticker(stickerShareFormat)',
                       'navigator.canShare({ files: [file] })'):
            self.assertIn(needle, send, needle)
        self.assertIn("{ files: [file] }", send)
        self.assertNotIn('text:', send)
        self.assertNotIn('url:', send)

    def test_the_sticker_is_shared_as_webp_where_the_browser_allows_it_and_png_elsewhere(self):
        # WebP is the sticker format (Telegram treats a WebP file as a sticker); a PNG arrives as a photo.
        source = self.source()
        self.assertIn("const stickerShareFormat = canShareType('image/webp', 'sticker.webp') ? 'webp' : 'png';", source)
        self.assertIn("fetchSticker(stickerShareFormat)", source)
        self.assertIn("new File([blob], `emoji-kitchen-sticker.${stickerShareFormat}`, { type: `image/${stickerShareFormat}` })", source)
        self.assertLess(source.index('const stickerShareFormat'), source.index('function prepareStickerFile'))

    def test_copy_still_uses_png_because_the_browser_clipboard_only_takes_png(self):
        source = self.source()
        copy = source[source.index('btnCopy.addEventListener'):]
        copy = copy[:copy.index('\n});') + 4]
        self.assertIn("fetchSticker('png')", copy)
        self.assertIn("'image/png': pngBlob", copy)
        self.assertNotIn('webp', copy)

    def test_usage_events_carry_only_an_outcome(self):
        source = self.source()
        track = source[source.index('function trackSticker'):]
        track = track[:track.index('\n}\n') + 3]
        self.assertIn("window.gtag('event', `sticker_${action}`, { outcome })", track)
        self.assertEqual(source.count("window.gtag("), 1, 'gtag is only called from trackSticker')
        for call in re.findall(r"trackSticker\(([^)]*)\)", source):
            if call.startswith('action'):
                continue
            action, outcome = [part.strip() for part in call.split(',')]
            self.assertRegex(action, r"^'(download|copy|send)'$", call)
            self.assertRegex(outcome, r"^('[a-z_]+'|format|copied)$", f'{call}: an outcome must be a fixed word, never emoji or text')
        self.assertNotIn('emoji1', track)
        self.assertNotIn('slot1Emoji', track)

    def test_analytics_failing_or_missing_cannot_break_the_buttons(self):
        track = self.source()[self.source().index('function trackSticker'):]
        track = track[:track.index('\n}\n') + 3]
        self.assertIn("typeof window.gtag === 'function'", track)
        self.assertIn('try {', track)
        self.assertIn('catch (err)', track)

    def test_the_faq_mentions_copy_and_send(self):
        answer = next(f['answer'] for f in views.FAQS if f['question'] == 'Can I download my emoji mashup?')
        self.assertIn('Copy image', answer)
        self.assertIn('Send image', answer)

    def test_ids_stay_unique_with_the_new_button(self):
        for path in self.PAGES:
            ids = re.findall(r'\sid="([^"]+)"', self.fetch(path))
            self.assertEqual(len(ids), len(set(ids)), path)
