"""Append internal links to never-crawled combo/keyboard pages on key blog posts.

    python manage.py seed_blog_crawl_links            # dry run
    python manage.py seed_blog_crawl_links --apply    # write to the database

Idempotent: only appends the related-links paragraph when a post is missing
/emoji-combos/love/ (and the other targets). Does not create posts or change
slugs. Safe by default without --apply.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_utils import CRAWL_LINKS_HTML
from kitchen.models import BlogPost

SLUGS = (
    'emoji-kitchen-gboard',
    'emoji-kitchen-samsung',
    'emoji-kitchen-whatsapp',
)

RELATED_HTML = CRAWL_LINKS_HTML

MARKER = '/emoji-combos/love/'


def _reading_time(content):
    return max(1, round(len(strip_tags(content).split()) / 200))


class Command(BaseCommand):
    help = (
        'Append crawl-target internal links on Gboard, Samsung and WhatsApp posts '
        '(dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save changes to the database.')

    def handle(self, *args, **options):
        apply = options['apply']
        posts = {p.slug: p for p in BlogPost.objects.filter(slug__in=SLUGS)}
        missing = [s for s in SLUGS if s not in posts]
        if missing:
            raise CommandError(
                f'These posts do not exist: {", ".join(missing)}. Nothing was changed.'
            )

        planned = []
        for slug in SLUGS:
            post = posts[slug]
            if MARKER in post.content:
                self.stdout.write(f'{slug}: already has crawl links — skip')
                continue
            new_content = post.content.rstrip() + '\n' + RELATED_HTML + '\n'
            planned.append((slug, post, new_content))
            self.stdout.write(f'{slug}: would append related-links paragraph')

        if not planned:
            self.stdout.write(self.style.SUCCESS('Nothing to change.'))
            return

        if not apply:
            self.stdout.write(self.style.WARNING(
                f'Dry run only. Re-run with --apply to update {len(planned)} post(s).'
            ))
            return

        with transaction.atomic():
            for slug, post, new_content in planned:
                post.content = new_content
                post.reading_time = _reading_time(new_content)
                post.updated_at = timezone.now()
                post.save(update_fields=['content', 'reading_time', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'{slug}: updated'))

        self.stdout.write(self.style.SUCCESS(f'Applied {len(planned)} post update(s).'))
