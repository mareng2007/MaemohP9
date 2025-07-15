from django.urls import path
from . import views

app_name = 'flowchart'

urlpatterns = [
    path('', views.FlowchartListView.as_view(), name='list'),
    path('create/', views.FlowchartCreateView.as_view(), name='create'),
    path('<int:pk>/', views.FlowchartDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.FlowchartUpdateView.as_view(), name='edit'),
    path('<int:pk>/download/<int:version>/', views.FlowchartExportView.as_view(), name='download'),
]