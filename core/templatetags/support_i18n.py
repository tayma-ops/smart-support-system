from django import template
from core.localization import department_label

register = template.Library()
register.filter("department_name", department_label)
