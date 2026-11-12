"""Add internal links from blog posts to the emoji combo category pages.

    python manage.py seed_combo_page_links            # dry run
    python manage.py seed_combo_page_links --apply    # write to the database

The posts live in the production database, so this is a data command. It is safe
to run more than once:

* Nothing is written without ``--apply``.
* A post is changed only when its paragraph is missing. A post that already has
  the exact paragraph, or already links to the new page, is skipped and never saved,
  so ``updated_at`` does not move on a re-run.
* Missing posts are skipped (they do not abort the run).
* The paragraphs for the Discord, iPhone and save/download posts are appended at the
  end and registered in ``blog_seed_utils`` as known inbound suffixes, so the older
  seed commands for those posts keep them instead of treating them as drift.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from kitchen.blog_seed_combo_links import COMBO_LINKS, SLUGS
from kitchen.blog_updates import BlockError, norm, split_blocks
from kitchen.models import BlogPost


def _reading_time(content):
    return max(1, round(len(strip_tags(content).split()) / 200))


def already_linked(content, marker, html):
    content = content or ''
    return html in content or bool(marker and marker in content)


def place_paragraph(content, placement, html):
    """Return (new_content, note). Never reorders or rewrites anything else in the post."""
    content = content or ''
    if placement.startswith('before:'):
        heading = placement[len('before:'):]
        try:
            hits = [b for b in split_blocks(content) if b.tag == 'h2' and norm(b.text) == norm(heading)]
        except BlockError:
            hits = []
        if len(hits) == 1 and content.count(hits[0].html) == 1:
            at = content.index(hits[0].html)
            return content[:at] + html + '\n\n' + content[at:], f'inserted before "{heading}"'
        note = f'heading "{heading}" not found exactly once; appended at the end instead'
    else:
        note = 'appended at the end'
    return content.rstrip() + '\n' + html + '\n', note


class Command(BaseCommand):
    help = 'Link blog posts to the emoji combo category pages (dry run unless --apply is given).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save changes to the database.')

    def handle(self, *args, **options):
        posts = {p.slug: p for p in BlogPost.objects.filter(slug__in=SLUGS)}
        planned = []
        for slug in SLUGS:
            marker, placement, html = COMBO_LINKS[slug]
            post = posts.get(slug)
            if post is None:
                self.stdout.write(f'{slug}: missing - skip')
                continue
            if already_linked(post.content, marker, html):
                self.stdout.write(f'{slug}: already has the link - skip')
                continue
            new_content, note = place_paragraph(post.content, placement, html)
            planned.append((slug, new_content))
            self.stdout.write(f'{slug}: would add the paragraph ({note})')

        if not planned:
            self.stdout.write(self.style.SUCCESS('Nothing to change.'))
            return
        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                f'Dry run only. Re-run with --apply to update {len(planned)} post(s).'
            ))
            return

        saved = 0
        with transaction.atomic():
            for slug, _planned_content in planned:
                marker, placement, html = COMBO_LINKS[slug]
                post = BlogPost.objects.select_for_update().get(slug=slug)
                if already_linked(post.content, marker, html):   # changed since the plan
                    continue
                post.content, _note = place_paragraph(post.content, placement, html)
                post.reading_time = _reading_time(post.content)
                post.updated_at = timezone.now()
                post.save(update_fields=['content', 'reading_time', 'updated_at'])
                saved += 1
                self.stdout.write(self.style.SUCCESS(f'{slug}: updated'))
        self.stdout.write(self.style.SUCCESS(f'Applied {saved} post update(s).'))
