import os
import uuid
import threading
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

from database import init_db, create_job, get_job, list_jobs
from gdrive import (
    has_credentials_file,
    is_authorized,
    start_auth_flow,
    complete_auth_flow,
    CREDENTIALS_PATH,
    DATA_DIR,
)
from worker import run_job

app = FastAPI(title="VPS Downloader")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

init_db()


# ── Pages ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "has_creds": has_credentials_file(),
        "authorized": is_authorized(),
    })


# ── Setup: upload credentials.json ─────────────────────────────────────────

@app.post("/setup/credentials")
async def upload_credentials(file: UploadFile = File(...)):
    os.makedirs(DATA_DIR, exist_ok=True)
    content = await file.read()
    # Basic sanity check
    try:
        import json
        parsed = json.loads(content)
        assert "installed" in parsed or "web" in parsed
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid credentials.json file."}, status_code=400)
    with open(CREDENTIALS_PATH, "wb") as f:
        f.write(content)
    return JSONResponse({"ok": True})


# ── OAuth ───────────────────────────────────────────────────────────────────

@app.get("/auth/start")
async def auth_start():
    if not has_credentials_file():
        return JSONResponse({"error": "credentials.json not uploaded yet."}, status_code=400)
    try:
        url = start_auth_flow()
        return JSONResponse({"auth_url": url})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/auth/code")
async def auth_code(request: Request):
    data = await request.json()
    code = data.get("code", "").strip()
    if not code:
        return JSONResponse({"ok": False, "error": "Code is required."}, status_code=400)
    try:
        complete_auth_flow(code)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


# ── Download ────────────────────────────────────────────────────────────────

@app.post("/download")
async def start_download(request: Request):
    if not is_authorized():
        return JSONResponse({"error": "Not connected to Google Drive."}, status_code=401)

    data = await request.json()
    url = data.get("url", "").strip()
    folder_id = data.get("folder_id", "").strip() or None

    if not url:
        return JSONResponse({"error": "URL is required."}, status_code=400)

    job_id = str(uuid.uuid4())
    create_job(job_id, url)

    t = threading.Thread(target=run_job, args=(job_id, url, folder_id), daemon=True)
    t.start()

    return JSONResponse({"job_id": job_id})


# ── Status ──────────────────────────────────────────────────────────────────

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Not found."}, status_code=404)
    return JSONResponse(job)


@app.get("/jobs")
async def jobs_list():
    return JSONResponse(list_jobs())
