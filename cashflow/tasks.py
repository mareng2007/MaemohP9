from celery import shared_task
from decimal import Decimal
from datetime import date
from .models import CashFlowForecast, CashTransaction, ProjectCashAccount, LCRequest

@shared_task
def run_cashflow_projection_task(start_month: str, num_months: int, assumptions: dict, scenario: str):
    """
    ฟังก์ชันหลักในการคำนวณ Cash Flow Projection (Base/Worst/Best)
    จะถูกเรียกจาก views.py ผ่าน Celery worker
    พารามิเตอร์:
      - start_month (str): วันที่รูปแบบ 'YYYY-MM-DD' ซึ่งจะถือเป็นวันที่ 1 ของเดือนเริ่มต้น
      - num_months (int): จำนวนเดือนที่จะคำนวณล่วงหน้า (เช่น 12 เดือน)
      - assumptions (dict): ข้อมูลตั้งต้น เช่น DSO, DPO, อัตราสินเชื่อต่าง ๆ
      - scenario (str): ชื่อสถานการณ์ ('Base', 'Worst', 'Best')
    """
    from dateutil.relativedelta import relativedelta

    # แปลง start_month ให้เป็น date object (วันที่ 1 ของเดือน)
    try:
        start_date = date.fromisoformat(start_month)
    except ValueError:
        # ถ้าแปลงไม่สำเร็จ จะใช้วันที่ปัจจุบันเป็น fallback
        start_date = date.today().replace(day=1)

    # ลูปคำนวณทีละเดือน
    for i in range(num_months):
        # คำนวณเดือนปัจจุบันจาก start_date บวก i เดือน
        current_month = start_date + relativedelta(months=i)
        # วันที่เก็บใน database เราจะเก็บเป็นวันที่ 1 ของ current_month เสมอ
        forecast_month = current_month.replace(day=1)

        # เริ่มต้นยอด inflow/outflow เป็น 0.00
        projected_inflow = Decimal('0.00')
        projected_outflow = Decimal('0.00')

        # -----------------------------------------
        # STEP 1: หายอดเงินเข้า (Cash Inflow) ซึ่งอาจประกอบด้วย:
        #  1. รายได้จากเจ้าของงาน (Revenue Paid)
        #  2. เงินกู้ PN ที่ออก (Receive_PNLoan)
        #  3. เงินกู้จาก Trade Finance (Receive_TradeFinance)
        #  4. เงินกู้จากสินเชื่อธนาคารอื่น ๆ (Receive_BankLoan)
        #  5. เงินกู้ ITD CEM (Receive_ITDLoan)
        # -----------------------------------------
        inflow_qs = CashTransaction.objects.filter(
            transaction_type__in=[
                'Revenue_Paid',
                'PNTicket_Issue',        # เมื่อ Issue PN แล้ว ก็ถือเป็น Inflow
                'Receive_TradeFinance',
                'Receive_BankLoan',
                'Receive_ITDLoan'
            ],
            transaction_date__year=forecast_month.year,
            transaction_date__month=forecast_month.month,
            is_inflow=True
        )
        # รวมยอดเงินเข้าในเดือนนั้น ๆ
        for tx in inflow_qs:
            projected_inflow += tx.amount

        # -----------------------------------------
        # STEP 2: หายอดเงินออก (Cash Outflow) ซึ่งอาจประกอบด้วย:
        #  1. จ่ายคืน PN (PNLoan_Repayment)
        #  2. จ่ายคืน Trade Finance (TradeFinance_Repayment)
        #  3. จ่ายคืน BankLoan (BankLoan_Repayment)
        #  4. จ่าย LC (LC_Payment)
        #  5. จ่าย TR (TR_Payment)
        #  6. จ่ายเช็ค CashPayment (Cash_Payment)
        #  7. ดอกเบี้ยธนาคาร (Interest_Fee)
        #  8. ค่าใช้เงิน ITD (ถ้ามีออกเป็น Outflow)
        # -----------------------------------------
        outflow_qs = CashTransaction.objects.filter(
            transaction_type__in=[
                'PNLoan_Repayment',
                'TradeFinance_Repayment',
                'BankLoan_Repayment',
                'LC_Payment',
                'TR_Payment',
                'Cash_Payment',
                'Interest_Fee',
                'ITDLoan_Usage'
            ],
            transaction_date__year=forecast_month.year,
            transaction_date__month=forecast_month.month,
            is_inflow=False
        )
        # รวมยอดเงินออกในเดือนนั้น ๆ
        for tx in outflow_qs:
            projected_outflow += tx.amount

        # -----------------------------------------
        # STEP 3: คำนวณ Net Cash Flow = Inflow - Outflow
        # -----------------------------------------
        net_cash_flow = projected_inflow - projected_outflow

        # -----------------------------------------
        # STEP 4: จัดเก็บผลลัพธ์ลงในตาราง CashFlowForecast
        # -----------------------------------------
        # ถ้ามีเรคอร์ดที่ตรงกับ forecast_month และ scenario อยู่แล้ว
        # ให้อัปเดตค่านั้นแทน (upsert logic)
        obj, created = CashFlowForecast.objects.update_or_create(
            forecast_month=forecast_month,
            scenario=scenario,
            defaults={
                'projected_cash_inflow': projected_inflow,
                'projected_cash_outflow': projected_outflow,
                'net_cash_flow': net_cash_flow,
                'assumptions': assumptions
            }
        )

    # -----------------------------------------
    # สิ้นสุดการคำนวณ Projection
    # -----------------------------------------
    return f"Projection for {scenario} starting {start_month} completed."

@shared_task
def daily_cashflow_projection():
    """
    งานที่รันทุกต้นเดือนเพื่อคำนวณ Cash Flow Projection เบื้องต้น (Default เป็น Base Scenario)
    """
    from dateutil.relativedelta import relativedelta

    # กำหนดค่าตั้งต้น (Assumptions) สำหรับ Forecast
    assumptions = {
        "DSO": 60,
        "DPO": 30,
        "PN_Rate": 0.8,
        "TF_Rate": 1.0,
        "InterestRates": {
            "Pre-Finance": 6.50,
            "Working Capital": 7.00,
            "Hire Purchase": 5.00
        }
    }
    today = date.today()
    first_of_month = today.replace(day=1)
    # เรียกใช้ฟังก์ชัน run_cashflow_projection_task เพื่อคำนวณ 12 เดือนล่วงหน้า
    run_cashflow_projection_task.delay(first_of_month.strftime('%Y-%m-%d'), 12, assumptions, 'Base')

@shared_task
def calculate_bankloan_interest():
    """
    งานที่รันทุกต้นเดือน: คำนวณดอกเบี้ยสินเชื่อธนาคาร
    จะสร้าง CashTransaction ประเภท 'Interest_Fee' แล้วบันทึก
    """
    from loans.models import BankLoan
    loans = BankLoan.objects.filter(status='Active')
    today = date.today()
    for loan in loans:
        # ดอกเบี้ยรายเดือน = (Outstanding Balance * อัตราดอกเบี้ยต่อปี) / 12 / 100
        interest = (loan.outstanding_balance * loan.interest_rate) / Decimal('1200')
        interest = interest.quantize(Decimal('0.01'))
        # สร้าง CashTransaction สำหรับบันทึกดอกเบี้ย
        CashTransaction.objects.create(
            transaction_date=today,
            transaction_type='Interest_Fee',
            related_id=loan.id,
            amount=interest,
            is_inflow=False,
            description=f"Monthly interest for {loan.loan_type}"
        )
        # บวกดอกเบี้ยเข้า outstanding_balance
        loan.outstanding_balance += interest
        loan.save(update_fields=['outstanding_balance'])

@shared_task
def check_lcrequests_expiry():
    """
    งานวันละครั้ง: ตรวจสอบ LCRequest ที่ครบ 180 วัน → แปลงเป็น TR
    """
    # ดึง LCRequest ที่สถานะ 'Swift_Sent' และ expiry_date <= วันนี้
    lcs = LCRequest.objects.filter(status='Swift_Sent', expiry_date__lte=date.today())
    for lc in lcs:
        # ถ้ายังไม่เคยแปลงเป็น TR (ไม่มี tr_request)
        if not hasattr(lc, 'tr_request'):
            from .models import TRRequest
            TRRequest.objects.create(
                lc_request=lc,
                tr_number=f"TR{lc.id}{date.today().strftime('%Y%m%d')}",
                tr_amount=lc.lc_amount,
                interest_rate=Decimal('5.00'),
                status='Active'
            )
            lc.status = 'TR_Converted'
            lc.save(update_fields=['status'])

