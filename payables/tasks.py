from celery import shared_task
from .models import SiteOperationExpense, AccountsPayable
from .models import Vendor

@shared_task
def fetch_erp_expenses():
    """
    ตัวอย่าง Task สำหรับดึงข้อมูลค่าใช้จ่ายจาก ERP
    Pseudocode: สมมติว่า ERP มี API คืนค่า JSON
    """
    # ตัวอย่าง data จำลอง
    erp_data = [
        {
            "vendor_name": "Fuel Supplier A",
            "expense_category": "Fuel",
            "date": "2025-05-31",
            "amount": 50000.00,
            "tax_withheld": 500.00,
            "net_amount": 49500.00,
            "pr_po_reference": "PO1234",
            "invoice_number": None
        },
        # … เพิ่มรายการตามต้องการ
    ]

    for item in erp_data:
        # ดึงหรือสร้าง Vendor
        vendor, created = Vendor.objects.get_or_create(
            name=item['vendor_name'],
            defaults={'category': 'Fuel Supplier', 'payment_terms': '30D'}
        )
        # สร้าง SiteOperationExpense
        SiteOperationExpense.objects.create(
            date=item['date'],
            expense_category=item['expense_category'],
            vendor=vendor,
            pr_po_reference=item['pr_po_reference'],
            amount=item['amount'],
            tax_withheld=item['tax_withheld'],
            net_amount=item['net_amount'],
            status='Pending_AP'
        )

    # กรณีมี Invoice ใน ERP สามารถสร้าง AccountsPayable แล้วผูกกับ SiteOperationExpense ได้
    # for item in erp_data_with_invoice:
    #     ap = AccountsPayable.objects.create(
    #         vendor=Vendor.objects.get(name=item['vendor_name']),
    #         invoice_number=item['invoice_number'],
    #         invoice_date=item['date'],
    #         due_date=compute_due_date(item['date'], vendor.payment_terms),
    #         amount=item['amount'],
    #         year=item['year']
    #     )
    #     expense = SiteOperationExpense.objects.get(pr_po_reference=item['pr_po_reference'])
    #     expense.ap_reference = ap
    #     expense.status = 'AP_Invoiced'
    #     expense.save()
