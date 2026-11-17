"""Trim blog meta descriptions and excerpts that were longer than 150 characters.

    python manage.py fix_blog_meta_descriptions            # dry run
    python manage.py fix_blog_meta_descriptions --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Only the listed
fields on the listed posts are updated when they differ from the trimmed
seed values. A rerun does not call post.save() when nothing changed, so
updated_at stays put.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from kitchen.blog_content import POST_UPDATES
from kitchen.blog_seed_discord import FIELDS as DISCORD_FIELDS
from kitchen.blog_seed_google_messages import FIELDS as GM_FIELDS
from kitchen.blog_seed_instagram import FIELDS as IG_FIELDS
from kitchen.blog_seed_iphone import FIELDS as IPHONE_FIELDS
from kitchen.blog_seed_not_working import FIELDS as NOT_WORKING_FIELDS
from kitchen.blog_seed_on_pc import FIELDS as ON_PC_FIELDS
from kitchen.blog_seed_save_download import FIELDS as SAVE_FIELDS
from kitchen.models import BlogPost

# Fields written for each slug. The iPhone excerpt comes from seed_iphone,
# not blog_content, because update_blog_posts --post emoji-kitchen-iphone
# fails after that seed and must not be relied on.
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
        'excerpt': POST_UPDATES['emoji-kitchen-samsung']['fields']['excerpt'],
    },
    'emoji-kitchen-gboard': {
        'excerpt': POST_UPDATES['emoji-kitchen-gboard']['fields']['excerpt'],
    },
    'emoji-kitchen-whatsapp': {
        'excerpt': POST_UPDATES['emoji-kitchen-whatsapp']['fields']['excerpt'],
    },
    'emoji-kitchen-iphone': {
        'excerpt': IPHONE_FIELDS['excerpt'],
    },
    'how-to-save-download-emoji-kitchen-stickers': {
        'excerpt': SAVE_FIELDS['excerpt'],
    },
    'emoji-kitchen-discord': {
        'excerpt': DISCORD_FIELDS['excerpt'],
    },
    'emoji-kitchen-google-messages': {
        'excerpt': GM_FIELDS['excerpt'],
    },
    'emoji-kitchen-instagram': {
        'excerpt': IG_FIELDS['excerpt'],
    },
}


class Command(BaseCommand):
    help = (
        'Trim blog meta descriptions and excerpts to 150 characters or fewer '
        '(dry run unless --apply is given).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write trimmed meta and excerpt fields to the database.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        planned = []
        missing = 0
        already_ok = 0

        self.stdout.write(self.style.MIGRATE_HEADING('\nblog meta descriptions and excerpts'))
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
                f'No meta descriptions or excerpts need fixing '
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
