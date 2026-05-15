import os
import glob
import tempfile
import yt_dlp
from database import update_job
from gdrive import upload_file


def run_job(job_id: str, url: str, folder_id: str | None = None):
    """Download url with yt-dlp, upload result to Google Drive."""
    update_job(job_id, status="downloading", progress="Starting download…")

    with tempfile.TemporaryDirectory() as tmpdir:
        last_pct = [""]

        def progress_hook(d: dict):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "?").strip()
                eta = d.get("_eta_str", "?").strip()
                msg = f"Downloading {pct} · {speed} · ETA {eta}"
                if pct != last_pct[0]:
                    last_pct[0] = pct
                    update_job(job_id, progress=msg)
            elif d["status"] == "finished":
                update_job(
                    job_id,
                    status="processing",
                    progress="Download done — processing / merging…",
                )

        ydl_opts: dict = {
            "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            # best mp4 with audio; fallback to best single file
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
        }

        proxy = os.getenv("PROXY", "").strip()
        if proxy:
            ydl_opts["proxy"] = proxy

        no_check_cert = os.getenv("NO_CHECK_CERT", "").lower() in ("1", "true", "yes")
        if no_check_cert:
            ydl_opts["nocheckcertificate"] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            update_job(job_id, status="error", error=str(e))
            return
        except Exception as e:
            update_job(job_id, status="error", error=f"Unexpected error: {e}")
            return

        # Find the output file (yt-dlp may change extension after merge)
        files = [
            f for f in glob.glob(os.path.join(tmpdir, "*"))
            if not f.endswith(".part") and not f.endswith(".ytdl")
            and os.path.isfile(f)
        ]
        if not files:
            update_job(job_id, status="error", error="No output file found after download.")
            return

        # If multiple files, take the largest (the merged video)
        filepath = max(files, key=os.path.getsize)
        filename = os.path.basename(filepath)
        size_mb = os.path.getsize(filepath) / 1_048_576

        update_job(
            job_id,
            status="uploading",
            progress=f"Uploading {filename} ({size_mb:.1f} MB) to Google Drive…",
        )

        try:
            result = upload_file(filepath, filename, folder_id)
            link = result.get("webViewLink", "")
            update_job(
                job_id,
                status="done",
                progress="Done!",
                result=link,
            )
        except Exception as e:
            update_job(job_id, status="error", error=f"Upload failed: {e}")
