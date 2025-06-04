from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BankAccountViewSet,
    PostFinanceFacilityViewSet,
    PNLoanUsageViewSet,
    ITDLoanViewSet,
    CashTransactionViewSet,
    ProjectCashAccountViewSet,
    CashFlowForecastViewSet,
    CommitteeMemberViewSet,
    PaymentRequestViewSet,
    PaymentRequestItemViewSet,
    VoteViewSet,
    LCRequestViewSet,
    TRRequestViewSet,
    PNTicketViewSet,
    CashPaymentViewSet
)

router = DefaultRouter()
router.register(r'bankaccounts', BankAccountViewSet, basename='bankaccount')
router.register(r'postfinance', PostFinanceFacilityViewSet, basename='postfinance')
router.register(r'pnloans', PNLoanUsageViewSet, basename='pnloan')
router.register(r'itdloan', ITDLoanViewSet, basename='itdloan')
router.register(r'transactions', CashTransactionViewSet, basename='transaction')
router.register(r'cashaccount', ProjectCashAccountViewSet, basename='cashaccount')
router.register(r'forecast', CashFlowForecastViewSet, basename='forecast')
router.register(r'committee', CommitteeMemberViewSet, basename='committee')
router.register(r'paymentrequests', PaymentRequestViewSet, basename='paymentrequest')
router.register(r'paymentitems', PaymentRequestItemViewSet, basename='paymentitem')
router.register(r'votes', VoteViewSet, basename='vote')
router.register(r'lcrequests', LCRequestViewSet, basename='lcrequest')
router.register(r'trrequests', TRRequestViewSet, basename='trrequest')
router.register(r'pntickets', PNTicketViewSet, basename='pnticket')
router.register(r'cashpayments', CashPaymentViewSet, basename='cashpayment')

urlpatterns = [
    path('', include(router.urls)),
]

