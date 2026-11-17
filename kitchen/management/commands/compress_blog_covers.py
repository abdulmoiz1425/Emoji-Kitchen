"""Attach compressed, content-hashed covers and JPEG og:image files.

    python manage.py compress_blog_covers            # dry run
    python manage.py compress_blog_covers --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Each post in
``kitchen.blog_covers.COVER_FILES`` gets the matching WebP as the on-page
featured image and a same-size JPEG as ``og_image``, both via
content-hashed names. A rerun that finds both already current does not
call post.save(), so updated_at stays put and IndexNow is not fired.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from kitchen.blog_covers import (
    COVER_FILES,
    cover_bytes,
    cover_filename,
    cover_path,
    og_bytes,
    og_filename,
    og_path,
)
from kitchen.blog_seed_utils import (
    assign_versioned_cover,
    assign_versioned_og_image,
    cover_versioned_filename,
    featured_is_current,
    og_is_current,
)
from kitchen.models import BlogPost


class Command(BaseCommand):
    help = (
        'Attach compressed WebP covers and JPEG og:image files (long edge 1200, '
        'source aspect) under content-hashed names (dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write new featured and og images to the database and storage.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        planned = []
        missing = 0
        already_ok = 0

        self.stdout.write(self.style.MIGRATE_HEADING('\nblog covers'))
        for slug in COVER_FILES:
            webp_path = cover_path(slug)
            jpg_path = og_path(slug)
            if not webp_path.is_file():
                raise CommandError(f'Cover fixture missing: {webp_path}')
            if not jpg_path.is_file():
                raise CommandError(f'OG JPEG fixture missing: {jpg_path}')
            webp = cover_bytes(slug)
            jpg = og_bytes(slug)
            webp_name = cover_filename(slug)
            jpg_name = og_filename(slug)
            featured_dest = cover_versioned_filename(webp_name, webp)
            og_dest = cover_versioned_filename(jpg_name, jpg)
            post = BlogPost.objects.filter(slug=slug).first()
            if post is None:
                missing += 1
                self.stdout.write(f'  {slug}: missing — skip')
                continue
            need_featured = not featured_is_current(post, webp, webp_name)
            need_og = not og_is_current(post, jpg, jpg_name)
            if not need_featured and not need_og:
                already_ok += 1
                self.stdout.write(
                    f'  {slug}: already blog/featured/{featured_dest} '
                    f'and blog/og/{og_dest}'
                )
                continue
            current_feat = post.featured_image.name if post.featured_image else '(none)'
            current_og = post.og_image.name if post.og_image else '(none)'
            planned.append((post, webp, webp_name, featured_dest, jpg, jpg_name, og_dest, need_featured, need_og))
            parts = []
            if need_featured:
                parts.append(f'{current_feat} -> blog/featured/{featured_dest} ({len(webp)} bytes)')
            if need_og:
                parts.append(f'{current_og} -> blog/og/{og_dest} ({len(jpg)} bytes)')
            self.stdout.write(f'  {slug}: ' + '; '.join(parts))

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
            for post, webp, webp_name, featured_dest, jpg, jpg_name, og_dest, need_featured, need_og in planned:
                post.refresh_from_db()
                need_featured = not featured_is_current(post, webp, webp_name)
                need_og = not og_is_current(post, jpg, jpg_name)
                if not need_featured and not need_og:
                    continue
                if need_featured:
                    assign_versioned_cover(post, webp, webp_name)
                if not og_is_current(post, jpg, jpg_name):
                    assign_versioned_og_image(post, jpg, jpg_name)
                post.updated_at = timezone.now()
                post.save()
                fresh = BlogPost.objects.get(pk=post.pk)
                if need_featured and (
                    not fresh.featured_image or not fresh.featured_image.name.endswith(featured_dest)
                ):
                    raise CommandError(
                        f'{post.slug} featured_image did not save correctly; rolled back.'
                    )
                if not fresh.og_image or not fresh.og_image.name.endswith(og_dest):
                    raise CommandError(
                        f'{post.slug} og_image did not save correctly; rolled back.'
                    )
                updated += 1
                self.stdout.write(self.style.SUCCESS(f'  {post.slug}: updated'))

        self.stdout.write(self.style.SUCCESS(
            f'Updated {updated} cover(s) '
            f'({already_ok} already current, {missing} missing).'
        ))
