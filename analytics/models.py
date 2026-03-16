from django.db import models

class BudgetPlan(models.Model):
    budget_year    = models.IntegerField()
    budget_code    = models.CharField(max_length=50)
    description    = models.CharField(max_length=255, blank=True, default="")
    budget_amount  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    budget_group   = models.CharField(max_length=100, blank=True, default="")
    budget_subgroup= models.CharField(max_length=100, blank=True, default="")
    budget_type    = models.CharField(max_length=50,  blank=True, default="")
    budget_owner   = models.CharField(max_length=100, blank=True, default="")
    dept           = models.CharField(max_length=100, blank=True, default="")
    ro_order       = models.CharField(max_length=20,  blank=True, default="")

    class Meta:
        unique_together = ("budget_year", "budget_code")
        indexes = [models.Index(fields=["budget_year","budget_code"])]

    def __str__(self):
        return f"{self.budget_year} - {self.budget_code}"

class BudgetActual(models.Model):
    doc_date      = models.DateField()
    budget_code   = models.CharField(max_length=50)
    amount        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    source        = models.CharField(max_length=20)   # 'csv' หรือ 'api'
    load_batch_id = models.CharField(max_length=40)

    # ✅ “ลำดับเวลา/การอ้างอิงรายการ”
    event_ts      = models.DateTimeField(null=True, blank=True)     # เวลาที่เกิดรายการจริง
    source_ref    = models.CharField(max_length=100, blank=True, default="")  # ไอดีจาก API/CSV (ถ้ามี)
    seq_no        = models.IntegerField(null=True, blank=True)      # ลำดับในวันเดียวกัน

    class Meta:
        indexes = [
            models.Index(fields=["doc_date"]),
            models.Index(fields=["budget_code"]),
            models.Index(fields=["event_ts"]),
            models.Index(fields=["source", "doc_date"]),
            models.Index(fields=["source_ref"]),
        ]

class RemainingSnapshot(models.Model):
    snapshot_at   = models.DateTimeField(auto_now_add=True)
    budget_year   = models.IntegerField()
    budget_code   = models.CharField(max_length=50)
    description   = models.CharField(max_length=255, blank=True, default="")
    budget_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual_to_date= models.DecimalField(max_digits=18, decimal_places=2, default=0)
    remaining     = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    usage_pct     = models.DecimalField(max_digits=9,  decimal_places=4, null=True, blank=True)
    budget_owner  = models.CharField(max_length=100, blank=True, default="")
    budget_group  = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["snapshot_at"]),
            models.Index(fields=["budget_year"]),
            models.Index(fields=["usage_pct"]),
            models.Index(fields=["budget_owner"]),
            models.Index(fields=["budget_group"]),
        ]

# ✅ ดัชนี RO สำหรับตอบใน LINE OA (แม้ API ไม่มี amount)
class RoIndex(models.Model):
    ro_id        = models.CharField(max_length=64, primary_key=True)
    budget_code  = models.CharField(max_length=50, db_index=True)
    budget_year  = models.IntegerField(db_index=True)
    created_at   = models.DateTimeField(db_index=True)
    amount       = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        indexes = [
            models.Index(fields=["budget_code", "budget_year"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"RO {self.ro_id} ({self.budget_year}/{self.budget_code})"



