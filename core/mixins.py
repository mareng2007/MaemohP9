# core/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class RevenueAccessRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin สำหรับให้ตรวจสอบว่า user ต้องล็อกอิน และต้องอยู่ในกลุ่ม "revenue_access"
    ถ้าไม่ใช่ จะถูก redirect ไปหน้า login (LoginRequiredMixin) 
    หรือแสดง Forbidden (403) (UserPassesTestMixin) ตามลำดับ
    """
    # ถ้าต้องการเปลี่ยน default login URL: 
    # login_url = '/accounts/login/'  # หรือ url name เช่น reverse_lazy('core:login')
    # redirect_field_name = 'next'     # ค่า default คือ 'next'

    def test_func(self):
        user = self.request.user
        return user.groups.filter(name="revenue_access").exists()

    # UserPassesTestMixin โดย default ถ้า test_func() คืน False 
    # จะ raise PermissionDenied (403 Forbidden) ถ้าต้องการ redirect ไปหน้าอื่น ให้ override handle_no_permission()
    # def handle_no_permission(self):
    #     return super().handle_no_permission()
