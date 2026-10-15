import json
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
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from . import views
from emoji_kitchen.envfile import load_env

from . import explore

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
    'Use the Right Emoji Method for Your PC',
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
        self.assertEqual(_clean(page.title), 'Emoji Keyboard for PC: Shortcuts & Windows 11 Guide')
        self.assertEqual(
            page.meta['description'],
            'Need an emoji keyboard for PC? Learn the Windows 11 and 10 shortcuts, '
            'how to type emojis, and how to use a free online emoji keyboard.',
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
                         r'\s+data-url="([^"]+)" aria-label="([^"]+)">\s*<img src="([^"]+)" alt="([^"]+)" loading="lazy"'
                         r' width="96" height="96"', html)
        self.assertIsNotNone(item)
        first, second, data_url, label, src, alt = item.groups()
        self.assertEqual(data_url, src)
        self.assertEqual(views.combo_image_url(first, second), data_url)
        self.assertIn('emoji mashup', alt)
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
        self.assertEqual(_clean(page.title), 'Emoji Kitchen - Mix Emojis into Sticker-Style Images')
        self.assertEqual(page.meta['description'],
                         'Explore supported emoji pairs with Emoji Kitchen Hub. Browse emoji combinations, '
                         'explore sticker-style mashups, and find standard emojis with the online keyboard.')
        self.assertEqual(page.meta['og:title'], 'Emoji Kitchen - Mix Emojis into Sticker-Style Images')
        self.assertEqual(len(page.h1), 1)   # the H1 stays

    def test_introduction_under_the_h1(self):
        html = self.home()
        for text in [
            'Emoji Kitchen Hub brings together emoji-related tools to help you explore combinations, find standard emoji characters and browse themed emoji collections.',
            'Choose two emojis in the mixer to see whether a supported sticker-style result is available.',
            'The type of result matters: a sticker-style mashup is an image, not a new Unicode emoji character added to your device keyboard.',
        ]:
            self.assertIn(text, html)
        self.assertEqual(html.count('class="hero__subtitle"'), 3)

    def test_tool_explanations_replace_the_old_benefit_cards(self):
        html = self.home()
        self.assertIn('<h2>Explore Emoji Tools for Different Tasks</h2>', html)
        for title in ['Explore Emoji Mashups', 'Copy Standard Emojis', 'Find Emoji Combos by Theme',
                      'Learn How Emoji Features Work']:
            self.assertIn(f'<h3>{title}</h3>', html)
        self.assertEqual(html.count('class="feature-card animate-up"'), 4)
        for old in ['Why Use Our Emoji Kitchen Tool?', 'Free Emoji Combiner', 'Fast Emoji Mixing',
                    'Works in Your Browser', 'Creative Combinations']:
            self.assertNotIn(old, html)

    def test_how_to_section_uses_the_new_instructions(self):
        html = self.home()
        self.assertIn('<h2>How to Use Emoji Kitchen</h2>', html)
        self.assertIn("The browser mixer on this website and Google's Emoji Kitchen feature are separate products.", html)
        self.assertIn('<h3>Use the Browser Mixer</h3>', html)
        self.assertIn("<h3>Use Google's Emoji Kitchen on Android</h3>", html)
        self.assertEqual(len(views.HOW_TO_WEB), 6)
        self.assertEqual(html.count('class="step-num"'), 6)
        self.assertNotIn('On Android &amp; Gboard', html)
        self.assertNotIn('how-to-card__note', html)

    def test_understanding_mashups_section_sits_before_the_faqs(self):
        html = self.home()
        self.assertIn('<h2>Understanding Emoji Mashups</h2>', html)
        self.assertIn('The mixer works with supported emoji pairs, not every possible combination.', html)
        self.assertIn('Emoji Kitchen Hub is an independent website and is not operated by Google.', html)
        self.assertLess(html.index('id="limitations"'), html.index('id="faq"'))
        self.assertGreater(html.index('id="limitations"'), html.index('id="how-to"'))

    def test_home_links_to_the_four_tools_from_its_body(self):
        links = self.body_links('/')
        for target in ['/emoji-maker/', '/emoji-generator/', '/emoji-keyboard/', '/emoji-combos/']:
            self.assertIn(target, links, f'Home does not link to {target}')

    def test_existing_sections_and_the_combo_count_are_kept(self):
        html = self.home()
        self.assertIn(f'{views.COMBO_COUNT:,}', html)       # the count comes from the data file, so it is accurate
        for kept in ['What Is an Emoji Kitchen?', 'Share Emoji Kitchen Stickers with Friends', 'Emoji Kitchen FAQs',
                     'id="kitchen"', 'class="explore"']:
            self.assertIn(kept, html)


# ── Emoji Maker and Emoji Generator: content from the "Emoji Updates" document ─

EDITOR_NOTES = [   # instructions to the editor in the document; they must never reach visitors
    'should not be described', 'unless that functionality is implemented', 'unless those features are actually implemented',
    'Keep this claim', 'Do not advertise', 'is presented as', 'Do not assume',
]


class MakerAndGeneratorContentTests(PageTestCase):
    MAKER_H2 = ['What This Emoji Maker Creates', 'How to Use the Emoji Maker', 'What This Tool Can and Cannot Do',
                'Why Some Emoji Pairs Do Not Produce a Result', 'Standard Emoji vs. Sticker-Style Mashup',
                'Frequently Asked Questions']
    GENERATOR_H2 = ['How to Generate an Emoji Mix', 'How to Choose a Useful Pair', 'Emoji Generator vs. Standard Emojis',
                    'Where Can You Use an Emoji Mix?', 'Frequently Asked Questions']

    def assertInOrder(self, html, headings):
        positions = [html.index(f'<h2>{h}</h2>') for h in headings]
        self.assertEqual(positions, sorted(positions))

    def test_titles_and_meta(self):
        maker, generator = self.parse('/emoji-maker/'), self.parse('/emoji-generator/')
        self.assertEqual(_clean(maker.title), 'Emoji Maker - Make an Emoji-Style Sticker Online')
        self.assertEqual(maker.meta['description'], "Explore supported emoji pairs with this online emoji maker. "
                         "Learn how to create a sticker-style mashup and understand the tool's limitations.")
        self.assertEqual(_clean(generator.title), 'Free Emoji Generator - Explore Supported Emoji Mixes')
        self.assertEqual(generator.meta['description'], 'Explore supported emoji pairs with this browser-based generator. '
                         'Learn how to choose a pair, understand unavailable results and use the image.')
        for page in (maker, generator):
            self.assertEqual(page.meta['og:title'], _clean(page.title))
            self.assertEqual(len(page.h1), 1)

    def test_h1s_and_introductions(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertIn('<h1>Emoji Maker: Make Your Own Emoji Free Online</h1>', maker)
        self.assertIn('<h1>Free Emoji Generator: Create Custom Emoji Mixes Online</h1>', generator)
        self.assertIn('Use this online emoji maker to explore combinations of familiar emojis', maker)
        self.assertIn('This tool combines existing emoji designs. It does not create a new Unicode character for your keyboard.', maker)
        self.assertIn('Use this emoji generator to explore two-emoji combinations', generator)
        self.assertIn("The available results depend on the tool's supported combinations.", generator)
        self.assertNotIn('quick-answer', maker + generator)

    def test_section_headings_follow_the_document(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        self.assertInOrder(maker, self.MAKER_H2)
        self.assertInOrder(generator, self.GENERATOR_H2)
        for h3 in ['Start with the Message', 'Keep the Main Idea Clear', 'Try Alternatives']:
            self.assertIn(f'<h3>{h3}</h3>', generator)
        self.assertEqual(maker.count('<li><strong>'), 4)    # standard emoji / combo / mashup / AI image

    def test_old_repetitive_sections_are_gone(self):
        maker, generator = self.fetch('/emoji-maker/'), self.fetch('/emoji-generator/')
        for old in ['What Is an Emoji Maker?', 'AI Emoji Maker, Photo Emoji Maker', 'Emoji Maker Games',
                    'Emoji Maker Online vs Emoji Maker App', 'Free Emoji Maker Online: What You Can Do']:
            self.assertNotIn(old, maker)
        for old in ['What Is an Emoji Generator?', 'Why Use an Emoji Generator Online?',
                    'Emoji Generator vs. Standard Emoji vs. AI Image Tool']:
            self.assertNotIn(old, generator)

    def test_faqs_are_the_documents_five_each_and_visitor_facing(self):
        self.assertEqual([f['question'] for f in views.EMOJI_MAKER_FAQS], [
            'Does this tool create a new Unicode emoji?', 'Can I make an emoji from a photo?', 'Does every emoji pair work?',
            'Can I use the result in any application?', 'What should I use for standard emoji characters?'])
        self.assertEqual([f['question'] for f in views.EMOJI_GENERATOR_FAQS], [
            'Is this emoji generator free?', 'Do I need to install an app?', 'Can I combine three emojis at once?',
            'Are the results new Unicode emojis?', 'Why is no result appearing?'])
        answers = {f['question']: f['answer'] for f in views.EMOJI_MAKER_FAQS + views.EMOJI_GENERATOR_FAQS}
        self.assertEqual(answers['Can I make an emoji from a photo?'],
                         'No. This tool combines existing emoji designs. It does not convert photos into emojis.')
        self.assertEqual(answers['Can I combine three emojis at once?'], 'No. The tool combines two emojis at a time.')
        for path in ['/emoji-maker/', '/emoji-generator/']:
            self.assertEqual(self.fetch(path).count('class="faq-item animate-up"'), 5, path)

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

