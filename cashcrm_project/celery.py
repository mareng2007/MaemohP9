import os
from celery import Celery

# บอก Celery ให้ใช้ Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cashcrm_project.settings')
app = Celery('cashcrm_project')

# โหลดการตั้งค่าจาก Django settings โดยมองหาคอนฟิกที่ขึ้นต้นด้วย CELERY_*
app.config_from_object('django.conf:settings', namespace='CELERY')

# ให้ Celery สแกนหา tasks ในแต่ละ app อัตโนมัติ
app.autodiscover_tasks()


# # ตั้ง Beat Schedule (Periodic Tasks)
# app.conf.beat_schedule = {
#     # ทุกต้นเดือน: คำนวณดอกเบี้ยสินเชื่อธนาคาร
#     'calculate-bank-loan-interest': {
#         'task': 'loans.tasks.calculate_bankloan_interest',
#         'schedule': {
#             'type': 'crontab',
#             'hour': 0,
#             'minute': 0,
#             'day_of_month': 1,
#         },
#     },
#     # ทุกต้นเดือน: รัน Cashflow Projection
#     'run-cashflow-projection': {
#         'task': 'cashflow.tasks.daily_cashflow_projection',
#         'schedule': {
#             'type': 'crontab',
#             'hour': 1,
#             'minute': 0,
#             'day_of_month': 1,
#         },
#     },
#     # ทุกวัน: ตรวจสอบ LC ที่ครบ 180 วัน แล้วแปลงเป็น TR
#     'lc_to_tr_rollover': {
#         'task': 'cashflow.tasks.check_lcrequests_expiry',
#         'schedule': {
#             'type': 'crontab',
#             'hour': 0,
#             'minute': 30,
#         },
#     },
# }
