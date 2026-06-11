from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify


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


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogPostQuerySet(models.QuerySet):
    def visible(self):
        """Posts that should be shown on the public site: published, or
        scheduled posts whose publish date has already passed."""
        now = timezone.now()
        return self.filter(
            models.Q(status=BlogPost.STATUS_PUBLISHED)
            | models.Q(status=BlogPost.STATUS_SCHEDULED, publish_date__lte=now)
        )


class BlogPost(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_SCHEDULED, 'Scheduled'),
    ]

    ROBOTS_CHOICES = [
        ('index, follow', 'Index, Follow'),
        ('noindex, follow', 'Noindex, Follow'),
        ('index, nofollow', 'Index, Nofollow'),
        ('noindex, nofollow', 'Noindex, Nofollow'),
    ]

    # ── Content ──────────────────────────────────────────────────────────
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True,
                             help_text='Leave blank to auto-generate from the title.')
    author = models.CharField(max_length=100, default='Emoji Kitchen Team')
    featured_image = models.ImageField(upload_to='blog/featured/', blank=True, null=True)
    excerpt = models.TextField(blank=True, help_text='Short summary shown on the blog listing page.')
    content = RichTextUploadingField()

    # ── Classification ───────────────────────────────────────────────────
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    reading_time = models.PositiveIntegerField(
        blank=True, null=True,
        help_text='Estimated reading time in minutes. Leave blank to auto-calculate from the content.'
    )

    # ── Publishing ───────────────────────────────────────────────────────
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_featured = models.BooleanField(default=False, help_text='Highlight this post on the blog page.')
    publish_date = models.DateTimeField(default=timezone.now)

    # ── SEO ──────────────────────────────────────────────────────────────
    seo_title = models.CharField(max_length=70, blank=True, help_text='Falls back to the post title if left blank.')
    seo_description = models.CharField(max_length=160, blank=True, help_text='Falls back to the excerpt if left blank.')
    seo_keywords = models.CharField(max_length=255, blank=True, help_text='Comma-separated keywords.')
    canonical_url = models.URLField(blank=True)
    meta_robots = models.CharField(max_length=30, choices=ROBOTS_CHOICES, default='index, follow')
    og_title = models.CharField(max_length=95, blank=True, help_text='Falls back to the SEO title if left blank.')
    og_description = models.CharField(max_length=200, blank=True, help_text='Falls back to the SEO description if left blank.')
    og_image = models.ImageField(upload_to='blog/og/', blank=True, null=True, help_text='Falls back to the featured image if left blank.')

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        ordering = ['-publish_date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 2
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug

        if self.reading_time is None:
            word_count = len(strip_tags(self.content).split())
            self.reading_time = max(1, round(word_count / 200))

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})

    @property
    def is_visible(self):
        if self.status == self.STATUS_PUBLISHED:
            return True
        if self.status == self.STATUS_SCHEDULED:
            return self.publish_date <= timezone.now()
        return False

    @property
    def meta_title(self):
        return self.seo_title or self.title

    @property
    def meta_description(self):
        return self.seo_description or self.excerpt

    @property
    def og_title_display(self):
        return self.og_title or self.meta_title

    @property
    def og_description_display(self):
        return self.og_description or self.meta_description

    @property
    def og_image_display(self):
        return self.og_image or self.featured_image
