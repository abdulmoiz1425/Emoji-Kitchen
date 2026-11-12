"""Correct BlogPost.canonical_url values that are not the post's own URL.

    python manage.py fix_blog_canonicals            # dry run
    python manage.py fix_blog_canonicals --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Every post
whose stored canonical_url is non-empty and not
https://emojikitchenhub.com/blog/<slug>/ is listed and, with --apply,
set to that URL. Empty values are left empty (the page already falls
back to the computed URL). A rerun does not call post.save() when
nothing changed, so updated_at stays put.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from kitchen.models import BlogPost
from kitchen.seo import absolute_blog_canonical


class Command(BaseCommand):
    help = (
        'List or correct BlogPost.canonical_url values that are not the '
        'post\'s own /blog/<slug>/ URL (dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write corrected canonical_url values to the database.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        planned = []
        already_ok = 0
        empty = 0

        self.stdout.write(self.style.MIGRATE_HEADING('\nblog canonicals'))
        for post in BlogPost.objects.all().order_by('slug'):
            desired = absolute_blog_canonical(post.slug)
            stored = (post.canonical_url or '').strip()
            if not stored:
                empty += 1
                self.stdout.write(f'  {post.slug}: empty — leave')
                continue
            if stored == desired:
                already_ok += 1
                self.stdout.write(f'  {post.slug}: already {desired}')
                continue
            planned.append((post, stored, desired))
            self.stdout.write(f'  {post.slug}: {stored} -> {desired}')

        if not planned:
            self.stdout.write(self.style.SUCCESS(
                f'No stored canonicals need fixing '
                f'({already_ok} already correct, {empty} empty).'
            ))
            return

        if not apply:
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN: {len(planned)} post(s) would be updated. '
                f'Run again with --apply to save.'
            ))
            return

        updated = 0
        for post, stored, desired in planned:
            # Re-read so a rerun or race does not bump updated_at for a
            # value that is already correct.
            post.refresh_from_db()
            current = (post.canonical_url or '').strip()
            if current == desired:
                continue
            post.canonical_url = desired
            post.updated_at = timezone.now()
            post.save(update_fields=['canonical_url', 'updated_at'])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f'  {post.slug}: updated'))

        self.stdout.write(self.style.SUCCESS(
            f'Corrected {updated} canonical_url value(s) '
            f'({already_ok} already correct, {empty} empty).'
        ))
