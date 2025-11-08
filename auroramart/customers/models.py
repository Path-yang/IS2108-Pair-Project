from django.contrib.auth.models import User
from django.db import models

from catalog.models import ProductCategory


class CustomerProfile(models.Model):
    """Customer demographics used for onboarding and recommendations."""

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    EMPLOYMENT_CHOICES = [
        ("Full-time", "Full-time"),
        ("Part-time", "Part-time"),
        ("Self-employed", "Self-employed"),
        ("Unemployed", "Unemployed"),
        ("Student", "Student"),
        ("Retired", "Retired"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        null=True,
        blank=True,
        help_text="Optional link to user account for registered customers",
    )
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES)
    employment_status = models.CharField(max_length=32, choices=EMPLOYMENT_CHOICES)
    occupation = models.CharField(max_length=64)
    education = models.CharField(max_length=64)
    household_size = models.PositiveSmallIntegerField()
    has_children = models.BooleanField(default=False)
    monthly_income_sgd = models.DecimalField(max_digits=10, decimal_places=2)
    preferred_category_label = models.CharField(max_length=128)
    preferred_category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        related_name="preferred_customers",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"{self.gender}, {self.age} – {self.occupation}"

# Create your models here.
