# D:\Django\MaemohP9\fleet\views.py

from rest_framework import viewsets
from .models import Truck, GPSLog
from .serializers import TruckSerializer, GPSLogSerializer
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsFleetUser  # เปลี่ยนมาใช้ IsFleetUser แทน IsAppUser

PERMS = [IsAuthenticated, IsFleetUser]

class TruckViewSet(viewsets.ModelViewSet):
    """
    จัดการข้อมูล Truck
    """
    queryset = Truck.objects.all().order_by('number_plate')
    serializer_class = TruckSerializer
    permission_classes = PERMS
    app_label = 'fleet'

class GPSLogViewSet(viewsets.ModelViewSet):
    """
    จัดการข้อมูล GPSLog
    """
    queryset = GPSLog.objects.all().order_by('-timestamp')
    serializer_class = GPSLogSerializer
    permission_classes = PERMS
    app_label = 'fleet'


