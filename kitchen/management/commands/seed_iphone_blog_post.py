"""Update the emoji-kitchen-iphone blog post with the rewritten body.

    python manage.py seed_iphone_blog_post            # dry run
    python manage.py seed_iphone_blog_post --apply    # write to the database

Safe by default: nothing is saved unless --apply is given. Updates the
existing slug only (no duplicate). Does not change the featured image.
Known inbound-link paragraphs appended by other seeds are ignored when
comparing content and are preserved if the fixture body is rewritten.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_iphone import FIELDS, SLUG, content_html
from kitchen.blog_seed_utils import desired_seed_content
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
    'reading_time',
)


def _reading_time(content):
    return max(1, round(len(strip_tags(content).split()) / 200))


class Command(BaseCommand):
    help = 'Update the emoji-kitchen-iphone post from the rewritten fixture (dry run unless --apply).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save changes to the database.')

    def handle(self, *args, **options):
        try:
            post = BlogPost.objects.get(slug=SLUG)
        except BlogPost.DoesNotExist as exc:
            raise CommandError(
                f'Post {SLUG!r} does not exist. Create it first or restore from backup. '
                'Nothing was changed.'
            ) from exc

        content = desired_seed_content(content_html(), post.content)
        desired = {**FIELDS, 'content': content}
        desired['reading_time'] = _reading_time(content)

        changes = []
        for field in UPDATE_FIELDS:
            current = getattr(post, field)
            new = desired[field]
            if current != new:
                changes.append(field)
                self.stdout.write(f'  {field}: will update')

        if not changes:
            self.stdout.write(self.style.SUCCESS(f'{SLUG}: already up to date.'))
            return

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                f'Dry run only ({len(changes)} field(s)). Re-run with --apply to save.'
            ))
            return

        with transaction.atomic():
            for field in changes:
                setattr(post, field, desired[field])
            post.updated_at = timezone.now()
            post.save(update_fields=changes + ['updated_at'])

        self.stdout.write(self.style.SUCCESS(f'{SLUG}: updated {", ".join(changes)}'))
