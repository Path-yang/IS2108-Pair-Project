from django import forms

from .models import Product, ProductCategory, ProductSubcategory, Review


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get category from data or initial or instance
        category = None
        if self.data:
            category = self.data.get("category")
        elif self.initial:
            category = self.initial.get("category")
        elif self.instance and self.instance.pk:
            category = self.instance.category_id
        
        # Filter subcategories based on selected category
        if category:
            try:
                category_id = int(category)
                self.fields["subcategory"].queryset = ProductSubcategory.objects.filter(
                    category_id=category_id
                )
            except (ValueError, TypeError):
                self.fields["subcategory"].queryset = ProductSubcategory.objects.none()
        else:
            # If no category selected, show no subcategories (user must select category first)
            self.fields["subcategory"].queryset = ProductSubcategory.objects.none()


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


class ReviewForm(forms.ModelForm):
    """Form for submitting product reviews (CUST-07, CUST-08)."""
    
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
                attrs={"class": "rating-select"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Share your experience with this product...",
                },
            ),
        }
        labels = {
            "rating": "Your Rating",
            "comment": "Your Review (optional)",
        }

