from django.db import models
from django.utils import timezone


class ModelArtifact(models.Model):
    """Metadata for persisted ML artifacts (decision tree, association rules)."""

    MODEL_TYPE_CHOICES = [
        ("decision_tree", "Decision Tree"),
        ("association_rules", "Association Rules"),
        ("other", "Other"),
    ]

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=32, choices=MODEL_TYPE_CHOICES)
    file_path = models.CharField(
        max_length=255,
        help_text="Relative path to the serialized model artifact.",
    )
    version = models.CharField(max_length=32, default="1.0.0")
    trained_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover - simple string repr
        return f"{self.code} ({self.model_type})"

# Create your models here.
