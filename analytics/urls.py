from django.urls import path
from .views import control_panel, embed_dashboard,superset_guest_token

app_name = "analytics"
urlpatterns = [
    path("control/", control_panel, name="control_panel"),
    path("embed/", embed_dashboard, name="embed"),
    path("api/superset_token/", superset_guest_token, name="superset_token"),
]

