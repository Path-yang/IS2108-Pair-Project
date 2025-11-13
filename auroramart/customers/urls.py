from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "customers"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    
    # Customer account management
    path("register/", views.CustomerRegistrationView.as_view(), name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="customers/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("profile/", views.CustomerProfileView.as_view(), name="profile"),
    path("orders/", views.OrderHistoryView.as_view(), name="order_history"),
    
    # Staff customer management
    path("staff/list/", views.StaffCustomerListView.as_view(), name="staff_customer_list"),
    path("staff/<int:pk>/", views.StaffCustomerDetailView.as_view(), name="staff_customer_detail"),
    path("staff/<int:pk>/toggle/", views.StaffCustomerToggleActiveView.as_view(), name="staff_customer_toggle"),
    path("staff/<int:pk>/delete/", views.StaffCustomerDeleteView.as_view(), name="staff_customer_delete"),
]
