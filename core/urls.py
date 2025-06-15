# D:\Django\MaemohP9\core\urls.py

from django.urls import path, include
from . import views
from rest_framework import routers
from .views import UserViewSet

app_name = 'core'

# Router สำหรับ DRF API ของ Core
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', views.home, name='home'),                                          # หน้าแรก
    path('dashboard/', views.dashboard_view, name='dashboard'),  # หน้า Dashboard (เฉพาะ CFO/PD)
    path('register/', views.register, name='register'),                          # สมัครสมาชิก
    path('activation-sent/', views.home, name='registration_sent'),              # (optional) หลังส่งอีเมล
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),         # ยืนยันอีเมล
    path('resend-activation/', views.resend_activation, name='resend_activation'),  # ส่งลิงก์ยืนยันใหม่

    # หน้า Login (Username/Password)  
    path('login/', views.login_view, name='login'),
    # หน้า Verify OTP (ทางอีเมล)
    path('login/verify-otp/', views.login_verify_otp, name='login_verify_otp'),

    path('logout/', views.logout_view, name='logout'),                            # ออกจากระบบ
    path('profile/', views.profile_view, name='profile'),                         # โปรไฟล์ (ต้อง login)
    path('contact/', views.contact_submit, name='contact'),  # ส่งข้อความติดต่อ

    # รวม API endpoints ของ Core (เช่น /api/core/users/)
    path('api/', include((router.urls, 'core-api'))),
    
]
