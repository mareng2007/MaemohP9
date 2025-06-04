from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('upload/', views.upload_document, name='upload'),
    path('success/', views.upload_success, name='upload_success'),
]
