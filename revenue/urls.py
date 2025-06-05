# revenue/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'revenue'

# สร้าง DefaultRouter สำหรับ DRF ViewSets
router = DefaultRouter()
router.register(r'jobs', views.RevenueJobViewSet, basename='revenuejob')
router.register(r'ar', views.AccountsReceivableViewSet, basename='accountsreceivable')

urlpatterns = [
    # ===== Web Views (HTML) =====
    # RevenueJob
    path('jobs/', views.RevenueJobListView.as_view(), name='revenuejob-list'),
    path('jobs/create/', views.RevenueJobCreateView.as_view(), name='revenuejob-create'),
    path('jobs/<int:pk>/', views.RevenueJobDetailView.as_view(), name='revenuejob-detail'),
    path('jobs/<int:pk>/update/', views.RevenueJobUpdateView.as_view(), name='revenuejob-update'),

    # AccountsReceivable
    path('ar/', views.AccountsReceivableListView.as_view(), name='ar-list'),
    path('ar/create/', views.AccountsReceivableCreateView.as_view(), name='ar-create'),
    path('ar/<int:pk>/', views.AccountsReceivableDetailView.as_view(), name='ar-detail'),
    path('ar/<int:pk>/update/', views.AccountsReceivableUpdateView.as_view(), name='ar-update'),

    # ส่วน API URLs ของ Revenue (เช่น /api/revenue/jobs/)
    path('api/', include((router.urls, 'revenue-api'))),
]




