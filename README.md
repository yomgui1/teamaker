# Tea Production Manager

A complete tea production management system with a Python REST backend and Vue.js 3 frontend.

## Features

- **Tea Brewing Tracking** — Start, complete, or cancel brewing sessions
- **Tea Types Management** — Add/edit/remove tea types with images (admin only)
- **Statistics Dashboard** — Production stats by tea type and month
- **Event Log** — Configurable event history with filtering
- **Database Management** — Export/import database (admin only)
- **Admin & Guest Modes** — Role-based access control
- **Dark Mode** — Toggle between light and dark themes
- **diaMCP Integration** — Query tea status from the agent

## Quick Start

### Server (Python stdlib only, no frameworks)

```bash
cd tea-server
python server.py [--host 127.0.0.1] [--port 5000] [--cors origin,origin]
```

All args support env var fallback: `TEAMAKER_HOST`, `TEAMAKER_PORT`, `TEAMAKER_CORS_ALLOW_ORIGIN`

### Client (Vite dev server)

```bash
cd tea-client
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

### Systemd (user service)

Install the server script and the systemd user service:

```bash
cp tea-server/server.py ~/.local/bin/teamaker-server.py
cp tea-server/tea-server.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start tea-server
systemctl --user enable tea-server   # auto-start on login
```

Configuration is done via environment variables: `TEAMAKER_HOST`, `TEAMAKER_PORT`, `TEAMAKER_CORS_ALLOW_ORIGIN`, `TEAMAKER_LOG_METHOD`, `TEAMAKER_LOG_FILE`

Check status and logs:

```bash
systemctl --user status tea-server
journalctl --user -u tea-server -f
```

### Behind a reverse proxy (nginx)

Set `VITE_API_BASE_URL` in a `.env.production` file (e.g. `VITE_API_BASE_URL=/tea`) and build:

```bash
cd tea-client
npm run build
```

Serve the `dist/` folder via nginx, proxying `/api/` and `/image/` to the backend.

## Architecture

- **Server:** `tea-server/server.py` — single-file stdlib HTTP server, `database.json` for persistence
- **Client:** `tea-client/src/` — Vue 3 + Pinia + Vue Router + Axios
- **Dev proxy:** Vite forwards `/api` and `/image` → `http://127.0.0.1:5000`
- **Behind proxy:** `VITE_API_BASE_URL` env var prefixes all API/image URLs

## Security

- Session-based auth with HttpOnly + Secure cookies
- PBKDF2-HMAC-SHA256 (200k iterations) password hashing
- CSRF double-submit cookie protection
- Rate limiting: 100 req/60s general, 10 req/60s login + 300s cooldown
- Input sanitization and length limits
- Image upload: magic bytes validation, 5MB limit, extension whitelist
- Path traversal protection on file serving
- Database locking with `threading.Lock()` and atomic writes

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/status` | Any | Get latest tea status |
| POST | `/api/v1/status` | Admin | Update status |
| POST | `/api/v1/auth/login` | — | Login (admin only) |
| POST | `/api/v1/auth/setup-password` | — | Set initial admin password |
| POST | `/api/v1/auth/change-password` | Admin | Change admin password |
| DELETE | `/api/v1/auth/logout` | Any | Logout |
| GET | `/api/v1/auth/me` | — | Check auth state |
| GET | `/api/v1/tea-types` | Any | List tea types |
| POST | `/api/v1/tea-types` | Admin | Create tea type |
| PUT | `/api/v1/tea-types?id=X` | Admin | Update tea type |
| DELETE | `/api/v1/tea-types?id=X` | Admin | Delete tea type |
| GET | `/api/v1/events?limit=N` | Any | List events |
| POST | `/api/v1/events` | Admin | Create event |
| POST | `/api/v1/events/brewing/start` | Admin | Start brewing |
| POST | `/api/v1/events/brewing/complete` | Admin | Complete brewing |
| POST | `/api/v1/events/brewing/cancel` | Admin | Cancel brewing |
| POST | `/api/v1/events/clear` | Admin | Clear all events |
| GET | `/api/v1/statistics` | Any | Get statistics |
| POST | `/api/v1/upload-image` | Admin | Upload image |
| GET | `/image/{filename}` | Any | Serve image |
| POST | `/api/v1/database/import` | Admin | Import database |
| DELETE | `/api/v1/database` | Admin | Delete all data |
| GET | `/api/v1/database/export` | Any | Export database |
| GET | `/api/v1/server-info` | Any | Get schema version |

## Directory Structure

```
teamaker/
├── tea-server/
│   ├── server.py               # Main REST server
│   ├── tea-server.service      # systemd user service unit
│   ├── database.json           # JSON database (auto-created)
│   └── image/                  # Tea image storage
├── tea-client/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.vue
│       ├── main.js
│       ├── styles.css
│       ├── router/
│       ├── stores/
│       └── views/
│           ├── CoffeeView.vue
│           ├── DatabaseView.vue
│           ├── EventsView.vue
│           ├── LoginView.vue
│           ├── StatisticsView.vue
│           ├── StatusView.vue
│           └── TeaTypesView.vue
├── AGENTS.md
├── diaMCP-AGENTS.md
├── LICENSE
└── MEMORIES.md
```

## License

MIT License

Copyright (c) 2026 RogDesign

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
