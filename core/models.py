# D:\Django\MaemohP9\core\models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class UserProfile(models.Model):
    """
    เก็บข้อมูลเสริมของผู้ใช้ (optional)
    เช่น รูปโปรไฟล์, ชื่อ-นามสกุล, เบอร์โทรศัพท์ ฯลฯ
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True, verbose_name="ชื่อ")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="นามสกุล")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="เบอร์มือถือ")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="รูปโปรไฟล์")
    score = models.IntegerField(default=0, verbose_name="คะแนน")
    # สามารถขยายฟิลด์ตามต้องการ

    def __str__(self):
        return f"Profile ของ {self.user.username}"


class EmailActivation(models.Model):
    """
    เก็บโทเคนสำหรับยืนยันอีเมลของผู้ใช้
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_activations')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"EmailActivation({self.user.username}, used={self.is_used})"


class OTP(models.Model):
    """
    เก็บรหัส OTP สำหรับการล็อกอิน 2FA ทางอีเมล
    """
    # email = models.EmailField(verbose_name="อีเมล")     # เก็บอีเมลของผู้ใช้ที่ส่ง OTP ไป
    email = models.EmailField(verbose_name="อีเมล", null=True, blank=True)
    code = models.CharField(max_length=6, verbose_name="รหัส OTP")  # รหัส OTP 6 หลัก
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="เวลาสร้าง")
    valid_until = models.DateTimeField(verbose_name="OTP หมดอายุ")   # เวลา OTP หมดอายุ (เช่น 5 นาทีหลังสร้าง)
    is_used = models.BooleanField(default=False, verbose_name="ถูกใช้งานแล้ว")  # เช็กว่าเคยใช้ไปยัง

    def __str__(self):
        return f"{self.email} → {self.code} (Used: {self.is_used})"
    


class ScoreTransaction(models.Model):
    """Record of point transfers between users."""

    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='scores_sent')
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='scores_received')
    amount = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.amount})"

    @staticmethod
    def transfer(from_user, to_user, amount, reason=""):
        if not from_user or not to_user or amount == 0:
            return None
        from_profile = from_user.profile
        to_profile = to_user.profile
        from_profile.score -= amount
        to_profile.score += amount
        from_profile.save(update_fields=["score"])
        to_profile.save(update_fields=["score"])
        return ScoreTransaction.objects.create(
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            reason=reason,
        )

