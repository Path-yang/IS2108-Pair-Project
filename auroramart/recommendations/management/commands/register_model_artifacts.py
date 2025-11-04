from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from recommendations.models import ModelArtifact


class Command(BaseCommand):
    help = "Register machine learning model artifacts for tracking."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--models-dir",
            type=str,
            default="../IS2108 - AY2526S1 - Pair Project/model",
            help="Directory containing serialized model artifacts.",
        )

    def handle(self, *args, **options):
        models_dir = Path(options["models_dir"]).resolve()
        if not models_dir.exists():
            self.stderr.write(self.style.ERROR(f"Directory not found: {models_dir}"))
            return

        artifacts = [
            (
                "decision_tree_customer_preference",
                "Customer Preferred Category Decision Tree",
                "decision_tree",
                "b2c_customers_100.joblib",
            ),
            (
                "association_rules_basket",
                "Basket Association Rules",
                "association_rules",
                "b2c_products_500_transactions_50k.joblib",
            ),
        ]

        created = 0
        updated = 0

        for code, name, model_type, filename in artifacts:
            file_path = models_dir / filename
            artifact, created_flag = ModelArtifact.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "model_type": model_type,
                    "description": f"Auto-registered from {file_path.name}",
                    "file_path": str(file_path),
                },
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Model artifact registration complete. "
                f"Created {created}, updated {updated} records."
            )
        )
