from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('emoji-maker/', views.emoji_maker, name='emoji_maker'),
    path('emoji-generator/', views.emoji_generator, name='emoji_generator'),
    path('emoji-combos/', views.emoji_combos, name='emoji_combos'),
    path('emoji-combos/love/', views.emoji_combos_love, name='emoji_combos_love'),
    path('emoji-combos/cute/', views.emoji_combos_cute, name='emoji_combos_cute'),
    path('emoji-combos/aesthetic/', views.emoji_combos_aesthetic, name='emoji_combos_aesthetic'),
    path('emoji-combos/funny/', views.emoji_combos_funny, name='emoji_combos_funny'),
    path('emoji-combos/pink/', views.emoji_combos_pink, name='emoji_combos_pink'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('api/combo/', views.get_combo, name='get_combo'),
    path('api/combos-for/', views.get_combos_for_emoji, name='get_combos_for_emoji'),
    path('api/random-combo/', views.get_random_combo, name='get_random_combo'),
    path('api/download/', views.download_combo, name='download_combo'),
    path('api/proxy/', views.proxy_image, name='proxy_image'),
]
