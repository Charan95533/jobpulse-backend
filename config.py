"""
JobPulse Configuration
Loads settings from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ──
    SECRET_KEY = os.getenv("SECRET_KEY", "jobpulse-secret-change-me")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))

    # ── Database ──
    DATABASE_PATH = os.getenv("DATABASE_PATH", "jobpulse.db")

    # ── Email Provider: "smtp" | "sendgrid" | "ses" ──
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp")

    # SMTP Settings (Gmail / Outlook / custom)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail: use App Password
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "JobPulse Alerts")

    # SendGrid Settings
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")

    # AWS SES Settings
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
    SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "")

    # ── User Settings (defaults, overridden via API) ──
    USER_EMAIL = os.getenv("USER_EMAIL", "agrcharanhrc@gmail.com")
    USER_NAME = os.getenv("USER_NAME", "Charan Adika")
    ALERT_FREQUENCY = os.getenv("ALERT_FREQUENCY", "instant")  # instant|daily|weekly
    MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", 70))

    # ── Scraper Settings ──
    SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 30))
    MAX_RESULTS_PER_SOURCE = int(os.getenv("MAX_RESULTS_PER_SOURCE", 20))

    # ── Default Skills (from Charan's resume) ──
    DEFAULT_SKILLS = [
        "OpenStack", "Red Hat OSP16", "KVM", "NFV", "Ansible",
        "Docker", "Kubernetes", "Nova", "Neutron", "Glance",
        "Cinder", "Keystone", "Heat", "Ironic", "RHEL 8",
        "Linux", "Bash", "Wireshark", "TCP/IP", "VLAN", "OVS",
        "5G Core", "SMF", "UPF", "TripleO", "Jira", "Git",
    ]
