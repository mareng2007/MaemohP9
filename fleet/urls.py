from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TruckViewSet, GPSLogViewSet

router = DefaultRouter()
router.register(r'trucks', TruckViewSet, basename='truck')
router.register(r'gpslogs', GPSLogViewSet, basename='gpslog')

urlpatterns = [
    path('', include(router.urls)),
]
