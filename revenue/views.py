# revenue/views.py

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# นำ IsRevenueUser มาใช้กับ API (DRF)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsRevenueUser

# นำ RevenueAccessRequiredMixin มาใช้กับ Web Views
from core.mixins import RevenueAccessRequiredMixin

from .models import RevenueJob, AccountsReceivable
from .forms import RevenueJobForm, AccountsReceivableForm
from .filters import RevenueJobFilter, AccountsReceivableFilter
from .serializers import RevenueJobSerializer, AccountsReceivableSerializer


# ----------------------------
# 1) API: DRF ViewSets
# ----------------------------
class RevenueJobViewSet(viewsets.ModelViewSet):
    """
    API endpoint: /api/revenue/jobs/
    - CRUD RevenueJob ทั้งหมด
    - จำกัดสิทธิ์เฉพาะผู้ใช้ที่ล็อกอินและอยู่ในกลุ่ม "revenue_access"
    """
    queryset = RevenueJob.objects.all().order_by('-date')
    serializer_class = RevenueJobSerializer
    # ตรวจสอบว่า user ได้ล็อกอินแล้ว และอยู่ในกลุ่ม revenue_access
    permission_classes = [IsAuthenticated, IsRevenueUser]


class AccountsReceivableViewSet(viewsets.ModelViewSet):
    """
    API endpoint: /api/revenue/ar/
    - CRUD AccountsReceivable ทั้งหมด
    - จำกัดสิทธิ์เฉพาะผู้ใช้ที่ล็อกอินและอยู่ในกลุ่ม "revenue_access"
    """
    queryset = AccountsReceivable.objects.all().order_by('-invoice_date')
    serializer_class = AccountsReceivableSerializer
    # ตรวจสอบว่า user ได้ล็อกอินแล้ว และอยู่ในกลุ่ม revenue_access
    permission_classes = [IsAuthenticated, IsRevenueUser]


# ----------------------------
# 2) WEB: Class-Based Views
# ----------------------------
# ทั้งหมดสืบทอดจาก RevenueAccessRequiredMixin ซึ่งตรวจสอบ:
#   1) LoginRequiredMixin → ต้องล็อกอิน
#   2) UserPassesTestMixin.test_func() → ต้องอยู่ในกลุ่ม "revenue_access"

class RevenueJobListView(RevenueAccessRequiredMixin, ListView):
    """
    แสดงรายการ RevenueJob ทั้งหมด
    """
    model = RevenueJob
    template_name = 'revenue/revenuejob_list.html'
    context_object_name = 'jobs'
    paginate_by = 10

    def get_queryset(self):
        qs = RevenueJob.objects.all().order_by('-date')
        self.filterset = RevenueJobFilter(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        return context


class RevenueJobCreateView(RevenueAccessRequiredMixin, CreateView):
    """
    ฟอร์มสร้าง RevenueJob ใหม่
    """
    model = RevenueJob
    form_class = RevenueJobForm
    template_name = 'revenue/revenuejob_form.html'
    success_url = reverse_lazy('revenue:revenuejob-list')

    def form_valid(self, form):
        # ถ้าต้องการผูก user ปัจจุบันเข้ากับ model ก็ทำตรงนี้ก่อนบันทึก
        # e.g. form.instance.created_by = self.request.user
        return super().form_valid(form)


class RevenueJobDetailView(RevenueAccessRequiredMixin, DetailView):
    """
    แสดงรายละเอียดของ RevenueJob ทีละรายการ
    """
    model = RevenueJob
    template_name = 'revenue/revenuejob_detail.html'
    context_object_name = 'job'


class RevenueJobUpdateView(RevenueAccessRequiredMixin, UpdateView):
    """
    ฟอร์มแก้ไข RevenueJob
    """
    model = RevenueJob
    form_class = RevenueJobForm
    template_name = 'revenue/revenuejob_form.html'
    success_url = reverse_lazy('revenue:revenuejob-list')


class AccountsReceivableListView(RevenueAccessRequiredMixin, ListView):
    """
    แสดงรายการ AccountsReceivable ทั้งหมด
    """
    model = AccountsReceivable
    template_name = 'revenue/accountsreceivable_list.html'
    context_object_name = 'ars'
    paginate_by = 10

    def get_queryset(self):
        qs = AccountsReceivable.objects.select_related('revenue_job').all().order_by('-invoice_date')
        self.filterset = AccountsReceivableFilter(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        return context


class AccountsReceivableCreateView(RevenueAccessRequiredMixin, CreateView):
    """
    ฟอร์มสร้าง AccountsReceivable ใหม่
    """
    model = AccountsReceivable
    form_class = AccountsReceivableForm
    template_name = 'revenue/accountsreceivable_form.html'
    success_url = reverse_lazy('revenue:ar-list')

    def form_valid(self, form):
        # เมื่อสร้าง AR ใหม่ ให้เปลี่ยนสถานะ RevenueJob ที่เกี่ยวข้องเป็น 'Invoiced'
        rv_job = form.cleaned_data.get('revenue_job')
        if rv_job:
            rv_job.status = 'Invoiced'
            rv_job.save(update_fields=['status'])
        return super().form_valid(form)


class AccountsReceivableDetailView(RevenueAccessRequiredMixin, DetailView):
    """
    แสดงรายละเอียด AccountsReceivable ทีละรายการ
    """
    model = AccountsReceivable
    template_name = 'revenue/accountsreceivable_detail.html'
    context_object_name = 'ar'


class AccountsReceivableUpdateView(RevenueAccessRequiredMixin, UpdateView):
    """
    ฟอร์มแก้ไข AccountsReceivable
    - เมื่อแก้ไข paid_amount ให้สั่งบันทึกและสร้าง CashTransaction (inflow) ในแอป cashflow
    """
    model = AccountsReceivable
    form_class = AccountsReceivableForm
    template_name = 'revenue/accountsreceivable_form.html'
    success_url = reverse_lazy('revenue:ar-list')

    def form_valid(self, form):
        # เช็คดูว่า paid_amount ถูกเปลี่ยนแปลงหรือไม่
        ar_obj = form.save(commit=False)
        old_ar = AccountsReceivable.objects.get(pk=ar_obj.pk)
        old_paid = old_ar.paid_amount
        new_paid = form.cleaned_data.get('paid_amount')
        ar_obj.bank_account = form.cleaned_data.get('bank_account')

        # ถ้า paid_amount มีการปรับขึ้นจนถึงยอดครบ (หรือบางส่วน) → อัปเดตสถานะของ AR
        if new_paid >= ar_obj.total_amount:
            ar_obj.status = 'Paid'
        elif new_paid > 0:
            ar_obj.status = 'Partial'
        else:
            ar_obj.status = 'Unpaid'

        ar_obj.save()

        # ถ้ามีการเพิ่ม paid_amount (เงินเข้าจริง) ให้สร้าง CashTransaction (inflow) ใน cashflow
        if new_paid > old_paid:
            from cashflow.models import CashTransaction
            from datetime import date

            CashTransaction.objects.create(
                transaction_date = date.today(),
                transaction_type = 'Revenue_Paid',  # ประเภท transaction
                related_id = ar_obj.id,             # เก็บ id ของ AR เพื่ออ้างอิง
                amount = new_paid - old_paid,       # จำนวนเงินที่รับเข้ามาในรอบนี้
                is_inflow = True,
                description = f"Income received for AR {ar_obj.invoice_number}",
                bank_account = ar_obj.bank_account
            )
        return redirect(self.success_url)


