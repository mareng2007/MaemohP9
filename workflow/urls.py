from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, TaskReviewViewSet,
    TaskListView, TaskDetailView, TaskCreateView, TaskUpdateView, TaskFileDiffView,
)

app_name = 'workflow'

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-reviews', TaskReviewViewSet, basename='taskreview')

urlpatterns = [
    # Web views
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/edit/', TaskUpdateView.as_view(), name='task-edit'),
    path('files/<int:pk>/diff/', TaskFileDiffView.as_view(), name='taskfile-diff'),

    # API endpoints (e.g. /api/workflow/api/tasks/)
    path('api/', include((router.urls, 'workflow-api'))),
]