"""Attach compressed, content-hashed covers to every seeded blog post.

    python manage.py compress_blog_covers            # dry run
    python manage.py compress_blog_covers --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Each post in
``kitchen.blog_covers.COVER_FILES`` gets the matching WebP via
``assign_versioned_cover``. A rerun that finds the same bytes under the
versioned name does not call post.save(), so updated_at stays put.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from kitchen.blog_covers import COVER_FILES, cover_bytes, cover_filename, cover_path
from kitchen.blog_seed_utils import (
    assign_versioned_cover,
    cover_is_current,
    cover_versioned_filename,
)
from kitchen.models import BlogPost


class Command(BaseCommand):
    help = (
        'Attach compressed WebP covers (long edge 1200, source aspect) under content-hashed names '
        '(dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write new featured images to the database and storage.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        planned = []
        missing = 0
        already_ok = 0

        self.stdout.write(self.style.MIGRATE_HEADING('\nblog covers'))
        for slug in COVER_FILES:
            path = cover_path(slug)
            if not path.is_file():
                raise CommandError(f'Cover fixture missing: {path}')
            image_bytes = cover_bytes(slug)
            filename = cover_filename(slug)
            name = cover_versioned_filename(filename, image_bytes)
            post = BlogPost.objects.filter(slug=slug).first()
            if post is None:
                missing += 1
                self.stdout.write(f'  {slug}: missing — skip')
                continue
            if cover_is_current(post, image_bytes, filename):
                already_ok += 1
                self.stdout.write(f'  {slug}: already blog/featured/{name}')
                continue
            current = post.featured_image.name if post.featured_image else '(none)'
            planned.append((post, image_bytes, filename, name, current))
            self.stdout.write(
                f'  {slug}: {current} -> blog/featured/{name} ({len(image_bytes)} bytes)'
            )

        if not planned:
            self.stdout.write(self.style.SUCCESS(
                f'No covers need updating '
                f'({already_ok} already current, {missing} missing).'
            ))
            return

        if not apply:
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN: {len(planned)} cover(s) would be updated. '
                f'Run again with --apply to save.'
            ))
            return

        updated = 0
        with transaction.atomic():
            for post, image_bytes, filename, name, _current in planned:
                post.refresh_from_db()
                if cover_is_current(post, image_bytes, filename):
                    continue
                assign_versioned_cover(post, image_bytes, filename)
                post.updated_at = timezone.now()
                post.save()
                fresh = BlogPost.objects.get(pk=post.pk)
                if not fresh.featured_image or not fresh.featured_image.name.endswith(name):
                    raise CommandError(
                        f'{post.slug} featured_image did not save correctly; rolled back.'
                    )
                updated += 1
                self.stdout.write(self.style.SUCCESS(f'  {post.slug}: updated'))

        self.stdout.write(self.style.SUCCESS(
            f'Updated {updated} cover(s) '
            f'({already_ok} already current, {missing} missing).'
        ))
