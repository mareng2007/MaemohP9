from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import MineProgressReport

User = get_user_model()


class MineProgressReportModelTest(TestCase):
    def test_string_representation(self):
        user = User.objects.create(username="reporter")
        report = MineProgressReport.objects.create(
            report_date=date.today(),
            description="Test", 
            progress_pct=1.5,
            created_by=user,
        )
        expected = f"Report {report.id} on {report.report_date} ({report.progress_pct}%)"
        self.assertEqual(str(report), expected)

