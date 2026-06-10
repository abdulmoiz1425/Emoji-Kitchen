from django.db import models


class FAQ(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('GUIDE', 'Guide'),
        ('HOW-TO', 'How-To'),
        ('FUN', 'Fun'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    read_time = models.CharField(max_length=50)
    emoji_header = models.CharField(max_length=20, help_text='Emoji(s) for card header')
    card_bg_color = models.CharField(max_length=20, default='#F5E6D3')
    coming_soon = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.title
