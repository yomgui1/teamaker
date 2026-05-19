# Tea Production Manager — Agent Instructions

## Quick Start
```bash
# Server (Python stdlib only, no frameworks)
cd tea-server && python server.py [--port 5000] [--cors origin,origin] [--log file] [--log-file path]
# All args support env var fallback: TEAMAKER_PORT, TEAMAKER_CORS_ALLOW_ORIGIN, TEAMAKER_LOG_METHOD, TEAMAKER_LOG_FILE
# CLI args override env vars. Use --help for full list.

# Client (Vite dev server proxies /api and /image to server port 5000)
cd tea-client && npm install && npm run dev
```

## Architecture
- **Server:** `tea-server/server.py` — single-file stdlib HTTP server, `database.json` for persistence
- **Client:** `tea-client/src/` — Vue 3 + Pinia + Vue Router + Axios
- **Dev proxy:** Vite forwards `/api` and `/image` → `http://127.0.0.1:5000`
- **CLI args:** `--port`, `--cors` (comma-separated origins or `*`), `--log stderr|file`, `--log-file`

## Security Constraints (always verify when modifying)
- **Auth:** session-based, HttpOnly + Secure cookies, PBKDF2-HMAC-SHA256 (200k iterations)
- **CSRF:** double-submit cookie pattern — all state-changing endpoints require `X-CSRF-Token` header
  - Client sends it via axios interceptor (`api.js` line 4-11)
  - Server checks via `check_csrf()` — never skip this on new endpoints
- **Rate limiting:** 100 req/60s general, 10 req/60s login + 300s cooldown
- **Input sanitization:** `sanitize_input()` strips HTML tags, `sanitize_description()` for longer text
- **Image upload:** magic bytes validation, 5MB limit, extension whitelist
- **Path traversal:** `realpath` validation on all file serving
- **Database locking:** `threading.Lock()` via `read_db()` / `update_db()` — always use `update_db(func)` for writes
- **Atomic writes:** `os.replace()` tmp → final path

## Admin Gatekeeping
- Server-side: `require_admin()` checks session role == "admin"
- Client-side: router guard (`router/index.js:49-54`) blocks `/tea-types` and `/database` for non-admin
- **Important:** router guard only blocks navigation — `App.vue:51-67` conditionally fetches data based on role
- Adding a new admin-only route requires BOTH: `meta: { requiresAdmin: true }` in router AND `require_admin()` in server

## Schema Versioning
- `SCHEMA_VERSION` constant in `server.py` — bump when DB structure changes
- `schema_version` field in `database.json` — auto-migrated by `check_migrate_database()` on server start
- Valid event types: `ALLOWED_EVENT_TYPES` set — server rejects unknown types with HTTP 422
- New event types: add to `ALLOWED_EVENT_TYPES` + bump `SCHEMA_VERSION`
- Query current state: `GET /api/v1/server-info`

## Event Types
- Server returns statistics with `started`/`completed`/`cancelled` keys (not `brewing_started` etc.)
- `StatisticsView.vue` reads `stat.started`, `stat.completed`, `stat.cancelled` — don't reference old names

## CSRF Gotcha
- Login endpoint does NOT require CSRF (it sets the token)
- All other state-changing endpoints DO require CSRF
- `importDatabase` sends raw JSON string with `Content-Type: application/json` — not multipart/form-data

## Deferred Issues (ISSUES.md)
- #7 Client-side admin checks bypassable — server-side enforced, client-side is convenience
- #10 Export endpoint publicly accessible — intentional, rate-limited
- #24 `/api/v1/auth/me` exposes role — low risk, expected behavior

## Files to Reference
- `MEMORIES.md` — full project context, security notes, fix history
- `ISSUES.md` — deferred security issues
- `diaMCP-AGENTS.md` — diaMCP tool creation instructions (not repo-specific)
