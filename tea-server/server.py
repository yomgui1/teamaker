import base64
import json
import os
import re
import sys
import hashlib
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import mimetypes

# Configuration
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.json')
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image')
PBKDF2_ITERATIONS = 200000
SESSION_TIMEOUT = 3600  # 1 hour
MAX_INPUT_LENGTH = 128  # Maximum length for input fields
MAX_DESCRIPTION_LENGTH = 1000  # Maximum length for description fields
MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10MB max for database import
MAX_RATE_LIMIT_ENTRIES = 10000  # Maximum entries in rate limit store
SCHEMA_VERSION = 1

# Database schema definition: {field: {"type": str|int|list|dict, "default": ...}}
_SCHEMA_TYPE_MAP = {str: "str", int: "int", list: "list", dict: "dict"}
SCHEMA = {
    "schema_version": {"type": _SCHEMA_TYPE_MAP[int], "default": 0},
    "admin_password_salt": {"type": _SCHEMA_TYPE_MAP[str], "default": None},
    "admin_password_hash": {"type": _SCHEMA_TYPE_MAP[str], "default": None},
    "tea_types": {"type": _SCHEMA_TYPE_MAP[list], "default": []},
    "events": {"type": _SCHEMA_TYPE_MAP[list], "default": []},
    "sessions": {"type": _SCHEMA_TYPE_MAP[dict], "default": {}},
}
CORS_ALLOW_ORIGIN = os.environ.get('TEAMAKER_CORS_ALLOW_ORIGIN', '127.0.0.1')
CORS_ALLOW_ORIGINS = [o.strip() for o in CORS_ALLOW_ORIGIN.split(',') if o.strip()]
LOG_METHOD = 'stderr'
LOG_FILE = None


def log_request(handler, message):
    """Log a request message based on configured log method."""
    timestamp = datetime.now(timezone.utc).isoformat()
    client_ip = handler.client_address[0] if handler.client_address else '127.0.0.1'
    formatted = f"{client_ip} - {timestamp} - {message}"
    if LOG_METHOD == 'file' and LOG_FILE:
        with open(LOG_FILE, 'a') as f:
            f.write(formatted + '\n')
    else:
        sys.stderr.write(formatted + '\n')
        sys.stderr.flush()


def _is_trusted_proxy(ip):
    """Check if IP is from a trusted proxy (loopback or private network)."""
    return ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.16.') or ip.startswith('172.17.') or ip.startswith('172.18.') or ip.startswith('172.19.') or ip.startswith('172.2') or ip.startswith('172.3')


def get_client_ip(handler):
    """Get client IP, trusting X-Forwarded-For only from trusted proxies."""
    forwarded = handler.headers.get('X-Forwarded-For')
    if forwarded and _is_trusted_proxy(handler.client_address[0] if handler.client_address else ''):
        return forwarded.split(',')[0].strip()
    return handler.client_address[0] if handler.client_address else '127.0.0.1'


def get_cors_header(handler):
    """Return the Access-Control-Allow-Origin value for this request.
    
    Returns None to indicate CORS should be denied (no header sent).
    """
    origin = handler.headers.get('Origin')
    if not origin:
        return CORS_ALLOW_ORIGIN
    if CORS_ALLOW_ORIGIN == '*':
        return '*'
    if origin in CORS_ALLOW_ORIGINS:
        return origin
    return None

os.makedirs(IMAGE_DIR, exist_ok=True)

# Global lock for database access
db_lock = threading.Lock()

# Rate limiter configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100  # max requests per window for general endpoints
LOGIN_RATE_LIMIT_MAX = 10  # max login attempts per window
LOGIN_COOLDOWN = 300  # seconds to wait after max attempts
PASSWORD_HASH_WINDOW = 300  # seconds — window for password hashing operations
PASSWORD_HASH_MAX = 5  # max password-hashing operations per window (includes login, setup, change)

# Rate limiter storage: {ip: [(timestamp, endpoint), ...]}
rate_limit_lock = threading.Lock()
rate_limit_store = {}


def cleanup_rate_limit_store():
    """Remove expired entries from rate limit store."""
    now = time.time()
    expired_ips = []
    for ip, requests in rate_limit_store.items():
        rate_limit_store[ip] = [(ts, ep) for ts, ep in requests if now - ts < RATE_LIMIT_WINDOW * 2]
        if not rate_limit_store[ip]:
            expired_ips.append(ip)
    for ip in expired_ips:
        del rate_limit_store[ip]
    # Enforce memory cap
    while len(rate_limit_store) > MAX_RATE_LIMIT_ENTRIES:
        oldest_ip = min(rate_limit_store, key=lambda ip: min(ts for ts, _ in rate_limit_store[ip]))
        del rate_limit_store[oldest_ip]


def check_rate_limit(ip, endpoint, max_requests=None):
    """Check if IP is rate limited. Returns (allowed, retry_after)."""
    if max_requests is None:
        max_requests = RATE_LIMIT_MAX_REQUESTS

    now = time.time()

    with rate_limit_lock:
        cleanup_rate_limit_store()

        if ip not in rate_limit_store:
            rate_limit_store[ip] = []

        # Filter to current window
        rate_limit_store[ip] = [(ts, ep) for ts, ep in rate_limit_store[ip] if now - ts < RATE_LIMIT_WINDOW]

        # Check if endpoint has been rate limited
        endpoint_requests = [(ts, ep) for ts, ep in rate_limit_store[ip] if ep == endpoint]
        if len(endpoint_requests) >= max_requests:
            oldest = min(ts for ts, _ in endpoint_requests)
            retry_after = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
            return False, max(retry_after, 1)

        # For login, also check global rate
        if endpoint == '/api/v1/auth/login':
            global_requests = rate_limit_store[ip]
            if len(global_requests) >= LOGIN_RATE_LIMIT_MAX:
                oldest = min(ts for ts, _ in global_requests)
                cooldown = int(LOGIN_COOLDOWN - (now - oldest)) + 1
                return False, max(cooldown, 1)

        # Record this request
        rate_limit_store[ip].append((now, endpoint))
        return True, 0


def check_password_hash_limit(ip):
    """Check global password hashing rate limit (covers login, setup, change)."""
    now = time.time()
    with rate_limit_lock:
        # Filter to password hash window
        password_ops = [(ts, ep) for ts, ep in rate_limit_store.get(ip, []) if ts > now - PASSWORD_HASH_WINDOW]
        if len(password_ops) >= PASSWORD_HASH_MAX:
            oldest = min(ts for ts, _ in password_ops)
            retry_after = int(PASSWORD_HASH_WINDOW - (now - oldest)) + 1
            return False, max(retry_after, 1)
        return True, 0


def load_database():
    if not os.path.exists(DATABASE_PATH):
        db = {
            "schema_version": SCHEMA_VERSION,
            "admin_password_salt": secrets.token_hex(16),
            "admin_password_hash": None,
            "tea_types": [],
            "events": [],
            "sessions": {}
        }
        save_database(db)
    else:
        with open(DATABASE_PATH, 'r') as f:
            db = json.load(f)
        check_migrate_database(db)
        save_database(db)
    return db


def check_migrate_database(db):
    """Migrate database to current schema version if needed."""
    version = db.get("schema_version", 0)
    if version >= SCHEMA_VERSION:
        return
    # Ensure all schema fields exist with proper defaults
    for field, spec in SCHEMA.items():
        if field not in db:
            db[field] = _make_default(spec["type"], spec["default"])
    # Set the current version
    db["schema_version"] = SCHEMA_VERSION


def _make_default(type_name, default_value):
    """Create a default value based on type name string."""
    if default_value is not None:
        return default_value
    if type_name == "str":
        return ""
    if type_name == "int":
        return 0
    if type_name == "list":
        return []
    if type_name == "dict":
        return {}
    return None


def save_database(db):
    tmp_path = DATABASE_PATH + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(db, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, DATABASE_PATH)


def read_db():
    """Read database under lock."""
    with db_lock:
        return load_database()


def update_db(func):
    """Read-modify-write database under lock. func(db) receives the db dict."""
    with db_lock:
        db = load_database()
        func(db)
        save_database(db)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), PBKDF2_ITERATIONS)
    return salt + ':' + dk.hex()


def verify_password(password, stored_hash):
    if stored_hash is None:
        return False
    if ':' not in stored_hash:
        # Backward compatibility: old SHA-256 hash
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash
    salt, hash_val = stored_hash.split(':', 1)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), PBKDF2_ITERATIONS)
    return secrets.compare_digest(dk.hex(), hash_val)


def set_admin_password(password):
    update_db(lambda db: db.__setitem__("admin_password_hash", hash_password(password)))


def generate_session_id():
    return secrets.token_hex(32)


def is_session_valid(session_id, db):
    if not session_id or session_id not in db.get("sessions", {}):
        return False
    session = db["sessions"][session_id]
    if datetime.now(timezone.utc).timestamp() - session.get("created_at", 0) > SESSION_TIMEOUT:
        del db["sessions"][session_id]
        save_database(db)
        return False
    return True


ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.svg'}
ALLOWED_EVENT_TYPES = {"status_update", "brewing_started", "brewing_completed", "brewing_cancelled", "manual"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def get_max_size_message():
    mb = MAX_IMAGE_SIZE // (1024 * 1024)
    return f"File too large (max {mb}MB)"

def sanitize_filename(filename):
    # Strip any directory components to prevent traversal
    filename = os.path.basename(filename)
    if not filename:
        return "unnamed"
    name, ext = os.path.splitext(filename)
    # Sanitize name: keep only alphanumeric, hyphens, underscores
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    if not safe_name:
        safe_name = "unnamed"
    ext = ext.lower()
    # Only allow known image extensions
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".png"
    return f"{safe_name}{ext}"


def _merge_by_id(existing, incoming, id_key):
    """Merge two lists of dicts by ID. Incoming entries overwrite existing ones."""
    existing_map = {item[id_key]: item for item in existing}
    for item in incoming:
        existing_map[item[id_key]] = item
    return list(existing_map.values())


def verify_image_magic_bytes(data):
    """Verify file is a valid image using magic bytes (MIME detection)."""
    if len(data) < 4:
        return False
    # PNG: 89 50 4E 47
    if data[:4] == b'\x89PNG':
        return True
    # GIF: 47 49 46 38
    if data[:4] in (b'GIF8', b'GIF9'):
        return True
    # JPEG: FF D8 FF
    if data[:3] == b'\xff\xd8\xff':
        return True
    # WEBP: 57 45 42 50
    if data[:4] == b'WEBP':
        return True
    # BMP: 42 4D
    if data[:2] == b'BM':
        return True
    return False


def sanitize_input(value, max_length=MAX_INPUT_LENGTH):
    """Sanitize and truncate input string."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    # Remove HTML tags to prevent XSS
    value = re.sub(r'<[^>]*>', '', value)
    return value[:max_length]


def sanitize_description(value, max_length=MAX_DESCRIPTION_LENGTH):
    """Sanitize and truncate description field."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    value = re.sub(r'<[^>]*>', '', value)
    return value[:max_length]


class TeaHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log_request(self, format % args)

    def send_json(self, data, status=200, retry_after=None, no_cache=False):
        response = json.dumps(data, default=str)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        if no_cache:
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
        if retry_after is not None:
            self.send_header('Retry-After', str(retry_after))
            self.send_header('X-RateLimit-Reset', str(int(time.time()) + retry_after))
        self.end_headers()
        self.wfile.write(response.encode())

    def send_error_json(self, message, status=400, retry_after=None, no_cache=False):
        self.send_json({"error": message}, status, retry_after=retry_after, no_cache=no_cache)

    def _cookie_str(self, name, value, extra='', httponly=True):
        http_only = '; HttpOnly' if httponly else ''
        return f'{name}={value}{http_only}; Secure; SameSite=Lax; Path=/{extra}'

    def get_session_id(self):
        cookie = self.headers.get('Cookie', '')
        for part in cookie.split(';'):
            part = part.strip()
            if part.startswith('session='):
                return part.split('=', 1)[1]
        return None

    def get_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode())
        except json.JSONDecodeError:
            return None

    def read_file_data(self):
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length)

    def do_OPTIONS(self):
        self.send_response(200)
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()

    def check_csrf(self):
        """Validate CSRF token for state-changing requests."""
        session_id = self.get_session_id()
        if not session_id:
            return True  # No session, no CSRF needed (e.g. login)
        db = read_db()
        if session_id not in db.get("sessions", {}):
            return True
        token = self.headers.get('X-CSRF-Token', '')
        stored_token = db["sessions"][session_id].get("csrf_token")
        if not stored_token:
            csrf_token = secrets.token_hex(32)
            db["sessions"][session_id]["csrf_token"] = csrf_token
            save_database(db)
            if not token:
                self.send_error_json("CSRF token missing", 403)
                return False
            if not secrets.compare_digest(token, csrf_token):
                self.send_error_json("CSRF token invalid", 403)
                return False
            return True
        if not token:
            self.send_error_json("CSRF token missing", 403)
            return False
        if not secrets.compare_digest(token, stored_token):
            self.send_error_json("CSRF token invalid", 403)
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        if path == '/api/v1/status':
            self.handle_status()
        elif path == '/api/v1/auth/me':
            self.handle_auth_me()
        elif path == '/api/v1/tea-types':
            self.handle_get_tea_types()
        elif path == '/api/v1/events':
            self.handle_get_events(query)
        elif path == '/api/v1/statistics':
            self.handle_statistics(query)
        elif path == '/api/v1/database/export':
            self.handle_export_database()
        elif path == '/api/v1/server-info':
            self.handle_server_info()
        elif path.startswith('/image/'):
            self.handle_get_image(path)
        else:
            self.send_error_json("Not found", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/api/v1/auth/login':
            self.handle_login()
        elif path == '/api/v1/auth/setup-password':
            self.handle_setup_password()
        elif path == '/api/v1/auth/change-password':
            self.handle_change_password()
        elif path == '/api/v1/status':
            self.handle_status_update()
        elif path == '/api/v1/events/brewing/start':
            self.handle_brewing_start()
        elif path == '/api/v1/events/brewing/complete':
            self.handle_brewing_complete()
        elif path == '/api/v1/events/brewing/cancel':
            self.handle_brewing_cancel()
        elif path == '/api/v1/tea-types':
            self.handle_create_tea_type()
        elif path == '/api/v1/events':
            self.handle_create_event()
        elif path == '/api/v1/events/clear':
            self.handle_clear_events()
        elif path == '/api/v1/database/import':
            self.handle_import_database()
        elif path == '/api/v1/upload-image':
            self.handle_upload_image()
        else:
            self.send_error_json("Not found", 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        if path == '/api/v1/tea-types':
            self.handle_delete_tea_type(query)
        elif path == '/api/v1/events':
            self.handle_delete_event(query)
        elif path == '/api/v1/database':
            self.handle_delete_database()
        elif path == '/api/v1/auth/logout':
            self.handle_logout()
        else:
            self.send_error_json("Not found", 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        if path == '/api/v1/tea-types':
            self.handle_update_tea_type(query)
        else:
            self.send_error_json("Not found", 404)

    def require_admin(self):
        db = read_db()
        session_id = self.get_session_id()
        if not is_session_valid(session_id, db):
            self.send_error_json("Unauthorized", 401)
            return False
        if db["sessions"][session_id].get("role") != "admin":
            self.send_error_json("Admin access required", 403)
            return False
        return True

    def handle_status(self):
        db = read_db()
        events = db.get("events", [])
        latest = None
        for event in reversed(events):
            if event.get("type") in ("brewing_started", "brewing_completed", "brewing_cancelled"):
                latest = event
                break

        if latest:
            status = "on-going" if latest.get("type") == "brewing_started" else "done"
            response = {
                "timestamp": latest.get("created_at", ""),
                "status": status,
                "type": latest.get("tea_type", "unknown")
            }
        else:
            response = {
                "timestamp": "",
                "status": "unknown",
                "type": "unknown"
            }
        self.send_json(response)

    def handle_status_update(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        tea_type = sanitize_input(body.get("type", "unknown"))
        update_db(lambda db: db["events"].append({
            "id": secrets.token_hex(8),
            "type": "status_update",
            "tea_type": tea_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        self.send_json({"status": "updated"})

    def handle_auth_me(self):
        db = read_db()
        session_id = self.get_session_id()
        initialized = db.get("admin_password_hash") is not None
        if is_session_valid(session_id, db):
            self.send_json({"authenticated": True, "role": db["sessions"][session_id].get("role", "guest"), "initialized": initialized}, no_cache=True)
        else:
            self.send_json({"authenticated": False, "role": "guest", "initialized": initialized}, no_cache=True)

    def handle_login(self):
        client_ip = get_client_ip(self)

        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip, '/api/v1/auth/login')
        if not allowed:
            self.send_error_json("Too many login attempts. Please try again later.", 429, retry_after=retry_after)
            return

        # Check password hashing limit (prevents CPU exhaustion via PBKDF2)
        pw_allowed, pw_retry = check_password_hash_limit(client_ip)
        if not pw_allowed:
            self.send_error_json("Too many password attempts. Please try again later.", 429, retry_after=pw_retry)
            return

        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        password = body.get("password", "")
        role = body.get("role", "guest")

        db = read_db()

        if role == "admin":
            if db.get("admin_password_hash") is None:
                self.send_error_json("Admin password not set. Use /api/v1/auth/setup-password first.", 403)
                return
            if not verify_password(password, db.get("admin_password_hash")):
                self.send_error_json("Invalid password", 401)
                return
            session_role = "admin"
        else:
            session_role = "guest"

        session_id = generate_session_id()
        csrf_token = secrets.token_hex(32)
        update_db(lambda db: db["sessions"].__setitem__(session_id, {
            "role": session_role,
            "created_at": datetime.now(timezone.utc).timestamp(),
            "csrf_token": csrf_token
        }))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('Set-Cookie', self._cookie_str('session', session_id))
        self.send_header('Set-Cookie', self._cookie_str('csrf_token', csrf_token, httponly=False))
        self.send_header('Access-Control-Expose-Headers', 'X-CSRF-Token')
        self.send_header('X-CSRF-Token', csrf_token)
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps({"authenticated": True, "role": session_role, "initialized": True}).encode())

    def handle_logout(self):
        if not self.check_csrf():
            return
        session_id = self.get_session_id()
        update_db(lambda db: db["sessions"].pop(session_id, None))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('Set-Cookie', self._cookie_str('session', '', '; Max-Age=0'))
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "logged out"}).encode())

    def handle_setup_password(self):
        client_ip = get_client_ip(self)
        allowed, retry_after = check_rate_limit(client_ip, '/api/v1/auth/setup-password')
        if not allowed:
            self.send_error_json("Too many requests. Please try again later.", 429, retry_after=retry_after)
            return

        # Check password hashing limit (prevents CPU exhaustion via PBKDF2)
        pw_allowed, pw_retry = check_password_hash_limit(client_ip)
        if not pw_allowed:
            self.send_error_json("Too many password attempts. Please try again later.", 429, retry_after=pw_retry)
            return
        db = read_db()
        if db.get("admin_password_hash") is not None:
            if not self.check_csrf():
                return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        password = body.get("password", "")
        if len(password) < 8:
            self.send_error_json("Password must be at least 8 characters", 400)
            return
        if len(password) > MAX_INPUT_LENGTH:
            self.send_error_json("Password too long", 400)
            return
        if db.get("admin_password_hash") is not None:
            self.send_error_json("Admin password already set. Use /api/v1/auth/change-password instead.", 409)
            return
        set_admin_password(password)
        self.send_json({"status": "password set"})

    def handle_change_password(self):
        client_ip = get_client_ip(self)
        allowed, retry_after = check_rate_limit(client_ip, '/api/v1/auth/change-password')
        if not allowed:
            self.send_error_json("Too many requests. Please try again later.", 429, retry_after=retry_after)
            return

        # Check password hashing limit (prevents CPU exhaustion via PBKDF2)
        pw_allowed, pw_retry = check_password_hash_limit(client_ip)
        if not pw_allowed:
            self.send_error_json("Too many password attempts. Please try again later.", 429, retry_after=pw_retry)
            return
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        old_password = body.get("old_password", "")
        new_password = body.get("new_password", "")
        if len(new_password) < 8:
            self.send_error_json("New password must be at least 8 characters", 400)
            return
        if len(new_password) > MAX_INPUT_LENGTH:
            self.send_error_json("New password too long", 400)
            return
        db = read_db()
        if not verify_password(old_password, db.get("admin_password_hash")):
            self.send_error_json("Invalid current password", 401)
            return
        set_admin_password(new_password)
        update_db(lambda db: db.__setitem__("sessions", {}))
        self.send_json({"status": "password changed"})

    def handle_brewing_start(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        tea_type = sanitize_input(body.get("tea_type", "unknown"))
        db = read_db()
        if self._has_active_brewing(db):
            self.send_error_json("Brewing already in progress. Complete or cancel it first.", 409)
            return
        update_db(lambda db: db["events"].append({
            "id": secrets.token_hex(8),
            "type": "brewing_started",
            "tea_type": tea_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        self.send_json({"status": "brewing_started"})

    def handle_brewing_complete(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        tea_type = sanitize_input(body.get("tea_type", "unknown"))
        db = read_db()
        if not self._has_active_brewing(db):
            self.send_error_json("No active brewing. Start a new one first.", 409)
            return
        active = self._get_active_brewing(db)
        if tea_type != active.get("tea_type"):
            self.send_error_json(f"Cannot complete a different tea. Current brewing: {active.get('tea_type')}", 409)
            return
        update_db(lambda db: db["events"].append({
            "id": secrets.token_hex(8),
            "type": "brewing_completed",
            "tea_type": tea_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        self.send_json({"status": "brewing_completed"})

    def handle_brewing_cancel(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        tea_type = sanitize_input(body.get("tea_type", "unknown"))
        db = read_db()
        if not self._has_active_brewing(db):
            self.send_error_json("No active brewing. Start a new one first.", 409)
            return
        active = self._get_active_brewing(db)
        if tea_type != active.get("tea_type"):
            self.send_error_json(f"Cannot cancel a different tea. Current brewing: {active.get('tea_type')}", 409)
            return
        update_db(lambda db: db["events"].append({
            "id": secrets.token_hex(8),
            "type": "brewing_cancelled",
            "tea_type": tea_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))
        self.send_json({"status": "brewing_cancelled"})

    def _has_active_brewing(self, db):
        """Check if there is an active brewing session."""
        events = db.get("events", [])
        latest_started = None
        for event in reversed(events):
            if event.get("type") == "brewing_started":
                latest_started = event
                break
            if event.get("type") in ("brewing_completed", "brewing_cancelled"):
                return False
        if not latest_started:
            return False
        started_idx = events.index(latest_started)
        for event in events[started_idx + 1:]:
            if event.get("type") in ("brewing_completed", "brewing_cancelled"):
                return False
        return True

    def _get_active_brewing(self, db):
        """Get the active brewing event if any."""
        events = db.get("events", [])
        for event in reversed(events):
            if event.get("type") == "brewing_started":
                return event
        return None

    def handle_get_tea_types(self):
        db = read_db()
        types = db.get("tea_types", [])
        self.send_json({"tea_types": types})

    def handle_create_tea_type(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        name = sanitize_input(body.get("name", ""))
        image = sanitize_input(body.get("image", ""))
        if not name:
            self.send_error_json("Name is required")
            return
        tea_type = {
            "id": secrets.token_hex(8),
            "name": name,
            "image": image
        }
        update_db(lambda db: db["tea_types"].append(tea_type))
        self.send_json({"status": "created", "tea_type": tea_type})

    def handle_update_tea_type(self, query):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        tea_id = query.get("id", [None])[0]
        if not tea_id:
            self.send_error_json("ID is required")
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        name = sanitize_input(body.get("name")) if body.get("name") is not None else None
        image = sanitize_input(body.get("image")) if body.get("image") is not None else None
        def _update_tt(db):
            for tt in db["tea_types"]:
                if tt["id"] == tea_id:
                    if name is not None:
                        tt["name"] = name
                    if image is not None:
                        tt["image"] = image
                    break
        update_db(_update_tt)
        self.send_json({"status": "updated"})

    def handle_delete_tea_type(self, query):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        tea_id = query.get("id", [None])[0]
        if not tea_id:
            self.send_error_json("ID is required")
            return
        update_db(lambda db: db.__setitem__("tea_types", [tt for tt in db["tea_types"] if tt["id"] != tea_id]))
        self.send_json({"status": "deleted"})

    def handle_get_events(self, query):
        db = read_db()
        limit = int(query.get("limit", [50])[0])
        events = db.get("events", [])
        events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        self.send_json({"events": events[:limit]})

    def handle_create_event(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        event_type = sanitize_input(body.get("type", "manual"))
        if event_type not in ALLOWED_EVENT_TYPES:
            self.send_error_json(
                f"Incompatible schema version (expected {SCHEMA_VERSION}). "
                f"Valid event types: {', '.join(sorted(ALLOWED_EVENT_TYPES))}. "
                "Server may need to be upgraded or database needs to be exported/imported.",
                422
            )
            return
        event = {
            "id": secrets.token_hex(8),
            "type": event_type,
            "tea_type": sanitize_input(body.get("tea_type", "unknown")),
            "description": sanitize_description(body.get("description", "")),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        update_db(lambda db: db["events"].append(event))
        self.send_json({"status": "created", "event": event})

    def handle_delete_event(self, query):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        event_id = query.get("id", [None])[0]
        if not event_id:
            self.send_error_json("ID is required")
            return
        update_db(lambda db: db.__setitem__("events", [e for e in db["events"] if e["id"] != event_id]))
        self.send_json({"status": "deleted"})

    def handle_clear_events(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        update_db(lambda db: db.__setitem__("events", []))
        self.send_json({"status": "all events cleared"})

    def handle_statistics(self, query):
        db = read_db()
        events = db.get("events", [])
        stats = {}
        for event in events:
            tea_type = event.get("tea_type", "unknown")
            created = event.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                month_key = dt.strftime("%Y-%m")
            except (ValueError, AttributeError):
                month_key = "unknown"

            key = f"{tea_type}|{month_key}"
            if key not in stats:
                stats[key] = {
                    "tea_type": tea_type,
                    "month": month_key,
                    "count": 0,
                    "started": 0,
                    "completed": 0,
                    "cancelled": 0
                }
            stats[key]["count"] += 1
            event_type = event.get("type", "")
            if event_type == "brewing_started":
                stats[key]["started"] += 1
            elif event_type == "brewing_completed":
                stats[key]["completed"] += 1
            elif event_type == "brewing_cancelled":
                stats[key]["cancelled"] += 1

        self.send_json({"statistics": list(stats.values())})

    def handle_get_image(self, path):
        image_filename = path[len('/image/'):]
        if not image_filename:
            self.send_error_json("Image not found", 404)
            return
        # Sanitize filename to prevent path traversal
        image_filename = sanitize_filename(image_filename)
        image_path = os.path.join(IMAGE_DIR, image_filename)
        # Resolve to absolute path and verify it's within IMAGE_DIR
        real_path = os.path.realpath(image_path)
        real_image_dir = os.path.realpath(IMAGE_DIR)
        if not real_path.startswith(real_image_dir + os.sep) and real_path != real_image_dir:
            self.send_error_json("Not found", 404)
            return
        if not os.path.isfile(real_path):
            self.send_error_json("Image not found", 404)
            return
        content_type, _ = mimetypes.guess_type(real_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        with open(real_path, 'rb') as f:
            image_data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(image_data)

    def handle_upload_image(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        body = self.get_json_body()
        if body is None:
            self.send_error_json("Invalid JSON")
            return
        filename = sanitize_input(body.get("filename", ""))
        data_b64 = body.get("data", "")
        if not filename or not data_b64:
            self.send_error_json("Filename and data are required")
            return
        try:
            file_data = base64.b64decode(data_b64)
        except Exception:
            self.send_error_json("Invalid base64 data")
            return
        if len(file_data) > MAX_IMAGE_SIZE:
            self.send_error_json(get_max_size_message())
            return
        # Validate image magic bytes
        if not verify_image_magic_bytes(file_data):
            self.send_error_json("Invalid image file")
            return
        # Sanitize and save
        filename = sanitize_filename(filename)
        image_path = os.path.join(IMAGE_DIR, filename)
        with open(image_path, 'wb') as f:
            f.write(file_data)
        self.send_json({"filename": filename, "path": f"/image/{filename}"})

    def handle_import_database(self):
        if not self.check_csrf():
            return
        if not self.require_admin():
            return
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > MAX_IMPORT_SIZE:
            self.send_error_json("Import file too large (max 10MB)", 413)
            return
        data = self.read_file_data()
        try:
            import_data = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error_json("Invalid JSON data")
            return
        if not isinstance(import_data, dict):
            self.send_error_json("Invalid database format")
            return
        allowed_keys = {"tea_types", "events"}
        if not any(k in import_data for k in allowed_keys):
            self.send_error_json("Invalid database format: must contain 'tea_types' and/or 'events'")
            return
        # Only extract allowed keys - never import sessions, password hashes, or other sensitive data
        tea_types = import_data.get("tea_types", [])
        events = import_data.get("events", [])
        if not isinstance(tea_types, list):
            self.send_error_json("Invalid database format: 'tea_types' must be an array")
            return
        if not isinstance(events, list):
            self.send_error_json("Invalid database format: 'events' must be an array")
            return
        # Validate tea_type entries
        for tt in tea_types:
            if not isinstance(tt, dict):
                self.send_error_json("Invalid database format: each tea_type must be an object")
                return
            if "id" not in tt or "name" not in tt:
                self.send_error_json("Invalid tea_type: must have 'id' and 'name' fields")
                return
       # Validate event entries
        for event in events:
            if not isinstance(event, dict):
                self.send_error_json("Invalid database format: each event must be an object")
                return
            if "id" not in event or "type" not in event or "created_at" not in event:
                self.send_error_json("Invalid event: must have 'id', 'type', and 'created_at' fields")
                return
            # Validate created_at is a parseable ISO format datetime
            try:
                datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.send_error_json(f"Invalid event: 'created_at' is not a valid ISO datetime: {event['created_at']!r}")
                return
        # Merge into existing database — union by ID, imported entries overwrite existing ones
        update_db(lambda db: (_merge_by_id(db["tea_types"], tea_types, "id"), _merge_by_id(db["events"], events, "id")))
        self.send_json({"status": "imported", "tea_types_imported": len(tea_types), "events_imported": len(events)})

    def handle_server_info(self):
        db = read_db()
        self.send_json({
            "schema_version": db.get("schema_version", 0),
            "schema": SCHEMA,
            "event_types": sorted(ALLOWED_EVENT_TYPES)
        })

    def handle_export_database(self):
        client_ip = get_client_ip(self)
        allowed, retry_after = check_rate_limit(client_ip, '/api/v1/database/export')
        if not allowed:
            self.send_error_json("Too many export requests. Please try again later.", 429, retry_after=retry_after)
            return
        db = read_db()
        export_data = {
            "tea_types": db.get("tea_types", []),
            "events": db.get("events", []),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        response_data = json.dumps(export_data, indent=2, default=str).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        cors = get_cors_header(self)
        if cors is not None:
            self.send_header('Access-Control-Allow-Origin', cors)
        self.send_header('Content-Disposition', f'attachment; filename="tea-database-{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.json"')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(response_data)

    def handle_delete_database(self):
        if not self.check_csrf():
            return
        if self.require_admin():
            def _clear_db(db):
                db["tea_types"] = []
                db["events"] = []
                db["sessions"] = {}
            update_db(_clear_db)
            self.send_json({"status": "database cleared"})
        else:
            self.send_error_json("Unauthorized", 401)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def run_server(host='127.0.0.1', port=5000):
    server = ThreadedHTTPServer((host, port), TeaHandler)
    print(f"Tea server running on {host}:{port}")
    print(f"CORS allow origins: {', '.join(CORS_ALLOW_ORIGINS)}")
    print(f"Logging: {LOG_METHOD}" + (f" -> {LOG_FILE}" if LOG_FILE else ""))
    server.serve_forever()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Tea Production Manager server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
env vars (overridden by CLI args):
  TEAMAKER_PORT              Server port (default: 5000)
  TEAMAKER_HOST              Server hostname (default: 127.0.0.1)
  TEAMAKER_CORS_ALLOW_ORIGIN Comma-separated origins or '127.0.0.1' (default: 127.0.0.1)
  TEAMAKER_LOG_METHOD        'stderr' or 'file' (default: stderr)
  TEAMAKER_LOG_FILE          Log file path (required if LOG_METHOD=file)
"""
    )
    parser.add_argument('--host', type=str, default=os.environ.get('TEAMAKER_HOST', '127.0.0.1'),
                        help='Server hostname (default: env TEAMAKER_HOST or 127.0.0.1)')
    parser.add_argument('--port', type=int, default=int(os.environ.get('TEAMAKER_PORT', '5000')),
                        help='Server port (default: env TEAMAKER_PORT or 5000)')
    parser.add_argument('--cors', type=str, default=os.environ.get('TEAMAKER_CORS_ALLOW_ORIGIN', '127.0.0.1'),
                        help="CORS origins, comma-separated or '127.0.0.1' (default: env TEAMAKER_CORS_ALLOW_ORIGIN or 127.0.0.1)")
    parser.add_argument('--log', dest='log_method', type=str,
                        default=os.environ.get('TEAMAKER_LOG_METHOD', 'stderr'),
                        choices=['stderr', 'file'],
                        help='Log destination: stderr or file (default: env TEAMAKER_LOG_METHOD or stderr)')
    parser.add_argument('--log-file', type=str, default=os.environ.get('TEAMAKER_LOG_FILE', None),
                        help='Log file path (required if --log=file)')

    args = parser.parse_args()

    globals()['LOG_METHOD'] = args.log_method
    globals()['LOG_FILE'] = args.log_file
    globals()['CORS_ALLOW_ORIGIN'] = args.cors
    globals()['CORS_ALLOW_ORIGINS'] = [o.strip() for o in args.cors.split(',') if o.strip()]
    run_server(args.host, args.port)
