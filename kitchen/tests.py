import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.test import TestCase
from django.urls import resolve, reverse

from . import views
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

    def test_new_page_sends_body_links_to_nine_pages(self):
        links = self.body_links(PC)
        targets = ['/', '/emoji-keyboard/', '/emoji-maker/', '/emoji-generator/', '/emoji-combos/',
                   '/blog/emoji-kitchen-whatsapp/', '/blog/emoji-kitchen-iphone/',
                   '/blog/emoji-kitchen-samsung/', '/blog/emoji-kitchen-gboard/']
        for target in targets:
            self.assertIn(target, links, f'{PC} does not link to {target}')

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

    def test_closing_sentence_links_emoji_kitchen_to_home(self):
        html = self.fetch(PC)
        self.assertIn('using <a href="/">Emoji Kitchen</a> — free, no sign-up required.', html)

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
