# AuroraMart Development Log

## Day 1 – Project Foundations
- Created virtual environment and installed core dependencies (`Django 5.2`, `djangorestframework`, `python-dotenv`).
- Bootstrapped the `auroramart` Django project with dedicated apps for catalogue, customers, orders, recommendations, and storefront.
- Added baseline models for products, categories, customers, baskets, orders, and ML artifacts with admin registration.
- Implemented management commands to ingest the provided CSV datasets and register the pretrained joblib models (graceful fallback if artefacts missing).
- Configured settings for templates, static/media, DRF defaults, login redirection, and dataset/model directories.

## Day 2 – Staff Catalogue & Taxonomy Tools
- Built staff-only catalogue management views covering search, sorting, CRUD operations, soft delete/reactivation, low-stock monitoring, CSV re-import, and category taxonomy maintenance.
- Added dedicated templates, forms, and navigation for the staff panel plus lightweight styling.

## Day 3 – Storefront Core & AI Integration
- Implemented customer-facing onboarding using the decision-tree service (with heuristic fallback) to redirect shoppers to relevant categories.
- Delivered product browsing with filtering, search, sorting, and out-of-stock indicators.
- Created product detail view with add-to-cart workflow and association-rule-driven “frequently bought together” recommendations (fallback to top-rated items).
- Added session-backed cart management, quantity updates, and inventory-aware order conversion that reduces stock levels.
- Completed a three-step checkout (shipping, payment, review) culminating in order confirmation and mock payment handling.
- Established recommendation services that lazily load joblib models, log missing artefacts, and expose sensible defaults when models are unavailable.

## Next Steps
- Populate remaining user stories (e.g., customer profile center, order history, wishlist) and expand unit/integration tests.
- Polish UI styling, add responsive behaviour, and integrate analytics hooks for product impressions.
