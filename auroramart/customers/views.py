from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import generic

from orders.models import Order

from .forms import (
    CustomerProfileForm,
    CustomerRegistrationForm,
    UserProfileUpdateForm,
)
from .models import CustomerProfile


def healthcheck(request):
    """Simple healthcheck placeholder for API wiring."""
    return JsonResponse({"status": "ok"})


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
            ctx["has_profile"] = True
        except CustomerProfile.DoesNotExist:
            ctx["profile_form"] = CustomerProfileForm()
            ctx["has_profile"] = False
        return ctx
    
    def post(self, request, *args, **kwargs):
        user_form = UserProfileUpdateForm(request.POST, instance=request.user)
        
        try:
            profile = request.user.customer_profile
            profile_form = CustomerProfileForm(request.POST, instance=profile)
        except CustomerProfile.DoesNotExist:
            profile_form = CustomerProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile = profile_form.save(commit=False)
            if not profile.user_id:
                profile.user = request.user
            profile.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("customers:profile")
        
        return render(
            request,
            self.template_name,
            {
                "user_form": user_form,
                "profile_form": profile_form,
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
        return Order.objects.filter(
            customer_email=self.request.user.email
        ).order_by("-created_at")


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
    """Staff view to list all customers (ADM-09)."""
    
    template_name = "staff/customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25
    
    def get_queryset(self):
        from django.contrib.auth.models import User
        
        queryset = User.objects.filter(is_staff=False).select_related("customer_profile").order_by("-date_joined")
        
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
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
        from django.contrib.auth.models import User
        return User.objects.filter(is_staff=False).select_related("customer_profile")
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["orders"] = Order.objects.filter(
            customer_email=self.object.email
        ).order_by("-created_at")[:10]
        return ctx


class StaffCustomerToggleActiveView(StaffRequiredMixin, generic.View):
    """Staff view to disable/enable customer accounts (ADM-11)."""
    
    def post(self, request, pk):
        from django.contrib.auth.models import User
        
        customer = get_object_or_404(User, pk=pk, is_staff=False)
        customer.is_active = not customer.is_active
        customer.save()
        
        status = "enabled" if customer.is_active else "disabled"
        messages.success(request, f"Customer account {customer.username} has been {status}.")
        return redirect("customers:staff_customer_detail", pk=pk)

