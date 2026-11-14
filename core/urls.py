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
    path("trend/<str:indicator_key>/chart/", views.trend_chart, name="trend_chart"),
    path("blackout/toggle/", views.blackout_toggle, name="blackout_toggle"),
    path("relay/", views.relay, name="relay"),
    path("relay/<int:item_id>/resolve/", views.relay_resolve, name="relay_resolve"),
    path("relay/export/", views.relay_export, name="relay_export"),
]
