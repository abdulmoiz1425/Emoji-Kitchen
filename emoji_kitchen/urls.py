from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.templatetags.static import static as static_url
from django.urls import path, include
from django.views.generic.base import RedirectView

from kitchen.sitemaps import StaticViewSitemap, BlogPostSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    # Browsers request /favicon.ico at the root regardless of the <link rel="icon">
    # tag in base.html, so redirect it to the real favicon instead of 404ing.
    path('favicon.ico', RedirectView.as_view(url=static_url('kitchen/img/favicon.svg')), name='favicon_ico'),
    path('', include('kitchen.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
