import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from catalog.models import Product, ProductCategory, ProductSubcategory


class Command(BaseCommand):
    help = "Load product catalog data from CSV files."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--products",
            type=str,
            default="../IS2108 - AY2526S1 - Pair Project/data/b2c_products_500.csv",
            help="Path to the products CSV file.",
        )

    def handle(self, *args, **options):
        products_path = Path(options["products"]).resolve()
        if not products_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {products_path}"))
            return

        created = 0
        updated = 0

        with products_path.open(encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                category_name = row["Product Category"].strip()
                subcategory_name = row["Product Subcategory"].strip()

                category, _ = ProductCategory.objects.get_or_create(name=category_name)
                subcategory, _ = ProductSubcategory.objects.get_or_create(
                    category=category,
                    name=subcategory_name,
                )

                try:
                    quantity_on_hand = int(row["Quantity on hand"])
                except ValueError:
                    quantity_on_hand = 0

                try:
                    reorder_quantity = int(row["Reorder Quantity"])
                except ValueError:
                    reorder_quantity = 0

                try:
                    unit_price = Decimal(str(row["Unit price"]))
                except Exception:
                    unit_price = Decimal("0.00")

                try:
                    rating_raw = row["Product rating"]
                    rating = Decimal(str(rating_raw)) if rating_raw else None
                except Exception:
                    rating = None

                product, created_flag = Product.objects.update_or_create(
                    sku=row["SKU code"].strip(),
                    defaults={
                        "name": row["Product name"].strip(),
                        "description": row["Product description"].strip(),
                        "category": category,
                        "subcategory": subcategory,
                        "unit_price": unit_price,
                        "product_rating": rating,
                        "quantity_on_hand": quantity_on_hand,
                        "reorder_quantity": reorder_quantity,
                        "is_active": True,
                    },
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog import complete. Created {created} products, updated {updated}."
            )
        )
