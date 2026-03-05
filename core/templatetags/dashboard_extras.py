from django import template

register = template.Library()

@register.filter
def get_item(container, key):
    """
    Template filter para acessar itens de qualquer container por chave/índice
    Uso: {{ container|get_item:key }}
    """
    try:
        if hasattr(container, 'get'):
            return container.get(key)
        elif hasattr(container, '__getitem__'):
            return container[key]
        elif hasattr(container, '__iter__'):
            # Se for um queryset ou lista, procura por ID
            for item in container:
                if hasattr(item, 'id') and item.id == key:
                    return item
                elif hasattr(item, 'pk') and item.pk == key:
                    return item
        return None
    except (TypeError, KeyError, IndexError):
        return None