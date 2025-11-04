import logging
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

import joblib
from django.conf import settings

from catalog.models import Product, ProductCategory

logger = logging.getLogger(__name__)


DECISION_TREE_FILENAME = "b2c_customers_100.joblib"
ASSOCIATION_RULES_FILENAME = "b2c_products_500_transactions_50k.joblib"

# Expected feature order for the onboarding model.
ONBOARDING_FEATURES = [
    "age",
    "gender",
    "employment_status",
    "occupation",
    "education",
    "household_size",
    "has_children",
    "monthly_income_sgd",
]


def _load_artifact(filename: str):
    path = Path(settings.MODELS_DIR) / filename
    if not path.exists():
        logger.warning("Model artifact %s not found at %s", filename, path)
        return None
    try:
        return joblib.load(path)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Unable to load model artifact %s: %s", filename, exc)
        return None


@lru_cache(maxsize=1)
def get_decision_tree_model():
    return _load_artifact(DECISION_TREE_FILENAME)


@lru_cache(maxsize=1)
def get_association_rules():
    return _load_artifact(ASSOCIATION_RULES_FILENAME)


def predict_preferred_category(onboarding_data: dict) -> Optional[str]:
    """Return predicted preferred category label or None."""

    model = get_decision_tree_model()
    if not model:
        logger.info("Falling back to heuristic category prediction.")
        return _heuristic_category_prediction(onboarding_data)

    try:
        feature_row = []
        for feature in getattr(model, "feature_names_in_", ONBOARDING_FEATURES):
            value = onboarding_data.get(feature)
            if feature == "has_children":
                value = int(bool(value))
            feature_row.append(value)
        prediction = model.predict([feature_row])[0]
        return prediction
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Decision tree prediction failed: %s", exc)
        return _heuristic_category_prediction(onboarding_data)


def _heuristic_category_prediction(onboarding_data: dict) -> Optional[str]:
    """Basic heuristic when the ML model is unavailable."""
    gender = onboarding_data.get("gender", "").lower()
    if "female" in gender:
        return "Beauty & Personal Care"
    if "male" in gender:
        return "Electronics"
    return (
        ProductCategory.objects.order_by("name")
        .values_list("name", flat=True)
        .first()
    )


def recommend_associated_products(
    basket_skus: Iterable[str], limit: int = 4
) -> List[Product]:
    """Return a list of product recommendations based on association rules."""

    basket_skus = list({sku for sku in basket_skus if sku})
    rules = get_association_rules()
    if not rules:
        return _fallback_association_recommendations(basket_skus, limit)

    suggestions = []
    for sku in basket_skus:
        match = rules.get(sku)
        if not match:
            continue
        suggestions.extend(match)
        if len(suggestions) >= limit:
            break

    unique_skus = []
    for sku in suggestions:
        if sku not in basket_skus and sku not in unique_skus:
            unique_skus.append(sku)
        if len(unique_skus) == limit:
            break

    products = list(Product.objects.filter(sku__in=unique_skus, is_active=True))
    if len(products) < limit:
        products.extend(
            _fallback_association_recommendations(basket_skus, limit - len(products))
        )
    return products[:limit]


def _fallback_association_recommendations(
    basket_skus: Iterable[str], limit: int
) -> List[Product]:
    """Fallback to top-rated products not already in the basket."""
    return list(
        Product.objects.exclude(sku__in=basket_skus)
        .filter(is_active=True)
        .order_by("-product_rating", "-quantity_on_hand")[:limit]
    )
