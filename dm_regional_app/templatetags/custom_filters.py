import datetime

from django import template

register = template.Library()


@register.filter
def add_days(date, days):
    try:
        days = int(days)
        if date:
            return date + datetime.timedelta(days=days)
    except (ValueError, TypeError):
        # Handle the error if days cannot be converted to an integer
        return date
    return date
