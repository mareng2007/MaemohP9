from rest_framework import permissions

class IsFleetUser(permissions.BasePermission):
    """
    ตรวจสอบว่า user อยู่ในกลุ่ม 'fleet_user' หรือไม่
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='fleet_user').exists()
