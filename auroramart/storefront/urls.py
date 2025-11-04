from django.urls import path

from . import views

app_name = "storefront"


urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("onboarding/", views.OnboardingView.as_view(), name="onboarding"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<str:sku>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("checkout/shipping/", views.ShippingView.as_view(), name="checkout_shipping"),
    path("checkout/payment/", views.PaymentView.as_view(), name="checkout_payment"),
    path("checkout/review/", views.ReviewView.as_view(), name="checkout_review"),
    path("checkout/complete/", views.ConfirmationView.as_view(), name="checkout_complete"),
]
