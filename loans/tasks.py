from celery import shared_task
from decimal import Decimal
from datetime import date
from .models import BankLoan
from cashflow.models import CashTransaction

@shared_task
def calculate_bankloan_interest():
    """
    คำนวณดอกเบี้ยสินเชื่อธนาคารทุกต้นเดือน
    ดอกเบี้ยรายเดือน = (outstanding_balance * interest_rate/100) / 12
    แล้วสร้าง CashTransaction ประเภท 'Interest_Fee'
    """
    loans = BankLoan.objects.filter(status='Active')
    today = date.today()
    for loan in loans:
        # คำนวณดอกเบี้ยรายเดือน
        interest = (loan.outstanding_balance * loan.interest_rate) / Decimal('1200')
        interest = interest.quantize(Decimal('0.01'))

        # สร้าง CashTransaction สำหรับดอกเบี้ย
        CashTransaction.objects.create(
            transaction_date = today,
            transaction_type = 'Interest_Fee',
            related_id       = loan.id,
            amount           = interest,
            is_inflow        = False,
            description      = f"Monthly interest for {loan.loan_type}"
        )

        # เพิ่มดอกเบี้ยเข้า outstanding_balance
        loan.outstanding_balance += interest
        loan.save(update_fields=['outstanding_balance'])

