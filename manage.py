#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emoji_kitchen.settings')
    # Local CLI only. gunicorn/wsgi does not import manage.py, so the live
    # process stays DEBUG=false and must get DJANGO_SECRET_KEY from the environment.
    os.environ.setdefault('DJANGO_DEBUG', 'true')
    if os.environ.get('DJANGO_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}:
        os.environ.setdefault(
            'DJANGO_SECRET_KEY',
            'django-insecure-dev-only-emoji-kitchen-not-for-production',
        )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
