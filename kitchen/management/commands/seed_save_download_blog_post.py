"""Create or update the save/download stickers blog post.

    python manage.py seed_save_download_blog_post            # dry run
    python manage.py seed_save_download_blog_post --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Running twice with
--apply is idempotent for the seeded fields and refreshes the featured cover
image on the same BlogPost row (no duplicate posts).
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_save_download import (
    COVER_FILENAME,
    COVER_PATH,
    FIELDS,
    SLUG,
    content_html,
    cover_bytes,
)
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


def _cover_needs_update(post, desired_bytes):
    """True when the post has no cover or the stored file differs from the seed PNG."""
    if not post or not post.featured_image:
        return True
    try:
        post.featured_image.open('rb')
        try:
            current = post.featured_image.read()
        finally:
            post.featured_image.close()
    except (FileNotFoundError, OSError, ValueError):
        return True
    return current != desired_bytes


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
        if not COVER_PATH.is_file():
            raise CommandError(f'Cover image missing: {COVER_PATH}')

        content = content_html()
        desired = {**FIELDS, 'content': content, 'status': BlogPost.STATUS_PUBLISHED}
        desired['reading_time'] = _reading_time(content)
        image_bytes = cover_bytes()

        existing = BlogPost.objects.filter(slug=SLUG).first()
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{SLUG}'))
        self.stdout.write(f'  web address: /blog/{SLUG}/')
        self.stdout.write(f'  cover source: {COVER_PATH.name} ({len(image_bytes)} bytes)')

        if existing is None:
            self.stdout.write('  action: create new published post')
            for field in UPDATE_FIELDS:
                if field == 'content':
                    self.stdout.write(f'  content: {len(content.split())} words (new)')
                else:
                    value = str(desired[field])
                    self.stdout.write(f'  {field}: {value[:110]}{"…" if len(value) > 110 else ""}')
            self.stdout.write(f'  featured_image: will set -> blog/featured/{COVER_FILENAME}')
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
            if _cover_needs_update(existing, image_bytes):
                changes += 1
                current_name = existing.featured_image.name if existing.featured_image else '(none)'
                self.stdout.write(
                    f'  featured_image: {current_name} -> blog/featured/{COVER_FILENAME}'
                )
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

            # Attach / refresh the cover on the same row (never create a second post).
            if _cover_needs_update(post if existing else None, image_bytes):
                if post.featured_image:
                    post.featured_image.delete(save=False)
                post.featured_image.save(
                    COVER_FILENAME,
                    ContentFile(image_bytes),
                    save=False,
                )

            post.save()
            fresh = BlogPost.objects.get(slug=SLUG)
            if fresh.content != content or fresh.status != BlogPost.STATUS_PUBLISHED:
                raise CommandError(f'{SLUG} did not save correctly; everything was rolled back.')
            if not fresh.featured_image or not fresh.featured_image.name.endswith(COVER_FILENAME):
                raise CommandError(f'{SLUG} featured_image did not save correctly; rolled back.')
            # Confirm only one row for this slug.
            if BlogPost.objects.filter(slug=SLUG).count() != 1:
                raise CommandError(f'{SLUG} duplicated; rolled back.')

        action = 'Created' if existing is None else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} /blog/{SLUG}/ '
            f'(status=published, reading_time={desired["reading_time"]} min, '
            f'featured_image=blog/featured/{COVER_FILENAME}).'
        ))
