import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emoji_kitchen.settings')
# Do not set DJANGO_DEBUG here. Unset means DEBUG=false.
# DevOps must set DJANGO_SECRET_KEY before this process starts.
application = get_wsgi_application()
