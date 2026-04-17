"""
JobPulse Scheduler
Runs periodic job scans, matches skills, and sends email alerts.

Usage:
    python scheduler.py              # Run continuous scheduler
    python scheduler.py --once       # Run single scan and exit
"""

import sys
import json
import time
import logging
from datetime import datetime

from config import Config
from scraper import JobScraper
from matcher import compute_match_score
from emailer import send_alert_email
from models import (
    get_settings, save_job, get_unsent_jobs,
    mark_alert_sent, log_scan
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jobpulse.scheduler")


def run_scan():
    """
    Execute a full scan cycle:
    1. Scrape jobs from all sources
    2. Match each job against user skills
    3. Save matched jobs to database
    4. Send email alerts for new matches
    """
    logger.info("=" * 60)
    logger.info("Starting job scan cycle")
    logger.info("=" * 60)

    settings = get_settings()
    if not settings or not settings.get("is_active"):
        logger.info("Alerts are disabled, skipping scan")
        return

    skills = settings["skills"]
    min_score = settings["min_match_score"]
    email = settings["email"]
    user_name = settings["name"]

    logger.info(f"Tracking {len(skills)} skills, min match: {min_score}%")
    logger.info(f"Alert email: {email}")

    # ── Step 1: Scrape jobs ──
    scraper = JobScraper(skills=skills, location="Bangalore")
    raw_jobs = scraper.scrape_all()
    logger.info(f"Scraped {len(raw_jobs)} total jobs")

    # ── Step 2: Match and save ──
    matched_count = 0
    for job in raw_jobs:
        # Combine title + description for matching
        match_text = f"{job['title']} {job.get('description', '')}"
        result = compute_match_score(skills, match_text)

        job["match_score"] = result["score"]
        job["skills_found"] = result["matched_skills"]

        if result["score"] >= min_score:
            save_job(job)
            matched_count += 1
            logger.info(
                f"  MATCH [{result['score']}%] {job['title']} "
                f"at {job['company']} — {result['matched_skills']}"
            )

    logger.info(f"Matched {matched_count} of {len(raw_jobs)} jobs (>= {min_score}%)")

    # ── Step 3: Send alerts ──
    alerts_sent_count = 0

    if settings["alert_frequency"] == "instant":
        # Send immediately for new unsent matches
        unsent = get_unsent_jobs()
        if unsent:
            logger.info(f"Sending instant alert for {len(unsent)} new jobs")
            success = send_alert_email(email, unsent, user_name)
            if success:
                for job in unsent:
                    mark_alert_sent(job["id"], email)
                    alerts_sent_count += 1
                logger.info(f"Alert email sent to {email}")
            else:
                logger.error("Failed to send alert email")
        else:
            logger.info("No new unsent jobs to alert about")

    elif settings["alert_frequency"] == "daily":
        # Only send at 9 AM
        now = datetime.now()
        if now.hour == 9 and now.minute < Config.SCAN_INTERVAL_MINUTES:
            unsent = get_unsent_jobs()
            if unsent:
                success = send_alert_email(email, unsent, user_name)
                if success:
                    for job in unsent:
                        mark_alert_sent(job["id"], email)
                        alerts_sent_count += 1

    elif settings["alert_frequency"] == "weekly":
        # Only send on Monday at 9 AM
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 9 and now.minute < Config.SCAN_INTERVAL_MINUTES:
            unsent = get_unsent_jobs()
            if unsent:
                success = send_alert_email(email, unsent, user_name)
                if success:
                    for job in unsent:
                        mark_alert_sent(job["id"], email)
                        alerts_sent_count += 1

    # ── Log scan results ──
    log_scan("all", len(raw_jobs), matched_count, alerts_sent_count)
    logger.info(
        f"Scan complete: {len(raw_jobs)} scraped, "
        f"{matched_count} matched, {alerts_sent_count} alerts sent"
    )
    logger.info("=" * 60)


def run_scheduler():
    """Run continuous scheduler loop."""
    interval = Config.SCAN_INTERVAL_MINUTES * 60
    logger.info(f"JobPulse Scheduler started (interval: {Config.SCAN_INTERVAL_MINUTES} min)")

    while True:
        try:
            run_scan()
        except Exception as e:
            logger.error(f"Scan cycle failed: {e}", exc_info=True)

        logger.info(f"Next scan in {Config.SCAN_INTERVAL_MINUTES} minutes...")
        time.sleep(interval)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_scan()
    else:
        run_scheduler()
