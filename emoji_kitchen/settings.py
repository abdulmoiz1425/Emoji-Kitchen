import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Production (gunicorn / emoji_kitchen.wsgi) does not set DJANGO_DEBUG, so DEBUG
# stays false. manage.py defaults DJANGO_DEBUG=true for local runserver only.
# DevOps must set these before deploy, or the live process will not boot:
#   DJANGO_SECRET_KEY — long random secret (required when DEBUG is false)
#   DJANGO_ALLOWED_HOSTS — optional comma-separated hosts; default is
#       emojikitchenhub.com,www.emojikitchenhub.com
# Do not set DJANGO_DEBUG on the server.


def _as_bool(value):
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG = _as_bool(os.environ.get('DJANGO_DEBUG', ''))

_DEV_SECRET_KEY = 'django-insecure-dev-only-emoji-kitchen-not-for-production'
_DEFAULT_HOSTS = ['emojikitchenhub.com', 'www.emojikitchenhub.com']


def _host_list(raw):
    return [host.strip() for host in (raw or '').split(',') if host.strip()]


if DEBUG:
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or _DEV_SECRET_KEY
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
else:
    SECRET_KEY = (os.environ.get('DJANGO_SECRET_KEY') or '').strip()
    if not SECRET_KEY:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY must be set when DEBUG is false. '
            'Do not set DJANGO_DEBUG on the server.'
        )
    ALLOWED_HOSTS = _host_list(os.environ.get('DJANGO_ALLOWED_HOSTS')) or list(_DEFAULT_HOSTS)
    if '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured('ALLOWED_HOSTS must not be "*" when DEBUG is false.')

# Nginx terminates TLS and forwards X-Forwarded-Proto. This makes
# request.is_secure() and build_absolute_uri() use https behind the proxy.
# SECURE_SSL_REDIRECT is intentionally unset so local runserver stays http.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = ['https://emojikitchenhub.com', 'https://www.emojikitchenhub.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'ckeditor',
    'ckeditor_uploader',
    'kitchen',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'emoji_kitchen.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'emoji_kitchen.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── CKEditor (rich text content) ────────────────────────────────────────────
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            [
                'Source', '-',
                'NewPage', 'Preview', 'Print', '-',
                'Templates',
            ],
            [
                'Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-',
                'Undo', 'Redo',
            ],
            [
                'Find', 'Replace', '-', 'SelectAll', '-', 'Scayt',
            ],
            [
                'Form', 'Checkbox', 'Radio', 'TextField', 'Textarea',
                'Select', 'Button', 'ImageButton', 'HiddenField',
            ],
            '/',
            [
                'Bold', 'Italic', 'Underline', 'Strike',
                'Subscript', 'Superscript', '-',
                'CopyFormatting', 'RemoveFormat',
            ],
            [
                'NumberedList', 'BulletedList', '-',
                'Outdent', 'Indent', '-',
                'Blockquote', 'CreateDiv', '-',
                'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-',
                'BidiLtr', 'BidiRtl', 'Language',
            ],
            [
                'Link', 'Unlink', 'Anchor',
            ],
            [
                'Image', 'Table', 'HorizontalRule',
                'Smiley', 'SpecialChar', 'PageBreak', 'Iframe',
            ],
            '/',
            ['Styles', 'Format', 'Font', 'FontSize'],
            ['TextColor', 'BGColor'],
            ['Maximize', 'ShowBlocks'],
            ['About'],
        ],
        'height': 500,
        'width': '100%',
    },
}
