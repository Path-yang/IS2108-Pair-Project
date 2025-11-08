from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import CustomerProfile


class CustomerRegistrationForm(UserCreationForm):
    """User registration form with email."""
    
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class CustomerProfileForm(forms.ModelForm):
    """Form for editing customer profile information."""
    
    class Meta:
        model = CustomerProfile
        fields = [
            "age",
            "gender",
            "employment_status",
            "occupation",
            "education",
            "household_size",
            "has_children",
            "monthly_income_sgd",
        ]
        widgets = {
            "age": forms.NumberInput(attrs={"min": 18, "max": 120}),
            "household_size": forms.NumberInput(attrs={"min": 1, "max": 20}),
            "monthly_income_sgd": forms.NumberInput(attrs={"step": "0.01"}),
        }


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating user account information."""
    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
