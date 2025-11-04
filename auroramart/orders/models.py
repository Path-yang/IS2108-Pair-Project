from django.db import models

from catalog.models import Product
from customers.models import CustomerProfile


class Basket(models.Model):
    """Transient shopping basket prior to checkout."""

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="baskets",
        null=True,
        blank=True,
    )
    session_key = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional session identifier for anonymous users.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_converted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        owner = self.customer or self.session_key or "anonymous"
        return f"Basket({owner})"


class BasketItem(models.Model):
    """Line items captured inside a basket."""

    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="basket_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("basket", "product")

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"{self.product.sku} x {self.quantity}"


class Order(models.Model):
    """Confirmed order created from a basket."""

    basket = models.OneToOneField(
        Basket,
        on_delete=models.PROTECT,
        related_name="order",
    )
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    order_number = models.CharField(max_length=32, unique=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=32, default="Pending")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"Order {self.order_number}"

# Create your models here.
