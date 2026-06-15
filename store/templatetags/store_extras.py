from django import template

register = template.Library()


@register.filter
def money(value):
    """تنسيق المبالغ: 10000 -> 10,000.00 (فاصلة كل ٣ خانات وعشرتان)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    return f"{v:,.2f}"
