"""Tiny .env loader (no extra dependency).

The server keeps its settings in a `.env` file next to manage.py, so plain
`python manage.py runserver` runs in production mode without extra commands:

    DJANGO_DEBUG=false
    DJANGO_SECRET_KEY=<long random secret>

Real environment variables always win over the file. Set DJANGO_ENV_FILE to
read a different file. With no file, nothing changes (local development).
"""
import os
from pathlib import Path


def env_file_path(base_dir=None):
    explicit = os.environ.get('DJANGO_ENV_FILE', '').strip()
    if explicit:
        return Path(explicit)
    return Path(base_dir or Path(__file__).resolve().parent.parent) / '.env'


def load_env(base_dir=None):
    """Load KEY=VALUE lines into os.environ without overriding existing values.

    Returns True if a file was read."""
    path = env_file_path(base_dir)
    if not path.is_file():
        return False
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        if line.startswith('export '):
            line = line[len('export '):].lstrip()
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)
    return True
