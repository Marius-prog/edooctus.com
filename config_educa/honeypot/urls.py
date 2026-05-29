from django.urls import path

from . import views

app_name = "honeypot"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tripwire/<str:token>/", views.tripwire, name="tripwire"),
]
