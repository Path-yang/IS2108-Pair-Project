from django.urls import path

from . import views

app_name = "recommendations"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
]
