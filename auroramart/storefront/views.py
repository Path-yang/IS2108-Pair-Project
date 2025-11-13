from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View, generic
from django.views.decorators.http import require_POST

from catalog.models import Product, ProductCategory
from orders import services as order_services
from recommendations.services import (
    predict_preferred_category,
    recommend_associated_products,
)

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

        # Get onboarding data from session
        onboarding_category = self.request.session.get('onboarding_category')
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
            if category:
                messages.success(
                    self.request,
                    f"We think you'll love browsing {category.name}.",
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
        ctx["onboarding_category"] = self.request.session.get('onboarding_category')

        # Add "Next best action" recommendations based on current page products
        # Get ALL products from current page (up to 20 due to pagination)
        # This ensures different pages give different recommendations
        page_products = list(ctx['products'])

        if page_products:
            # Use ALL product SKUs from the current page
            # Now that services.py processes all SKUs, this provides maximum variety
            current_page_skus = [product.sku for product in page_products]

            # Get association rule recommendations
            next_best = recommend_associated_products(current_page_skus, limit=4)

            # If show_recommendations is ON, further filter by predicted category
            # This combines both models: decision tree filters, association rules recommend
            if show_recommendations and self.request.session.get('onboarding_category'):
                predicted_category = ProductCategory.objects.filter(
                    name__iexact=self.request.session.get('onboarding_category')
                ).first()

                if predicted_category:
                    # Filter next_best to only include products from predicted category
                    next_best = [p for p in next_best if p.category == predicted_category]

                    # If we filtered out too many, get more from that category
                    if len(next_best) < 4:
                        additional = (
                            Product.objects.filter(
                                is_active=True,
                                category=predicted_category
                            )
                            .exclude(sku__in=[p.sku for p in next_best] + current_page_skus)
                            .order_by("-product_rating", "-quantity_on_hand")[:4 - len(next_best)]
                        )
                        next_best.extend(list(additional))

            ctx["next_best_action"] = next_best

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
        recommendations = recommend_associated_products([product.sku], limit=4)
        
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
        recommendations = recommend_associated_products([product.sku], limit=4)
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
        recommendations = recommend_associated_products(
            [item.product.sku for item in items], limit=4
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
        form = UpdateCartForm(request.POST)
        if form.is_valid():
            order_services.update_basket_item(
                form.cleaned_data["line_id"], form.cleaned_data["quantity"]
            )
            messages.success(request, "Cart updated.")
        return redirect("storefront:cart")


class ShippingView(View):
    template_name = "storefront/checkout_shipping.html"
    form_class = ShippingAddressForm

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


class PaymentView(View):
    template_name = "storefront/checkout_payment.html"
    form_class = PaymentForm

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


class ReviewView(View):
    template_name = "storefront/checkout_review.html"

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


class ConfirmationView(generic.TemplateView):
    template_name = "storefront/checkout_complete.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["shipping"] = self.request.session.pop("checkout_shipping", {})
        ctx["order_number"] = self.request.session.pop("last_order_number", "")
        self.request.session.pop("checkout_payment", None)
        return ctx
