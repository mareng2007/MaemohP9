from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class BankAccount(models.Model):
    """
    เก็บข้อมูลบัญชีธนาคารจริงที่ integrate เข้ามาในระบบ
    """
    name = models.CharField(max_length=100, unique=True)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50, unique=True)
    balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.bank_name} – {self.account_number} (Balance {self.balance})"


class PostFinanceFacility(models.Model):
    """
    สินเชื่อ Post Finance (วงเงินตามสัญญา) ที่ต้องขออนุมัติก่อนกู้ PN
    """
    facility_name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    credit_limit = models.DecimalField(max_digits=16, decimal_places=2)   # วงเงินสูงสุด
    used_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='postfinance_created')
    approved_on = models.DateField(null=True, blank=True)  # วันอนุมัติจากธนาคาร

    def __str__(self):
        return f"{self.facility_name} ({self.credit_limit} / Used {self.used_amount})"


class PNLoanUsage(models.Model):
    """
    สินเชื่อ PN Against Payment (อ้างอิงภายใต้ PostFinanceFacility ที่อนุมัติแล้ว)
    approved_amount = 80% ของ income_amount (ใน RevenueJob)
    """
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Partial_Repaid', 'Partial Repaid'),
        ('Repaid', 'Repaid'),
    ]

    facility = models.ForeignKey(
        PostFinanceFacility,
        on_delete=models.CASCADE,
        related_name='pn_loans'
    )
    revenue_job = models.ForeignKey(
        'revenue.RevenueJob',
        on_delete=models.CASCADE,
        related_name='pn_loans'
    )
    date = models.DateField(default=timezone.now)
    approved_amount = models.DecimalField(max_digits=16, decimal_places=2)
    received_amount = models.DecimalField(max_digits=16, decimal_places=2)
    bank_interest_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    repayment_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    repayment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"PNLoan ({self.revenue_job.job_code} on {self.date}) → {self.status}"


class ITDLoan(models.Model):
    """
    สินเชื่อ ITD CEM จำนวน 300 ล้านบาทที่สำนักงานใหญ่สนับสนุน
    """
    loan_name = models.CharField(max_length=100, unique=True, default='ITD CEM Loan')
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('300000000.00'))
    received_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    used_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='itdloan_created')
    created_on = models.DateField(default=timezone.now)

    def remaining_balance(self):
        """Return remaining credit available on this ITDLoan."""
        return self.total_amount - self.used_amount

    def __str__(self):
        return f"{self.loan_name} (Total {self.total_amount} / Used {self.used_amount})"


class CashTransaction(models.Model):
    """
    ทุกรายการเคลื่อนไหวทางการเงิน (ทั้ง Inflow/Outflow)
    รวมทั้งการรับ/จ่าย ITDLoan, PN, LC, TR, Cash, SupplierCredit ฯลฯ
    """
    TRANSACTION_CHOICES = [
        ('Revenue_Paid', 'Revenue Paid'),
        ('Receive_PNLoan', 'Receive PNLoan'),
        ('Receive_TradeFinance', 'Receive TradeFinance'),
        ('Receive_BankLoan', 'Receive BankLoan'),
        ('Receive_ITDLoan', 'Receive ITDLoan'),
        ('PNLoan_Repayment', 'PNLoan Repayment'),
        ('TradeFinance_Repayment', 'TradeFinance Repayment'),
        ('BankLoan_Repayment', 'BankLoan Repayment'),
        ('LC_Payment', 'LC Payment'),
        ('TR_Payment', 'TR Payment'),
        ('PNTicket_Issue', 'PNTicket Issue'),
        ('Cash_Payment', 'Cash Payment'),
        ('LC_Fee', 'LC Fee'),
        ('ITDLoan_Usage', 'ITDLoan Usage'),
        ('Interest_Fee', 'Interest Fee'),
        ('Supplier_Credit_Usage', 'Supplier Credit Usage'),  # ใหม่: ใช้เครดิต Suppliers
    ]

    transaction_date = models.DateField(default=timezone.now)
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_CHOICES)
    related_id = models.PositiveIntegerField(null=True, blank=True)  # เก็บ FK แบบ Generic (เช่น PNLoanUsage.id, TRRequest.id, PNTicket.id, ฯลฯ)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    is_inflow = models.BooleanField()
    description = models.TextField(blank=True)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_transactions'
    )

    def __str__(self):
        direction = 'Inflow' if self.is_inflow else 'Outflow'
        return f"{self.transaction_date} | {self.transaction_type} | {direction} {self.amount}"


class ProjectCashAccount(models.Model):
    """
    เก็บยอด Cash Balance ประจำวัน/เดือน
    จะอัปเดตอัตโนมัติเมื่อมี CashTransaction เกิดขึ้น
    """
    date = models.DateField(default=timezone.now, unique=True)
    opening_balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    closing_balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.date} → เปิด {self.opening_balance}, ปิด {self.closing_balance}"


class CashFlowForecast(models.Model):
    """
    เก็บผลลัพธ์การคาดการณ์กระแสเงินสด (Forecast) แยกตาม Scenario
    """
    SCENARIO_CHOICES = [
        ('Base', 'Base Case'),
        ('Worst', 'Worst Case'),
        ('Best', 'Best Case'),
    ]

    forecast_month = models.DateField()  # เก็บเป็นวันที่ 1 ของเดือน
    projected_cash_inflow = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    projected_cash_outflow = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    net_cash_flow = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    scenario = models.CharField(max_length=10, choices=SCENARIO_CHOICES, default='Base')
    assumptions = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('forecast_month', 'scenario')

    def __str__(self):
        return f"Forecast {self.forecast_month} [{self.scenario}]"


# --------------------------
# Workflow: ขอจ่ายเงิน (PaymentRequest)
# --------------------------

class CommitteeMember(models.Model):
    """
    ข้อมูลสมาชิกคณะกรรมการที่โหวต PaymentRequest
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='committee_member')
    department = models.CharField(max_length=50)  # เช่น 'Accounting', 'Finance', 'LC'

    def __str__(self):
        return f"{self.user.username} ({self.department})"


class PaymentRequest(models.Model):
    """
    สร้างคำขอจ่ายเงิน (PaymentRequest) เพื่อรวมรายการจากหลายแหล่ง:
    - AP (ปี 2566/2567)
    - SiteOperationExpense (หมวดหมู่ค่าใช้จ่าย)
    - LCRequest (จาก Execute)
    - ITDLoan Usage
    - SupplierCredit Usage
    และอนุญาตให้ CommitteeMember โหวต, CFO, PD อนุมัติ, แล้วจึง Execute จ่ายเงินย่อย
    """
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Committee_Review', 'Committee Review'),
        ('CFO_Review', 'CFO Review'),
        ('PD_Approval', 'PD Approval'),
        ('Executed', 'Executed'),
        ('Rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="อธิบายเหตุผลโดยสังเขปของการขอจ่ายเงิน"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='paymentrequests_created')
    created_on = models.DateField(auto_now_add=True)
    scheduled_date = models.CharField(
        max_length=2,
        blank=True,
        help_text="รอบการรวม เช่น '5','15','25' หรือเว้นว่างให้กำหนดเอง"
    )
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')

    def __str__(self):
        return f"PaymentRequest {self.id} – {self.title} [{self.get_status_display()}]"


class PaymentRequestItem(models.Model):
    """
    รายการย่อยใน PaymentRequest
    สามารถเชื่อมกับ:
    - AccountsPayable (if paying AP)
    - SiteOperationExpense (if paying ExpenseCategory)
    - LCRequest (if payment_type='LC')
    - SupplierCredit (if payment_type='SupplierCredit')
    - PN/PNTicket/ITDLoan (handled in Execute step)
    """
    PAYMENT_TYPE_CHOICES = [
        ('LC', 'LC'),
        ('PN', 'PN'),
        ('Cash', 'Cash'),
        ('ITDLoan', 'ITDLoan'),
        ('SupplierCredit', 'SupplierCredit'),
    ]

    payment_request = models.ForeignKey(
        PaymentRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    description = models.TextField()
    related_ap = models.ForeignKey(
        'payables.AccountsPayable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    related_expense_category = models.ForeignKey(
        'payables.SiteOperationExpense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    related_lcrequest = models.ForeignKey(
        'LCRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    related_suppliercredit = models.ForeignKey(
        'payables.SupplierCredit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    vote_count = models.PositiveIntegerField(default=0)
    chosen = models.BooleanField(default=False)

    def __str__(self):
        return f"Item {self.id} – {self.amount} [{self.payment_type}]"


class Vote(models.Model):
    """
    เก็บโหวตของแต่ละ CommitteeMember ต่อแต่ละ PaymentRequestItem
    """
    member = models.ForeignKey(CommitteeMember, on_delete=models.CASCADE, related_name='votes')
    item = models.ForeignKey(PaymentRequestItem, on_delete=models.CASCADE, related_name='votes')
    voted_on = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('member', 'item')

    def __str__(self):
        return f"{self.member.user.username} โหวต Item {self.item.id}"


# --------------------------
# Workflow: LC & TR
# --------------------------

class LCRequest(models.Model):
    """
    เก็บการขอเปิด LC (เมื่อ Execute PaymentRequestItem เป็น LC)
    """
    STATUS_CHOICES = [
        ('Pending_ProfReview', 'Pending Professor Review'),
        ('Prof_Approved', 'Professor Approved'),
        ('LC_Created', 'LC Created'),
        ('Swift_Sent', 'Swift Sent'),
        ('TR_Converted', 'TR Converted'),
        ('Closed', 'Closed'),
        ('Rejected', 'Rejected'),
    ]

    payment_item = models.OneToOneField(
        PaymentRequestItem,
        on_delete=models.CASCADE,
        related_name='lc_request'
    )
    request_date = models.DateField(auto_now_add=True)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    lc_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    lc_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)  # วันครบ 180 วัน
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending_ProfReview')

    def __str__(self):
        return f"LCRequest {self.id} for Item {self.payment_item.id} [{self.get_status_display()}]"


class SwiftMessage(models.Model):
    """
    เก็บ Swift Message ที่ธนาคารส่งกลับหลังเปิด LC
    """
    lc_request = models.ForeignKey(LCRequest, on_delete=models.CASCADE, related_name='swift_messages')
    sent_date = models.DateField(auto_now_add=True)
    content = models.TextField()

    def __str__(self):
        return f"SwiftMessage for LCRequest {self.lc_request.id} on {self.sent_date}"


class TRRequest(models.Model):
    """
    เมื่อ LC ครบ 180 วัน → แปลงเป็น Trust Receipt (TR)
    """
    lc_request = models.OneToOneField(LCRequest, on_delete=models.CASCADE, related_name='tr_request')
    tr_number = models.CharField(max_length=100, blank=True)
    tr_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    created_on = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('Active', 'Active'),
            ('Repaid', 'Repaid'),
            ('Closed', 'Closed'),
        ],
        default='Active'
    )

    def __str__(self):
        return f"TRRequest {self.id} for LCRequest {self.lc_request.id} [{self.status}]"


# --------------------------
# Workflow: PNTicket & CashPayment
# --------------------------

class PNTicket(models.Model):
    """
    เมื่อ Execute PaymentRequestItem เป็น PN → สร้าง PNTicket เพื่อขอออกตั๋ว PN
    """
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Executed', 'Executed'),
    ]

    payment_item = models.OneToOneField(PaymentRequestItem, on_delete=models.CASCADE, related_name='pn_ticket')
    request_date = models.DateField(auto_now_add=True)
    ticket_number = models.CharField(max_length=100, blank=True)
    approved_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"PNTicket {self.id} for Item {self.payment_item.id} [{self.status}]"


class CashPayment(models.Model):
    """
    เมื่อ Execute PaymentRequestItem เป็น Cash → สร้าง CashPayment เพื่อออกเช็คจ่าย
    """
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Issued', 'Issued'),
        ('Rejected', 'Rejected'),
        ('Cleared', 'Cleared'),
    ]

    payment_item = models.OneToOneField(PaymentRequestItem, on_delete=models.CASCADE, related_name='cash_payment')
    request_date = models.DateField(auto_now_add=True)
    check_number = models.CharField(max_length=100, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"CashPayment {self.id} for Item {self.payment_item.id} [{self.status}]"


