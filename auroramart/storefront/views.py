from django.shortcuts import render


def home(request):
    """Temporary landing page placeholder."""
    return render(request, "storefront/home.html")
