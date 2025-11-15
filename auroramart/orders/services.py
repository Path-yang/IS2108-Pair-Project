from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils.crypto import get_random_string

from catalog.models import Product
from .models import Basket, BasketItem, Order


def get_or_create_session_basket(request) -> Basket:
    basket_id = request.session.get("basket_id")
    basket: Optional[Basket] = None
    if basket_id:
        basket = Basket.objects.filter(pk=basket_id, is_converted=False).first()

    if not basket:
        if not request.session.session_key:
            request.session.save()
        basket = Basket.objects.create(session_key=request.session.session_key)
        request.session["basket_id"] = basket.id
    return basket


def add_product_to_basket(basket: Basket, product: Product, quantity: int = 1):
    if product.quantity_on_hand <= 0:
        return
    item, created = BasketItem.objects.get_or_create(
        basket=basket,
        product=product,
        defaults={"quantity": quantity, "unit_price": product.unit_price},
    )
    if not created:
        item.quantity = min(item.quantity + quantity, product.quantity_on_hand)
        item.unit_price = product.unit_price
    else:
        item.quantity = min(item.quantity, product.quantity_on_hand)
    item.unit_price = product.unit_price
    item.save(update_fields=["quantity", "unit_price"])


def update_basket_item(item_id: int, quantity: int):
    try:
        item = BasketItem.objects.get(pk=item_id)
    except BasketItem.DoesNotExist:
        return
    if item.basket.is_converted:
        return
    if quantity <= 0:
        item.delete()
    else:
        max_quantity = item.product.quantity_on_hand or quantity
        if quantity > max_quantity:
            quantity = max_quantity
        item.quantity = quantity
        item.save(update_fields=["quantity"])


def remove_basket_item(item_id: int):
    """Remove an item from the basket."""
    try:
        item = BasketItem.objects.get(pk=item_id)
    except BasketItem.DoesNotExist:
        return False
    if item.basket.is_converted:
        return False
    item.delete()
    return True


@transaction.atomic
def convert_basket_to_order(basket: Basket, shipping_data: dict, payment_data: dict, customer_profile=None):
    """Create an order from the basket and mark it as converted."""
    if basket.is_converted or not basket.items.exists():
        return basket.order if hasattr(basket, "order") else None

    total_amount = Decimal("0.00")
    for item in basket.items.all():
        total_amount += item.unit_price * item.quantity
        product = item.product
        if product.quantity_on_hand >= item.quantity:
            product.quantity_on_hand -= item.quantity
            product.save(update_fields=["quantity_on_hand", "updated_at"])

    order_number = f"ORD-{get_random_string(8).upper()}"
    order = Order.objects.create(
        basket=basket,
        order_number=order_number,
        total_amount=total_amount,
        status="Placed",
        customer=customer_profile,
    )
    basket.is_converted = True
    basket.save(update_fields=["is_converted"])
    return order


def clear_basket_session(request):
    if "basket_id" in request.session:
        del request.session["basket_id"]
