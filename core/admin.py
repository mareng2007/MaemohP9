# D:\Django\MaemohP9\core\admin.py

from django.contrib import admin
from .models import UserProfile, EmailActivation, OTP, ScoreTransaction

# ถ้าต้องการให้แอดมินจัดการ model เหล่านี้ ก็สามารถ register เพิ่มได้
admin.site.register(UserProfile)
admin.site.register(EmailActivation)
admin.site.register(OTP)
admin.site.register(ScoreTransaction)
