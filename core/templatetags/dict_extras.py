from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Permite acessar dicionários por chave variável no template."""
    return d.get(key)