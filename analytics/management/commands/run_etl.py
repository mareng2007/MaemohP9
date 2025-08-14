from django.core.management.base import BaseCommand
from analytics.tasks import etl_budget_all

class Command(BaseCommand):
    help = "Run full ETL (Budget.xlsx + Actual_old.csv + API) and refresh remaining snapshot."

    def handle(self, *args, **options):
        etl_budget_all.apply(args=[], kwargs={}).get()
        self.stdout.write(self.style.SUCCESS("ETL สำเร็จ และอัปเดตสรุปคงเหลือแล้ว"))
