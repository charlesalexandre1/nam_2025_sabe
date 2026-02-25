from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """Retorna o valor do dicionário para a chave fornecida."""
    return d.get(key)

@register.filter
def br_decimal(value, arg=1):
    """Formata número com vírgula como separador decimal."""
    if value is None:
        return ''
    try:
        # Converte para float para garantir que funcione com Decimal
        num = float(value)
        formatted = f"{num:.{arg}f}".replace('.', ',')
        return formatted
    except (ValueError, TypeError):
        return value