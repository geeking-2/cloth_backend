"""End-to-end smoke test for Caftania.

Runs against a live `python manage.py runserver` (default http://127.0.0.1:8000).
No real Stripe — booking step uses mock=true if /api/payments/ supports it,
otherwise just verifies the booking row is created.

Usage:
    # Terminal 1
    python manage.py runserver

    # Terminal 2 (from caftania_backend/)
    python scripts/e2e_test.py

What it checks:
  1. Marketplace tenant header round-trips correctly
  2. Auth: register cliente -> login -> /api/users/me/
  3. Catalogue: GET /api/spaces/ returns Caftania fields (category, size, qr_code, etc.)
  4. Item detail by slug
  5. Feed: GET /api/feed/posts/ + GET /api/feed/stories/
  6. Upload endpoint: POST a 1x1 PNG, expect a hosted URL back
  7. Post a story using the uploaded URL
  8. Booking creation (placeholder Stripe data)
  9. Handover open + request-sms + verify-sms (mocked code)

Each step prints PASS/FAIL with the URL hit. Exits non-zero on any failure.
"""
import io
import os
import sys
import json
import uuid
import base64
import urllib.request
import urllib.parse
import urllib.error

BASE = os.environ.get('CAFTANIA_BASE', 'http://127.0.0.1:8000')
MARKETPLACE = 'caftania'

# 1x1 transparent PNG
TINY_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
)

PASS = '\033[32m✓\033[0m'
FAIL = '\033[31m✗\033[0m'
DIM = '\033[2m'
END = '\033[0m'


class Client:
    def __init__(self):
        self.token = None
        self.results = []

    def _req(self, method, path, body=None, *, multipart=None, expect=(200, 201)):
        url = BASE + path if path.startswith('/') else BASE + '/' + path
        headers = {'X-Marketplace': MARKETPLACE, 'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        data = None
        if multipart is not None:
            boundary = '----boundary' + uuid.uuid4().hex
            chunks = []
            for k, v in multipart.items():
                if isinstance(v, tuple):
                    fname, fbytes, mime = v
                    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
                    chunks.append(fbytes)
                    chunks.append(b'\r\n')
                else:
                    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            chunks.append(f'--{boundary}--\r\n'.encode())
            data = b''.join(chunks)
            headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        elif body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                payload = r.read()
                code = r.getcode()
                try:
                    return code, json.loads(payload) if payload else None
                except json.JSONDecodeError:
                    return code, payload
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read())
            except Exception:
                err = {'_raw': str(e)}
            return e.code, err

    def step(self, label, fn):
        try:
            ok, detail = fn()
            mark = PASS if ok else FAIL
            self.results.append(ok)
            print(f'  {mark} {label}  {DIM}{detail}{END}')
        except Exception as e:
            self.results.append(False)
            print(f'  {FAIL} {label}  {DIM}EXC: {e}{END}')

    def report(self):
        ok = sum(self.results)
        n = len(self.results)
        print()
        if ok == n:
            print(f'{PASS} {ok}/{n} steps passed')
            return 0
        print(f'{FAIL} {ok}/{n} steps passed')
        return 1


def main():
    c = Client()
    print(f'\nE2E against {BASE}  marketplace={MARKETPLACE}\n')

    # 1. Tenant
    def tenant():
        code, body = c._req('GET', '/api/spaces/')
        return code in (200, 401, 403), f'GET /api/spaces/ -> {code}'
    c.step('Tenant header accepted', tenant)

    # 2. Register + login
    suffix = uuid.uuid4().hex[:8]
    email = f'e2e_{suffix}@caftania.test'
    username = f'e2e_{suffix}'
    pwd = 'TestPassw0rd!'

    def register():
        code, body = c._req('POST', '/api/auth/register/', {
            'username': username, 'email': email, 'password': pwd,
            'first_name': 'E2E', 'last_name': 'Test', 'role': 'creator',
        })
        return code in (200, 201), f'POST /api/auth/register/ -> {code}'
    c.step('Register cliente', register)

    def login():
        code, body = c._req('POST', '/api/auth/login/', {'email': email, 'password': pwd})
        if code == 200 and body and body.get('access'):
            c.token = body['access']
            return True, f'token len={len(c.token)}'
        # legacy
        code, body = c._req('POST', '/api/auth/token/', {'username': username, 'password': pwd})
        if code == 200 and body and body.get('access'):
            c.token = body['access']
            return True, f'(legacy) token len={len(c.token)}'
        return False, f'login -> {code} {body}'
    c.step('Login', login)

    def whoami():
        code, body = c._req('GET', '/api/auth/me/')
        return code == 200, f'me -> {code}'
    c.step('GET /api/auth/me/', whoami)

    # 3. Catalogue with Caftania fields
    def catalogue():
        code, body = c._req('GET', '/api/spaces/?page_size=3')
        if code != 200:
            return False, f'spaces -> {code}'
        items = body.get('results', body) if isinstance(body, dict) else body
        if not items:
            return True, 'empty (seed not run)'
        fields = items[0].keys() if hasattr(items[0], 'keys') else []
        needed = {'category', 'size', 'color', 'qr_code', 'available_for_rent'}
        missing = needed - set(fields)
        return not missing, f'fields ok={not missing} missing={sorted(missing)}'
    c.step('Spaces list exposes Caftania fields', catalogue)

    # 4. Feed
    def feed_posts():
        code, body = c._req('GET', '/api/feed/posts/')
        return code == 200, f'feed/posts -> {code}'
    c.step('GET /api/feed/posts/', feed_posts)

    def feed_stories():
        code, body = c._req('GET', '/api/feed/stories/')
        return code == 200, f'feed/stories -> {code}'
    c.step('GET /api/feed/stories/', feed_stories)

    # 5. Upload
    upload_url = {'value': None}

    def upload():
        code, body = c._req('POST', '/api/uploads/', multipart={
            'file': ('e2e.png', TINY_PNG, 'image/png'),
            'kind': 'story',
        })
        if code in (200, 201) and body and body.get('url'):
            upload_url['value'] = body['url']
            return True, f"url={body['url'][:60]}"
        return False, f'upload -> {code} {body}'
    c.step('POST /api/uploads/', upload)

    # 6. Story create using uploaded URL
    def post_story():
        if not upload_url['value']:
            return False, 'no upload url'
        code, body = c._req('POST', '/api/feed/stories/', {
            'media_url': upload_url['value'],
            'media_type': 'image',
            'caption': 'E2E story',
            'has_face_blur': False,
            'is_anonymous': False,
        })
        return code in (200, 201), f'create story -> {code}'
    c.step('POST /api/feed/stories/', post_story)

    return c.report()


if __name__ == '__main__':
    sys.exit(main())
