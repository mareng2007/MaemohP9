# revenue/models.py

from django.db import models
from decimal import Decimal
from django.utils import timezone

class RevenueJob(models.Model):
    """
    เก็บข้อมูลรายได้จากแต่ละ Job (Job1–Job4, ขายดีเซล, รายได้อื่นๆ)
    """
    JOB_CHOICES = [
        ('Job1', 'Excavation and Removal of Overburden'),
        ('Job2', 'Extraction of Lignite'),
        ('Job3', 'Conveying of Overburden'),
        ('Job4', 'ค่า k'),
        ('DieselSale', 'รายได้จากการขายน้ำมันดีเซล'),
        ('Other', 'รายได้อื่นๆ'),
    ]

    date = models.DateField(default=timezone.now)  
    job_code = models.CharField(
        max_length=20,
        choices=JOB_CHOICES,
    )
    # เพิ่มฟิลด์ "รายการ" เพื่อใส่คำอธิบายงาน/ผลงาน
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="อธิบายงานหรือผลงาน (เช่น 'งานเดือน ม.ค. 2568')"
    )
    volume = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    income_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Requested_PN', 'Requested PN'),
            ('Invoiced', 'Invoiced'),
            ('Paid', 'Paid'),
        ],
        default='Pending'
    )

    def __str__(self):
        return f"{self.job_code} ({self.date}): {self.income_amount}"


class AccountsReceivable(models.Model):
    """
    เก็บข้อมูล invoice ที่ออกให้เจ้าของงาน (EGAT)
    """
    revenue_job = models.ForeignKey(
        RevenueJob,
        on_delete=models.CASCADE,
        related_name='ar_records'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    bank_account = models.ForeignKey(
        'cashflow.BankAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('Unpaid', 'Unpaid'),
            ('Partial', 'Partially Paid'),
            ('Paid', 'Paid'),
        ],
        default='Unpaid'
    )

    def __str__(self):
        return f"AR {self.invoice_number} for {self.revenue_job.job_code}"

    @property
    def outstanding_amount(self):
        return self.total_amount - self.paid_amount



