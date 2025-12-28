# game/templatetags/game_extras.py
from django import template
from django.core import serializers
import json

register = template.Library()


@register.filter
def json_dump(obj):
    """Safely serialize an object to JSON for use in JavaScript."""
    from django.forms.models import model_to_dict
    import json
    
    if hasattr(obj, '__iter__'):
        # It's a queryset or list
        result = []
        for item in obj:
            if hasattr(item, '__dict__'):
                result.append(model_to_dict(item))
            else:
                result.append(item)
        return json.dumps(result)
    else:
        # It's a single object
        if hasattr(obj, '__dict__'):
            return json.dumps(model_to_dict(obj))
        return json.dumps(obj)
