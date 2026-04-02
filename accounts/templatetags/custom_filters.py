from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """获取字典中指定键的值"""
    if dictionary is None:
        return None
    return dictionary.get(key)
