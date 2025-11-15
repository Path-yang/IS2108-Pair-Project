import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View, generic
from django.views.decorators.http import require_POST

from catalog.models import Product, ProductCategory
from customers.models import CustomerProfile
from orders import services as order_services
from recommendations.services import (
    predict_preferred_category,
    recommend_associated_products,
)

logger = logging.getLogger(__name__)

from .forms import (
    AddToCartForm,
    OnboardingForm,
    PaymentForm,
    ProductFilterForm,
    ShippingAddressForm,
    UpdateCartForm,
)


class HomeView(generic.TemplateView):
    template_name = "storefront/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Check if ML recommendations are enabled
        show_recommendations = self.request.session.get('show_recommendations', False)
        ctx["show_recommendations"] = show_recommendations

        # Get onboarding category from session, or fallback to user's profile if available
        onboarding_category = self.request.session.get('onboarding_category')
        if not onboarding_category and self.request.user.is_authenticated:
            try:
                profile = self.request.user.customer_profile
                if profile and profile.preferred_category_label:
                    onboarding_category = profile.preferred_category_label
                    # Restore it to session for consistency
                    self.request.session['onboarding_category'] = onboarding_category
            except CustomerProfile.DoesNotExist:
                pass
        
        ctx["onboarding_category"] = onboarding_category

        # Always show featured categories
        ctx["featured_categories"] = ProductCategory.objects.annotate(
            product_count=Count("products")
        ).order_by("-product_count")[:6]

        if show_recommendations and onboarding_category:
            # Show personalized recommendations based on predicted category
            predicted_category = ProductCategory.objects.filter(
                name__iexact=onboarding_category
            ).first()

            if predicted_category:
                ctx["predicted_category"] = predicted_category
                ctx["recommended_products"] = (
                    Product.objects.filter(is_active=True, category=predicted_category)
                    .order_by("-product_rating", "-quantity_on_hand")[:8]
                )
            else:
                # Fallback to trending if category not found
                ctx["recommended_products"] = (
                    Product.objects.filter(is_active=True)
                    .order_by("-product_rating", "-quantity_on_hand")[:8]
                )
        else:
            # Show generic trending products
            ctx["trending_products"] = (
                Product.objects.filter(is_active=True)
                .order_by("-product_rating", "-quantity_on_hand")[:8]
            )

        # Always show new arrivals
        ctx["new_arrivals"] = (
            Product.objects.filter(is_active=True).order_by("-created_at")[:6]
        )
        return ctx


@require_POST
def toggle_recommendations(request):
    """Toggle ML recommendation mode on/off."""
    current_state = request.session.get('show_recommendations', False)
    new_state = not current_state
    request.session['show_recommendations'] = new_state

    return JsonResponse({
        'success': True,
        'show_recommendations': new_state,
        'message': 'Recommendations enabled' if new_state else 'Showing all products'
    })


class OnboardingView(generic.FormView):
    template_name = "storefront/onboarding.html"
    form_class = OnboardingForm

    def form_valid(self, form):
        onboarding_data = form.cleaned_data
        category_label = predict_preferred_category(onboarding_data)
        category = None
        if category_label:
            category = ProductCategory.objects.filter(name__iexact=category_label).first()
            self.request.session["onboarding_category"] = category_label
            # Automatically enable recommendations after onboarding
            self.request.session["show_recommendations"] = True
            if category:
                messages.success(
                    self.request,
                    f"We think you'll love browsing {category.name}.",
                )
        
        # Create or update CustomerProfile with onboarding data
        if self.request.user.is_authenticated:
            profile, created = CustomerProfile.objects.update_or_create(
                user=self.request.user,
                defaults={
                    "age": onboarding_data["age"],
                    "gender": onboarding_data["gender"],
                    "employment_status": onboarding_data["employment_status"],
                    "occupation": onboarding_data["occupation"],
                    "education": onboarding_data["education"],
                    "household_size": onboarding_data["household_size"],
                    "has_children": onboarding_data.get("has_children", False),
                    "monthly_income_sgd": onboarding_data["monthly_income_sgd"],
                    "preferred_category_label": category_label or "",
                    "preferred_category": category,
                }
            )
        
        if not category_label:
            messages.info(
                self.request, "Thanks! We'll show you our most popular products."
            )
        url = reverse("storefront:product_list")
        if category:
            url += f"?category={category.id}&highlight={category.name.replace(' ', '+')}"
        elif category_label:
            url += f"?highlight={category_label.replace(' ', '+')}"
        return redirect(url)


class ProductListView(generic.ListView):
    template_name = "storefront/product_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("category", "subcategory")
            .filter(is_active=True)
            .order_by("name")
        )

        # Check if ML recommendations are enabled
        show_recommendations = self.request.session.get('show_recommendations', False)
        onboarding_category = self.request.session.get('onboarding_category')

        # If recommendations enabled and category exists, filter by predicted category
        if show_recommendations and onboarding_category:
            predicted_category = ProductCategory.objects.filter(
                name__iexact=onboarding_category
            ).first()
            if predicted_category:
                queryset = queryset.filter(category=predicted_category)

        self.filter_form = ProductFilterForm(self.request.GET or None)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("q"):
                queryset = queryset.filter(
                    Q(name__icontains=data["q"])
                    | Q(description__icontains=data["q"])
                    | Q(sku__icontains=data["q"])
                )
            if data.get("category"):
                queryset = queryset.filter(category=data["category"])
            if data.get("subcategory"):
                queryset = queryset.filter(subcategory=data["subcategory"])
            if data.get("sort"):
                queryset = queryset.order_by(data["sort"])
        highlight = self.request.GET.get("highlight")
        if highlight:
            queryset = queryset.order_by(
                "-category__name", "name"
            )  # surface highlight results early
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        highlight = self.request.GET.get("highlight")
        if highlight:
            highlight = highlight.replace("+", " ")
        ctx["highlight_category"] = highlight

        # Pass toggle state and onboarding data to template
        show_recommendations = self.request.session.get('show_recommendations', False)
        ctx["show_recommendations"] = show_recommendations
        
        # Get onboarding category from session, or fallback to user's profile if available
        onboarding_category = self.request.session.get('onboarding_category')
        if not onboarding_category and self.request.user.is_authenticated:
            try:
                profile = self.request.user.customer_profile
                if profile and profile.preferred_category_label:
                    onboarding_category = profile.preferred_category_label
                    # Restore it to session for consistency
                    self.request.session['onboarding_category'] = onboarding_category
            except CustomerProfile.DoesNotExist:
                pass
        
        ctx["onboarding_category"] = onboarding_category

        # Add "Next best action" recommendations to nudge exploration
        # ONLY show when filters are applied (category, subcategory, or search)
        page_products = list(ctx['products'])
        
        # Check if any filters are actually applied
        filters_applied = False
        current_category = None
        current_subcategory = None
        search_query = None
        
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            current_category = data.get("category")
            current_subcategory = data.get("subcategory")
            search_query = data.get("q")
            
            # Check if any filter is actually set
            if current_category or current_subcategory or search_query:
                filters_applied = True
        
        # Also check URL parameters directly (for category links from home page)
        if not filters_applied:
            if self.request.GET.get("category"):
                filters_applied = True
                if not current_category:
                    try:
                        current_category = ProductCategory.objects.get(pk=self.request.GET.get("category"))
                    except (ProductCategory.DoesNotExist, ValueError):
                        pass
        
        if page_products and filters_applied:
            # Use all products from current page for recommendations
            all_page_skus = [p.sku for p in page_products]
            
            # Debug: Log the SKUs being used (first 10 for debugging)
            logger.info(f"Explore Other Categories - Page has {len(all_page_skus)} products. First 10 SKUs: {all_page_skus[:10]}")
            
            # If no category filter from form, check if all products are from same category
            if not current_category and page_products:
                categories = {p.category for p in page_products}
                if len(categories) == 1:
                    current_category = list(categories)[0]
            
            # Strategy for "nudge exploration": Show products from OTHER categories
            if current_category:
                # User is viewing a specific category - show products from OTHER categories
                # Get MORE recommendations initially (12) so we have enough after filtering by category
                next_best = recommend_associated_products(all_page_skus, limit=12, context_products=page_products)
                logger.info(f"Got {len(next_best)} recommendations before category filter. Recommended SKUs: {[p.sku for p in next_best]}")
                logger.info(f"Current category: {current_category.name if current_category else None}")
                
                # Filter to show products from OTHER categories (to encourage exploration)
                next_best = [p for p in next_best if p.category != current_category]
                logger.info(f"After category filter: {len(next_best)} recommendations. SKUs: {[p.sku for p in next_best]}")
                
                # If we don't have enough cross-category recommendations, add diverse products from other categories
                if len(next_best) < 4:
                    # Use page products to create variety - hash the SKUs to get consistent but different results per page
                    import hashlib
                    page_hash = int(hashlib.md5(','.join(sorted(all_page_skus)).encode()).hexdigest()[:8], 16)
                    
                    # Get count of available products for offset calculation
                    from django.db.models import Count
                    total_count = Product.objects.filter(
                        is_active=True
                    ).exclude(
                        category=current_category
                    ).exclude(
                        sku__in=[p.sku for p in next_best] + all_page_skus
                    ).count()
                    
                    if total_count > 0:
                        # Use hash to select different starting point for variety (max offset of 50)
                        offset = min(page_hash % total_count, 50)
                        
                        # Get products with offset to vary selection based on page
                        queryset = Product.objects.filter(
                            is_active=True
                        ).exclude(
                            category=current_category
                        ).exclude(
                            sku__in=[p.sku for p in next_best] + all_page_skus
                        ).order_by("category", "-product_rating", "-quantity_on_hand", "-created_at")
                        
                        # Try with offset first
                        additional = list(queryset[offset:offset + 20])
                        if len(additional) < 10:
                            # If not enough, also try from beginning
                            additional.extend(list(queryset[:20]))
                        
                        # Take diverse products from different categories
                        seen_categories = {p.category for p in next_best}
                        diverse_products = []
                        for p in additional:
                            if p.category not in seen_categories or len(diverse_products) < (4 - len(next_best)):
                                diverse_products.append(p)
                                seen_categories.add(p.category)
                            if len(diverse_products) >= (4 - len(next_best)):
                                break
                        next_best.extend(diverse_products)
                
                # Limit to 4 for display
                next_best = next_best[:4]
            else:
                # No specific category but filters applied (e.g., search query) - use association rules
                next_best = recommend_associated_products(all_page_skus, limit=4, context_products=page_products)
            
            # If ML recommendations are ON, we can still respect it but prioritize exploration
            if show_recommendations and self.request.session.get('onboarding_category'):
                predicted_category = ProductCategory.objects.filter(
                    name__iexact=self.request.session.get('onboarding_category')
                ).first()
                
                # If viewing predicted category, still show other categories for exploration
                # If viewing other categories, prioritize predicted category products
                if predicted_category:
                    if current_category == predicted_category:
                        # Already viewing predicted category - show other categories (exploration)
                        next_best = [p for p in next_best if p.category != predicted_category]
                    else:
                        # Viewing other category - show predicted category products (personalization)
                        predicted_products = [
                            p for p in next_best if p.category == predicted_category
                        ]
                        if predicted_products:
                            next_best = predicted_products[:4]
                        else:
                            # Add predicted category products if not in recommendations
                            additional = (
                                Product.objects.filter(
                                    is_active=True,
                                    category=predicted_category
                                )
                                .exclude(sku__in=[p.sku for p in next_best] + all_page_skus)
                                .order_by("-product_rating", "-quantity_on_hand")[:4 - len(next_best)]
                            )
                            next_best = list(additional)[:4]
            
            ctx["next_best_action"] = next_best
            ctx["current_category"] = current_category  # Pass to template for conditional display
        else:
            # No filters applied - don't show next best action
            ctx["next_best_action"] = None
            ctx["current_category"] = None

        return ctx


class ProductDetailView(View):
    template_name = "storefront/product_detail.html"

    def get(self, request, sku):
        from catalog.forms import ReviewForm
        from catalog.models import Review
        
        product = get_object_or_404(
            Product.objects.select_related("category", "subcategory"),
            sku=sku,
            is_active=True,
        )
        form = AddToCartForm()
        form.fields["quantity"].widget.attrs["max"] = max(product.quantity_on_hand, 1)
        recommendations = recommend_associated_products([product.sku], limit=4, context_products=[product])
        
        # Get reviews for this product
        reviews = Review.objects.filter(product=product).select_related("user").order_by("-created_at")
        
        # Check if current user has already reviewed
        user_review = None
        if request.user.is_authenticated:
            user_review = reviews.filter(user=request.user).first()
        
        # Review form for authenticated users who haven't reviewed yet
        review_form = ReviewForm() if request.user.is_authenticated and not user_review else None
        
        return render(
            request,
            self.template_name,
            {
                "product": product,
                "form": form,
                "recommendations": recommendations,
                "reviews": reviews,
                "user_review": user_review,
                "review_form": review_form,
            },
        )

    def post(self, request, sku):
        product = get_object_or_404(
            Product.objects.select_related("category", "subcategory"),
            sku=sku,
            is_active=True,
        )
        form = AddToCartForm(request.POST)
        form.fields["quantity"].widget.attrs["max"] = max(product.quantity_on_hand, 1)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            if quantity > product.quantity_on_hand:
                form.add_error("quantity", f"Only {product.quantity_on_hand} units available in stock.")
            else:
                basket = order_services.get_or_create_session_basket(request)
                order_services.add_product_to_basket(basket, product, quantity)
                messages.success(request, f"{product.name} added to your cart.")
                return redirect("storefront:cart")
        recommendations = recommend_associated_products([product.sku], limit=4, context_products=[product])
        return render(
            request,
            self.template_name,
            {"product": product, "form": form, "recommendations": recommendations},
        )


class CartView(View):
    template_name = "storefront/cart.html"

    def get(self, request):
        basket = order_services.get_or_create_session_basket(request)
        items = basket.items.select_related("product")
        recommendations = None
        # Only show "Complete the set" recommendations if cart has items
        if items.exists():
            item_products = [item.product for item in items]
            recommendations = recommend_associated_products(
                [item.product.sku for item in items], limit=4, context_products=item_products
            )
        update_form = UpdateCartForm()
        return render(
            request,
            self.template_name,
            {
                "basket": basket,
                "items": items,
                "recommendations": recommendations,
                "update_form": update_form,
            },
        )

    def post(self, request):
        # Check if this is an add to cart request from "Complete the set"
        if "add_product_sku" in request.POST:
            sku = request.POST.get("add_product_sku")
            try:
                product = Product.objects.get(sku=sku, is_active=True)
                if product.quantity_on_hand > 0:
                    basket = order_services.get_or_create_session_basket(request)
                    order_services.add_product_to_basket(basket, product, quantity=1)
                    messages.success(request, f"{product.name} added to your cart.")
                else:
                    messages.error(request, f"{product.name} is out of stock.")
            except Product.DoesNotExist:
                messages.error(request, "Product not found.")
            return redirect("storefront:cart")
        
        # Check if this is a delete request
        if "delete_item" in request.POST:
            item_id = request.POST.get("line_id")
            if item_id:
                try:
                    item_id = int(item_id)
                    if order_services.remove_basket_item(item_id):
                        messages.success(request, "Item removed from cart.")
                    else:
                        messages.error(request, "Unable to remove item.")
                except (ValueError, TypeError):
                    messages.error(request, "Invalid item.")
            return redirect("storefront:cart")
        
        # Otherwise, it's an update request
        form = UpdateCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            if quantity == 0:
                # If quantity is 0, remove the item
                if order_services.remove_basket_item(form.cleaned_data["line_id"]):
                    messages.success(request, "Item removed from cart.")
            else:
                order_services.update_basket_item(
                    form.cleaned_data["line_id"], form.cleaned_data["quantity"]
                )
                messages.success(request, "Cart updated.")
        return redirect("storefront:cart")


class ShippingView(LoginRequiredMixin, View):
    template_name = "storefront/checkout_shipping.html"
    form_class = ShippingAddressForm
    login_url = "customers:login"

    def get(self, request):
        initial = request.session.get("checkout_shipping", {})
        form = self.form_class(initial=initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            request.session["checkout_shipping"] = form.cleaned_data
            return redirect("storefront:checkout_payment")
        return render(request, self.template_name, {"form": form})


class PaymentView(LoginRequiredMixin, View):
    template_name = "storefront/checkout_payment.html"
    form_class = PaymentForm
    login_url = "customers:login"

    def get(self, request):
        initial = request.session.get("checkout_payment", {})
        form = self.form_class(initial=initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            payment_data = form.cleaned_data.copy()
            payment_data["card_number"] = str(payment_data["card_number"])
            payment_data["cvv"] = "***"
            request.session["checkout_payment"] = payment_data
            return redirect("storefront:checkout_review")
        return render(request, self.template_name, {"form": form})


class ReviewView(LoginRequiredMixin, View):
    template_name = "storefront/checkout_review.html"
    login_url = "customers:login"

    def get(self, request):
        basket = order_services.get_or_create_session_basket(request)
        if not basket.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("storefront:product_list")
        context = {
            "basket": basket,
            "items": basket.items.select_related("product"),
            "shipping": request.session.get("checkout_shipping", {}),
            "payment": request.session.get("checkout_payment", {}),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        basket = order_services.get_or_create_session_basket(request)
        shipping = request.session.get("checkout_shipping")
        payment = request.session.get("checkout_payment")
        if not (shipping and payment):
            messages.error(request, "Please complete the checkout steps.")
            return redirect("storefront:checkout_shipping")
        order = order_services.convert_basket_to_order(basket, shipping, payment)
        order_services.clear_basket_session(request)
        request.session["checkout_shipping"] = shipping
        request.session["last_order_number"] = order.order_number if order else ""
        return redirect("storefront:checkout_complete")


class ConfirmationView(LoginRequiredMixin, generic.TemplateView):
    template_name = "storefront/checkout_complete.html"
    login_url = "customers:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["shipping"] = self.request.session.pop("checkout_shipping", {})
        ctx["order_number"] = self.request.session.pop("last_order_number", "")
        self.request.session.pop("checkout_payment", None)
        return ctx
