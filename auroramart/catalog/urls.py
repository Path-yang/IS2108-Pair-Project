from django.urls import path

from . import views

app_name = "catalog"


urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    path("staff/dashboard/", views.StaffDashboardView.as_view(), name="dashboard"),
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
        "staff/catalog/export/",
        views.ProductExportView.as_view(),
        name="product_export",
    ),
    path(
        "staff/catalog/categories/",
        views.CategoryManagementView.as_view(),
        name="category_management",
    ),
    # Review URLs
    path(
        "reviews/product/<int:product_pk>/create/",
        views.ReviewCreateView.as_view(),
        name="review_create",
    ),
    path(
        "reviews/<int:pk>/edit/",
        views.ReviewUpdateView.as_view(),
        name="review_update",
    ),
    path(
        "reviews/<int:pk>/delete/",
        views.ReviewDeleteView.as_view(),
        name="review_delete",
    ),
]
