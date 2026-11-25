from django import template
from django.urls import reverse

from kitchen import mood

register = template.Library()


@register.inclusion_tag('kitchen/_mood_form.html')
def mood_form(input_id='mood-input', value='', show_chips=True):
    """The "find an emoji combo for your mood" box. Needs no view context, so any page can use it."""
    base = reverse('emoji_combos_mood')
    chips = [
        {'icon': mood.MOODS[key]['icon'], 'label': mood.MOODS[key]['label'], 'href': f'{base}?mood={key}'}
        for key in mood.CHIP_MOODS
    ]
    return {
        'action': base,
        'input_id': input_id,
        'value': value,
        'chips': chips if show_chips else [],
        'max_length': mood.MAX_TEXT_LENGTH,
    }
