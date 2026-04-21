from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import FileResponse, Http404
import os
import glob
import mimetypes


# --- PWA root-scoped files -------------------------------------------------
# Service workers must be served from the origin root to control the whole
# app. These views read the files out of staticfiles/ and serve them at `/`.

_PWA_ROOT_FILES = {
    'manifest.webmanifest': 'application/manifest+json',
    'sw.js': 'application/javascript',
    'registerSW.js': 'application/javascript',
    'favicon.ico': 'image/x-icon',
    'apple-touch-icon.png': 'image/png',
    'icon-192.png': 'image/png',
    'icon-512.png': 'image/png',
    'icon-maskable-512.png': 'image/png',
}


def _serve_pwa_file(request, filename):
    if filename not in _PWA_ROOT_FILES and not filename.startswith('workbox-'):
        raise Http404
    # Allow workbox-*.js from staticfiles too
    content_type = _PWA_ROOT_FILES.get(filename) or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    path = os.path.join(settings.BASE_DIR, 'staticfiles', filename)
    if not os.path.exists(path):
        raise Http404
    resp = FileResponse(open(path, 'rb'), content_type=content_type)
    # Let the SW itself never cache — always fetch a fresh copy.
    if filename == 'sw.js' or filename == 'registerSW.js':
        resp['Cache-Control'] = 'public, max-age=0, must-revalidate'
    return resp


def _serve_root_asset(request, asset_path):
    """Serve /assets/* from staticfiles/frontend/assets/ — the SW precache
    manifest emits root-relative asset URLs, so we mirror them at origin root."""
    if '..' in asset_path or asset_path.startswith('/'):
        raise Http404
    path = os.path.join(settings.BASE_DIR, 'staticfiles', 'frontend', 'assets', asset_path)
    if not os.path.exists(path):
        raise Http404
    content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    resp = FileResponse(open(path, 'rb'), content_type=content_type)
    resp['Cache-Control'] = 'public, max-age=31536000, immutable'
    return resp


def frontend_view(request):
    """Serve React frontend with dynamic asset paths."""
    static_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'frontend', 'assets')
    # Only inject the entry bundle — Vite's lazy chunks are imported dynamically at runtime.
    css_files = glob.glob(os.path.join(static_dir, 'index-*.css'))
    js_files = glob.glob(os.path.join(static_dir, 'index-*.js'))

    css_tags = ''
    for f in css_files:
        name = os.path.basename(f)
        css_tags += f'<link rel="stylesheet" crossorigin href="/static/frontend/assets/{name}">\n'

    js_tags = ''
    for f in js_files:
        name = os.path.basename(f)
        js_tags += f'<script type="module" crossorigin src="/static/frontend/assets/{name}"></script>\n'

    return render(request, 'index.html', {'css_tags': css_tags, 'js_tags': js_tags})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.spaces.urls')),
    path('api/', include('apps.proposals.urls')),
    path('api/', include('apps.bookings.urls')),
    path('api/', include('apps.reviews.urls')),
    path('api/', include('apps.events.urls')),
    path('api/', include('apps.follows.urls')),
    path('api/', include('apps.messaging.urls')),
    path('api/', include('apps.tickets.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/', include('apps.handovers.urls')),
    path('api/feed/', include('apps.feed.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# PWA root-scoped files (manifest, service worker, icons)
urlpatterns += [
    re_path(
        r'^(?P<filename>(manifest\.webmanifest|sw\.js|registerSW\.js|workbox-[^/]+\.js|favicon\.ico|apple-touch-icon\.png|icon-[^/]+\.png))$',
        _serve_pwa_file,
    ),
    # Root-level /assets/ mirror so SW precache URLs resolve
    re_path(r'^assets/(?P<asset_path>[^/]+)$', _serve_root_asset),
]

# Share Target — Android / desktop Chrome launches the PWA here when the user
# picks "CultureConnect" from the native share sheet. We just hand the data to
# the SPA, which routes to the appropriate receiver page.
urlpatterns += [path('share/', frontend_view)]

# Catch-all: serve React frontend for all non-API routes
urlpatterns += [re_path(r'^(?!api/|admin/|static/|media/|assets/).*$', frontend_view)]
