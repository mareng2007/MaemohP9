from decimal import Decimal
from datetime import date
from django.test import TestCase
from .models import Vendor, AccountsPayable


class AccountsPayableModelTest(TestCase):
    def test_outstanding_amount_computed_correctly(self):
        vendor = Vendor.objects.create(name="Test Vendor")
        ap = AccountsPayable.objects.create(
            vendor=vendor,
            invoice_number="INV-1",
            invoice_date=date.today(),
            due_date=date.today(),
            amount=Decimal("100.00"),
            year=2566,
            paid_amount=Decimal("40.00"),
        )
        self.assertEqual(ap.outstanding_amount, Decimal("60.00"))

