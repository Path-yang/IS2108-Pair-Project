import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils.crypto import get_random_string

from catalog.models import Product
from orders.models import Basket, BasketItem, Order


class Command(BaseCommand):
    help = "Load historical basket transactions into Basket/Order tables."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--transactions",
            type=str,
            default="../IS2108 - AY2526S1 - Pair Project/data/b2c_products_500_transactions_50k.csv",
            help="Path to the basket transactions CSV file.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="Limit the number of baskets to import for development (default 1000). "
            "Use a larger number to ingest more data.",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Clear existing Basket, BasketItem, and Order records before import.",
        )

    def handle(self, *args, **options):
        transactions_path = Path(options["transactions"]).resolve()
        if not transactions_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {transactions_path}"))
            return

        if options["purge"]:
            self._purge_existing()

        limit = options["limit"]
        imported = 0
        skipped_items = 0

        with transactions_path.open(encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if limit and imported >= limit:
                    break

                sku_list = [sku.strip() for sku in row if sku.strip()]
                if not sku_list:
                    continue

                with transaction.atomic():
                    basket = Basket.objects.create(is_converted=True)
                    total_amount = Decimal("0.00")

                    for sku in sku_list:
                        product = Product.objects.filter(sku=sku).first()
                        if not product:
                            skipped_items += 1
                            continue
                        BasketItem.objects.create(
                            basket=basket,
                            product=product,
                            quantity=1,
                            unit_price=product.unit_price,
                        )
                        total_amount += product.unit_price

                    if basket.items.exists():
                        order_number = f"ORDER-{get_random_string(10).upper()}"
                        Order.objects.create(
                            basket=basket,
                            order_number=order_number,
                            total_amount=total_amount,
                            status="Imported",
                        )
                        imported += 1
                    else:
                        basket.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Transaction import complete. Imported {imported} baskets. "
                f"Skipped {skipped_items} items without matching products."
            )
        )

    def _purge_existing(self):
        BasketItem.objects.all().delete()
        Order.objects.all().delete()
        Basket.objects.all().delete()
        self.stdout.write(self.style.WARNING("Existing order history purged."))
