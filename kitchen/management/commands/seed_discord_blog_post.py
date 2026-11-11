"""Create or update the emoji-kitchen-discord blog post and inbound links.

    python manage.py seed_discord_blog_post            # dry run
    python manage.py seed_discord_blog_post --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Running twice with
--apply is idempotent for the seeded fields and the featured cover, and it
does not call post.save() when nothing changed, so updated_at stays put.
Inbound links are appended on related posts only when missing. Missing related
posts are skipped (they do not abort the seed).
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_discord import (
    COVER_FILENAME,
    COVER_PATH,
    FIELDS,
    INBOUND_HTML,
    INBOUND_MARKER,
    INBOUND_SLUGS,
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
    'canonical_url',
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
        'Create or update the emoji-kitchen-discord blog post and append '
        'inbound links on related posts (dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Save the post and inbound links to the database.',
        )

    def handle(self, *args, **options):
        if not COVER_PATH.is_file():
            raise CommandError(f'Cover image missing: {COVER_PATH}')
        try:
            content = content_html()
        except FileNotFoundError as exc:
            raise CommandError(f'Content fixture missing: {exc}') from exc
        if not content.strip():
            raise CommandError('Content fixture is empty.')

        desired = {**FIELDS, 'content': content, 'status': BlogPost.STATUS_PUBLISHED}
        desired['reading_time'] = _reading_time(content)
        image_bytes = cover_bytes()

        existing = BlogPost.objects.filter(slug=SLUG).first()
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{SLUG}'))
        self.stdout.write(f'  web address: /blog/{SLUG}/')
        self.stdout.write(f'  cover source: {COVER_PATH.name} ({len(image_bytes)} bytes)')

        post_changes = 0
        cover_changes = False
        if existing is None:
            self.stdout.write('  action: create new published post')
            post_changes = len(UPDATE_FIELDS) + 1
            for field in UPDATE_FIELDS:
                if field == 'content':
                    self.stdout.write(f'  content: {len(content.split())} words (new)')
                else:
                    value = str(desired[field])
                    self.stdout.write(f'  {field}: {value[:110]}{"…" if len(value) > 110 else ""}')
            self.stdout.write(f'  featured_image: will set -> blog/featured/{COVER_FILENAME}')
            cover_changes = True
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
            if _cover_needs_update(existing, image_bytes):
                post_changes += 1
                cover_changes = True
                current_name = existing.featured_image.name if existing.featured_image else '(none)'
                self.stdout.write(
                    f'  featured_image: {current_name} -> blog/featured/{COVER_FILENAME}'
                )
            if post_changes == 0:
                self.stdout.write('  fields: already up to date')

        # Plan inbound links (skip missing posts; never abort for them).
        inbound_planned = []
        self.stdout.write(self.style.MIGRATE_HEADING('\ninbound links'))
        for related_slug in INBOUND_SLUGS:
            related = BlogPost.objects.filter(slug=related_slug).first()
            if related is None:
                self.stdout.write(f'  {related_slug}: missing — skip')
                continue
            if INBOUND_MARKER in (related.content or ''):
                self.stdout.write(f'  {related_slug}: already links here — skip')
                continue
            inbound_planned.append(related_slug)
            self.stdout.write(f'  {related_slug}: would append discord link')

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

                if cover_changes or _cover_needs_update(post if existing else None, image_bytes):
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
                if BlogPost.objects.filter(slug=SLUG).count() != 1:
                    raise CommandError(f'{SLUG} duplicated; rolled back.')
            else:
                self.stdout.write('  skipped post.save(); nothing changed')

            for related_slug in inbound_planned:
                related = BlogPost.objects.filter(slug=related_slug).first()
                if related is None:
                    continue
                if INBOUND_MARKER in (related.content or ''):
                    continue
                related.content = related.content.rstrip() + '\n' + INBOUND_HTML + '\n'
                related.reading_time = _reading_time(related.content)
                related.updated_at = timezone.now()
                related.save(update_fields=['content', 'reading_time', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'  {related_slug}: linked'))

        if existing is None:
            action = 'Created'
        elif post_changes:
            action = 'Updated'
        else:
            action = 'Left unchanged'
        self.stdout.write(self.style.SUCCESS(
            f'{action} /blog/{SLUG}/ '
            f'(status=published, reading_time={desired["reading_time"]} min, '
            f'featured_image=blog/featured/{COVER_FILENAME}, '
            f'inbound={len(inbound_planned)}).'
        ))
