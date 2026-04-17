"""
JobPulse REST API
Flask server that powers the frontend dashboard.

Endpoints:
    GET  /api/skills       — Get tracked skills
    POST /api/skills       — Update tracked skills
    GET  /api/alerts       — Get recent matched jobs
    POST /api/settings     — Update email/frequency settings
    POST /api/scan         — Trigger manual scan
    GET  /api/stats        — Dashboard statistics
"""

import json
import logging
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from models import (
    get_settings, update_settings,
    get_recent_jobs, get_stats, init_db
)
from scheduler import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app = Flask(__name__)
CORS(app)  # Allow frontend to connect

init_db()


# ── Health check ──
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "JobPulse API",
        "version": "1.0.0",
        "status": "running",
    })


# ── Get current settings ──
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    settings = get_settings()
    if settings:
        return jsonify(settings)
    return jsonify({"error": "No settings found"}), 404


# ── Update settings ──
@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    allowed_fields = {"email", "name", "alert_frequency", "min_match_score", "skills"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    update_settings(**update_data)
    return jsonify({"status": "updated", "settings": get_settings()})


# ── Get tracked skills ──
@app.route("/api/skills", methods=["GET"])
def api_get_skills():
    settings = get_settings()
    return jsonify({"skills": settings["skills"] if settings else []})


# ── Update tracked skills ──
@app.route("/api/skills", methods=["POST"])
def api_update_skills():
    data = request.get_json()
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        return jsonify({"error": "Skills must be a list"}), 400

    update_settings(skills=skills)
    return jsonify({"status": "updated", "skills": skills, "count": len(skills)})


# ── Get recent alerts/matched jobs ──
@app.route("/api/alerts", methods=["GET"])
def api_get_alerts():
    limit = request.args.get("limit", 20, type=int)
    min_score = request.args.get("min_score", 70, type=int)
    jobs = get_recent_jobs(limit=limit, min_score=min_score)

    # Parse skills_found JSON strings
    for job in jobs:
        if isinstance(job.get("skills_found"), str):
            try:
                job["skills_found"] = json.loads(job["skills_found"])
            except (json.JSONDecodeError, TypeError):
                job["skills_found"] = []

    return jsonify({"alerts": jobs, "count": len(jobs)})


# ── Trigger manual scan ──
@app.route("/api/scan", methods=["POST"])
def api_trigger_scan():
    # Run scan in background thread so API responds immediately
    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    return jsonify({
        "status": "scan_started",
        "message": "Job scan started in background. Check /api/alerts for results.",
    })


# ── Get dashboard stats ──
@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    stats = get_stats()
    settings = get_settings()
    stats["tracked_skills"] = len(settings["skills"]) if settings else 0
    stats["alert_frequency"] = settings["alert_frequency"] if settings else "instant"
    stats["email"] = settings["email"] if settings else ""
    return jsonify(stats)


# ── Run server ──
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )
