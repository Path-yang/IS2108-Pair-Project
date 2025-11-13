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
            elif feature == "monthly_income_sgd":
                # Convert Decimal to float for sklearn compatibility
                value = float(value) if value is not None else 0.0
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
    if rules is None:
        logger.info("Association rules not loaded, using fallback")
        return _fallback_association_recommendations(basket_skus, limit)

    # Query the DataFrame for rules where basket items are in antecedents
    # Process ALL input SKUs to ensure variety in recommendations
    suggestions = []
    matched_count = 0
    for sku in basket_skus:
        # Find rules where this SKU is in the antecedents
        matched_rules = rules[rules['antecedents'].apply(lambda x: sku in x)]

        if not matched_rules.empty:
            matched_count += 1
            # Sort by confidence (highest first) and get consequents
            top_rules = matched_rules.sort_values(by='confidence', ascending=False).head(5)

            for _, row in top_rules.iterrows():
                # Add all items from consequents
                suggestions.extend(list(row['consequents']))

    logger.info(f"Processed {len(basket_skus)} SKUs, {matched_count} had rules, {len(suggestions)} suggestions before dedup")

    # Remove duplicates and items already in basket, preserving order
    unique_skus = []
    for sku in suggestions:
        if sku not in basket_skus and sku not in unique_skus:
            unique_skus.append(sku)
        if len(unique_skus) == limit:
            break

    # Fetch products from database
    products = list(Product.objects.filter(sku__in=unique_skus, is_active=True))

    # If we didn't find enough products, supplement with fallback recommendations
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
