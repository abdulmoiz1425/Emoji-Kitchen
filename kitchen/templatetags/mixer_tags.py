from django import template

from kitchen.explore import explore_groups

register = template.Library()


@register.inclusion_tag('kitchen/_explore.html')
def explore_combinations():
    return {'groups': explore_groups()}
