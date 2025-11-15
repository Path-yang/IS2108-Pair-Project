import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auroramart.settings')
django.setup()

from django.contrib.auth.models import User
from catalog.models import ProductCategory, ProductSubcategory, Product

# Check categories
print("=" * 50)
print("CHECKING CATEGORIES")
print("=" * 50)
categories = ProductCategory.objects.all()
print(f"Total categories: {categories.count()}")
for cat in categories:
    print(f"  - {cat.name}")

print("\nChecking subcategories...")
subcategories = ProductSubcategory.objects.all()
print(f"Total subcategories: {subcategories.count()}")
for subcat in subcategories[:10]:  # Show first 10
    print(f"  - {subcat.name} (Category: {subcat.category.name if subcat.category else 'None'})")

print("\nChecking products...")
products = Product.objects.all()
print(f"Total products: {products.count()}")
for prod in products[:5]:  # Show first 5
    print(f"  - {prod.name} (SKU: {prod.sku})")

# Create staff account
print("\n" + "=" * 50)
print("CREATING STAFF ACCOUNT")
print("=" * 50)

try:
    user = User.objects.get(username='staff')
    print(f"Staff user already exists: {user.username}")
    # Update password
    user.set_password('12345')
    user.is_staff = True
    user.is_superuser = False
    user.save()
    print("Password updated to: 12345")
except User.DoesNotExist:
    user = User.objects.create_user(
        username='staff',
        password='12345',
        email='staff@auroramart.com',
        is_staff=True,
        is_superuser=False
    )
    print(f"Created staff user: {user.username}")
    print("Password: 12345")

print("\n✅ Staff account ready!")
print("   Username: staff")
print("   Password: 12345")
print("   Can access admin panel: Yes")
print("\n" + "=" * 50)
