from django.contrib import admin
from .models import FAQ, BlogPost, Category, Tag


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'is_featured', 'publish_date', 'updated_at')
    list_filter = ('status', 'is_featured', 'category', 'tags', 'publish_date')
    search_fields = ('title', 'author', 'category__name', 'status')
    filter_horizontal = ('tags',)
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'publish_date'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'author', 'featured_image', 'excerpt', 'content'),
        }),
        ('Classification', {
            'fields': ('category', 'tags', 'reading_time'),
        }),
        ('Publishing', {
            'fields': ('status', 'is_featured', 'publish_date'),
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': (
                'seo_title', 'seo_description', 'seo_keywords',
                'canonical_url', 'meta_robots',
                'og_title', 'og_description', 'og_image',
            ),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )
