"""Trim three blog meta descriptions that were longer than 150 characters.

    python manage.py fix_blog_meta_descriptions            # dry run
    python manage.py fix_blog_meta_descriptions --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Only the three
posts named below are considered, and only the listed meta fields are
updated when they differ from the trimmed seed values. A rerun does not
call post.save() when nothing changed, so updated_at stays put.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from kitchen.blog_content import POST_UPDATES
from kitchen.blog_seed_not_working import FIELDS as NOT_WORKING_FIELDS
from kitchen.blog_seed_on_pc import FIELDS as ON_PC_FIELDS
from kitchen.models import BlogPost

# Fields written for each slug. Samsung keeps its longer listing excerpt;
# only the SEO meta field is trimmed.
META_TARGETS = {
    'emoji-kitchen-on-pc': {
        'seo_description': ON_PC_FIELDS['seo_description'],
        'excerpt': ON_PC_FIELDS['excerpt'],
        'og_description': ON_PC_FIELDS['og_description'],
    },
    'emoji-kitchen-not-working': {
        'seo_description': NOT_WORKING_FIELDS['seo_description'],
        'excerpt': NOT_WORKING_FIELDS['excerpt'],
    },
    'emoji-kitchen-samsung': {
        'seo_description': POST_UPDATES['emoji-kitchen-samsung']['fields']['seo_description'],
    },
}


class Command(BaseCommand):
    help = (
        'Trim the on-pc, not-working, and samsung blog meta descriptions '
        'to 150 characters or fewer (dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write trimmed meta fields to the database.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        planned = []
        missing = 0
        already_ok = 0

        self.stdout.write(self.style.MIGRATE_HEADING('\nblog meta descriptions'))
        for slug, desired in META_TARGETS.items():
            post = BlogPost.objects.filter(slug=slug).first()
            if post is None:
                missing += 1
                self.stdout.write(f'  {slug}: missing — skip')
                continue
            changes = {
                field: (getattr(post, field) or '', value)
                for field, value in desired.items()
                if (getattr(post, field) or '') != value
            }
            if not changes:
                already_ok += 1
                self.stdout.write(f'  {slug}: already up to date')
                continue
            planned.append((post, changes))
            for field, (old, new) in changes.items():
                self.stdout.write(f'  {slug} {field}: {len(old)} -> {len(new)} chars')

        if not planned:
            self.stdout.write(self.style.SUCCESS(
                f'No meta descriptions need fixing '
                f'({already_ok} already correct, {missing} missing).'
            ))
            return

        if not apply:
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN: {len(planned)} post(s) would be updated. '
                f'Run again with --apply to save.'
            ))
            return

        updated = 0
        for post, changes in planned:
            post.refresh_from_db()
            fields = []
            for field, (_old, new) in changes.items():
                if (getattr(post, field) or '') == new:
                    continue
                setattr(post, field, new)
                fields.append(field)
            if not fields:
                continue
            post.updated_at = timezone.now()
            post.save(update_fields=fields + ['updated_at'])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f'  {post.slug}: updated'))

        self.stdout.write(self.style.SUCCESS(
            f'Updated {updated} post(s) '
            f'({already_ok} already correct, {missing} missing).'
        ))
