from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MineProgressReportViewSet, DocumentCheckViewSet

router = DefaultRouter()
router.register(r'reports', MineProgressReportViewSet, basename='report')
router.register(r'docchecks', DocumentCheckViewSet, basename='doccheck')

urlpatterns = [
    path('', include(router.urls)),
]
