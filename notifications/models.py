from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    CHANNEL_EMAIL = 'email'
    CHANNEL_APP = 'app'
    CHANNEL_CHAT = 'chat'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_APP, 'App'),
        (CHANNEL_CHAT, 'Chat'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.title}"
