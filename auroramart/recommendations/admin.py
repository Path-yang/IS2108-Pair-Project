from django.contrib import admin

from .models import ModelArtifact


@admin.register(ModelArtifact)
class ModelArtifactAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "model_type",
        "version",
        "trained_at",
        "updated_at",
    )
    list_filter = ("model_type", "trained_at")
    search_fields = ("code", "name", "description")

# Register your models here.
