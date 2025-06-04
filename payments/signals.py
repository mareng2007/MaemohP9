from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from notifications.tasks import send_notification

@receiver(post_save, sender=Payment)
def notify_payment(sender, instance, created, **kwargs):
    if created and instance.status == Payment.STATUS_PENDING:
        send_notification.delay(
            instance.user.id,
            'Payment Initiated',
            f'Payment of {instance.amount} {instance.currency} initiated via {instance.provider}.',
            'app'
        )
    elif instance.status == Payment.STATUS_COMPLETED:
        send_notification.delay(
            instance.user.id,
            'Payment Completed',
            f'Thank you for your payment of {instance.amount} {instance.currency}.',
            'email'
        )
