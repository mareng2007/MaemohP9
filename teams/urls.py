from django.urls import path
from .views import TeamListView, TeamCreateView, TeamDetailView

app_name = 'teams'

urlpatterns = [
    path('', TeamListView.as_view(), name='team-list'),
    path('create/', TeamCreateView.as_view(), name='team-create'),
    path('<int:pk>/', TeamDetailView.as_view(), name='team-detail'),
]