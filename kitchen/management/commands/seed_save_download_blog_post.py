"""Create or update the save/download stickers blog post.

    python manage.py seed_save_download_blog_post            # dry run
    python manage.py seed_save_download_blog_post --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Running twice with
--apply is idempotent for the seeded fields.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_save_download import FIELDS, SLUG, content_html
from kitchen.models import BlogPost

UPDATE_FIELDS = (
    'title',
    'excerpt',
    'seo_title',
    'seo_description',
    'focus_keyword_title',
    'focus_keyword_description',
    'seo_keywords',
    'og_title',
    'og_description',
    'content',
    'status',
    'reading_time',
)


def _reading_time(content):
    return max(1, round(len(strip_tags(content).split()) / 200))


class Command(BaseCommand):
    help = (
        'Create or update the how-to-save-download-emoji-kitchen-stickers blog post '
        '(dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Save the post to the database.',
        )

    def handle(self, *args, **options):
        content = content_html()
        desired = {**FIELDS, 'content': content, 'status': BlogPost.STATUS_PUBLISHED}
        desired['reading_time'] = _reading_time(content)

        existing = BlogPost.objects.filter(slug=SLUG).first()
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{SLUG}'))
        self.stdout.write(f'  web address: /blog/{SLUG}/')

        if existing is None:
            self.stdout.write('  action: create new published post')
            for field in UPDATE_FIELDS:
                if field == 'content':
                    self.stdout.write(f'  content: {len(content.split())} words (new)')
                else:
                    value = str(desired[field])
                    self.stdout.write(f'  {field}: {value[:110]}{"…" if len(value) > 110 else ""}')
        else:
            self.stdout.write(f'  action: update existing post (id={existing.pk})')
            changes = 0
            for field in UPDATE_FIELDS:
                old = getattr(existing, field)
                new = desired[field]
                if (old or '') != (new or ''):
                    changes += 1
                    if field == 'content':
                        self.stdout.write(
                            f'  content: {len(strip_tags(old).split())} -> '
                            f'{len(strip_tags(new).split())} words'
                        )
                    else:
                        self.stdout.write(f'  {field}:')
                        self.stdout.write(f'      was: {str(old)[:110]}{"…" if len(str(old)) > 110 else ""}')
                        self.stdout.write(f'      now: {str(new)[:110]}{"…" if len(str(new)) > 110 else ""}')
            if changes == 0:
                self.stdout.write('  fields: already up to date')

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                '\nDRY RUN: nothing was changed. Run again with --apply to save.'
            ))
            return

        with transaction.atomic():
            if existing is None:
                post = BlogPost(slug=SLUG, publish_date=timezone.now())
            else:
                post = existing
            for field, value in desired.items():
                setattr(post, field, value)
            if existing is None and not post.publish_date:
                post.publish_date = timezone.now()
            post.save()
            fresh = BlogPost.objects.get(slug=SLUG)
            if fresh.content != content or fresh.status != BlogPost.STATUS_PUBLISHED:
                raise CommandError(f'{SLUG} did not save correctly; everything was rolled back.')

        action = 'Created' if existing is None else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} /blog/{SLUG}/ (status=published, reading_time={desired["reading_time"]} min).'
        ))
