from django.db import models
from django.utils.text import slugify


class ProductCategory(models.Model):
    """Top-level merchandising category."""

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True, editable=False)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return self.name


class ProductSubcategory(models.Model):
    """Nested merchandising category to support curated storefronts."""

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, editable=False)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category__name", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"{self.category.name} :: {self.name}"


class Product(models.Model):
    """Single SKU that customers can browse and purchase."""

    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    subcategory = models.ForeignKey(
        ProductSubcategory,
        on_delete=models.PROTECT,
        related_name="products",
        blank=True,
        null=True,
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Average customer rating on a 1-5 scale.",
    )
    quantity_on_hand = models.PositiveIntegerField(default=0)
    reorder_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"{self.sku} – {self.name}"

# Create your models here.
