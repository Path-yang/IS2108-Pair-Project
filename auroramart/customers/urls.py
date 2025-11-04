from django.urls import path

from . import views

app_name = "customers"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
]
