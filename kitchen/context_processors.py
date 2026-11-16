from django.conf import settings


def google_analytics(request):
    return {'GA_MEASUREMENT_ID': getattr(settings, 'GA_MEASUREMENT_ID', '')}


def site_url(request):
    """Expose the fixed public origin (no trailing slash) to every template."""
    return {'SITE_URL': (getattr(settings, 'SITE_URL', '') or 'https://emojikitchenhub.com').rstrip('/')}
