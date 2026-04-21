from django.utils.deprecation import MiddlewareMixin


class MarketplaceMiddleware(MiddlewareMixin):
    """Resolve the current tenant from request headers / Origin.

    Order of resolution:
      1. X-Marketplace header (slug)
      2. Origin/Host domain → Marketplace.domain match
      3. Fallback: first active marketplace (default tenant, usually 'caftania')

    The resolved Marketplace instance is attached as `request.marketplace`.
    Never raises — if nothing matches, `request.marketplace` is None and
    legacy endpoints keep working as before.
    """

    def process_request(self, request):
        # Import lazily so django app loading never deadlocks
        try:
            from .models import Marketplace
        except Exception:
            request.marketplace = None
            return None

        marketplace = None

        slug = request.META.get('HTTP_X_MARKETPLACE', '').strip().lower()
        if slug:
            marketplace = Marketplace.objects.filter(slug=slug, is_active=True).first()

        if marketplace is None:
            origin = request.META.get('HTTP_ORIGIN', '') or request.META.get('HTTP_HOST', '')
            if origin:
                host = origin.replace('https://', '').replace('http://', '').split('/')[0].split(':')[0]
                if host:
                    marketplace = Marketplace.objects.filter(
                        domain__iexact=host, is_active=True
                    ).first()

        if marketplace is None:
            marketplace = Marketplace.objects.filter(is_active=True).order_by('id').first()

        request.marketplace = marketplace
        return None
