from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import generic

from orders.models import Order

from .forms import (
    CustomerProfileForm,
    CustomerRegistrationForm,
    EmailAuthenticationForm,
    ShippingInfoForm,
    UserProfileUpdateForm,
)
from .models import CustomerProfile


def healthcheck(request):
    """Simple healthcheck placeholder for API wiring."""
    return JsonResponse({"status": "ok"})


class CustomerLoginView(generic.FormView):
    """Custom login view that accepts email instead of username."""
    
    template_name = "customers/login.html"
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy("storefront:home")
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("storefront:home")
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        
        # Handle 'next' redirect
        next_url = self.request.GET.get('next', '')
        if next_url:
            return redirect(next_url)
        return redirect(self.success_url)


class CustomerRegistrationView(generic.CreateView):
    """Customer registration view (CUST-01)."""
    
    template_name = "customers/register.html"
    form_class = CustomerRegistrationForm
    success_url = reverse_lazy("storefront:onboarding")
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Account created successfully! Complete your profile to get personalized recommendations.")
        return redirect(self.success_url)
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("storefront:home")
        return super().get(request, *args, **kwargs)


class CustomerProfileView(LoginRequiredMixin, generic.TemplateView):
    """Customer profile view and edit (CUST-04)."""
    
    template_name = "customers/profile.html"
    login_url = "customers:login"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user_form"] = UserProfileUpdateForm(instance=self.request.user)
        try:
            profile = self.request.user.customer_profile
            ctx["profile_form"] = CustomerProfileForm(instance=profile)
            ctx["shipping_form"] = ShippingInfoForm(instance=profile)
            ctx["has_profile"] = True
        except CustomerProfile.DoesNotExist:
            ctx["profile_form"] = CustomerProfileForm()
            ctx["shipping_form"] = ShippingInfoForm()
            ctx["has_profile"] = False
            # If user has onboarding category in session but no profile, suggest completing onboarding
            if self.request.session.get("onboarding_category"):
                messages.info(
                    self.request,
                    "Complete your profile by filling in the personal information below, or "
                    "<a href='{}'>complete onboarding again</a> to auto-fill your data.".format(
                        reverse("storefront:onboarding")
                    ),
                    extra_tags="safe"
                )
            else:
                messages.info(
                    self.request,
                    "Please fill in your personal information below to complete your profile."
                )
        return ctx
    
    def post(self, request, *args, **kwargs):
        user_form = UserProfileUpdateForm(request.POST, instance=request.user)
        
        try:
            profile = request.user.customer_profile
            profile_form = CustomerProfileForm(request.POST, instance=profile)
            shipping_form = ShippingInfoForm(request.POST, instance=profile)
        except CustomerProfile.DoesNotExist:
            profile_form = CustomerProfileForm(request.POST)
            shipping_form = ShippingInfoForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid() and shipping_form.is_valid():
            user_form.save()
            profile = profile_form.save(commit=False)
            if not profile.user_id:
                profile.user = request.user
            profile.save()
            # Save shipping information
            shipping_form.instance = profile
            shipping_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("customers:profile")
        
        return render(
            request,
            self.template_name,
            {
                "user_form": user_form,
                "profile_form": profile_form,
                "shipping_form": shipping_form,
                "has_profile": hasattr(request.user, "customer_profile"),
            },
        )


class OrderHistoryView(LoginRequiredMixin, generic.ListView):
    """Customer order history view (CUST-05)."""
    
    template_name = "customers/order_history.html"
    context_object_name = "orders"
    login_url = "customers:login"
    paginate_by = 10
    
    def get_queryset(self):
        # Get the customer profile for the logged-in user
        try:
            profile = self.request.user.customer_profile
            return Order.objects.filter(customer=profile).order_by("-created_at")
        except CustomerProfile.DoesNotExist:
            return Order.objects.none()


class DeleteAccountView(LoginRequiredMixin, generic.View):
    """Allow customers to delete their own account."""
    
    login_url = "customers:login"
    
    def post(self, request):
        user = request.user
        
        # Prevent staff from deleting their account through this view
        if user.is_staff:
            messages.error(request, "Staff accounts cannot be deleted through this page.")
            return redirect("customers:profile")
        
        # Get user's profile if it exists
        try:
            profile = user.customer_profile
        except CustomerProfile.DoesNotExist:
            profile = None
        
        # Set orders.customer to NULL before deletion (since Order has PROTECT)
        # This preserves order history but removes the link to the user
        if profile:
            Order.objects.filter(customer=profile).update(customer=None)
        
        # Store username for message
        username = user.username
        
        # Delete the user (this will cascade delete the CustomerProfile due to CASCADE)
        user.delete()
        
        # Log out the user
        logout(request)
        
        messages.success(request, f"Your account ({username}) has been permanently deleted.")
        return redirect("storefront:home")


# Staff-only views for customer management (ADM-09, ADM-10, ADM-11)

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Ensure the user is authenticated and marked as staff."""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have access to staff tools.")
            return redirect("storefront:home")
        return super().handle_no_permission()


class StaffCustomerListView(StaffRequiredMixin, generic.ListView):
    """Staff view to list all customers from CSV data (ADM-09)."""
    
    template_name = "staff/customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25
    
    def get_queryset(self):
        queryset = CustomerProfile.objects.select_related("user", "preferred_category").order_by("-created_at")
        
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(gender__icontains=search)
                | Q(occupation__icontains=search)
                | Q(employment_status__icontains=search)
                | Q(education__icontains=search)
                | Q(preferred_category_label__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class StaffCustomerDetailView(StaffRequiredMixin, generic.DetailView):
    """Staff view to see customer profile and order history (ADM-10)."""
    
    template_name = "staff/customers/customer_detail.html"
    context_object_name = "customer"
    
    def get_queryset(self):
        return CustomerProfile.objects.select_related("user", "preferred_category")
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Get orders for this customer profile
        ctx["orders"] = Order.objects.filter(
            customer=self.object
        ).order_by("-created_at")[:10]
        return ctx


class StaffCustomerToggleActiveView(StaffRequiredMixin, generic.View):
    """Staff view to disable/enable customer accounts (ADM-11). Only works if User account is linked."""
    
    def post(self, request, pk):
        profile = get_object_or_404(CustomerProfile, pk=pk)
        
        if not profile.user:
            messages.error(request, "This customer profile does not have a linked user account.")
            return redirect("customers:staff_customer_detail", pk=pk)
        
        if profile.user.is_staff:
            messages.error(request, "Cannot modify staff accounts.")
            return redirect("customers:staff_customer_detail", pk=pk)
        
        profile.user.is_active = not profile.user.is_active
        profile.user.save()
        
        status = "enabled" if profile.user.is_active else "disabled"
        messages.success(request, f"Customer account {profile.user.username} has been {status}.")
        return redirect("customers:staff_customer_detail", pk=pk)


class StaffCustomerDeleteView(StaffRequiredMixin, generic.View):
    """Staff view to delete customer profiles from the system."""
    
    def post(self, request, pk):
        profile = get_object_or_404(CustomerProfile, pk=pk)
        
        # Prevent deletion of staff accounts
        if profile.user and profile.user.is_staff:
            messages.error(request, "Cannot delete staff accounts.")
            return redirect("customers:staff_customer_detail", pk=pk)
        
        customer_name = ""
        if profile.user:
            if profile.user.first_name or profile.user.last_name:
                customer_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
            else:
                customer_name = profile.user.username
            # Delete the associated user account if it exists
            profile.user.delete()
        else:
            customer_name = f"Customer #{profile.pk}"
        
        # Delete the profile (user deletion will cascade if linked)
        profile.delete()
        
        messages.success(request, f"Customer {customer_name} has been removed from the system.")
        return redirect("customers:staff_customer_list")

