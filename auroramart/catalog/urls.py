from django.urls import path

from . import views

app_name = "catalog"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    path("staff/catalog/", views.ProductListView.as_view(), name="product_list"),
    path("staff/catalog/new/", views.ProductCreateView.as_view(), name="product_create"),
    path(
        "staff/catalog/<int:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_update",
    ),
    path(
        "staff/catalog/<int:pk>/deactivate/",
        views.ProductDeactivateView.as_view(),
        name="product_deactivate",
    ),
    path(
        "staff/catalog/<int:pk>/reactivate/",
        views.ProductReactivateView.as_view(),
        name="product_reactivate",
    ),
    path(
        "staff/catalog/low-stock/",
        views.LowStockListView.as_view(),
        name="low_stock_list",
    ),
    path(
        "staff/catalog/upload/",
        views.CatalogUploadView.as_view(),
        name="catalog_upload",
    ),
    path(
        "staff/catalog/categories/",
        views.CategoryManagementView.as_view(),
        name="category_management",
    ),
]
