from django.contrib import admin
from .models import Task, TaskReview, TaskFile

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'assigned_to', 'assigned_team', 'created_at')
    list_filter = ('status',)

@admin.register(TaskReview)
class TaskReviewAdmin(admin.ModelAdmin):
    list_display = ('task', 'reviewer', 'approved', 'created_at')
    list_filter = ('approved',)


@admin.register(TaskFile)
class TaskFileAdmin(admin.ModelAdmin):
    list_display = ('task', 'version', 'uploaded_by', 'uploaded_at')
