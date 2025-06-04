from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class MineProgressReport(models.Model):
    """
    เก็บข้อมูลรายงานความก้าวหน้าของงานเหมือง 
    """
    report_date = models.DateField()
    description = models.TextField()
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2)  # เปอร์เซ็นต์ความก้าวหน้า
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Report {self.id} on {self.report_date} ({self.progress_pct}%)"

class DocumentCheck(models.Model):
    """
    เก็บข้อมูลการตรวจเอกสาร (เช่น อาจารย์ มช. หรือ ลาดกระบัง)
    """
    report = models.ForeignKey(MineProgressReport, on_delete=models.CASCADE, related_name='doc_checks')
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    check_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"DocCheck {self.id} for Report {self.report.id}"

