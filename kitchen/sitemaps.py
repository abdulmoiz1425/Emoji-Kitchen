from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'

    # home highest; main tools next; combo category pages; blog index; legal lowest
    PRIORITIES = {
        'home': 1.0,
        'emoji_maker': 0.9,
        'emoji_generator': 0.9,
        'emoji_combos': 0.9,
        'emoji_keyboard': 0.9,
        'emoji_keyboard_for_pc': 0.9,
        'emoji_combos_love': 0.7,
        'emoji_combos_cute': 0.7,
        'emoji_combos_aesthetic': 0.7,
        'emoji_combos_funny': 0.7,
        'emoji_combos_pink': 0.7,
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
            'emoji_combos',
            'emoji_combos_love',
            'emoji_combos_cute',
            'emoji_combos_aesthetic',
            'emoji_combos_funny',
            'emoji_combos_pink',
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


class BlogPostSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'

    def get_domain(self, site=None):
        # Keep sitemap loc identical to the public blog canonical, even when
        # the request host is www, a staging name, or the test client.
        from kitchen.seo import CANONICAL_HOST

        return CANONICAL_HOST

    def items(self):
        return BlogPost.objects.visible()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()
