from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VendorViewSet,
    AccountsPayableViewSet,
    SiteOperationExpenseViewSet,
    SupplierCreditViewSet
)

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'ap', AccountsPayableViewSet, basename='accounts_payable')
router.register(r'site-expenses', SiteOperationExpenseViewSet, basename='site_expense')
router.register(r'supplier-credits', SupplierCreditViewSet, basename='supplier_credit')

urlpatterns = [
    path('', include(router.urls)),
]
