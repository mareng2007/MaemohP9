from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification
import requests


@shared_task
def send_notification(user_id: int, title: str, message: str, channel: str):
    """Send a notification via the specified channel."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    if channel == Notification.CHANNEL_EMAIL:
        if user.email:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
    elif channel == Notification.CHANNEL_CHAT:
        token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', None)
        targets = getattr(settings, 'LINE_TARGET_IDS', [])
        if token and targets:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "to": targets,
                "messages": [{"type": "text", "text": message}],
            }
            try:
                requests.post(
                    "https://api.line.me/v2/bot/message/multicast",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
            except Exception:
                pass

    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        channel=channel,
    )


@shared_task
def monthly_important_notifications():
    """Send sample monthly notifications to all active users."""
    users = User.objects.filter(is_active=True)
    for user in users:
        send_notification.delay(user.id, "Monthly Summary", "Please review monthly financial summary.", Notification.CHANNEL_EMAIL)
        send_notification.delay(user.id, "New Tasks", "Check your dashboard for new tasks this month.", Notification.CHANNEL_APP)
        send_notification.delay(user.id, "Chat Reminder", "You have unread messages.", Notification.CHANNEL_CHAT)
