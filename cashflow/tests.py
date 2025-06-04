from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group
from decimal import Decimal

from cashflow.models import BankAccount, ITDLoan, CashTransaction


@override_settings(
    SECRET_KEY="testsecret",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
)
class ITDLoanWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        group = Group.objects.create(name="cashflow_access")
        self.user = User.objects.create_user("cashuser", password="pass123", is_active=True)
        self.user.groups.add(group)
        self.client.login(username="cashuser", password="pass123")

    def test_itdloan_use_funds_and_balance(self):
        bank = BankAccount.objects.create(
            name="Main",
            bank_name="TestBank",
            account_number="123456",
            balance=Decimal("0.00"),
        )

        resp = self.client.post(
            "/api/cashflow/itdloan/",
            {"loan_name": "ITD CEM Loan", "total_amount": "1000.00"},
        )
        self.assertEqual(resp.status_code, 201)
        loan_id = resp.json()["id"]

        detail = self.client.get(f"/api/cashflow/itdloan/{loan_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["remaining_balance"], "1000.00")

        use_url = f"/api/cashflow/itdloan/{loan_id}/use_funds/"
        resp = self.client.post(
            use_url,
            {"amount": "200.00", "description": "Test", "bank_account": bank.id},
        )
        self.assertEqual(resp.status_code, 201)

        loan = ITDLoan.objects.get(id=loan_id)
        self.assertEqual(loan.used_amount, Decimal("200.00"))

        detail = self.client.get(f"/api/cashflow/itdloan/{loan_id}/")
        self.assertEqual(detail.json()["remaining_balance"], "800.00")

        self.assertEqual(CashTransaction.objects.count(), 1)
        tx = CashTransaction.objects.first()
        self.assertEqual(tx.transaction_type, "ITDLoan_Usage")
        self.assertEqual(tx.amount, Decimal("200.00"))
