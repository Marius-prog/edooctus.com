from django.urls import path

from .views import ComponentsDebugView

app_name = "shared"

urlpatterns = [
    path("", ComponentsDebugView.as_view(), name="components_debug"),
]
