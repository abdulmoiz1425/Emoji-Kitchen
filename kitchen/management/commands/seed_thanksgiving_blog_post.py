"""Create or update the thanksgiving-emoji-combos blog post.

    python manage.py seed_thanksgiving_blog_post            # dry run
    python manage.py seed_thanksgiving_blog_post --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Running twice with
--apply is idempotent for the seeded fields, the featured WebP cover, and the
JPEG og:image, and it does not call post.save() when nothing changed, so
updated_at stays put. Known inbound-link paragraphs appended by other seeds
are ignored when comparing content and are preserved if the fixture body is
rewritten.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_thanksgiving import (
    COVER_FILENAME,
    COVER_PATH,
    FIELDS,
    OG_FILENAME,
    OG_PATH,
    SLUG,
    content_html,
    cover_bytes,
    og_bytes,
)
from kitchen.blog_seed_utils import (
    assign_versioned_cover,
    assign_versioned_og_image,
    cover_versioned_filename,
    desired_seed_content,
    featured_is_current,
    og_is_current,
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
    'canonical_url',
    'content',
    'status',
    'reading_time',
)


def _reading_time(content):
    return max(1, round(len(strip_tags(content).split()) / 200))


def _canonical():
    """Pin the public URL to SITE_URL so a request host cannot change it."""
    origin = (getattr(settings, 'SITE_URL', None) or 'https://emojikitchenhub.com').rstrip('/')
    return f'{origin}/blog/{SLUG}/'


class Command(BaseCommand):
    help = (
        'Create or update the thanksgiving-emoji-combos blog post '
        '(dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Save the post, cover, and og:image to the database.',
        )

    def handle(self, *args, **options):
        if not COVER_PATH.is_file():
            raise CommandError(f'Cover image missing: {COVER_PATH}')
        if not OG_PATH.is_file():
            raise CommandError(f'OG JPEG missing: {OG_PATH}')
        try:
            fixture = content_html()
        except FileNotFoundError as exc:
            raise CommandError(f'Content fixture missing: {exc}') from exc
        if not fixture.strip():
            raise CommandError('Content fixture is empty.')

        existing = BlogPost.objects.filter(slug=SLUG).first()
        content = desired_seed_content(fixture, existing.content if existing else '')
        desired = {**FIELDS, 'content': content, 'status': BlogPost.STATUS_PUBLISHED}
        desired['canonical_url'] = _canonical()
        desired['reading_time'] = _reading_time(content)
        image_bytes = cover_bytes()
        jpg_bytes = og_bytes()
        cover_name = cover_versioned_filename(COVER_FILENAME, image_bytes)
        og_name = cover_versioned_filename(OG_FILENAME, jpg_bytes)
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{SLUG}'))
        self.stdout.write(f'  web address: /blog/{SLUG}/')
        self.stdout.write(f'  cover source: {COVER_PATH.name} ({len(image_bytes)} bytes)')
        self.stdout.write(f'  og source: {OG_PATH.name} ({len(jpg_bytes)} bytes)')

        post_changes = 0
        cover_changes = False
        og_changes = False
        if existing is None:
            self.stdout.write('  action: create new published post')
            post_changes = len(UPDATE_FIELDS) + 2
            for field in UPDATE_FIELDS:
                if field == 'content':
                    self.stdout.write(f'  content: {len(content.split())} words (new)')
                else:
                    value = str(desired[field])
                    self.stdout.write(f'  {field}: {value[:110]}{"…" if len(value) > 110 else ""}')
            self.stdout.write(f'  featured_image: will set -> blog/featured/{cover_name}')
            self.stdout.write(f'  og_image: will set -> blog/og/{og_name}')
            cover_changes = True
            og_changes = True
        else:
            self.stdout.write(f'  action: update existing post (id={existing.pk})')
            for field in UPDATE_FIELDS:
                old = getattr(existing, field)
                new = desired[field]
                if (old or '') != (new or ''):
                    post_changes += 1
                    if field == 'content':
                        self.stdout.write(
                            f'  content: {len(strip_tags(old).split())} -> '
                            f'{len(strip_tags(new).split())} words'
                        )
                    else:
                        self.stdout.write(f'  {field}:')
                        self.stdout.write(f'      was: {str(old)[:110]}{"…" if len(str(old)) > 110 else ""}')
                        self.stdout.write(f'      now: {str(new)[:110]}{"…" if len(str(new)) > 110 else ""}')
            if not featured_is_current(existing, image_bytes, COVER_FILENAME):
                post_changes += 1
                cover_changes = True
                current_name = existing.featured_image.name if existing.featured_image else '(none)'
                self.stdout.write(
                    f'  featured_image: {current_name} -> blog/featured/{cover_name}'
                )
            if not og_is_current(existing, jpg_bytes, OG_FILENAME):
                post_changes += 1
                og_changes = True
                current_og = existing.og_image.name if existing.og_image else '(none)'
                self.stdout.write(f'  og_image: {current_og} -> blog/og/{og_name}')
            if post_changes == 0:
                self.stdout.write('  fields: already up to date')

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                '\nDRY RUN: nothing was changed. Run again with --apply to save.'
            ))
            return

        with transaction.atomic():
            if existing is None or post_changes:
                if existing is None:
                    post = BlogPost(slug=SLUG, publish_date=timezone.now())
                else:
                    post = existing
                for field, value in desired.items():
                    setattr(post, field, value)
                if existing is None and not post.publish_date:
                    post.publish_date = timezone.now()

                if cover_changes or not featured_is_current(post if existing else None, image_bytes, COVER_FILENAME):
                    assign_versioned_cover(post, image_bytes, COVER_FILENAME)
                if og_changes or not og_is_current(post, jpg_bytes, OG_FILENAME):
                    assign_versioned_og_image(post, jpg_bytes, OG_FILENAME)

                post.save()
                fresh = BlogPost.objects.get(slug=SLUG)
                if fresh.content != content or fresh.status != BlogPost.STATUS_PUBLISHED:
                    raise CommandError(f'{SLUG} did not save correctly; everything was rolled back.')
                if not fresh.featured_image or not fresh.featured_image.name.endswith(cover_name):
                    raise CommandError(f'{SLUG} featured_image did not save correctly; rolled back.')
                if not fresh.og_image or not fresh.og_image.name.endswith(og_name):
                    raise CommandError(f'{SLUG} og_image did not save correctly; rolled back.')
                if BlogPost.objects.filter(slug=SLUG).count() != 1:
                    raise CommandError(f'{SLUG} duplicated; rolled back.')
            else:
                self.stdout.write('  skipped post.save(); nothing changed')

        if existing is None:
            action = 'Created'
        elif post_changes:
            action = 'Updated'
        else:
            action = 'Left unchanged'
        self.stdout.write(self.style.SUCCESS(
            f'{action} /blog/{SLUG}/ '
            f'(status=published, reading_time={desired["reading_time"]} min, '
            f'featured_image=blog/featured/{cover_name}, '
            f'og_image=blog/og/{og_name}).'
        ))
