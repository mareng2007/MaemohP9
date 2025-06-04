from rest_framework import permissions

class IsMineProgressUser(permissions.BasePermission):
    """
    ตรวจสอบว่า user อยู่ในกลุ่ม 'mineprogress_access' หรือไม่
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='mineprogress_access').exists()
