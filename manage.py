#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emoji_kitchen.settings')
    # The server keeps DJANGO_DEBUG=false and DJANGO_SECRET_KEY in a .env file next to
    # this script (see emoji_kitchen/envfile.py), so `python manage.py runserver` is safe
    # there. With no .env (local development) DEBUG defaults to true below.
    from emoji_kitchen.envfile import load_env
    load_env()
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
