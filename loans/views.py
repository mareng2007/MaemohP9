from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsLoansUser  # ตรวจสิทธิ์ "loans_access"
from .models import BankLoan
from .serializers import BankLoanSerializer

PERMS = [IsAuthenticated, IsLoansUser]

class BankLoanViewSet(viewsets.ModelViewSet):
    """
    จัดการข้อมูล BankLoan
    """
    queryset = BankLoan.objects.all().order_by('-agreement_date')
    serializer_class = BankLoanSerializer
    permission_classes = PERMS
    app_label = 'loans'

