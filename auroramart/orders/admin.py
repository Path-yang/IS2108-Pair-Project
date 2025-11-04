from django.contrib import admin

from .models import Basket, BasketItem, Order


class BasketItemInline(admin.TabularInline):
    model = BasketItem
    extra = 0
    readonly_fields = ("unit_price",)


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "session_key", "is_converted", "updated_at")
    list_filter = ("is_converted", "created_at")
    search_fields = ("session_key", "customer__occupation")
    inlines = [BasketItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "customer__occupation")

# Register your models here.
