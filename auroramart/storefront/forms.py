from django import forms

from catalog.models import ProductCategory, ProductSubcategory


class OnboardingForm(forms.Form):
    age = forms.IntegerField(min_value=18, max_value=90)
    gender = forms.ChoiceField(
        choices=[
            ("Female", "Female"),
            ("Male", "Male"),
            ("Other", "Other"),
        ],
    )
    employment_status = forms.ChoiceField(
        choices=[
            ("Full-time", "Full-time"),
            ("Part-time", "Part-time"),
            ("Self-employed", "Self-employed"),
            ("Student", "Student"),
            ("Unemployed", "Unemployed"),
            ("Retired", "Retired"),
        ]
    )
    occupation = forms.ChoiceField(
        choices=[
            ("Sales", "Sales"),
            ("Service", "Service"),
            ("Admin", "Admin"),
            ("Tech", "Tech"),
            ("Education", "Education"),
            ("Skilled Trades", "Skilled Trades"),
        ]
    )
    education = forms.ChoiceField(
        choices=[
            ("Secondary", "Secondary"),
            ("Diploma", "Diploma"),
            ("Bachelor", "Bachelor"),
            ("Masters", "Masters"),
            ("Doctorate", "Doctorate"),
        ]
    )
    household_size = forms.IntegerField(min_value=1, max_value=12)
    has_children = forms.BooleanField(required=False)
    monthly_income_sgd = forms.DecimalField(
        min_value=0, max_digits=10, decimal_places=2
    )


class ProductFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.none(), required=False
    )
    subcategory = forms.ModelChoiceField(
        queryset=ProductSubcategory.objects.none(), required=False
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("name", "Name (A → Z)"),
            ("-name", "Name (Z → A)"),
            ("unit_price", "Price (Low to High)"),
            ("-unit_price", "Price (High to Low)"),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ProductCategory.objects.all()
        category = self.data.get("category") or self.initial.get("category")
        if category:
            self.fields["subcategory"].queryset = ProductSubcategory.objects.filter(
                category_id=category
            )
        else:
            self.fields["subcategory"].queryset = ProductSubcategory.objects.all()


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)


class UpdateCartForm(forms.Form):
    line_id = forms.IntegerField()
    quantity = forms.IntegerField(min_value=0)


class ShippingAddressForm(forms.Form):
    full_name = forms.CharField(max_length=128)
    address_line_1 = forms.CharField(max_length=255)
    address_line_2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=64)
    postal_code = forms.CharField(max_length=16)
    contact_number = forms.CharField(max_length=24)


class PaymentForm(forms.Form):
    cardholder_name = forms.CharField(max_length=128)
    card_number = forms.CharField(max_length=19)
    expiry_month = forms.IntegerField(min_value=1, max_value=12)
    expiry_year = forms.IntegerField(min_value=2024, max_value=2040)
    cvv = forms.CharField(max_length=4)
