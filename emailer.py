"""
JobPulse Email Alerter
Sends job match alerts via SMTP, SendGrid, or AWS SES.
"""

import smtplib
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Config

logger = logging.getLogger("jobpulse.emailer")


# ───────────────────────────────────────────────
# Email template
# ───────────────────────────────────────────────

def build_email_html(jobs, user_name="Charan"):
    """Build HTML email body for job alerts."""

    job_cards = ""
    for job in jobs:
        skills_found = job.get("skills_found", "[]")
        if isinstance(skills_found, str):
            try:
                skills_found = json.loads(skills_found)
            except (json.JSONDecodeError, TypeError):
                skills_found = []

        skill_tags = "".join(
            f'<span style="display:inline-block;padding:3px 10px;margin:2px;'
            f'border-radius:4px;background:#e8f5ee;color:#1a7a52;font-size:12px;">'
            f'{s}</span>'
            for s in skills_found[:6]
        )

        match_score = round(job.get("match_score", 0))
        match_color = "#1a7a52" if match_score >= 90 else "#2563a8" if match_score >= 80 else "#a8710a"

        job_cards += f"""
        <div style="background:#fff;border:1px solid #eae8e2;border-radius:10px;
                    padding:20px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <h3 style="margin:0 0 4px;font-size:16px;color:#1a1917;font-weight:600;">
                        {job['title']}
                    </h3>
                    <p style="margin:0;font-size:13px;color:#7a7870;">
                        {job['company']} &middot; {job.get('location', 'India')}
                    </p>
                </div>
                <span style="font-size:20px;font-weight:700;color:{match_color};
                             font-family:monospace;">
                    {match_score}%
                </span>
            </div>
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid #f0efe9;">
                <p style="margin:0 0 6px;font-size:11px;font-weight:600;color:#9a9890;
                          text-transform:uppercase;letter-spacing:0.5px;">
                    Matched skills
                </p>
                {skill_tags}
            </div>
            <div style="margin-top:16px;">
                <a href="{job.get('url', '#')}"
                   style="display:inline-block;padding:10px 24px;background:#0a0a0a;
                          color:#fff;text-decoration:none;border-radius:6px;
                          font-size:13px;font-weight:600;">
                    View job &amp; apply &rarr;
                </a>
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#faf9f6;font-family:-apple-system,
                 BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="max-width:600px;margin:0 auto;padding:32px 20px;">
            <!-- Header -->
            <div style="margin-bottom:24px;">
                <div style="display:inline-flex;align-items:center;gap:8px;">
                    <div style="width:28px;height:28px;border-radius:6px;background:#0a0a0a;
                                display:inline-flex;align-items:center;justify-content:center;
                                color:#fff;font-size:12px;font-weight:700;">J</div>
                    <span style="font-size:16px;font-weight:700;color:#0a0a0a;">JobPulse</span>
                </div>
            </div>

            <!-- Greeting -->
            <h1 style="margin:0 0 8px;font-size:22px;color:#1a1917;font-weight:700;">
                {len(jobs)} new job{'s' if len(jobs) != 1 else ''} matching your skills
            </h1>
            <p style="margin:0 0 24px;font-size:14px;color:#7a7870;">
                Hi {user_name}, we found new openings that match your tracked skills.
            </p>

            <!-- Job Cards -->
            {job_cards}

            <!-- Footer -->
            <div style="margin-top:32px;padding-top:20px;border-top:1px solid #eae8e2;
                        text-align:center;">
                <p style="font-size:12px;color:#c0bfb8;margin:0;">
                    You received this because you have active job alerts on JobPulse.
                    <br>
                    <a href="#" style="color:#9a9890;">Manage alerts</a> &middot;
                    <a href="#" style="color:#9a9890;">Unsubscribe</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """


# ───────────────────────────────────────────────
# Provider 1: SMTP (Gmail, Outlook, etc.)
# ───────────────────────────────────────────────

def send_via_smtp(to_email, subject, html_body):
    """Send email using SMTP (Gmail, Outlook, custom SMTP)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_USER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_USER, to_email, msg.as_string())

        logger.info(f"Email sent via SMTP to {to_email}")
        return True
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return False


# ───────────────────────────────────────────────
# Provider 2: SendGrid
# ───────────────────────────────────────────────

def send_via_sendgrid(to_email, subject, html_body):
    """Send email using SendGrid API (free tier: 100/day)."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content

        sg = sendgrid.SendGridAPIClient(api_key=Config.SENDGRID_API_KEY)
        message = Mail(
            from_email=Email(Config.SENDGRID_FROM_EMAIL, Config.SMTP_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )
        response = sg.send(message)
        logger.info(f"Email sent via SendGrid to {to_email} (status: {response.status_code})")
        return response.status_code in (200, 201, 202)
    except ImportError:
        logger.error("SendGrid package not installed. Run: pip install sendgrid")
        return False
    except Exception as e:
        logger.error(f"SendGrid send failed: {e}")
        return False


# ───────────────────────────────────────────────
# Provider 3: AWS SES
# ───────────────────────────────────────────────

def send_via_ses(to_email, subject, html_body):
    """Send email using AWS SES."""
    try:
        import boto3

        client = boto3.client(
            "ses",
            region_name=Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY,
        )

        response = client.send_email(
            Source=f"{Config.SMTP_FROM_NAME} <{Config.SES_FROM_EMAIL}>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_body}},
            },
        )
        logger.info(f"Email sent via SES to {to_email} (MessageId: {response['MessageId']})")
        return True
    except ImportError:
        logger.error("boto3 package not installed. Run: pip install boto3")
        return False
    except Exception as e:
        logger.error(f"SES send failed: {e}")
        return False


# ───────────────────────────────────────────────
# Main send function (routes to configured provider)
# ───────────────────────────────────────────────

def send_alert_email(to_email, jobs, user_name="Charan"):
    """
    Send job alert email using the configured provider.

    Args:
        to_email: recipient email address
        jobs: list of matched job dicts
        user_name: recipient name for personalization

    Returns:
        bool: True if sent successfully
    """
    if not jobs:
        logger.info("No jobs to send, skipping email")
        return False

    # Build subject line
    top_job = max(jobs, key=lambda j: j.get("match_score", 0))
    subject = (
        f"[JobPulse] {len(jobs)} new match{'es' if len(jobs) > 1 else ''}: "
        f"{top_job['title']} at {top_job['company']} "
        f"({round(top_job.get('match_score', 0))}% match)"
    )

    html_body = build_email_html(jobs, user_name)

    # Route to configured provider
    provider = Config.EMAIL_PROVIDER.lower()

    if provider == "sendgrid":
        return send_via_sendgrid(to_email, subject, html_body)
    elif provider == "ses":
        return send_via_ses(to_email, subject, html_body)
    else:  # default: smtp
        return send_via_smtp(to_email, subject, html_body)


# ── Quick test ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_jobs = [
        {
            "title": "OpenStack Cloud Engineer",
            "company": "Squircle IT",
            "location": "Pune",
            "match_score": 95,
            "skills_found": '["OpenStack", "KVM", "RHEL 8", "Linux"]',
            "url": "https://example.com/job/1",
        }
    ]
    html = build_email_html(test_jobs)
    with open("test_email.html", "w") as f:
        f.write(html)
    print("Test email saved to test_email.html — open in browser to preview")
