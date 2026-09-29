from django import template

from kitchen.seo import clean_post_html as _clean_post_html
from kitchen.seo import image_is_usable as _image_is_usable

register = template.Library()


@register.filter
def clean_post_html(html):
    return _clean_post_html(html)


@register.filter
def image_is_usable(image):
    return _image_is_usable(image)
