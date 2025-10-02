from django.http import HttpResponse


def home_view(request):
    """Simple home view that returns a welcome message"""
    return HttpResponse(
        "<h1>Welcome to HomeSer Backend API</h1><p>Visit <a href='/api/schema/swagger-ui/'>API Documentation</a> for available endpoints.</p>"
    )


def favicon_view(request):
    """Simple favicon view that returns an empty response"""
    return HttpResponse(status=404)  # Return 404 if no actual favicon
