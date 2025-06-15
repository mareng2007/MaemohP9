from celery import shared_task
from django.utils import timezone

from .models import OTP

@shared_task
def delete_expired_otps():
    """Delete OTP entries whose valid_until has passed."""
    OTP.objects.filter(valid_until__lt=timezone.now()).delete()

