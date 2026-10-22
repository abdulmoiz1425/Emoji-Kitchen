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
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from . import views
from emoji_kitchen.envfile import load_env

from . import blog_content, blog_updates, explore

from .models import BlogPost
from .sitemaps import StaticViewSitemap

PC = '/emoji-keyboard-for-pc/'
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
LEGAL = ['/about-us/', '/contact/', '/privacy/', '/terms/', '/disclaimer/', '/cookie-policy/']
ALL_PAGES = HUBS + [PC] + COMBOS + ['/blog/'] + POSTS + LEGAL
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
            'Open the Windows emoji panel, search for a character and learn how to troubleshoot '
            'common emoji keyboard problems.',
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
        self.assertEqual(len(StaticViewSitemap().items()), 18)
        self.assertEqual(len(locs), 18 + len(POST_SLUGS))
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
    def test_new_page_receives_body_links_from_five_pages(self):
        for source in ['/', '/emoji-keyboard/', '/emoji-combos/', '/emoji-maker/', '/emoji-generator/']:
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
        self.assertEqual(self.body_links('/emoji-combos/')[PC], ['emoji keyboard for pc guide'])

    def test_required_anchor_texts_for_outgoing_links(self):
        links = self.body_links(PC)
        self.assertEqual(links['/emoji-keyboard/'], ['emoji keyboard'])
        self.assertEqual(links['/blog/emoji-kitchen-whatsapp/'], ['emoji kitchen whatsapp'])

    def test_each_page_links_to_the_new_page_only_once(self):
        for source in ['/', '/emoji-keyboard/', '/emoji-combos/', '/emoji-maker/', '/emoji-generator/']:
            self.assertEqual(len(self.body_links(source)[PC]), 1, f'{source} links to {PC} more than once')

    def test_more_than_three_incoming_and_outgoing_internal_links(self):
        incoming = [p for p in ALL_PAGES if p != PC and PC in self.body_links(p)]
        outgoing = [t for t in self.body_links(PC) if t != PC]
        self.assertGreater(len(incoming), 3, incoming)
        self.assertGreater(len(outgoing), 3, outgoing)

    def test_closing_sentence_has_no_links(self):
        html = self.fetch(PC)
        sentence = ('Merge two emojis into one unique image using Emoji Kitchen — free, no sign-up required. '
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
        for source in ['/', '/emoji-keyboard/', '/emoji-combos/', '/emoji-maker/', '/emoji-generator/']:
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
        for source in ['/', '/emoji-keyboard/', '/emoji-combos/', '/emoji-maker/', '/emoji-generator/']:
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
            '/emoji-combos/': {'/'} | set(COMBOS),
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
        # the six menu items fit on one line from ~1040px; below that the hamburger takes over
        self.assertRegex(css, r'@media\(max-width:1040px\)\{\s*\.nav__links,\.nav__cta\{display:none\}')


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


# ── Existing behaviour that must not regress ──────────────────────────────────

class RegressionTests(PageTestCase):
    def test_all_public_pages_return_200(self):
        for path in ALL_PAGES + ['/robots.txt', '/ads.txt', '/sitemap.xml']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

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

    def test_download_and_proxy_reject_foreign_urls(self):
        for path in ['/api/download/', '/api/proxy/']:
            self.assertEqual(self.client.get(path, {'url': 'https://example.com/x.png'}).status_code, 400)
            self.assertEqual(self.client.get(path).status_code, 400)

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
        for path in [PC, '/emoji-keyboard/', '/emoji-combos/', '/blog/']:
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
        self.assertIn('Unicode emoji specifications are updated periodically', self.fetch('/emoji-combos/'))


# ── Home page: content from the "Emoji Updates" document (Page 1) ─────────────

class HomePageContentTests(PageTestCase):
    def home(self):
        return self.fetch('/')

    def test_title_and_meta_description(self):
        page = self.parse('/')
        self.assertEqual(_clean(page.title), 'Emoji Kitchen – Mix Emojis & Create Custom Stickers')
        self.assertEqual(page.meta['description'],
                         'Mix two compatible emojis to create fun sticker-style mashups. Explore emoji combinations, '
                         'copy or download results, and find new ideas for your chats.')
        self.assertEqual(page.meta['og:title'], 'Emoji Kitchen – Mix Emojis & Create Custom Stickers')
        self.assertEqual(len(page.h1), 1)
        self.assertEqual(_clean(page.h1[0]), 'Emoji Kitchen – Mix Emojis and Create Custom Stickers')

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
        self.assertIn('<h2>Using Emoji Mashups on Different Devices</h2>', html)
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

    def test_faqs_are_the_eight_questions_from_the_brief(self):
        self.assertEqual([f['question'] for f in views.FAQS], [
            'Is Emoji Kitchen Hub free?', 'Do I need to install an app?', 'Can I combine any two emojis?',
            'Are the results real Unicode emojis?', 'Can I use the tool on my phone?', 'Can I download my emoji mashup?',
            'Can I save favourite combinations?', 'Is Emoji Kitchen Hub operated by Google?'])
        html = self.home()
        self.assertEqual(html.count('class="faq-item animate-up"'), 8)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(\{"@context": "https://schema.org", "@type": "FAQPage".*?)</script>', html).group(1))
        self.assertEqual(len(ld['mainEntity']), 8)
        self.assertNotIn('Google Search mixer', html)

    def test_closing_call_to_action_follows_the_faqs(self):
        html = self.home()
        self.assertIn('<h2>Ready to Create Your Emoji Mashup?</h2>', html)
        self.assertIn('Choose two emojis, explore the available result, and find a combination that suits your message.', html)
        self.assertIn('>Start Mixing Emojis</a>', html)
        self.assertGreater(html.index('Ready to Create Your Emoji Mashup?'), html.index('id="faq"'))

    def test_home_links_to_the_four_tools_from_its_body(self):
        links = self.body_links('/')
        for target in ['/emoji-maker/', '/emoji-generator/', '/emoji-keyboard/', '/emoji-combos/']:
            self.assertIn(target, links, f'Home does not link to {target}')

    def test_existing_sections_are_kept(self):
        html = self.home()
        for kept in ['What Is an Emoji Kitchen?', 'Share Emoji Kitchen Stickers with Friends', 'Emoji Kitchen FAQs',
                     'id="kitchen"', 'class="explore"']:
            self.assertIn(kept, html)


# ── Emoji Maker and Emoji Generator: content from the "Emoji Updates" document ─

EDITOR_NOTES = [   # instructions to the editor in the document; they must never reach visitors
    'should not be described', 'unless that functionality is implemented', 'unless those features are actually implemented',
    'Keep this claim', 'Do not advertise', 'is presented as', 'Do not assume',
]


class MakerAndGeneratorContentTests(PageTestCase):
    MAKER_H2 = ['What Is an Emoji Maker?', 'How to Make Your Own Emoji', 'Choose Emoji Pairs That Express an Idea',
                'Emoji Maker vs. Standard Emoji vs. AI Image Generator', 'Can You Make an Emoji From a Photo?',
                'Can You Create a New Keyboard Emoji?', 'Copying and Sharing Your Emoji', 'Troubleshooting',
                'Emoji Maker FAQs', 'Create Your Next Emoji Mashup']
    GENERATOR_H2 = ['Emoji Mix Ideas to Try', 'How to Choose a Useful Pair',
                    'Where Can You Use an Emoji Mix?', 'Frequently Asked Questions']

    def assertInOrder(self, html, headings):
        positions = [html.index(f'<h2>{h}</h2>') for h in headings]
        self.assertEqual(positions, sorted(positions))

    def test_titles_and_meta(self):
        maker, generator = self.parse('/emoji-maker/'), self.parse('/emoji-generator/')
        self.assertEqual(_clean(maker.title), 'Emoji Maker – Create Custom Emoji Stickers Online')
        self.assertEqual(maker.meta['description'], 'Make custom emoji-style stickers by combining two compatible emojis. '
                         'Preview your mashup, then copy or download the result using our online emoji maker.')
        self.assertEqual(_clean(generator.title), 'Free Emoji Generator - Emoji Mix Ideas to Try')
        self.assertEqual(generator.meta['description'], 'Need an emoji mix idea? Get pairing ideas for reactions, love, animals, '
                         'food and nature, then try them in this free browser-based emoji generator.')

        for page in (maker, generator):
            self.assertLessEqual(len(page.meta['description']), 160)
            self.assertLessEqual(len(_clean(page.title)), 60)
            self.assertEqual(page.meta['og:title'], _clean(page.title))
            self.assertEqual(len(page.h1), 1)

    def test_h1s_and_introductions(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertIn('<h1>Emoji Maker – Create Custom Emoji Stickers Online</h1>', maker)
        self.assertIn('<h1>Free Emoji Generator: Create Custom Emoji Mixes Online</h1>', generator)
        self.assertIn('This online emoji maker lets you combine two compatible emojis into a sticker-style image.', maker)
        self.assertIn('It does not draw entirely new characters, edit uploaded photos, or create new Unicode keyboard emojis.', maker)
        self.assertIn('Use this emoji generator to explore two-emoji combinations', generator)
        self.assertIn("The available results depend on the tool's supported combinations.", generator)
        self.assertNotIn('quick-answer', maker + generator)

    def test_section_headings_follow_the_document(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertInOrder(maker, self.MAKER_H2)
        self.assertInOrder(generator, self.GENERATOR_H2)
        for h3 in ['Start with the Message', 'Keep the Main Idea Clear', 'Try Alternatives']:
            self.assertIn(f'<h3>{h3}</h3>', generator)
        self.assertEqual(maker.count('<li><strong>'), 4)    # the four numbered steps
        for h3 in ['Express a Feeling', 'Make a Playful Reaction', 'Create a Themed Sticker', 'Unsupported Combinations',
                   'Loading Problems', 'Copying Failures', 'Download Problems']:
            self.assertIn(f'<h3>{h3}</h3>', maker)

    def test_old_repetitive_sections_are_gone(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        for old in ['What This Emoji Maker Creates', 'AI Emoji Maker, Photo Emoji Maker', 'Emoji Maker Games',
                    'Emoji Maker Online vs Emoji Maker App', 'Free Emoji Maker Online: What You Can Do']:
            self.assertNotIn(old, maker)
        for old in ['What Is an Emoji Generator?', 'Why Use an Emoji Generator Online?',
                    'Emoji Generator vs. Standard Emoji vs. AI Image Tool']:
            self.assertNotIn(old, generator)

    def test_faqs_are_the_documents_five_each_and_visitor_facing(self):
        self.assertEqual([f['question'] for f in views.EMOJI_MAKER_FAQS], [
            'What does an emoji maker do?', 'Can I make my own emoji for free?', 'Does this tool use AI?',
            'Can I edit individual facial features?', 'Can I make an emoji from a photo?', 'Why does a combination fail?',
            'Can I use the result in messages?'])
        self.assertEqual([f['question'] for f in views.EMOJI_GENERATOR_FAQS], [
            'Is this emoji generator free?', 'Do I need to install an app?', 'Can I combine three emojis at once?',
            'Which emoji pairs should I try first?', 'Where can I use a generated emoji mix?'])
        answers = {f['question']: f['answer'] for f in views.EMOJI_MAKER_FAQS + views.EMOJI_GENERATOR_FAQS}
        self.assertEqual(answers['Can I make an emoji from a photo?'],
                         'No. This tool combines existing emoji designs. It does not convert photos into emojis.')
        self.assertEqual(answers['Can I combine three emojis at once?'], 'No. The tool combines two emojis at a time.')
        self.assertEqual(self.fetch('/emoji-maker/').count('class="faq-item animate-up"'), 7)
        self.assertEqual(self.fetch('/emoji-generator/').count('class="faq-item animate-up"'), 5)

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
        ideas = html[html.index('<h2>Emoji Mix Ideas to Try</h2>'):html.index('<h2>How to Choose a Useful Pair</h2>')]
        pairs = re.findall(r'(\S+) \+ (\S+?)(?=[ ,.<])', re.sub(r'<[^>]+>', ' ', ideas).replace('  ', ' '))
        self.assertEqual(len(pairs), 13)
        for first, second in pairs:
            self.assertTrue(views.combo_image_url(first, second), f'{first} + {second} is not supported')

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
        ideas = generator[generator.index('<h2>Emoji Mix Ideas to Try</h2>'):generator.index('<h2>How to Choose a Useful Pair</h2>')]
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
        for target in ['/emoji-keyboard/', '/emoji-combos/', '/emoji-generator/', '/']:
            self.assertIn(target, maker, f'Maker does not link to {target}')
        for target in ['/emoji-maker/', '/emoji-keyboard/', '/emoji-combos/']:
            self.assertIn(target, generator, f'Generator does not link to {target}')

    def test_links_to_the_pc_page_survive_the_rewrite(self):
        self.assertEqual(self.body_links('/emoji-maker/')[PC], ['emoji keyboard for pc'])
        self.assertEqual(self.body_links('/emoji-generator/')[PC], ['emoji keyboard shortcut'])

    def test_the_mixer_is_untouched_on_both_pages(self):
        for path in ['/emoji-maker/', '/emoji-generator/']:
            html = self.fetch(path)
            for part in ['id="kitchen"', 'id="btn-swap"', 'id="mixer-status"', 'class="explore"', 'id="btn-surprise"']:
                self.assertIn(part, html, f'{part} missing on {path}')


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
    '/emoji-combos/': ('Emoji Combos to Copy and Paste - Ideas for Every Mood',
                       'Browse emoji combos for cute, aesthetic, funny, love and color themes. Choose a sequence for a bio, caption or message.',
                       'Emoji combos are groups of two or more emoji characters used together to express a mood, topic or visual style.'),
    '/emoji-combos/love/': ('Love Emoji Combos to Copy and Paste',
                            'Browse romantic, affectionate and soft love emoji combos for messages, captions and bios.',
                            'Love emoji combos bring hearts, faces, flowers and other symbols together to add tone to a message.'),
    '/emoji-combos/cute/': ('Cute Emoji Combos to Copy and Paste',
                            'Find cute emoji combos with animals, bows, flowers, hearts and soft expressions for bios, messages and captions.',
                            'Cute emoji combos often use friendly faces, small animals, hearts, flowers, bows and soft colors.'),
    '/emoji-combos/aesthetic/': ('Aesthetic Emoji Combos for Bios and Captions',
                                 'Explore aesthetic emoji combos by mood, color and visual style. Find coordinated sequences for profiles and captions.',
                                 'Aesthetic emoji combos use a consistent visual mood, such as soft pastels, night skies, flowers, nature, minimal symbols or warm neutral tones.'),
    '/emoji-combos/funny/': ('Funny Emoji Combos to Copy and Paste',
                             'Browse funny emoji combos for reactions, jokes, group chats and captions. Choose a sequence that fits the context.',
                             'Funny emoji combos bring faces, objects, animals and symbols together to make a reaction more playful.'),
    '/emoji-combos/pink/': ('Pink Emoji Combos to Copy and Paste',
                            'Explore pink emoji combos featuring hearts, flowers, bows and pastel symbols for bios, captions, profiles and messages.',
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
    '/emoji-combos/': (155, 140), '/emoji-combos/love/': (352, 173), '/emoji-combos/cute/': (202, 185),
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
        html = self.fetch('/emoji-combos/')
        self.assertEqual(html.count('<h2>Browse Emoji Combos by Theme</h2>'), 1)
        for theme in ['Cute', 'Aesthetic', 'Love', 'Funny', 'Pink']:
            self.assertIn(f'<h3>{theme} Emoji Combos</h3>', html)
        links = self.body_links('/emoji-combos/')
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
        self.assertEqual(page.meta['description'], 'Learn about Emoji Kitchen Hub, its emoji tools, educational resources '
                         'and how to report corrections or problems.')
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
                         'or ask a question about the website.')
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
        self.assertIn('does not set its own cookies on its public pages and does not use a separate analytics service', html)
        self.assertIn('https://policies.google.com/technologies/partner-sites', html)
        self.assertIn('https://adssettings.google.com', html)
        self.assertIn('EmojiKitchenHub uses Google AdSense to show advertising on some pages.', self.fetch('/privacy/'))

    def test_the_facts_stated_in_the_policies_are_still_true(self):
        """If one of these fails, update the Cookie Policy and Privacy Policy as well."""
        js = (Path(settings.BASE_DIR) / 'kitchen/static/kitchen/js/main.js').read_text(encoding='utf-8')
        self.assertIn('persistCombos(combos.slice(0, 6))', js)                  # "up to six"
        self.assertIn("localStorage.setItem(COMBOS_KEY", js)                     # local storage, on the device
        self.assertIn("sessionStorage.setItem(RECENT_KEY", js)                   # session storage
        self.assertNotRegex(js, r'method:\s*[\'"]POST')                           # the saved list is never uploaded
        for path in MIXER_PAGES + [PC, '/emoji-combos/', '/blog/', '/about-us/', '/contact/', '/privacy/', '/cookie-policy/']:
            self.assertFalse(self.client.get(path).cookies, f'{path} sets a cookie')
        templates = Path(settings.BASE_DIR) / 'kitchen/templates'
        scripts = '\n'.join(p.read_text(encoding='utf-8') for p in templates.rglob('*.html'))
        for tracker in ['googletagmanager', 'gtag(', 'google-analytics', 'clarity.ms', 'hotjar', 'plausible', 'matomo']:
            self.assertNotIn(tracker, scripts, f'a tracking script ({tracker}) was added: update the policies')
        self.assertIn('fonts.googleapis.com', scripts)                           # Google Fonts, as the Cookie Policy says
        self.assertIn('pagead2.googlesyndication.com', self.fetch('/'))          # AdSense, as the policies say

    def test_all_contact_emails_still_appear_on_the_legal_pages(self):
        for path in LEGAL:
            html = self.fetch(path)
            self.assertIn('mailto:abdulmannanfiv@gmail.com', html, path)
            self.assertIn('mailto:mannanmaan1425@gmail.com', html, path)


# ── "Remaining Content Updates" document: Home, Emoji Maker, Generator, Blog index ──

class RemainingUpdatesTests(PageTestCase):
    def test_home_results_claim_matches_how_fast_the_tool_really_is(self):
        html = self.fetch('/')
        self.assertIn('Free · No sign-up · Results in seconds', html)
        self.assertNotIn('Instant results', html)

    def test_home_strip_shows_labels_only_without_the_four_big_words(self):
        html = self.fetch('/')
        self.assertNotIn('stat__value', html)
        for word in ['60,553', '>Free<', '>Zero<', '>PNG<']:
            self.assertNotIn(word, html)
        for label in ['Emoji combos', 'Always &amp; forever', 'Sign-up needed', 'Transparent files']:
            self.assertIn(f'<span class="stat__label">{label}</span>', html)

    def test_home_what_is_section_uses_the_new_explanation(self):
        html = self.fetch('/')
        self.assertIn("Emoji Kitchen is commonly associated with Google's emoji-mixing feature", html)
        self.assertIn('Emoji Kitchen Hub is an independent website that provides its own browser-based emoji-mixing experience.', html)
        self.assertIn('sticker-style images, not newly registered Unicode emoji characters.', html)
        self.assertIn('<h2>What Is an Emoji Kitchen?</h2>', html)
        for old in ['Google first introduced the feature through Gboard on Android.', 'through Google Search',
                    'Emoji Kitchen Hub is an unofficial fan-made tool']:
            self.assertNotIn(old, html)
        links = self.body_links('/')
        for target in ['/emoji-keyboard/', '/emoji-combos/', '/blog/', PC]:
            self.assertIn(target, links)

    def test_maker_closing_section(self):
        html = self.fetch('/emoji-maker/')
        self.assertIn('<h2>Create Your Next Emoji Mashup</h2>', html)
        self.assertIn('Choose two emojis, explore the supported combinations, and copy or download a result that matches your message.', html)
        self.assertIn('>Make My Emoji Mashup</a>', html)
        for old in ['Make Your Next Emoji Mashup', 'Make Your Next Custom Emoji', 'save the combinations you want to use again']:
            self.assertNotIn(old, html)

    def test_no_page_promises_that_results_can_be_saved_for_later(self):
        for path in ['/emoji-maker/', '/emoji-generator/', '/']:
            html = self.fetch(path)
            for promise in ['save the results that fit your style', 'save the combinations you want to use again',
                            'save your favourites', 'keeps every creation']:
                self.assertNotIn(promise, html, f'"{promise}" is on {path}')
        self.assertIn('copy or download the results that fit your style', self.fetch('/emoji-generator/'))

    def test_my_combos_wording_stays_accurate(self):
        html = self.fetch('/emoji-maker/')
        self.assertIn('Click any combo to reload it in the mixer', html)
        for overclaim in ['permanent', 'forever', 'every previous', 'synced', 'on all your devices']:
            self.assertNotIn(overclaim, html.split('id="my-combos"')[1].split('</div>')[0], overclaim)

    def test_blog_index_introduction(self):
        html = self.fetch('/blog/')
        self.assertIn('Explore practical guides to emoji tools, keyboards, sticker-style mashups and common sharing problems.', html)
        self.assertIn('without reading unrelated tutorials.', html)
        self.assertNotIn('Tips, tricks, and fun discoveries', html)
        self.assertEqual(len(self.parse('/blog/').h1), 1)
        self.assertIn('<h1>From the Blog</h1>', html)                       # the H1 stays
        for post in POSTS:
            self.assertIn(f'href="{post}"', html)                           # the article cards stay


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

