# JobPulse Backend — Skill-Based Job Alert Service

A complete Python backend that scrapes job boards, matches jobs to your skills,
and sends email alerts when new matching jobs are found.

## Architecture

```
jobpulse-backend/
├── app.py                  # Flask REST API server
├── scraper.py              # Job board scraper (Naukri, LinkedIn, Indeed)
├── matcher.py              # Skill matching engine
├── emailer.py              # Email alert sender (SMTP / SendGrid)
├── scheduler.py            # Cron-based job scheduler
├── config.py               # Configuration & environment variables
├── models.py               # Database models (SQLite)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── templates/
│   └── email_alert.html    # Email template
└── README.md               # This file
```

## Quick Start

### 1. Install dependencies
```bash
cd jobpulse-backend
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your email credentials
```

### 3. Run the server
```bash
python app.py
```

### 4. Start the job scanner (separate terminal)
```bash
python scheduler.py
```

## API Endpoints

| Method | Endpoint              | Description                     |
|--------|-----------------------|---------------------------------|
| GET    | /api/skills           | Get user's tracked skills       |
| POST   | /api/skills           | Update tracked skills           |
| GET    | /api/alerts           | Get recent job alerts           |
| POST   | /api/settings         | Update email/frequency settings |
| POST   | /api/scan             | Trigger manual job scan         |
| GET    | /api/stats            | Get dashboard statistics        |

## Email Providers

Supports 3 email providers:

1. **Gmail SMTP** (free, for personal use)
2. **SendGrid** (free tier: 100 emails/day)
3. **AWS SES** (cheapest at scale)

See `.env.example` for configuration details.

## Deployment Options

- **Free**: Railway.app, Render.com, or PythonAnywhere
- **VPS**: Any $5/mo server (DigitalOcean, Linode)
- **Serverless**: AWS Lambda + EventBridge for scheduling

## License
MIT
