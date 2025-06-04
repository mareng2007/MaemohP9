from django.db import models
from decimal import Decimal
from django.utils import timezone

class Vendor(models.Model):
    """
    ข้อมูลซัพพลายเออร์ (Subcontractor, Fuel Supplier, Spare Parts, ฯลฯ)
    """
    CATEGORY_CHOICES = [
        ('Subcontractor', 'Subcontractor'),
        ('Fuel Supplier', 'Fuel Supplier'),
        ('Spare Parts', 'Spare Parts'),
        ('General Service', 'General Service'),
        ('Insurance', 'Insurance'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    payment_terms = models.CharField(max_length=20, blank=True)  # เช่น "30D", "60D"
    tax_withholding_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return self.name


class AccountsPayable(models.Model):
    """
    เก็บหนี้ค้างชำระ (AP) จาก ERP แบ่งเป็นปี 2566, 2567
    """
    VENDOR_YEAR_CHOICES = [
        (2566, 'ปี 2566'),
        (2567, 'ปี 2567'),
    ]
    STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Partial', 'Partially Paid'),
        ('Paid', 'Paid'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)  # ยอดก่อนหักภาษี
    year = models.PositiveSmallIntegerField(choices=VENDOR_YEAR_CHOICES)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')

    def __str__(self):
        return f"AP {self.invoice_number} ({self.year})"

    @property
    def outstanding_amount(self):
        return self.amount - self.paid_amount


class SiteOperationExpense(models.Model):
    """
    เก็บ “หมวดหมู่ค่าใช้จ่าย” (Expense Categories) 
    ที่จะถูกนำมารวม Batch ใน PaymentRequest
    ไม่ได้หมายถึงเฉพาะ “ภาคสนาม” เสมอไป
    """
    CATEGORY_CHOICES = [
        ('Salary & Wage', 'Salary & Wage'),
        ('Fuel', 'Fuel'),
        ('Subcontractor', 'Subcontractor'),
        ('Blasting Mat.', 'Blasting Material'),
        ('Lubricant', 'Lubricant'),
        ('Spare part', 'Spare part'),
        ('Main Equipment Overhaul', 'Main Equipment Overhaul'),
        ('Service & General', 'Service & General'),
        ('Insurance', 'Insurance'),
        ('Excess Electricity', 'Excess Electricity'),
        ('Withholding Tax', 'Withholding Tax'),
        ('Breakdown Repair', 'Breakdown Repair'),
        ('Conveyor Belt Extend', 'Conveyor Belt Extend'),
    ]
    STATUS_CHOICES = [
        ('Pending_AP', 'Pending AP'),       # ยังไม่ออกบิล
        ('AP_Invoiced', 'AP Invoiced'),     # มีบิลแล้ว
        ('Paid', 'Paid'),                   # จ่ายแล้ว
    ]

    date = models.DateField(default=timezone.now)
    expense_category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_expenses'
    )
    pr_po_reference = models.CharField(max_length=50, blank=True)  # ถ้ายังเป็น PR/PO
    ap_reference = models.ForeignKey(
        AccountsPayable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_expenses'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))        
    tax_withheld = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending_AP')

    def __str__(self):
        return f"{self.expense_category} ({self.date}): {self.amount}"


class SupplierCredit(models.Model):
    """
    ใหม่: เก็บวงเงินเครดิตจาก Suppliers
    ตัวอย่าง: Supplier A ให้วงเงินเครดิต 50 ล้านบาท
    """
    supplier_name = models.CharField(max_length=100, unique=True)
    credit_limit = models.DecimalField(max_digits=16, decimal_places=2)
    used_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    created_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    def remaining_credit(self):
        return self.credit_limit - self.used_amount

    def __str__(self):
        return f"{self.supplier_name} (Limit {self.credit_limit} / Used {self.used_amount})"

