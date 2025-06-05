from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsPayablesUser  # ตรวจสิทธิ์ "payables_access"

from .models import Vendor, AccountsPayable, SiteOperationExpense, SupplierCredit
from .serializers import (
    VendorSerializer,
    AccountsPayableSerializer,
    SiteOperationExpenseSerializer,
    SupplierCreditSerializer
)

PERMS = [IsAuthenticated, IsPayablesUser]

class VendorViewSet(viewsets.ModelViewSet):
    """
    จัดการ Vendor
    """
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    permission_classes = PERMS
    app_label = 'payables'


class AccountsPayableViewSet(viewsets.ModelViewSet):
    """
    จัดการหนี้ค้างชำระ (AccountsPayable)
    """
    queryset = AccountsPayable.objects.all().order_by('-invoice_date')
    serializer_class = AccountsPayableSerializer
    permission_classes = PERMS
    app_label = 'payables'


class SiteOperationExpenseViewSet(viewsets.ModelViewSet):
    """
    จัดการหมวดหมู่ค่าใช้จ่าย (SiteOperationExpense)
    """
    queryset = SiteOperationExpense.objects.all().order_by('-date')
    serializer_class = SiteOperationExpenseSerializer
    permission_classes = PERMS
    app_label = 'payables'


class SupplierCreditViewSet(viewsets.ModelViewSet):
    """
    จัดการวงเงินเครดิต Suppliers
    """
    queryset = SupplierCredit.objects.all().order_by('supplier_name')
    serializer_class = SupplierCreditSerializer
    permission_classes = PERMS
    app_label = 'payables'


