from django.http import JsonResponse


def healthcheck(request):
    """Simple healthcheck placeholder for API wiring."""
    return JsonResponse({"status": "ok"})
