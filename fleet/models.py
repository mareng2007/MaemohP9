from django.db import models

class Truck(models.Model):
    """
    เก็บข้อมูลรถบรรทุก (Truck)
    """
    number_plate = models.CharField(max_length=20, unique=True)
    driver_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.number_plate

class GPSLog(models.Model):
    """
    เก็บตำแหน่ง GPS ของรถบรรทุก ณ เวลานั้น ๆ
    """
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='gps_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return f"{self.truck.number_plate} at {self.timestamp}"
