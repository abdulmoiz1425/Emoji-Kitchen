from django.contrib import admin
from .models import FAQ, BlogPost


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'read_time', 'coming_soon')
    list_filter = ('category', 'coming_soon')
