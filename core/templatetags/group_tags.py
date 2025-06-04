# D:\Django\MaemohP9\core\templatetags\group_tags.py

from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    ตรวจว่า user อยู่ใน group ที่ชื่อ group_name หรือไม่
    Usage ใน template:
      {% if user|has_group:"fleet_access" %}
        ... แสดงเนื้อหาสำหรับผู้ที่อยู่ใน fleet_access ...
      {% endif %}
    """
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()

