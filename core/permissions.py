# D:\Django\MaemohP9\core\permissions.py

from rest_framework.permissions import BasePermission

class IsFleetUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'fleet_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='fleet_access').exists()
        )

class IsCashflowUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'cashflow_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='cashflow_access').exists()
        )

class IsPayablesUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'payables_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='payables_access').exists()
        )

class IsMineProgressUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'mineprogress_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='mineprogress_access').exists()
        )

class IsRevenueUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'revenue_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='revenue_access').exists()
        )

class IsLoansUser(BasePermission):
    """ อนุญาตเฉพาะ user ในกลุ่ม 'loans_access' """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='loans_access').exists()
        )

# =========================================
# เพิ่ม Role-Based Permissions
# =========================================

class IsCFOUser(BasePermission):
    """
    อนุญาตเฉพาะ user ในกลุ่ม 'cfo_access'
    ใช้สำหรับ action ที่ CFO เท่านั้น (Create LC, Record Swift, Approve PNTicket/CashPayment,
    Repay TR, Approve ITDLoan)
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='cfo_access').exists()
        )

class IsPDUser(BasePermission):
    """
    อนุญาตเฉพาะ user ในกลุ่ม 'pd_access'
    ใช้สำหรับ PD Approve (PaymentRequest)
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='pd_access').exists()
        )

class IsCommitteeUser(BasePermission):
    """
    อนุญาตเฉพาะ user ในกลุ่ม 'committee_access'
    ใช้สำหรับ vote/recommend PaymentRequestItem
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='committee_access').exists()
        )

class IsProfessorUser(BasePermission):
    """
    อนุญาตเฉพาะ user ในกลุ่ม 'professor_access'
    ใช้สำหรับ action ที่ต้องอาจารย์อนุมัติ (LCRequest, PNTicket, CashPayment)
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='professor_access').exists()
        )
