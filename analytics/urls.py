from django.urls import path
from .views import control_panel

app_name = "analytics"
urlpatterns = [
    path("control/", control_panel, name="control_panel"),
]
