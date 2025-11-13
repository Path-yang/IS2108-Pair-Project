import csv
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
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
        customer_counter = 1  # Starting counter for customer IDs

        with profiles_path.open(encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                preferred_label = row["preferred_category"].strip()
                category = self._resolve_category(preferred_label)
                
                # Create a unique username for this customer
                username = f"customer{customer_counter}"
                email = f"{username}@auroramart.com"
                
                # Create or get user account (all active by default)
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'is_active': True,
                        'is_staff': False,
                    }
                )
                
                # Set a default password if user was just created
                if user_created:
                    user.set_password('password123')
                    user.save()

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
                        "user": user,
                    },
                )
                
                # If profile exists but has no user, link it
                if not created_flag and not profile.user:
                    profile.user = user
                    profile.save()

                if created_flag:
                    created += 1
                else:
                    updated += 1
                    
                customer_counter += 1

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
