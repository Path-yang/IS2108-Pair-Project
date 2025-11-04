# AuroraMart – IS2108 Pair Project

## Getting Started
1. Create the virtual environment and install dependencies
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Apply migrations and seed the datasets
   ```bash
   cd auroramart
   python manage.py migrate
   python manage.py load_catalog_data
   python manage.py load_customer_profiles
python manage.py register_model_artifacts
   ```
3. Run the development server
   ```bash
   python manage.py runserver
   ```

> **Note:** The pretrained joblib files are tracked via Git LFS. If the raw artefacts are unavailable, the application gracefully falls back to heuristic recommendations.

## Staff Catalogue Tools
- `/staff/login/` – staff authentication (use Django admin credentials).
- `/api/catalog/staff/catalog/` – manage products (search, filter, CRUD, soft delete).
- `/api/catalog/staff/catalog/low-stock/` – monitor SKUs below reorder threshold.
- `/api/catalog/staff/catalog/upload/` – CSV-based bulk import following the provided dataset schema.
- `/api/catalog/staff/catalog/categories/` – maintain category and subcategory taxonomy.

## Storefront Highlights
- AI-assisted onboarding form that predicts a preferred category via the decision-tree model.
- Product browsing with search, filters, and out-of-stock indicators.
- Product detail pages featuring association-rule recommendations.
- Session-backed cart with quantity adjustments and responsive stock validation.
- Guided checkout (shipping → payment → review) with order confirmation and inventory deductions.

See `PROGRESS.md` for the development log and remaining to-dos.
