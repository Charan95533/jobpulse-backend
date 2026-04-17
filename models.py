"""
JobPulse Database Models
Uses SQLite for zero-config persistence.
"""

import sqlite3
import json
import os
from datetime import datetime
from config import Config


def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            email TEXT NOT NULL,
            name TEXT NOT NULL,
            skills TEXT NOT NULL,
            alert_frequency TEXT DEFAULT 'instant',
            min_match_score INTEGER DEFAULT 70,
            is_active INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            description TEXT,
            url TEXT,
            source TEXT,
            skills_found TEXT,
            match_score REAL DEFAULT 0,
            status TEXT DEFAULT 'new',
            posted_at TIMESTAMP,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alerts_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            email TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            jobs_found INTEGER DEFAULT 0,
            jobs_matched INTEGER DEFAULT 0,
            alerts_sent INTEGER DEFAULT 0,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Insert default settings if not exist
    existing = cursor.execute("SELECT id FROM user_settings WHERE id = 1").fetchone()
    if not existing:
        cursor.execute(
            "INSERT INTO user_settings (id, email, name, skills, alert_frequency, min_match_score) VALUES (?, ?, ?, ?, ?, ?)",
            (1, Config.USER_EMAIL, Config.USER_NAME,
             json.dumps(Config.DEFAULT_SKILLS),
             Config.ALERT_FREQUENCY, Config.MIN_MATCH_SCORE)
        )

    conn.commit()
    conn.close()


# ── User Settings CRUD ──

def get_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM user_settings WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {
            "email": row["email"],
            "name": row["name"],
            "skills": json.loads(row["skills"]),
            "alert_frequency": row["alert_frequency"],
            "min_match_score": row["min_match_score"],
            "is_active": bool(row["is_active"]),
        }
    return None


def update_settings(**kwargs):
    conn = get_db()
    settings = get_settings()
    settings.update(kwargs)
    if "skills" in kwargs and isinstance(kwargs["skills"], list):
        settings["skills"] = json.dumps(kwargs["skills"])
    elif "skills" in settings and isinstance(settings["skills"], list):
        settings["skills"] = json.dumps(settings["skills"])

    conn.execute("""
        UPDATE user_settings
        SET email = ?, name = ?, skills = ?, alert_frequency = ?,
            min_match_score = ?, updated_at = ?
        WHERE id = 1
    """, (
        settings["email"], settings["name"], settings["skills"],
        settings["alert_frequency"], settings["min_match_score"],
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


# ── Jobs CRUD ──

def save_job(job_data):
    """Save a job, skip if already exists (by external_id)."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs
            (external_id, title, company, location, description, url, source,
             skills_found, match_score, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_data.get("external_id"),
            job_data.get("title"),
            job_data.get("company"),
            job_data.get("location"),
            job_data.get("description", ""),
            job_data.get("url"),
            job_data.get("source"),
            json.dumps(job_data.get("skills_found", [])),
            job_data.get("match_score", 0),
            job_data.get("posted_at"),
        ))
        conn.commit()
        return conn.execute(
            "SELECT id FROM jobs WHERE external_id = ?",
            (job_data["external_id"],)
        ).fetchone()["id"]
    except Exception:
        return None
    finally:
        conn.close()


def get_recent_jobs(limit=20, min_score=70):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM jobs
        WHERE match_score >= ?
        ORDER BY scraped_at DESC
        LIMIT ?
    """, (min_score, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unsent_jobs():
    """Get matched jobs that haven't been emailed yet."""
    conn = get_db()
    settings = get_settings()
    rows = conn.execute("""
        SELECT j.* FROM jobs j
        LEFT JOIN alerts_sent a ON j.id = a.job_id
        WHERE a.id IS NULL
          AND j.match_score >= ?
        ORDER BY j.match_score DESC
    """, (settings["min_match_score"],)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_alert_sent(job_id, email):
    conn = get_db()
    conn.execute(
        "INSERT INTO alerts_sent (job_id, email) VALUES (?, ?)",
        (job_id, email)
    )
    conn.commit()
    conn.close()


def log_scan(source, jobs_found, jobs_matched, alerts_sent):
    conn = get_db()
    conn.execute(
        "INSERT INTO scan_log (source, jobs_found, jobs_matched, alerts_sent) VALUES (?, ?, ?, ?)",
        (source, jobs_found, jobs_matched, alerts_sent)
    )
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    total_jobs = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
    matched_jobs = conn.execute(
        "SELECT COUNT(*) as c FROM jobs WHERE match_score >= 70"
    ).fetchone()["c"]
    alerts_count = conn.execute("SELECT COUNT(*) as c FROM alerts_sent").fetchone()["c"]
    last_scan = conn.execute(
        "SELECT scanned_at FROM scan_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {
        "total_jobs_scraped": total_jobs,
        "matched_jobs": matched_jobs,
        "alerts_sent": alerts_count,
        "last_scan": last_scan["scanned_at"] if last_scan else None,
    }


# Initialize on import
init_db()
