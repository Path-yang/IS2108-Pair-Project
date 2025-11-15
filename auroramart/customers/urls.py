from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "customers"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    
    # Customer account management
    path("register/", views.CustomerRegistrationView.as_view(), name="register"),
    path("login/", views.CustomerLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("profile/", views.CustomerProfileView.as_view(), name="profile"),
    path("orders/", views.OrderHistoryView.as_view(), name="order_history"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete_account"),
    
    # Password reset
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="customers/password_reset.html",
        email_template_name="customers/password_reset_email.html",
        subject_template_name="customers/password_reset_subject.txt",
        success_url=reverse_lazy("customers:password_reset_done")
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="customers/password_reset_done.html"), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="customers/password_reset_confirm.html",
        success_url=reverse_lazy("customers:password_reset_complete")
    ), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(template_name="customers/password_reset_complete.html"), name="password_reset_complete"),
    
    # Staff customer management
    path("staff/list/", views.StaffCustomerListView.as_view(), name="staff_customer_list"),
    path("staff/<int:pk>/", views.StaffCustomerDetailView.as_view(), name="staff_customer_detail"),
    path("staff/<int:pk>/toggle/", views.StaffCustomerToggleActiveView.as_view(), name="staff_customer_toggle"),
    path("staff/<int:pk>/delete/", views.StaffCustomerDeleteView.as_view(), name="staff_customer_delete"),
]
