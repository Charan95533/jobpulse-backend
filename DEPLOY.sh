# ╔═══════════════════════════════════════════════════════════════╗
# ║            JobPulse Deployment Guide                         ║
# ║   Step-by-step instructions to get your alerts running       ║
# ╚═══════════════════════════════════════════════════════════════╝

# ============================
# STEP 1: SET UP EMAIL (Gmail)
# ============================
#
# Gmail is the easiest free option. Follow these steps:
#
# 1. Go to https://myaccount.google.com/security
# 2. Enable "2-Step Verification" if not already on
# 3. Go to https://myaccount.google.com/apppasswords
# 4. Select "Mail" as the app, "Other" as device, name it "JobPulse"
# 5. Google will show a 16-character password like: abcd efgh ijkl mnop
# 6. Copy that password (remove spaces) into .env as SMTP_PASSWORD
#
# Your .env should look like:
#   SMTP_USER=agrcharanhrc@gmail.com
#   SMTP_PASSWORD=abcdefghijklmnop


# ============================
# STEP 2: LOCAL SETUP
# ============================

# Clone or copy the jobpulse-backend folder to your machine
cd jobpulse-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Gmail app password

# Test it works
python matcher.py               # Should show match score
python emailer.py               # Creates test_email.html to preview

# Run the API server
python app.py
# API running at http://localhost:5000

# In a separate terminal, run the scanner
python scheduler.py --once      # Single scan test
python scheduler.py             # Continuous scanning


# ====================================
# STEP 3: FREE CLOUD DEPLOYMENT
# ====================================

# ── Option A: Render.com (Recommended, easiest) ──
#
# 1. Push code to GitHub
# 2. Go to https://render.com → New → Web Service
# 3. Connect your GitHub repo
# 4. Settings:
#      Build: pip install -r requirements.txt
#      Start: python app.py
# 5. Add environment variables from .env
# 6. Create a second service (Background Worker):
#      Start: python scheduler.py
#
# Free tier: 750 hours/month (enough for 24/7)


# ── Option B: Railway.app ──
#
# 1. Go to https://railway.app
# 2. New Project → Deploy from GitHub
# 3. Add environment variables
# 4. It auto-detects Python and deploys
#
# Free tier: $5 credit/month


# ── Option C: PythonAnywhere (Best for beginners) ──
#
# 1. Sign up at https://www.pythonanywhere.com (free)
# 2. Upload files via Files tab
# 3. Create Web App → Flask → Python 3.10
# 4. Set up a Scheduled Task for scheduler.py
#    (free tier allows 1 daily task)
# 5. Add environment vars in .env file
#
# Free tier: 1 web app + 1 scheduled task/day


# ── Option D: VPS (Most control, $5/month) ──
#
# 1. Get a $5/mo server from DigitalOcean or Linode
# 2. SSH in and install Python:
#      sudo apt update && sudo apt install python3-pip python3-venv
# 3. Clone your code and set up:
#      cd jobpulse-backend
#      python3 -m venv venv
#      source venv/bin/activate
#      pip install -r requirements.txt
# 4. Use systemd to run as services:

# --- /etc/systemd/system/jobpulse-api.service ---
# [Unit]
# Description=JobPulse API
# After=network.target
#
# [Service]
# User=ubuntu
# WorkingDirectory=/home/ubuntu/jobpulse-backend
# Environment="PATH=/home/ubuntu/jobpulse-backend/venv/bin"
# ExecStart=/home/ubuntu/jobpulse-backend/venv/bin/python app.py
# Restart=always
#
# [Install]
# WantedBy=multi-user.target

# --- /etc/systemd/system/jobpulse-scanner.service ---
# [Unit]
# Description=JobPulse Scanner
# After=network.target
#
# [Service]
# User=ubuntu
# WorkingDirectory=/home/ubuntu/jobpulse-backend
# Environment="PATH=/home/ubuntu/jobpulse-backend/venv/bin"
# ExecStart=/home/ubuntu/jobpulse-backend/venv/bin/python scheduler.py
# Restart=always
#
# [Install]
# WantedBy=multi-user.target

# Enable and start:
# sudo systemctl enable jobpulse-api jobpulse-scanner
# sudo systemctl start jobpulse-api jobpulse-scanner


# ====================================
# STEP 4: CONNECT FRONTEND
# ====================================
#
# Update the React frontend (JobAlertDashboard.jsx) to call your API:
#
#   const API_BASE = "https://your-app.onrender.com";
#
#   // Fetch alerts
#   const res = await fetch(`${API_BASE}/api/alerts`);
#   const data = await res.json();
#
#   // Update skills
#   await fetch(`${API_BASE}/api/skills`, {
#     method: "POST",
#     headers: { "Content-Type": "application/json" },
#     body: JSON.stringify({ skills: selectedSkills }),
#   });
#
#   // Trigger manual scan
#   await fetch(`${API_BASE}/api/scan`, { method: "POST" });


# ====================================
# STEP 5: VERIFY IT WORKS
# ====================================
#
# 1. Open http://localhost:5000 — should show API status
# 2. Run: python scheduler.py --once
# 3. Check your email for the alert
# 4. Open http://localhost:5000/api/stats — shows scan stats
# 5. Open http://localhost:5000/api/alerts — shows matched jobs
