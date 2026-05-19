# Security Audit Summary

**Date:** 2026-05-18
**Scope:** tea-server/server.py, tea-client/src/
**Status:** All critical, high, and medium-severity issues resolved. No remaining issues.

**29 of 29 security issues fixed. 0 deferred.**

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
