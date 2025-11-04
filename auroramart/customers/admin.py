from django.contrib import admin

from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "age",
        "gender",
        "employment_status",
        "household_size",
        "has_children",
        "preferred_category_label",
        "preferred_category",
        "monthly_income_sgd",
    )
    list_filter = (
        "gender",
        "employment_status",
        "has_children",
        "preferred_category",
    )
    search_fields = (
        "occupation",
        "education",
        "preferred_category_label",
    )

# Register your models here.
