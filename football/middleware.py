from django.conf import settings


class FootballHostMiddleware:
    """Route only the football hostname to its own homepage, not the main site."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = request.get_host().split(':', 1)[0].lower()
        if hostname in settings.FOOTBALL_SITE_HOSTS:
            request.urlconf = 'football.site_urls'
        return self.get_response(request)
