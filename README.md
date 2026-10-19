# blindxss-lite

A lightweight Blind XSS (Cross-Site Scripting) collector and payload server built with Flask. It serves a JavaScript payload that captures victim browser data (cookies, localStorage, DOM snippets, etc.) and forwards it to a SQLite-backed dashboard protected by HTTP Basic Auth.

## Features

- **Payload delivery** — `/p.js` serves a self-contained JS payload using `sendBeacon` or `fetch`
- **Collector endpoints** — POST `/c` (JSON/FormData) and GET `/c.gif` (CSP-friendly pixel beacon)
- **Admin dashboard** — `/events` lists captured events, `/events/<id>/view` shows full details
- **Payload generator** — `/payloads` offers 14 XSS payload variants plus a custom JS editor
- **HTTP Basic Auth** — admin routes protected by `ADMIN_USER` / `ADMIN_PASSWORD`
- **SQLite persistence** — database auto-created on first run; deleting `bxss.db` rebuilds it fresh
- **Docker-ready** — `Dockerfile` and `docker-compose.yml` included
- **Rate limiting** — SQLite-backed sliding-window limiter for collector endpoints (shared across workers)

## Quick Start

### Docker Compose

```bash
# Set credentials
echo "ADMIN_USER=admin" > .env
echo "ADMIN_PASSWORD=your-admin-password" >> .env

# Build and run
docker compose up -d --build
```

Dashboard: <http://127.0.0.1:8089/events> (browser will prompt for Basic Auth)

### Without Docker

```bash
pip install -r requirements.txt
export ADMIN_USER="admin"
export ADMIN_PASSWORD="your-admin-password"
gunicorn -b 127.0.0.1:8080 --workers 2 --threads 4 wsgi:app
```

## Usage

1. Visit `/payloads` (after authenticating) to copy an XSS payload.
2. Inject the payload into a target input field suspected of Blind XSS.
3. When a victim loads the page, the payload runs and sends their data to your server.
4. View captured events at `/events`.

## Endpoints

### Collector (public, no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/p.js` | XSS payload JavaScript |
| POST | `/c` | Receives JSON/FormData from payload |
| GET | `/c.gif` | Pixel beacon (CSP-friendly) |

### Admin (HTTP Basic Auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/events` | Last 500 events |
| GET | `/events/<id>` | Event detail as JSON |
| GET | `/events/<id>/view` | Event detail as HTML |
| GET/POST | `/payloads` | Payload generator + custom JS editor |

### Utility

| Method | Path | Description |
|--------|------|-------------|
| GET | `/_healthz` | Health check |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USER` | `admin` | Dashboard username |
| `ADMIN_PASSWORD` | *(required)* | Dashboard password — startup fails if unset |
| `DB_PATH` | `./bxss.db` | SQLite database path |
| `PUBLIC_URL` | *(empty)* | Public base URL for generated payloads (use when behind a tunnel/reverse proxy; falls back to request host) |
| `TRUST_PROXY` | *(empty)* | Set `1` to trust `X-Forwarded-For`/`CF-Connecting-IP` for client IP (only when behind a trusted reverse proxy; required there or all clients share the proxy IP for rate limiting) |
| `MAX_BODY` | `524288` | Max collector body size (bytes) |
| `RATE_LIMIT_COUNT` | `60` | Max collector requests per window (per IP) |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `LOG_LEVEL` | `INFO` | Python logging level |

> Custom JS is edited and stored via the `/payloads` admin page (persisted in the SQLite `settings` table) and appended to `/p.js`. It is no longer read from a file.

## Project Structure

```
blindxss-lite/
├── wsgi.py              # WSGI entry point
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image
├── docker-compose.yml   # Compose config
├── .env                 # Credentials (don't commit)
└── app/
    ├── __init__.py      # App factory, CORS, health check
    ├── config.py        # Config + .env loader
    ├── db.py            # SQLite layer
    ├── collectors.py    # /p.js, /c, /c.gif
    ├── events.py        # /events admin
    ├── payloads.py      # /payloads admin
    ├── utils.py         # Helpers + Basic Auth decorator
    ├── static/
    │   └── style.css
    └── templates/
        ├── events.html
        ├── event.html
        └── payloads.html
```

## Payload Data Collected

- Document title and URL
- Origin and referrer
- `document.cookie`
- User agent
- localStorage and sessionStorage (all keys)
- DOM snippet (first 200KB, zlib+base64 compressed)

## Showcase
Payloads:
![Payload Page](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiAYXF2l8PBFoYrzEXGAO6dsyqb3Jdv6emctJwyAZ4G4bwW4XWLUb-_JRpOqACmE_hyphenhyphenfNEhQbKC0nfdOyru1e5vyRio9ux93t3fm-nkcU_XG2vCKK2P2R4Q4Vflm2QYYVQ07LSsYE4fXBHvmBrAiBKyPnVQ-WFtODSWBJJcGwhc_F4MO6j3rp9B5HUIa2w/s961/payloads.png)

Result:
![](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiCGLiaWIXAmuIoFYzEUj8BGxc_-QG0i8qXqba4_Gctnj6eL6MtRQFovP9i5j6149ZZfG5qNBv1jciy7IL_EvEC3ojtNchGXqJKpEHj-xJwuZnjXQBuieoLGJqVEuzlC2JiEkReFFXrT6k48XLgNZgFqgVFrVYFDFoQj9ZOapF7LJsX2LUHxtA5dCri6v8/s937/bxss%20data.png)

Result detail:
![](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjCQ1gaOTOC30X8857DScHOV-TX1Tn_MyulK2M35ZGF2DND14ru8LPAB-WEn60E0ysP9xZ_bMOy5GIMvi0pn1PNXP4KMclTTpB8DCU9YjKUEDkYSP41SaqFK8jwl0eHZxtqoYw960Y1ferXjD5sA9lMbxLrWTMI8ib5Kb6NisXSlQfYctVaJNKpl9nxnqk/s911/events%20detail.png)
## Security Notes

- Admin routes require HTTP Basic Auth. Use a strong password in production.
- Collector endpoints are intentionally unauthenticated.
- All origins are allowed for CORS so payloads can send data from any site.
- SQLite-backed rate limiting helps mitigate collector abuse and is shared across workers.
- `.env` should never be committed to version control.