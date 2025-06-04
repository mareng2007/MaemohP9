from rest_framework import serializers
from .models import Truck, GPSLog

class TruckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = ['id', 'number_plate', 'driver_name', 'is_active']

class GPSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSLog
        fields = ['id', 'truck', 'timestamp', 'latitude', 'longitude']
        read_only_fields = ['timestamp']
