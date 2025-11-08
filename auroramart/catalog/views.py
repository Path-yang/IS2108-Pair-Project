import csv
import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View, generic

from customers.models import CustomerProfile
from orders.models import Order

from .forms import (
    CatalogUploadForm,
    ProductCategoryForm,
    ProductForm,
    ProductSubcategoryForm,
    ReviewForm,
)
from .models import Product, ProductCategory, ProductSubcategory, Review


def healthcheck(request):
    """Simple healthcheck placeholder for API wiring."""
    return JsonResponse({"status": "ok"})


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Ensure the user is authenticated and marked as staff."""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have access to staff tools.")
            return redirect("storefront:home")
        return super().handle_no_permission()


class StaffDashboardView(StaffRequiredMixin, generic.TemplateView):
    """Staff dashboard with key statistics (ADM-13)."""
    
    template_name = "staff/dashboard.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Product statistics
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        low_stock_products = Product.objects.filter(
            quantity_on_hand__lte=F("reorder_quantity"),
            is_active=True
        ).count()
        
        # Customer statistics
        from django.contrib.auth.models import User
        total_customers = User.objects.filter(is_staff=False).count()
        customers_with_profiles = CustomerProfile.objects.filter(user__isnull=False).count()
        
        # Order statistics
        total_orders = Order.objects.count()
        recent_orders = Order.objects.order_by("-created_at")[:5]
        
        # Category breakdown
        category_stats = ProductCategory.objects.annotate(
            product_count=Count("products")
        ).order_by("-product_count")[:5]
        
        ctx.update({
            "total_products": total_products,
            "active_products": active_products,
            "low_stock_products": low_stock_products,
            "total_customers": total_customers,
            "customers_with_profiles": customers_with_profiles,
            "total_orders": total_orders,
            "recent_orders": recent_orders,
            "top_categories": category_stats,
        })
        
        return ctx


class ProductListView(StaffRequiredMixin, generic.ListView):
    template_name = "staff/catalog/product_list.html"
    model = Product
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("category", "subcategory")
            .annotate(
                inventory_status=F("quantity_on_hand") - F("reorder_quantity"),
            )
            .order_by("name")
        )

        search = self.request.GET.get("q")
        category_id = self.request.GET.get("category")
        show_inactive = self.request.GET.get("show_inactive") == "1"

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(sku__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if not show_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ProductCategory.objects.all()
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["selected_category"] = self.request.GET.get("category") or ""
        ctx["show_inactive"] = self.request.GET.get("show_inactive") == "1"
        ctx["low_stock_count"] = Product.objects.filter(
            quantity_on_hand__lte=F("reorder_quantity")
        ).count()
        return ctx


class ProductCreateView(StaffRequiredMixin, generic.CreateView):
    template_name = "staff/catalog/product_form.html"
    form_class = ProductForm
    success_url = reverse_lazy("catalog:product_list")

    def form_valid(self, form):
        messages.success(self.request, "Product added to catalogue.")
        return super().form_valid(form)


class ProductUpdateView(StaffRequiredMixin, generic.UpdateView):
    template_name = "staff/catalog/product_form.html"
    form_class = ProductForm
    model = Product
    success_url = reverse_lazy("catalog:product_list")

    def form_valid(self, form):
        messages.success(self.request, "Product details updated.")
        return super().form_valid(form)


class ProductDeactivateView(StaffRequiredMixin, View):
    """Soft delete by setting is_active to False."""

    def post(self, request, pk):
        product = Product.objects.get(pk=pk)
        product.is_active = False
        product.save(update_fields=["is_active"])
        messages.warning(request, f"{product.name} marked as inactive.")
        return redirect("catalog:product_list")


class ProductReactivateView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = Product.objects.get(pk=pk)
        product.is_active = True
        product.save(update_fields=["is_active"])
        messages.success(request, f"{product.name} reactivated.")
        return redirect("catalog:product_list")


class LowStockListView(StaffRequiredMixin, generic.ListView):
    template_name = "staff/catalog/low_stock_list.html"
    context_object_name = "products"

    def get_queryset(self):
        return (
            Product.objects.select_related("category", "subcategory")
            .filter(quantity_on_hand__lte=F("reorder_quantity"))
            .order_by("quantity_on_hand")
        )


class CatalogUploadView(StaffRequiredMixin, generic.FormView):
    template_name = "staff/catalog/catalog_upload.html"
    form_class = CatalogUploadForm
    success_url = reverse_lazy("catalog:product_list")

    def form_valid(self, form):
        file = form.cleaned_data["file"]
        decoded = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        created = 0
        updated = 0

        for row in reader:
            category, _ = ProductCategory.objects.get_or_create(
                name=row["Product Category"].strip()
            )
            subcategory, _ = ProductSubcategory.objects.get_or_create(
                category=category,
                name=row["Product Subcategory"].strip(),
            )
            product, created_flag = Product.objects.update_or_create(
                sku=row["SKU code"].strip(),
                defaults={
                    "name": row["Product name"].strip(),
                    "description": row["Product description"].strip(),
                    "category": category,
                    "subcategory": subcategory,
                    "unit_price": Decimal(str(row.get("Unit price") or 0)),
                    "product_rating": (
                        Decimal(str(row.get("Product rating")))
                        if row.get("Product rating")
                        else None
                    ),
                    "quantity_on_hand": int(row.get("Quantity on hand") or 0),
                    "reorder_quantity": int(row.get("Reorder Quantity") or 0),
                    "is_active": True,
                },
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        messages.success(
            self.request,
            f"Catalogue import complete. Created {created}, updated {updated}.",
        )
        return super().form_valid(form)


class CategoryManagementView(StaffRequiredMixin, generic.TemplateView):
    template_name = "staff/catalog/category_management.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = (
            ProductCategory.objects.prefetch_related("subcategories").order_by("name")
        )
        ctx["category_form"] = ProductCategoryForm()
        ctx["subcategory_form"] = ProductSubcategoryForm()
        return ctx

    def post(self, request, *args, **kwargs):
        if "category_submit" in request.POST:
            form = ProductCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Category added.")
            else:
                messages.error(request, "Unable to add category.")
        elif "subcategory_submit" in request.POST:
            form = ProductSubcategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Subcategory added.")
            else:
                messages.error(request, "Unable to add subcategory.")
        return redirect("catalog:category_management")


class ProductExportView(StaffRequiredMixin, View):
    """Export all products to CSV (ADM-14)."""
    
    def get(self, request):
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="auroramart_products_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            "SKU Code",
            "Product Name",
            "Description",
            "Category",
            "Subcategory",
            "Unit Price",
            "Product Rating",
            "Quantity on Hand",
            "Reorder Quantity",
            "Active Status"
        ])
        
        products = Product.objects.select_related("category", "subcategory").order_by("sku")
        
        for product in products:
            writer.writerow([
                product.sku,
                product.name,
                product.description,
                product.category.name if product.category else "",
                product.subcategory.name if product.subcategory else "",
                product.unit_price,
                product.product_rating if product.product_rating else "",
                product.quantity_on_hand,
                product.reorder_quantity,
                "Active" if product.is_active else "Inactive"
            ])
        
        return response


# Review views (CUST-07, CUST-08)

class ReviewCreateView(LoginRequiredMixin, View):
    """Create a review for a product (CUST-07)."""
    
    login_url = "customers:login"
    
    def post(self, request, product_pk):
        from django.shortcuts import get_object_or_404
        
        product = get_object_or_404(Product, pk=product_pk, is_active=True)
        form = ReviewForm(request.POST)
        
        if form.is_valid():
            # Check if user already reviewed this product
            existing_review = Review.objects.filter(
                product=product,
                user=request.user
            ).first()
            
            if existing_review:
                messages.warning(request, "You have already reviewed this product. You can edit your existing review.")
            else:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                messages.success(request, "Thank you for your review!")
        else:
            messages.error(request, "Unable to submit review. Please check your rating.")
        
        return redirect("storefront:product_detail", pk=product_pk)


class ReviewUpdateView(LoginRequiredMixin, View):
    """Edit a review (CUST-08)."""
    
    login_url = "customers:login"
    
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        
        review = get_object_or_404(Review, pk=pk, user=request.user)
        form = ReviewForm(request.POST, instance=review)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated successfully!")
        else:
            messages.error(request, "Unable to update review.")
        
        return redirect("storefront:product_detail", pk=review.product.pk)


class ReviewDeleteView(LoginRequiredMixin, View):
    """Delete a review (CUST-08)."""
    
    login_url = "customers:login"
    
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        
        review = get_object_or_404(Review, pk=pk, user=request.user)
        product_pk = review.product.pk
        review.delete()
        messages.success(request, "Review deleted successfully.")
        
        return redirect("storefront:product_detail", pk=product_pk)


