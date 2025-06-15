# D:\Django\MaemohP9\core\views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import Group
from datetime import timedelta, date
from .forms import (
    RegistrationForm, CustomLoginForm,
    OTPVerifyForm, ProfileUpdateForm,
    EmailResendForm
)
from .models import UserProfile, EmailActivation, OTP
from .permissions import IsCFOUser, IsPDUser  # ใช้สำหรับ Dashboard
import random  # สำหรับสร้าง OTP

# สำหรับ Rest Framework API
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework import serializers
from .permissions import IsRevenueUser, IsCashflowUser, IsLoansUser, IsPayablesUser, IsCFOUser, IsPDUser

# ------------------------------
# API Serializers & ViewSets
# ------------------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint: /api/core/users/
    ให้ดูรายชื่อผู้ใช้งาน (สำหรับ mobile/app)
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]  # ปรับได้ตามต้องการ

# ------------------------------
# WEB Views (HTML)
# ------------------------------


User = get_user_model()


def home(request):
    """
    หน้า Home (Web Base)
    """
    return render(request, 'core/home.html')


def contact_submit(request):
    """รับข้อมูลฟอร์มติดต่อแล้วส่งอีเมลถึงทีมงาน"""

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        if name and email and message:
            subject = f"[Contact] Message from {name}"
            body = (
                f"ชื่อ: {name}\n"
                f"อีเมล: {email}\n\n"
                f"ข้อความ:\n{message}"
            )
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "ส่งข้อความเรียบร้อยแล้ว")
        else:
            messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")

    return redirect("core:home")




def register(request):
    """
    สมัครสมาชิก (Registration)
    - สร้าง user (is_active=False)
    - สร้าง UserProfile ว่าง ๆ
    - Add user ไปยังกลุ่ม 'mineprogress_access' (Default)
    - สร้าง EmailActivation token → ส่งอีเมลยืนยัน
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email'].lower()
            user.is_active = False
            user.save()

            # สร้าง UserProfile (ถ้ายังไม่มี)
            UserProfile.objects.create(user=user)

            # กำหนด Default Group: mineprogress_access
            try:
                default_group = Group.objects.get(name='mineprogress_access')
            except Group.DoesNotExist:
                default_group = Group.objects.create(name='mineprogress_access')
            user.groups.add(default_group)

            # สร้าง EmailActivation (expire after 24 hrs)
            token_obj = EmailActivation.objects.create(
                user=user,
                expired_at=timezone.now() + timedelta(days=1),
            )
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            activation_url = request.build_absolute_uri(
                reverse('core:activate', kwargs={'uidb64': uidb64, 'token': token_obj.token})
            )
            subject = 'ยืนยันการสมัครสมาชิก MaemohMine Project'
            message = render_to_string('core/activation_email.html', {
                'user': user,
                'activation_url': activation_url,
            })
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return render(request, 'core/registration_sent.html', {'email': user.email})
    else:
        form = RegistrationForm()
    return render(request, 'core/register.html', {'form': form})


def activate(request, uidb64, token):
    """
    ยืนยันอีเมลผ่านลิงก์ activation_url
    → user.is_active = True, token.is_used = True
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user:
        try:
            token_obj = EmailActivation.objects.get(user=user, token=token, is_used=False)
        except EmailActivation.DoesNotExist:
            token_obj = None

        if token_obj and timezone.now() <= token_obj.expired_at:
            user.is_active = True
            user.save()
            token_obj.is_used = True
            token_obj.save()
            messages.success(request, "ยืนยันอีเมลสำเร็จ! กรุณาเข้าสู่ระบบเพื่อใช้งาน")
            return redirect('core:login')
    return render(request, 'core/activation_invalid.html')


def resend_activation(request):
    """
    ส่งลิงก์ยืนยันอีเมลใหม่ กรณี token เดิมหมดอายุ
    """
    if request.method == 'POST':
        form = EmailResendForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            user = User.objects.get(email=email, is_active=False)
            # ทำให้ token เดิมหมดอายุ
            EmailActivation.objects.filter(user=user, is_used=False).update(is_used=True)
            # สร้าง token ใหม่
            new_tok = EmailActivation.objects.create(
                user=user,
                expired_at=timezone.now() + timedelta(days=1),
            )
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            activation_url = request.build_absolute_uri(
                reverse('core:activate', kwargs={'uidb64': uidb64, 'token': new_tok.token})
            )
            subject = 'ส่งลิงก์ยืนยันอีเมลใหม่ – MaemohMine Project'
            message = render_to_string('core/activation_email.html', {
                'user': user,
                'activation_url': activation_url,
            })
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, "ส่งลิงก์ยืนยันอีเมลใหม่แล้ว")
            return redirect('core:login')
    else:
        form = EmailResendForm()
    return render(request, 'core/resend_activation.html', {'form': form})


def login_view(request):
    """
    ขั้นตอนที่ 1: ล็อกอินด้วย Username/Password
    → สร้าง OTP และส่งอีเมล OTP แล้วเก็บใน session ชั่วคราว
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "บัญชียังไม่ได้ยืนยันอีเมล")
                return redirect('core:login')

            email = user.email
            code = f"{random.randint(0, 999999):06d}"
            now = timezone.now()
            otp_obj = OTP.objects.create(
                email=email,
                code=code,
                valid_until=now + timedelta(minutes=5),
            )
            # ส่งอีเมล OTP
            subject = "[MaemohMine] รหัส OTP สำหรับล็อกอิน"
            message = f"สวัสดี {user.username},\n\n" \
                      f"รหัส OTP สำหรับเข้าสู่ระบบของคุณคือ: {code}\n\n" \
                      f"รหัสนี้จะหมดอายุใน 5 นาที\n\n" \
                      f"หากคุณไม่ได้ร้องขอ OTP นี้ กรุณาละเว้นอีเมลฉบับนี้"
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            # เก็บ session ชั่วคราว
            request.session['pre_2fa_user_id'] = user.pk
            request.session['pre_2fa_email'] = email
            return redirect('core:login_verify_otp')
    else:
        form = CustomLoginForm()

    return render(request, 'core/login.html', {'form': form})


def login_verify_otp(request):
    """
    ขั้นตอนที่ 2: ยืนยัน OTP (ทางอีเมล)
    → ถ้า valid → ทำ login จริง
    """
    if 'pre_2fa_user_id' not in request.session:
        return redirect('core:login')

    email = request.session.get('pre_2fa_email', '')
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp_obj = form.cleaned_data['otp_obj']
            otp_obj.is_used = True
            otp_obj.save(update_fields=['is_used'])
            user_pk = request.session.get('pre_2fa_user_id')
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                messages.error(request, "เกิดข้อผิดพลาด ไม่พบผู้ใช้")
                return redirect('core:login')
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)
            # ล้าง session ชั่วคราว
            request.session.pop('pre_2fa_user_id', None)
            request.session.pop('pre_2fa_email', None)
            return redirect('core:home')
    else:
        form = OTPVerifyForm(initial={'email': email})
    return render(request, 'core/login_verify_otp.html', {'form': form, 'email': email})


@login_required
def logout_view(request):
    """
    ออกจากระบบ → redirect ไปหน้า Home
    """
    auth_logout(request)
    return redirect('core:home')


@login_required
def profile_view(request):
    """
    แก้ไขโปรไฟล์ (UserProfile) และเปลี่ยนรหัสผ่าน
    ถ้ายังไม่มีเบอร์โทร (หลังยืนยันอีเมล) → บังคับเปลี่ยนก่อนใช้งาน
    """
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        if 'profile_submit' in request.POST:
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            password_form = PasswordChangeForm(user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "อัปเดตข้อมูลโปรไฟล์เรียบร้อยแล้ว")
                # return redirect('core:login')
                return redirect('core:profile')
        elif 'password_submit' in request.POST:
            profile_form = ProfileUpdateForm(instance=profile)
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว")
                return redirect('core:profile')
    else:
        profile_form = ProfileUpdateForm(instance=profile)
        password_form = PasswordChangeForm(user)

    return render(request, 'core/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


# ===========================================
# Dashboard View: สรุปสถานะแต่ละ Workflow
# ===========================================
@login_required
def dashboard_view(request):
    """
    Main Dashboard: เฉพาะ CFO หรือ PD เท่านั้น
    - ถ้าไม่ใช่ CFO หรือ PD → redirect ไป home พร้อม error message
    - ดึงข้อมูลสรุปจาก cashflow, payables, revenue ไว้แสดงใน template 'dashboard.html'
    """
    user = request.user
    # ตรวจสิทธิ์: ต้องเป็น CFO หรือ PD เท่านั้น
    if not (user.groups.filter(name='cfo_access').exists() or user.groups.filter(name='pd_access').exists()):
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้า Dashboard")
        return redirect('core:home')

    # ดึงข้อมูลสรุป (ตัวอย่าง):
    from cashflow.models import (
        BankAccount, ProjectCashAccount, CashFlowForecast,
        PNLoanUsage, LCRequest, PNTicket, CashPayment, ITDLoan
    )
    from payables.models import AccountsPayable
    from revenue.models import AccountsReceivable

    # 1) BankAccount ยอดปัจจุบัน
    bank_accounts = BankAccount.objects.all().order_by('bank_name')
    # 2) ProjectCashAccount ยอดล่าสุด
    latest_cash_account = ProjectCashAccount.objects.order_by('-date').first()
    # 3) Forecast (Base Scenario) ล่าสุด
    forecast = CashFlowForecast.objects.filter(scenario='Base').order_by('-forecast_month').first()
    # 4) Outstanding AP & AR
    outstanding_aps = AccountsPayable.objects.filter(status__in=['Unpaid','Partial']).count()
    outstanding_ars = AccountsReceivable.objects.filter(status__in=['Unpaid','Partial']).count()
    # 5) PNLoanUsage (Active)
    pn_active_count = PNLoanUsage.objects.filter(status='Active').count()
    # 6) LCRequest (แต่ละสถานะ)
    lc_pending_prof = LCRequest.objects.filter(status='Pending_ProfReview').count()
    lc_prof_approved = LCRequest.objects.filter(status='Prof_Approved').count()
    lc_created = LCRequest.objects.filter(status='LC_Created').count()
    lc_swift_sent = LCRequest.objects.filter(status='Swift_Sent').count()
    # 7) PNTicket (Pending, Approved)
    pn_pending = PNTicket.objects.filter(status='Pending').count()
    pn_approved = PNTicket.objects.filter(status='Approved').count()
    # 8) CashPayment (Pending, Issued)
    cash_pending = CashPayment.objects.filter(status='Pending').count()
    cash_issued = CashPayment.objects.filter(status='Issued').count()
    # 9) ITDLoan (Pending, Active)
    itd_active = ITDLoan.objects.filter(status='Active').count()
    itd_pending = ITDLoan.objects.filter(status='Pending').count()

    context = {
        'bank_accounts'       : bank_accounts,
        'latest_cash_account' : latest_cash_account,
        'forecast'            : forecast,
        'outstanding_aps'     : outstanding_aps,
        'outstanding_ars'     : outstanding_ars,
        'pn_active_count'     : pn_active_count,
        'lc_pending_prof'     : lc_pending_prof,
        'lc_prof_approved'    : lc_prof_approved,
        'lc_created'          : lc_created,
        'lc_swift_sent'       : lc_swift_sent,
        'pn_pending'          : pn_pending,
        'pn_approved'         : pn_approved,
        'cash_pending'        : cash_pending,
        'cash_issued'         : cash_issued,
        'itd_active'          : itd_active,
        'itd_pending'         : itd_pending,
    }
    return render(request, 'core/dashboard.html', context)




