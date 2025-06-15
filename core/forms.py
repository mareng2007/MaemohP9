# D:\Django\MaemohP9\core\forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from .models import UserProfile, EmailActivation, OTP
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import random
import re

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """
    ฟอร์มสมัครสมาชิก (Username, Email, Password)
    เมื่อสมัครแล้ว user.is_active=False รอการยืนยันอีเมล
    """
    email = forms.EmailField(
        required=True,
        label="อีเมล",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'})
    )
    username = forms.CharField(
        required=True,
        label="ชื่อผู้ใช้",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password1 = forms.CharField(
        required=True,
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        required=True,
        label="ยืนยันรหัสผ่าน",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("อีเมลนี้ถูกใช้งานแล้ว กรุณาใช้ใหม่")
        return email


class CustomLoginForm(AuthenticationForm):
    """
    ฟอร์มล็อกอิน Username / Password (ขั้นแรก)
    """
    username = forms.CharField(
        required=True,
        label="ชื่อผู้ใช้",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        required=True,
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class OTPVerifyForm(forms.Form):
    """
    ฟอร์มกรอกรหัส OTP ที่ส่งไปทางอีเมล
    """
    email = forms.EmailField(widget=forms.HiddenInput())  # ซ่อนอีเมลในฟอร์ม
    code = forms.CharField(
        label="รหัส OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'xxxxxx'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        code = cleaned_data.get('code')
        now = timezone.now()
        try:
            otp_obj = OTP.objects.filter(
                email=email,
                code=code,
                is_used=False,
                valid_until__gte=now
            ).latest('created_at')
        except OTP.DoesNotExist:
            raise ValidationError("รหัส OTP ไม่ถูกต้องหรือหมดอายุ")
        cleaned_data['otp_obj'] = otp_obj
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    """
    ฟอร์มแก้ไขข้อมูลโปรไฟล์ (UserProfile)
    - แปลงเบอร์มือถือเป็น E.164 (ตามเดิม)
    """
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'phone_number', 'avatar')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อ'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'นามสกุล'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0812345678'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            return ''
        digits_only = re.sub(r'[^\d+]', '', phone)
        if len(digits_only) == 10 and digits_only.startswith('0'):
            digits_only = '+66' + digits_only[1:]
        elif len(digits_only) == 11 and digits_only.startswith('66'):
            digits_only = '+' + digits_only
        elif len(digits_only) == 12 and digits_only.startswith('+66'):
            pass
        else:
            raise ValidationError("กรุณากรอกเบอร์มือถือให้ถูกต้อง เช่น 0812345678")
        return digits_only


class EmailResendForm(forms.Form):
    """
    ฟอร์มกรอกอีเมล หากต้องการส่งลิงก์ยืนยันใหม่
    """
    email = forms.EmailField(
        required=True,
        label="อีเมล",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if not User.objects.filter(email=email, is_active=False).exists():
            raise ValidationError("ไม่พบผู้ใช้ที่รอการยืนยันอีเมลนี้")
        return email


class ContactForm(forms.Form):
    """ฟอร์มติดต่อเรา (สำหรับผู้ที่ไม่ได้ล็อกอิน)"""

    name = forms.CharField(
        required=True,
        label="ชื่อ-นามสกุล",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "กรอกชื่อของคุณ"}
        ),
    )

    email = forms.EmailField(
        required=True,
        label="อีเมล",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "you@example.com"}
        ),
    )

    message = forms.CharField(
        required=True,
        label="ข้อความ",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "พิมพ์ข้อความของคุณ",
            }
        ),
    )


