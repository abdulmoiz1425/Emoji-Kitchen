from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save


class KitchenConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kitchen'
    verbose_name = 'Emoji Kitchen'

    def ready(self):
        from kitchen.indexnow import on_blog_post_save, snapshot_blog_post_before_save
        from kitchen.models import BlogPost

        pre_save.connect(
            snapshot_blog_post_before_save,
            sender=BlogPost,
            dispatch_uid='kitchen.indexnow.blogpost.presave',
        )
        post_save.connect(
            on_blog_post_save,
            sender=BlogPost,
            dispatch_uid='kitchen.indexnow.blogpost',
        )
