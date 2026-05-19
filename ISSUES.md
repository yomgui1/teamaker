# Deferred Security Issues

**Date:** 2026-05-18
**Scope:** tea-server/server.py, tea-client/src/
**Note:** All critical, high, and medium-severity issues have been resolved. Only low-priority deferred issues remain.

---

## HIGH

### 7. Client-side admin checks bypassable via direct API calls
**File:** `tea-client/src/App.vue:51-66`
The router guard only prevents navigation. The App.vue component fetches all data on mount regardless of role, and there's no client-side protection against calling admin endpoints directly via browser devtools.
**Rationale:** Server-side auth is properly enforced. Client-side protection is a convenience feature.

---

### 10. `handle_export_database` is publicly accessible
**File:** `tea-server/server.py:923-942`
The export endpoint is a GET request with no authentication. While the exported data (tea_types and events) is not sensitive, it reveals the full database structure.
**Rationale:** Intentional for guest access. Rate limiting has been added to prevent abuse.

---

## LOW

### 24. `handle_auth_me` exposes role information
**File:** `tea-server/server.py:436-442`
The `/api/v1/auth/me` endpoint returns the user's role (`admin` or `guest`) to any request, even unauthenticated ones.
**Rationale:** Low risk, expected behavior.

---

## Summary

| Severity | Count |
|----------|-------|
| High | 2 |
| Low | 1 |
| **Total** | **3** |

## Schema Versioning

**Feature:** Database schema versioning with field-level auto-migration

- `SCHEMA` dict defines all DB fields with types and defaults
- `schema_version` field stored in `database.json`
- `check_migrate_database()` adds missing fields with defaults, bumps version
- `GET /api/v1/server-info` returns schema version, full schema definition, and valid event types
- Event type validation returns HTTP 422 with upgrade hint on mismatch
- When adding new fields: add to `SCHEMA` dict + bump `SCHEMA_VERSION`

## Deployment Features

- **`--host` CLI option** (2026-05-19): Server hostname configurable via `--host` flag or `TEAMAKER_HOST` env var (default: `127.0.0.1`)
- **`VITE_API_BASE_URL`** (2026-05-19): Client API/image URLs configurable via Vite env var for behind-proxy deployments (e.g. nginx)

## Dependencies

- Vite 8.0.13 (latest)
- @vitejs/plugin-vue 6.0.7 (supports Vite 5-8)
- Vue 3.5.34 (latest)
- axios 1.16.1 (latest)
- pinia 2.3.1 (latest)
- vue-router 4.3.0 (latest)
- **0 known CVEs**
