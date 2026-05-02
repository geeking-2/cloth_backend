"""Media upload endpoint for Caftania.

POST /api/uploads/ accepts multipart/form-data with `file` and optional `kind`
(post|story|item|avatar|condition). Returns { url, kind, size, mime } so the
frontend can stop sending base64 data URLs (audit finding #3).

Storage backend: defaults to local MEDIA_ROOT under /uploads/<kind>/<yyyy>/<mm>/.
Drop-in S3/Scaleway by setting DEFAULT_FILE_STORAGE in settings — no code change.
"""
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

ALLOWED_MIME = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'video/mp4', 'video/quicktime', 'video/webm',
}
MAX_BYTES = 25 * 1024 * 1024  # 25MB
ALLOWED_KINDS = {'post', 'story', 'item', 'avatar', 'cover', 'condition', 'handover'}


class UploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get('file')
        kind = request.data.get('kind', 'post')
        if not f:
            return Response({'error': 'file required'}, status=400)
        if kind not in ALLOWED_KINDS:
            return Response({'error': f'kind must be one of {sorted(ALLOWED_KINDS)}'}, status=400)
        if f.size > MAX_BYTES:
            return Response({'error': f'file too large (max {MAX_BYTES // 1024 // 1024}MB)'}, status=400)
        mime = getattr(f, 'content_type', '') or ''
        if mime and mime not in ALLOWED_MIME:
            return Response({'error': f'mime {mime} not allowed'}, status=400)

        ext = os.path.splitext(f.name)[1].lower() or '.bin'
        now = datetime.utcnow()
        fname = f"{uuid.uuid4().hex}{ext}"
        path = f"uploads/{kind}/{now:%Y/%m}/{fname}"

        saved = default_storage.save(path, ContentFile(f.read()))
        url = default_storage.url(saved)
        # Make absolute URL when MEDIA_URL is relative.
        if url.startswith('/'):
            url = request.build_absolute_uri(url)

        return Response({
            'url': url,
            'kind': kind,
            'size': f.size,
            'mime': mime,
            'filename': f.name,
        }, status=201)
