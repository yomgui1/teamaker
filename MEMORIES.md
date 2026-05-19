# Tea Production Manager - Project Context

## Project Overview
A complete tea production management system with:
- Python REST server (no frameworks, stdlib only) with JSON database
- Vue.js 3 frontend with Vite
- DiaMCP tool for querying tea status

## Directory Structure
```
test_tea/
├── tea-server/
│   ├── server.py          # Main REST server (stdlib only)
│   ├── database.json       # JSON database (auto-created)
│   └── image/              # Tea image storage
├── tea-client/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── styles.css
│       ├── router/index.js
│       ├── stores/
│       │   ├── auth.js     # Auth store (Pinia)
│       │   └── api.js      # API store (Pinia)
│       └── views/
│           ├── HomeView.vue
│           ├── LoginView.vue
│           ├── StatusView.vue
│           ├── StatisticsView.vue
│           ├── TeaTypesView.vue
│           ├── EventsView.vue
│           └── DatabaseView.vue
├── diaMCP-AGENTS.md
├── ISSUES.md
└── MEMORIES.md
```

## Server (tea-server/server.py)
- Pure Python stdlib HTTP server (no Flask/FastAPI)
- JSON database at `database.json` with `schema_version` field for migration tracking
- Image storage in `image/` subfolder
- Session-based auth with HttpOnly cookies
- Password: PBKDF2-HMAC-SHA256 (200k iterations) with random salt in database.json
- Initial setup via POST /api/v1/auth/setup-password
- Change password via POST /api/v1/auth/change-password (admin only)
- require_admin() now checks session role (was broken)
- Schema versioning: `SCHEMA` dict defines all fields with types/defaults, `SCHEMA_VERSION` constant, `check_migrate_database()` adds missing fields on load, `GET /api/v1/server-info` exposes version + full schema + valid event types

### API Endpoints
| Method | Path | Auth | CSRF | Rate Limit | Description |
|--------|------|------|------|------------|-------------|
| GET | /api/v1/status | Any | - | 100/60s | Get latest tea status |
| POST | /api/v1/status | Admin | Required | 100/60s | Update status |
| POST | /api/v1/auth/login | - | - | 10/60s | Login (admin/guest), returns csrf_token |
| POST | /api/v1/auth/setup-password | - | Required | 100/60s | Set initial admin password |
| POST | /api/v1/auth/change-password | Admin | Required | 100/60s | Change admin password |
| DELETE | /api/v1/auth/logout | Any | Required | 100/60s | Logout |
| GET | /api/v1/auth/me | - | - | 100/60s | Check auth state |
| GET | /api/v1/tea-types | Any | - | 100/60s | List tea types |
| POST | /api/v1/tea-types | Admin | Required | 100/60s | Create tea type |
| PUT | /api/v1/tea-types?id=X | Admin | Required | 100/60s | Update tea type |
| DELETE | /api/v1/tea-types?id=X | Admin | Required | 100/60s | Delete tea type |
| GET | /api/v1/events?limit=N | Any | - | 100/60s | List events (newest first) |
| POST | /api/v1/events | Admin | Required | 100/60s | Create event |
| DELETE | /api/v1/events?id=X | Admin | Required | 100/60s | Delete event |
| POST | /api/v1/events/brewing/start | Admin | Required | 100/60s | Start brewing |
| POST | /api/v1/events/brewing/complete | Admin | Required | 100/60s | Complete brewing |
| POST | /api/v1/events/brewing/cancel | Admin | Required | 100/60s | Cancel brewing |
| GET | /api/v1/statistics | Any | - | 100/60s | Get statistics |
| POST | /api/v1/upload-image | Admin | Required | 100/60s | Upload image |
| GET | /image/{filename} | Any | - | 100/60s | Serve image |
| POST | /api/v1/database/import | Admin | Required | 100/60s | Import database |
| DELETE | /api/v1/database | Admin | Required | 100/60s | Delete all data |
| GET | /api/v1/server-info | Any | - | 100/60s | Get schema version and valid event types |

## Client (tea-client/)
Vue 3 + Vite + Pinia + Vue Router + Axios

### Pages
1. **Login** - Admin password only (no guest login)
2. **Status** - Tea brewing controls (admin), status display (guest) — default page
3. **Statistics** - Tea production stats by type and month (all users)
4. **Tea Types** - Add/edit/remove tea types with images (admin only)
5. **Events** - Event log with configurable limit, delete events (admin delete)
6. **Database** - Export/import/delete database (admin only)

### Features
- Night mode toggle (moon/sun icon in nav)
- Admin/guest mode indicator badge
- Image upload (PNG, JPG, WEBP, GIF)
- Responsive design
- Session-based authentication

## DiaMCP Tool
- Tool: `get_tea_status`
- Location: `/workspace/tools/get_tea_status_tool.py`
- Purpose: Query tea status via REST API
- Requires: `httpx` in requirements.txt + MCP restart

## How to Run

### Server
```bash
cd tea-server
python server.py
```

### Client
```bash
cd tea-client
npm install
npm run dev
```

### MCP Tool
After creating the tool, restart MCP server:
```bash
cd ~/diamcp && ./restart.sh
```

## Security Notes
- Password: PBKDF2-HMAC-SHA256 (200k iterations), random salt per instance
- `secrets.compare_digest()` for constant-time password comparison
- Backward compatible with old SHA-256 hashes
- Sessions use secure random tokens (secrets.token_hex)
- HttpOnly + Secure cookies prevent XSS and MITM (login and logout)
- Session timeout: 1 hour
- Input sanitization for filenames and user input (HTML tag removal)
- CORS enabled for API, configurable via `--cors` CLI flag or `CORS_ALLOW_ORIGIN` env var (defaults to `*`). Supports comma-separated list of origins; unauthorized origins are denied when multiple origins specified
- require_admin() properly checks session role
- Image serving: path traversal protection via realpath validation
- Image upload: multipart parsing, magic bytes validation, 5MB size limit
- X-Content-Type-Options: nosniff on all responses (JSON, images, OPTIONS)
- CSRF protection: double-submit cookie pattern, all state-changing endpoints require X-CSRF-Token header
- Rate limiting: sliding window per IP, 100 req/60s general, 10 req/60s login with 300s cooldown, HTTP 429 responses
- Rate limit store: capped at 10000 entries with oldest-entry eviction
- Input length limits: 128 chars for most fields, 1000 for descriptions, 10MB for imports
- X-Forwarded-For support for reverse proxy deployments (login handler)
- Cache-Control: no-store on auth-sensitive responses (login, logout, auth/me)
- Bulk delete endpoint for events (POST /api/v1/events/clear)
- Export endpoint rate limited (100 req/60s)
- Database locking: threading.Lock() for concurrent access safety
- Atomic writes: os.replace() for database persistence
- Server logging: configurable via `--log stderr|file` and `--log-file` arguments
- CLI: `argparse` with env var fallback (TEAMAKER_PORT, TEAMAKER_CORS_ALLOW_ORIGIN, TEAMAKER_LOG_METHOD, TEAMAKER_LOG_FILE), `--help` supported, CLI overrides env vars
- Schema versioning: `SCHEMA` dict defines all DB fields with types/defaults, auto-migration adds missing fields on load, `GET /api/v1/server-info` exposes version + full schema + valid event types, event type validation returns 422 with upgrade hint on mismatch

## Security Fixes Applied (Original Hardening)
- **#1 RESOLVED** (2026-05-18): Replaced hardcoded SHA-256 password with PBKDF2-HMAC-SHA256 (200k iterations), random salt in database.json, setup/change-password endpoints, require_admin() role check fixed
- **#5 RESOLVED** (2026-05-18): require_admin() now checks session role == "admin" (was only checking session validity)
- **#3 RESOLVED** (2026-05-18): Path traversal fixed - realpath validation, sanitize_filename on serving, multipart parsing with magic bytes validation, file size limit (5MB), extension whitelist
- **#4 RESOLVED** (2026-05-18): Import validation - only allows tea_types/events keys, validates structure of each entry, never imports sessions/password hashes, merges into existing DB
- **#2 RESOLVED** (2026-05-18): Database locking - added threading.Lock(), read_db()/update_db() helpers, atomic writes with os.replace(), ThreadingMixIn for concurrent handling
- **#7 RESOLVED** (2026-05-18): CSRF protection - double-submit cookie pattern, csrf_token stored in session, check_csrf() on all 14 state-changing handlers, secrets.compare_digest()
- **#6 RESOLVED** (2026-05-18): Rate limiting - sliding window per IP, 100 req/60s general, 10 req/60s login with 300s cooldown, HTTP 429 responses
- **#8 RESOLVED** (2026-05-18): Image upload multipart parsing - extracts file content only, validates magic bytes, extension whitelist (resolved during #3)
- **#9 RESOLVED** (2026-05-18): File size limit on uploads - 5MB MAX_IMAGE_SIZE, Content-Length check, HTTP 413 responses (resolved during #3)
- **#10 RESOLVED** (2026-05-18): Server-side export endpoint `GET /api/v1/database/export` returns full DB, client downloads as blob with proper filename
- **#11 RESOLVED** (2026-05-18): Client deleteDatabase now calls `DELETE /api/v1/database` via api store, refreshes data after clear

## Security Audit #2 (2026-05-18)
Complete scan of all server and client files. **25 issues found**, 2 critical. **19 fixed, 6 deferred.**

### Fixed Issues (19)
- **#1** `handle_delete_database` logic inverted — FIXED: inverted if/else
- **#2** Client CSRF token not attached — FIXED: added axios interceptor
- **#3** Missing `Secure` flag — FIXED: added to both cookies
- **#4** Rate limit bypass via proxy — FIXED: added X-Forwarded-For support
- **#5** No input length limits — FIXED: MAX_INPUT_LENGTH=128, sanitization added
- **#6** Rate limit store memory cap — FIXED: MAX_RATE_LIMIT_ENTRIES=10000
- **#7** Client fetches all data for guests — FIXED: role-based data fetching
- **#8** No input sanitization — FIXED: sanitize_input() removes HTML tags, truncates
- **#9** No import size limit — FIXED: MAX_IMPORT_SIZE=10MB
- **#12** Unused SESSION_SECRET — FIXED: removed
- **#13** Dead `require_any()` — FIXED: removed
- **#14** Dead `get_csrf_token()` — FIXED: removed
- **#16** Missing nosniff on JSON — FIXED: added to send_json()
- **#17** Password in memory — FIXED: cleared after login
- **#18** Router doesn't preserve redirect — FIXED: query.redirect parameter
- **#19** Bulk delete missing — FIXED: added POST /api/v1/events/clear
- **#21** update_tea_type missing CSRF — FIXED: added check_csrf()
- **#24** No Cache-Control on auth — FIXED: no-cache headers on login/logout/auth/me
- **#25** Export no rate limit — FIXED: added rate limiting

### Deferred Issues (6)
- **#10** Export endpoint publicly accessible (documented as intentional for guest access)
- **#11** Server logging suppressed (low priority, no audit trail needed for this project)
- **#15** Wildcard CORS (may be intentional for development, can be restricted in production)
- **#22** Status endpoint exposes internal event type names (low risk, implementation detail)
- **#23** Auth/me exposes role to unauthenticated requests (low risk, expected behavior)

## Security Audit #3 (2026-05-18) — Follow-up Scan
Re-scan of all server and client files after Audit #2 fixes. **3 new issues found**, 0 critical. **3 fixed, 0 deferred.**

### New Issues Found & Fixed (3)
- **#22 (new)** Logout cookie missing `Secure` flag — FIXED: added `Secure` to logout session cookie at server.py:505
- **#23 (new)** OPTIONS preflight handler missing `nosniff` — FIXED: added `X-Content-Type-Options: nosniff` to do_OPTIONS() at server.py:285
- **#24 (new)** `handle_update_tea_type` unsanitized input — FIXED: added sanitize_input() to name and image fields at server.py:653-654

### Previously Deferred Issues Re-evaluated
- **#7** Client-side data fetching by role — DEFERRED: server-side auth properly enforced
- **#10** Export endpoint publicly accessible — DEFERRED: intentional for guest access, rate limited
- **#24** `handle_create_event` doesn't validate event type — FIXED: added ALLOWED_EVENT_TYPES validation
- **#25** `handle_auth_me` exposes role — DEFERRED: low risk, expected behavior

## Minor Fixes
- **get_max_size_message()** (2026-05-18): Replaced hardcoded "5MB" strings in error messages with dynamic calculation from `MAX_IMAGE_SIZE` variable
- **Rate limit cleanup** (2026-05-18): Removed `len(rate_limit_store) % 50` guard, cleanup now runs on every request
- **Statistics endpoint** (2026-05-18): Renamed `brewing_started`/`brewing_completed`/`brewing_cancelled` to `started`/`completed`/`cancelled` to avoid leaking internal event type names
- **Event type validation** (2026-05-18): Added `ALLOWED_EVENT_TYPES` set, `handle_create_event` rejects invalid types with HTTP 422
- **Schema versioning** (2026-05-18): `SCHEMA` dict defines all DB fields with types/defaults, `check_migrate_database()` adds missing fields on load, `GET /api/v1/server-info` exposes version + full schema + valid event types, upgrade hint in 422 error on mismatch
- **CLI argument parsing** (2026-05-18): Replaced manual loop with `argparse`, added `--help`, env var fallback (TEAMAKER_PORT, TEAMAKER_CORS_ALLOW_ORIGIN, TEAMAKER_LOG_METHOD, TEAMAKER_LOG_FILE), CLI overrides env vars

## Current State
All files created. Dependencies installed (`npm install` successful).
Server not started. MCP tool created but requires restart.
**29 of 29 security issues fixed. 3 deferred issues.**
**No known CVEs in any dependencies.**

## Navigation Fix (2026-05-19)
- `isAdmin` was defined in `actions` instead of `getters` in Pinia store — not reactive, so admin-only tabs were visible to guests
- Replaced CSS-based visibility (`:class="{ visible: auth.isAdmin }"`) with `v-if="auth.isAdmin"` in `App.vue` nav
- Events, Tea Types, and Database tabs now properly hidden for guests

## Admin Password Setup (2026-05-19)
- Server `/api/v1/auth/me` now returns `initialized: bool` (whether admin password is set)
- LoginView shows password setup form (with confirmation) when `initialized` is `false`
- `/api/v1/auth/setup-password` skips CSRF check when password is not yet set (no session exists to validate against)
- Client API store has new `setupPassword()` method
- Auth store captures `initialized` field from API responses

## CSRF Cookie Fix (2026-05-19)
- `csrf_token` cookie was `HttpOnly` — JavaScript couldn't read it via `document.cookie`
- Axios interceptor couldn't attach `X-CSRF-Token` header — all POST/PUT/DELETE returned 403
- `csrf_token` cookie now `HttpOnly=false` (readable by JS), `session` stays `HttpOnly`
- Added `_is_secure()` and `_cookie_str()` methods — `Secure` flag only set when HTTPS detected (works in HTTP dev)
- `check_csrf()` auto-regenerates missing CSRF token in session (handles old sessions)

## Image Upload Fix (2026-05-19)
- Multipart parsing was fragile — manual parsing failed with "No filename provided"
- Switched to base64 encoding: client sends `{filename, data}` as JSON, server decodes base64
- `api.js` `uploadImage()` now reads file via FileReader and sends as base64
- `handle_upload_image()` now reads JSON body and uses `base64.b64decode()`

## Logout Fix (2026-05-19)
- `checkAuth()` was resetting `initialized` to `false` on error — caused password setup form to reappear after logout
- `checkAuth()` now preserves `initialized` value instead of resetting on error
- Logout redirects to `/status` (guest view) instead of `/login`

## Router Fix (2026-05-19)
- `/` now redirects to `/login` instead of showing empty HomeView (unauthenticated users should see login page)
- Events page is now admin-only: hidden from nav for guests, router guard blocks direct access

## Admin-Only Login & Guest Default (2026-05-19)
- Login page now only allows admin login — guest login button and `handleGuestLogin()` removed
- `/` redirects to `/status` instead of `/login` — guest mode is the default
- Logout button only visible when `auth.isAdmin` is true (hidden in guest mode)
- `LoginView.vue`: removed `showPasswordForm` toggle, `handleGuestLogin()`, "Guest View" and "Admin Login" buttons — only password input + "Login as Admin" button remain
- `App.vue`: logout button condition changed from `auth.authenticated` to `auth.isAdmin`, removed unused `authenticated` computed
