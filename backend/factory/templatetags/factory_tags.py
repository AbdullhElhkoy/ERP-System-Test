from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """الوصول لعنصر قاموس بمفتاح ديناميكي في القالب."""
    try:
        return mapping.get(key, "")
    except AttributeError:
        return ""
