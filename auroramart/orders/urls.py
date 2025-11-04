from django.urls import path

from . import views

app_name = "orders"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
]
