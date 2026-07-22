from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('emoji-maker/', views.emoji_maker, name='emoji_maker'),
    path('emoji-generator/', views.emoji_generator, name='emoji_generator'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('api/combo/', views.get_combo, name='get_combo'),
    path('api/combos-for/', views.get_combos_for_emoji, name='get_combos_for_emoji'),
    path('api/random-combo/', views.get_random_combo, name='get_random_combo'),
    path('api/download/', views.download_combo, name='download_combo'),
    path('api/proxy/', views.proxy_image, name='proxy_image'),
]
