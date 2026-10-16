"""Update the four blog posts with the "Remaining Content Updates" text.

    python manage.py update_blog_posts               # dry run: shows what would change, changes nothing
    python manage.py update_blog_posts --apply       # backs the posts up, then applies the changes
    python manage.py update_blog_posts --restore PATH_TO_BACKUP.json    # puts the old text back

Safe by design: nothing is saved unless every post can be updated; the old text is written to a
backup file first; slugs (the web addresses) are never changed; running it twice changes nothing
the second time.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from kitchen import blog_updates
from kitchen.blog_content import POST_UPDATES
from kitchen.models import BlogPost

BACKUP_FIELDS = ('title', 'excerpt', 'seo_title', 'seo_description', 'content', 'reading_time')


def _reading_time(content):
    return max(1, round(len(blog_updates.plain(content).split()) / 200))


class Command(BaseCommand):
    help = 'Update the Gboard, Samsung, iPhone and WhatsApp blog posts (dry run unless --apply is given).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save the changes (a backup is written first).')
        parser.add_argument('--restore', metavar='BACKUP_FILE', help='Restore the posts from a backup file.')
        parser.add_argument('--backup-dir', default=str(Path(settings.BASE_DIR) / 'backups'),
                            help='Where backups are written (default: backups/ next to manage.py).')
        parser.add_argument('--post', action='append', dest='posts', metavar='SLUG',
                            help='Only this post (can be repeated).')

    # ── entry point ──────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        if options['restore']:
            return self.restore(options['restore'])
        slugs = options['posts'] or list(POST_UPDATES)
        unknown = [s for s in slugs if s not in POST_UPDATES]
        if unknown:
            raise CommandError(f'No update is defined for: {", ".join(unknown)}')
        posts = {p.slug: p for p in BlogPost.objects.filter(slug__in=slugs)}
        missing = [s for s in slugs if s not in posts]
        if missing:
            raise CommandError(f'These posts do not exist in the database: {", ".join(missing)}. Nothing was changed.')

        plans = {}
        for slug in slugs:
            post = posts[slug]
            current = {f: getattr(post, f) for f in blog_updates.FIELDS + ('content',)}
            plans[slug] = blog_updates.plan_post(slug, current, POST_UPDATES[slug])
        self.report(plans, posts)

        failed = [s for s, plan in plans.items() if not plan.ok]
        if failed:
            raise CommandError(f'Cannot update {", ".join(failed)} (see above). Nothing was changed.')
        if not options['apply']:
            changes = sum(len(p.field_changes) + sum(1 for _, s, _ in p.operations if s == 'will change') for p in plans.values())
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN: nothing was changed. {changes} change(s) are ready. Run again with --apply to save them.'
                if changes else '\nDRY RUN: everything is already up to date. Nothing to do.'))
            return
        self.apply(plans, posts, Path(options['backup_dir']))

    # ── report ───────────────────────────────────────────────────────────────
    def report(self, plans, posts):
        for slug, plan in plans.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n{slug}'))
            self.stdout.write(f'  web address (unchanged): /blog/{slug}/')
            if not plan.field_changes:
                self.stdout.write('  title, excerpt and SEO fields: already up to date')
            for field, (old, new) in plan.field_changes.items():
                self.stdout.write(f'  {field}:')
                self.stdout.write(f'      was: {old[:110]}{"…" if len(old) > 110 else ""}')
                self.stdout.write(f'      now: {new[:110]}{"…" if len(new) > 110 else ""}')
            for name, status, note in plan.operations:
                self.stdout.write(f'  [{status}] {name}: {note}')
            if plan.ok:
                self.stdout.write(f'  article length: {plan.old_words} -> {plan.new_words} words')
            else:
                self.stdout.write(self.style.ERROR(f'  ERROR: {plan.error}'))

    # ── apply ────────────────────────────────────────────────────────────────
    def apply(self, plans, posts, backup_dir):
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime('%Y%m%d-%H%M%S')
        backup_path = backup_dir / f'blog_posts_{stamp}.json'
        backup = {slug: {f: getattr(posts[slug], f) for f in BACKUP_FIELDS} for slug in plans}
        backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(f'\nBackup written: {backup_path}')

        with transaction.atomic():
            for slug, plan in plans.items():
                post = posts[slug]
                for field, (_old, new) in plan.field_changes.items():
                    setattr(post, field, new)
                post.content = plan.new_content
                post.reading_time = _reading_time(post.content)
                post.save(update_fields=list(blog_updates.FIELDS) + ['content', 'reading_time', 'updated_at'])
            # check the saved result before the transaction is allowed to finish
            for slug, plan in plans.items():
                fresh = BlogPost.objects.get(slug=slug)
                if fresh.content != plan.new_content or fresh.slug != slug:
                    raise CommandError(f'{slug} did not save correctly; everything was rolled back.')
                for field, (_old, new) in plan.field_changes.items():
                    if getattr(fresh, field) != new:
                        raise CommandError(f'{slug}.{field} did not save correctly; everything was rolled back.')
        self.stdout.write(self.style.SUCCESS(f'Updated {len(plans)} post(s). To undo: python manage.py update_blog_posts --restore {backup_path}'))

    # ── restore ──────────────────────────────────────────────────────────────
    def restore(self, path):
        file = Path(path)
        if not file.is_file():
            raise CommandError(f'Backup file not found: {file}')
        backup = json.loads(file.read_text(encoding='utf-8'))
        posts = {p.slug: p for p in BlogPost.objects.filter(slug__in=list(backup))}
        missing = [s for s in backup if s not in posts]
        if missing:
            raise CommandError(f'These posts are no longer in the database: {", ".join(missing)}. Nothing was changed.')
        with transaction.atomic():
            for slug, saved in backup.items():
                post = posts[slug]
                for field in BACKUP_FIELDS:
                    setattr(post, field, saved[field])
                post.save(update_fields=list(BACKUP_FIELDS) + ['updated_at'])
        self.stdout.write(self.style.SUCCESS(f'Restored {len(backup)} post(s) from {file}.'))
