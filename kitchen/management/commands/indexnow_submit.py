"""Submit URLs to the IndexNow API.

    python manage.py indexnow_submit https://emojikitchenhub.com/blog/foo/
    python manage.py indexnow_submit --sitemap
    python manage.py indexnow_submit --sitemap --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from kitchen.indexnow import (
    INDEXNOW_BATCH_SIZE,
    collect_sitemap_urls,
    configured_key,
    submit_urls,
)


class Command(BaseCommand):
    help = (
        'Submit one or more URLs, or every URL in the site sitemaps, to IndexNow. '
        'Use --dry-run to print the list without sending.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'urls',
            nargs='*',
            help='Absolute URLs or site paths to submit.',
        )
        parser.add_argument(
            '--sitemap',
            action='store_true',
            help='Include every URL from the Django sitemap classes.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the URLs that would be submitted, and do not send.',
        )

    def handle(self, *args, **options):
        urls = list(options['urls'])
        if options['sitemap']:
            urls.extend(collect_sitemap_urls())
        if not urls:
            raise CommandError('Provide at least one URL, or use --sitemap.')

        if not options['dry_run'] and not configured_key():
            raise CommandError('INDEXNOW_KEY is empty; nothing was submitted.')

        # Deduplicate while preserving order (submit_urls also does this).
        unique = []
        seen = set()
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique.append(url)

        if options['dry_run']:
            for url in unique:
                self.stdout.write(url)
            self.stdout.write(self.style.SUCCESS(
                f'Would submit {len(unique)} URL(s) in '
                f'{(len(unique) + INDEXNOW_BATCH_SIZE - 1) // INDEXNOW_BATCH_SIZE} batch(es).'
            ))
            return

        sent = 0
        for start in range(0, len(unique), INDEXNOW_BATCH_SIZE):
            chunk = unique[start:start + INDEXNOW_BATCH_SIZE]
            # force=True: the operator asked to send, even under DEBUG / tests.
            if submit_urls(chunk, force=True) is not None:
                sent += len(chunk)
        self.stdout.write(self.style.SUCCESS(f'Submitted {sent} URL(s) to IndexNow.'))
