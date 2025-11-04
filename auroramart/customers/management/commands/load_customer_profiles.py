import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from catalog.models import ProductCategory
from customers.models import CustomerProfile


class Command(BaseCommand):
    help = "Load customer demographic profiles from CSV."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--profiles",
            type=str,
            default="../IS2108 - AY2526S1 - Pair Project/data/b2c_customers_100.csv",
            help="Path to the customer profiles CSV file.",
        )

    def handle(self, *args, **options):
        profiles_path = Path(options["profiles"]).resolve()
        if not profiles_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {profiles_path}"))
            return

        created = 0
        updated = 0

        with profiles_path.open(encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                preferred_label = row["preferred_category"].strip()
                category = self._resolve_category(preferred_label)

                profile, created_flag = CustomerProfile.objects.update_or_create(
                    age=int(row["age"]),
                    gender=row["gender"].strip(),
                    employment_status=row["employment_status"].strip(),
                    occupation=row["occupation"].strip(),
                    education=row["education"].strip(),
                    household_size=int(row["household_size"]),
                    has_children=bool(int(row["has_children"])),
                    monthly_income_sgd=Decimal(str(row["monthly_income_sgd"])),
                    defaults={
                        "preferred_category_label": preferred_label,
                        "preferred_category": category,
                    },
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Customer profile import complete. "
                f"Created {created}, updated {updated} records."
            )
        )

    def _resolve_category(self, label: str):
        if not label:
            return None

        # Exact match on category name.
        category = ProductCategory.objects.filter(name=label).first()
        if category:
            return category

        # Attempt to match first segment when label is "Category - Detail".
        if "-" in label:
            primary = label.split("-")[0].strip()
            category = ProductCategory.objects.filter(name=primary).first()
            if category:
                return category

        # Fallback: return None and let the label persist for reporting.
        return None
