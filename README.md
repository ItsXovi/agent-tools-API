# PDF Toolkit API

Self-serve **PDF processing API** — merge, split, compress, and watermark PDF files. Metered API keys with monthly usage limits.

## Features

- `POST /v1/pdf/merge` — merge multiple PDFs into one
- `POST /v1/pdf/split` — split by page ranges or extract every page
- `POST /v1/pdf/compress` — reduce PDF file size
- `POST /v1/pdf/watermark` — add a text watermark
- `GET /v1/usage` — monthly conversion usage for your API key
- `POST /v1/keys` — create API keys (admin only)

## Quick start

**Requires real Python 3.11+** (not the Microsoft Store stub).

1. Install from https://www.python.org/downloads/ — check **Add python.exe to PATH**
2. Disable Store aliases: **Settings → Apps → Advanced app settings → App execution aliases** → turn OFF `python.exe` and `python3.exe`
3. Run:

```powershell
cd C:\Users\gdick\agent-tools-api
.\run.ps1
```

Open http://localhost:8000/docs

## Examples

### Merge PDFs

```bash
curl -X POST https://YOUR_DOMAIN/v1/pdf/merge \
  -H "X-API-Key: atk_your_key_here" \
  -F "files=@chapter1.pdf" \
  -F "files=@chapter2.pdf" \
  --output merged.pdf
```

### Split PDF

```bash
# Single range → returns one PDF
curl -X POST "https://YOUR_DOMAIN/v1/pdf/split?pages=1-3" \
  -H "X-API-Key: atk_your_key_here" \
  -F "file=@document.pdf" \
  --output pages_1-3.pdf

# Multiple ranges or "all" → returns ZIP
curl -X POST "https://YOUR_DOMAIN/v1/pdf/split?pages=all" \
  -H "X-API-Key: atk_your_key_here" \
  -F "file=@document.pdf" \
  --output split.zip
```

### Compress PDF

```bash
curl -X POST https://YOUR_DOMAIN/v1/pdf/compress \
  -H "X-API-Key: atk_your_key_here" \
  -F "file=@large.pdf" \
  --output compressed.pdf
```

### Watermark PDF

```bash
curl -X POST "https://YOUR_DOMAIN/v1/pdf/watermark?text=CONFIDENTIAL&position=center" \
  -H "X-API-Key: atk_your_key_here" \
  -F "file=@document.pdf" \
  --output watermarked.pdf
```

Positions: `center` (default), `top`, `bottom`, `diagonal`.

## API keys and usage

Each customer gets a per-key monthly conversion limit. Each PDF operation counts as **1 conversion**.

| Tier | Limit / month | Suggested price |
|------|----------------|-----------------|
| `free` | 50 | Free |
| `indie` (Pro) | 2,000 | $25/mo |
| `team` | 10,000 | Custom |

Conversion endpoints: `POST /v1/pdf/merge`, `/v1/pdf/split`, `/v1/pdf/compress`, `/v1/pdf/watermark`.

Responses include rate-limit headers:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (Unix timestamp; resets on the 1st of each month UTC)

When over limit, the API returns **429** with the same headers.

### Create your first key

**Option A — CLI (local / bootstrap):**

```powershell
python scripts/create_key.py --label "my app" --tier free
```

**Option B — Admin API (production):**

```bash
curl -X POST https://YOUR_DOMAIN/v1/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: your-admin-secret" \
  -d '{"label":"my app","tier":"free"}'
```

Save the returned `api_key` — it is shown only once.

### Check usage

```bash
curl https://YOUR_DOMAIN/v1/usage -H "X-API-Key: atk_your_key_here"
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REQUIRE_API_KEY` | `false` | Require `X-API-Key` on PDF endpoints |
| `ADMIN_SECRET` | _(empty)_ | Secret for `POST /v1/keys` (`X-Admin-Secret` header) |
| `DATABASE_PATH` | `data/agent_tools.db` | SQLite path for keys and usage |
| `MAX_PDF_BYTES` | `10485760` | Max upload size per file (10 MB) |
| `DEBUG` | `false` | Enable debug mode |

Example `.env` for production:

```
REQUIRE_API_KEY=true
ADMIN_SECRET=change-me-to-a-long-random-string
DATABASE_PATH=/app/data/agent_tools.db
MAX_PDF_BYTES=10485760
```

## Tests

```powershell
pip install -r requirements.txt
python -m pytest tests -q
```

## Deploy

### Docker

```bash
docker build -t pdf-toolkit-api .
docker run -p 8000:8000 \
  -e REQUIRE_API_KEY=true \
  -e ADMIN_SECRET=your-secret \
  -v pdf-toolkit-data:/app/data \
  pdf-toolkit-api
```

### Railway

Deploy from the [Railway dashboard](https://railway.app) (GitHub) or the Railway CLI (local folder). The repo includes `Dockerfile` and `railway.toml` (Docker build + `GET /health` health check).

#### Option A — Deploy from GitHub (recommended)

1. Push this project to a GitHub repo (Railway needs committed code):
   ```powershell
   cd C:\Users\gdick\agent-tools-api
   git add .
   git commit -m "Initial PDF Toolkit API"
   git remote add origin https://github.com/ItsXovi/agent-tools-api.git
   git push -u origin main
   ```
2. In Railway: **New Project** → **Deploy from GitHub repo**
3. Select your repo. Railway detects `railway.toml` and builds from the Dockerfile.
4. Continue with **Environment variables**, **Volume**, and **Public URL** below.

#### Option B — Deploy from local folder (CLI)

Install the CLI (requires Node.js):

```powershell
npm install -g @railway/cli
railway login
cd C:\Users\gdick\agent-tools-api
railway init          # create a new project
railway up            # build and deploy from this folder
```

No git commit is required for `railway up` — it uploads your local files.

#### Environment variables (required)

In Railway: open your **service** → **Variables** → **Raw Editor** and paste:

```
REQUIRE_API_KEY=true
ADMIN_SECRET=change-me-to-a-long-random-string
DATABASE_PATH=/app/data/agent_tools.db
MAX_PDF_BYTES=10485760
```

| Variable | Value | Notes |
|----------|-------|-------|
| `REQUIRE_API_KEY` | `true` | Require `X-API-Key` on PDF endpoints |
| `ADMIN_SECRET` | *(generate your own)* | Protects `POST /v1/keys`; run `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_PATH` | `/app/data/agent_tools.db` | SQLite file inside the persistent volume |
| `MAX_PDF_BYTES` | `10485760` | Max upload size per file (10 MB) |

Optional: `DEBUG=false`. See `.env.example` for local defaults.

**Do not set `PORT`** — Railway injects it automatically; the Dockerfile binds to `${PORT:-8000}`.

#### Persistent volume (SQLite)

Without a volume, API keys and usage reset on every redeploy.

1. Open your **service** in Railway
2. Click **Volumes** (or **Settings** → **Volumes**)
3. **Add Volume**
4. **Mount path:** `/app/data`
5. Save — Railway redeploys the service

The app creates `/app/data/agent_tools.db` on first start (`DATABASE_PATH` must match).

#### Public URL

1. Open your **service** → **Settings** → **Networking**
2. Click **Generate Domain** (or **Add Public Domain**)
3. Copy the URL, e.g. `https://pdf-toolkit-api-production-xxxx.up.railway.app`

#### Create your first API key (production)

**Option A — Admin API (easiest after deploy):**

```powershell
curl -X POST https://YOUR_RAILWAY_DOMAIN/v1/keys `
  -H "Content-Type: application/json" `
  -H "X-Admin-Secret: your-admin-secret" `
  -d '{\"label\":\"my app\",\"tier\":\"free\"}'
```

Save the `api_key` from the JSON response — it is shown only once.

**Option B — CLI against production DB:** not practical on Railway (SQLite lives on the volume inside the container). Use Option A.

#### Verify deployment

```powershell
# Health check (no auth)
curl https://YOUR_RAILWAY_DOMAIN/health

# Usage (with your new key)
curl https://YOUR_RAILWAY_DOMAIN/v1/usage -H "X-API-Key: atk_your_key_here"
```

Expected health response: `{"status":"ok","version":"0.2.0"}`

Interactive docs: `https://YOUR_RAILWAY_DOMAIN/docs`


### Fly.io / Render

Same Docker image works on any container host. Set `PORT` if the platform provides it (the Dockerfile uses `${PORT:-8000}`).

Health check: `GET /health`

## RapidAPI listing blurb

> **PDF Toolkit API** — Merge, split, compress, and watermark PDF files with a simple REST API. Upload files via multipart form data, get back processed PDFs (or ZIP for multi-part splits). Free tier: 50 operations/month. Pro: 2,000 operations/month for $25. API key authentication, usage metering, and rate-limit headers included.

## Monetization path

1. Deploy with per-customer API keys and usage metering (this release)
2. List on [RapidAPI](https://rapidapi.com) — use the blurb above; map Pro tier to `indie` keys
3. Add Stripe metered billing for paid tiers
4. Cross-list on [Postman API Network](https://www.postman.com/explore)

## License

MIT
