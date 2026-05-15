# Madmin

Download anything yt-dlp supports → directly to your Google Drive.
Self-hosted on your VPS, simple web UI.

## Requirements

- Docker + Docker Compose
- A Google Cloud project (free tier is fine)

---

## Setup

### 1. Clone and configure

```bash
git clone <your-repo>
cd vps-downloader
cp .env.example .env
mkdir data
```

Edit `.env` if you need a proxy.

### 2. Create Google OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google Drive API**:
   - APIs & Services → Enable APIs → search "Google Drive API" → Enable
4. Create credentials:
   - APIs & Services → Credentials → Create Credentials → **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
   - Name: anything (e.g. "VPS Downloader")
   - Click Create → **Download JSON**

### 3. Run

```bash
docker compose up -d
```

Open **http://your-server-ip:8000** in your browser.

### 4. First-time setup (in the web UI)

1. Upload the `credentials.json` file you downloaded from Google Cloud
2. Click **Get authorization URL** → open the URL in your browser → approve access → paste the code back
3. Done — start pasting URLs!

---

## Usage

- Paste any URL supported by yt-dlp (YouTube, Vimeo, Twitter/X, direct links, etc.)
- Optionally provide a Google Drive **folder ID** (the last part of the folder's URL)
- Click **Send to Drive** — the download progress is shown in real time

---

## Security note

The web UI has no authentication. If your VPS is public, either:
- Put it behind a reverse proxy (nginx) with HTTP Basic Auth
- Bind to localhost and use SSH tunneling: `ssh -L 8000:localhost:8000 user@your-vps`

---

## Updating yt-dlp

YouTube changes frequently. To update yt-dlp without rebuilding:

```bash
docker compose exec app pip install -U yt-dlp
```

Or just rebuild:

```bash
docker compose build --no-cache && docker compose up -d
```
