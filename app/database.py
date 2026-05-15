import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "/data/jobs.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id       TEXT PRIMARY KEY,
            url      TEXT NOT NULL,
            status   TEXT NOT NULL DEFAULT 'pending',
            progress TEXT NOT NULL DEFAULT '',
            result   TEXT,
            error    TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_job(job_id: str, url: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO jobs (id, url, status, progress, created_at) VALUES (?, ?, 'pending', 'Queued', ?)",
        (job_id, url, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def update_job(job_id: str, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    conn = get_conn()
    conn.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_job(job_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_jobs(limit: int = 30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
