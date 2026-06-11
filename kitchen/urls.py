from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('api/combo/', views.get_combo, name='get_combo'),
    path('api/download/', views.download_combo, name='download_combo'),
    path('api/proxy/', views.proxy_image, name='proxy_image'),
]
