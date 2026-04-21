"""Heroku Scheduler entry point.

Recommended cadence: Monday 09:00 UTC.
    heroku addons:create scheduler:standard -a cultureconnect
    heroku addons:open scheduler -a cultureconnect
    # add job: `python manage.py send_weekly_digest` — weekly
"""
from django.core.management.base import BaseCommand
from apps.events.digest import send_weekly_digest


class Command(BaseCommand):
    help = 'Send the weekly "what\'s happening" digest to all active users.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Count recipients but do not send')
        parser.add_argument('--limit', type=int, default=None, help='Cap number of recipients (useful for staging)')

    def handle(self, *args, **opts):
        sent, skipped = send_weekly_digest(dry_run=opts['dry_run'], limit=opts['limit'])
        mode = '[dry-run] ' if opts['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(f'{mode}Digest: {sent} sent, {skipped} skipped.'))
