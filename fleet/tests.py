from django.test import TestCase
from .models import Truck


class TruckModelTest(TestCase):
    def test_string_representation(self):
        truck = Truck.objects.create(number_plate="AB-123", driver_name="Bob")
        self.assertEqual(str(truck), "AB-123")

