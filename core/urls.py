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


    # path('activate/<uidb64>/<token>/', views.activate, name='activate'),         # ยืนยันอีเมล
    
    # # ← เปลี่ยนให้เป็นแบบ query‐string ล้วน
    # path('activate/', views.activate, name='activate'),

    # # → New: Query-string based activation URL
    # #    reverse('core:activate') → /activate/?uid=<uidb64>&token=<token>
    # path('activate/', views.activate, name='activate'),

    # # → Legacy fallback: path-segment based link
    # #    /activate/<uidb64>/<token>/ 
    # path(
    #     'activate/<uidb64>/<token>/',
    #     views.activate,
    #     name='activate_legacy'
    # ),

    # 1) Query-string based:
    path('activate/', views.activate, name='activate'),
    # 2) Legacy path-segment based:
    path('activate/<uidb64>/<token>/', views.activate, name='activate_segment'),


    path('resend-activation/', views.resend_activation, name='resend_activation'),  # ส่งลิงก์ยืนยันใหม่

    # หน้า Login (Username/Password)  
    path('login/', views.login_view, name='login'),
    # หน้า Verify OTP (ทางอีเมล)
    path('login/verify-otp/', views.login_verify_otp, name='login_verify_otp'),

    path('logout/', views.logout_view, name='logout'),                            # ออกจากระบบ
    path('profile/', views.profile_view, name='profile'),                         # โปรไฟล์ (ต้อง login)
    path('contact/', views.contact_submit, name='contact'),  # ส่งข้อความติดต่อ
    path('scoreboard/', views.scoreboard_view, name='scoreboard'),

    # รวม API endpoints ของ Core (เช่น /api/core/users/)
    path('api/', include((router.urls, 'core-api'))),
    
]
