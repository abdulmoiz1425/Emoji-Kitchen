from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost


class CanonicalOriginSitemap(Sitemap):
    """Sitemap locs use the SITE_URL origin, never the request host or scheme."""

    protocol = 'https'

    def get_domain(self, site=None):
        from kitchen.seo import canonical_host

        return canonical_host()


class StaticViewSitemap(CanonicalOriginSitemap):
    changefreq = 'weekly'

    # home highest; main tools next; blog index; legal lowest (the combo pages are in ComboPageSitemap)
    PRIORITIES = {
        'home': 1.0,
        'emoji_maker': 0.9,
        'emoji_generator': 0.9,
        'emoji_keyboard': 0.9,
        'emoji_keyboard_for_pc': 0.9,
        'blog': 0.8,
        'privacy': 0.3,
        'terms': 0.3,
        'contact': 0.3,
        'disclaimer': 0.3,
        'about': 0.3,
        'cookie_policy': 0.3,
    }

    def items(self):
        return [
            'home',
            'emoji_maker',
            'emoji_generator',
            'emoji_keyboard',
            'emoji_keyboard_for_pc',
            'blog',
            'privacy',
            'terms',
            'contact',
            'disclaimer',
            'about',
            'cookie_policy',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORITIES.get(item, 0.5)

    def changefreq(self, item):
        if item in {'privacy', 'terms', 'contact', 'disclaimer', 'about', 'cookie_policy'}:
            return 'yearly'
        if item == 'blog':
            return 'weekly'
        if item == 'home':
            return 'daily'
        return 'weekly'


# Url names of the emoji combo hub and category pages, in sitemap order.
COMBO_PAGE_URL_NAMES = (
    'emoji_combos',
    'emoji_combos_love',
    'emoji_combos_cute',
    'emoji_combos_aesthetic',
    'emoji_combos_funny',
    'emoji_combos_pink',
    'emoji_combos_birthday',
    'emoji_combos_sad',
    'emoji_combos_friendship',
    'emoji_combos_bio',
    'emoji_combos_dark',
    'emoji_combos_christmas',
)


class ComboPageSitemap(CanonicalOriginSitemap):
    """The /emoji-combos/ hub and its category pages, pinned to the public https apex.

    Their canonical tags are pinned to SITE_URL (see ``absolute_site_url``), so
    the sitemap locs are pinned the same way and always equal the canonicals,
    whatever host or scheme the request used.
    """
    changefreq = 'weekly'

    PRIORITIES = {
        'emoji_combos': 0.9,
        'emoji_combos_love': 0.7,
        'emoji_combos_cute': 0.7,
        'emoji_combos_aesthetic': 0.7,
        'emoji_combos_funny': 0.7,
        'emoji_combos_pink': 0.7,
    }

    def items(self):
        return list(COMBO_PAGE_URL_NAMES)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORITIES.get(item, 0.6)


class BlogPostSitemap(CanonicalOriginSitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return BlogPost.objects.visible()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()
