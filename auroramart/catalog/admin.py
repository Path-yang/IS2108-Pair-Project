from django.contrib import admin

from .models import Product, ProductCategory, ProductSubcategory, Review


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(ProductSubcategory)
class ProductSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name", "category__name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "category",
        "subcategory",
        "unit_price",
        "quantity_on_hand",
        "is_active",
    )
    list_filter = ("category", "subcategory", "is_active")
    search_fields = ("sku", "name", "description")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")

