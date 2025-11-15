from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
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
    
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your full shipping address'}),
        required=False,
        help_text="Your default shipping address for orders"
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+65 1234 5678'}),
        help_text="Contact number for delivery"
    )
    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'your.email@example.com'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }


class EmailAuthenticationForm(forms.Form):
    """Custom login form that accepts email instead of username."""
    
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'Enter your email address'})
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct email and password.",
        'inactive': "This account is inactive.",
    }
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            except User.MultipleObjectsReturned:
                # If multiple users have same email, get the first active one
                user = User.objects.filter(email=email, is_active=True).first()
                if not user:
                    raise forms.ValidationError(
                        self.error_messages['invalid_login'],
                        code='invalid_login',
                    )
            
            if not user.check_password(password):
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            
            if not user.is_active:
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
            
            self.user_cache = user
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache
