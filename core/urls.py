"""URL patterns for the core app."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("checkin/", views.checkin, name="checkin"),
    path("checkin/fields/", views.checkin_fields, name="checkin_fields"),
    path("status/", views.status, name="status"),
    path("region/<str:region>/", views.region_detail, name="region_detail"),
    path("trend/<str:indicator_key>/", views.trend, name="trend"),
]
