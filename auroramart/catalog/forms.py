from django import forms

from .models import Product, ProductCategory, ProductSubcategory


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "description",
            "category",
            "subcategory",
            "unit_price",
            "product_rating",
            "quantity_on_hand",
            "reorder_quantity",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name"]


class ProductSubcategoryForm(forms.ModelForm):
    class Meta:
        model = ProductSubcategory
        fields = ["category", "name"]


class CatalogUploadForm(forms.Form):
    file = forms.FileField(
        help_text="Upload a CSV file with the same columns as the provided dataset."
    )
