# D:\Django\MaemohP9\mineprogress\views.py

from rest_framework import viewsets
from .models import MineProgressReport, DocumentCheck
from .serializers import MineProgressReportSerializer, DocumentCheckSerializer
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsMineProgressUser   # เปลี่ยนมาใช้ IsMineProgressUser แทน IsAppUser

PERMS = [IsAuthenticated, IsMineProgressUser]

class MineProgressReportViewSet(viewsets.ModelViewSet):
    """
    จัดการ MineProgressReport
    """
    queryset = MineProgressReport.objects.all().order_by('-report_date')
    serializer_class = MineProgressReportSerializer
    permission_classes = PERMS
    app_label = 'mineprogress'

class DocumentCheckViewSet(viewsets.ModelViewSet):
    """
    จัดการ DocumentCheck
    """
    queryset = DocumentCheck.objects.all().order_by('-check_date')
    serializer_class = DocumentCheckSerializer
    permission_classes = PERMS
    app_label = 'mineprogress'


