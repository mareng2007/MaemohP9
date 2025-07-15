from django.db import models
from django.contrib.auth import get_user_model
from teams.models import Team

User = get_user_model()

class Task(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In_Review', 'In Review'),
        ('Approved', 'Approved'),
        ('Closed', 'Closed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tasks_created')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks_assigned')
    assigned_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

class TaskReview(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='task_reviews')
    comment = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = 'Approved' if self.approved else 'Comment'
        return f"{self.reviewer} on {self.task}: {status}"


class TaskFile(models.Model):
    """File attachment for a task with basic versioning."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    version = models.PositiveIntegerField()
    file = models.FileField(upload_to='task_files/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='task_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'version')
        ordering = ['version']

    def save(self, *args, **kwargs):
        if not self.pk:
            last_version = TaskFile.objects.filter(task=self.task).aggregate(models.Max('version'))['version__max'] or 0
            self.version = last_version + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.title} v{self.version}"
