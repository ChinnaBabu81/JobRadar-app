# JobRadar-app
JobRadar is an automated web app that scrapes LinkedIn every morning at 5:00 AM to find the latest " your interested jobs name ", so you wake up ready to apply.

# 🎯 JobRadar — AI Internship Hunter

## ✨ Features

| Feature | Description |
|---|---|
| ⏰ Auto-scrape at 5 AM | APScheduler runs every morning automatically |
| 🔍 LinkedIn Scraper | Finds AI Engineer, Data Analyst, ML, Data Science interns, etc |
| 🔔 Desktop Notifications | Browser notification when new jobs are found |
| ✨ AI Resume Tailoring | Claude generates a custom resume per job |
| 📊 Match Score | Shows how well your resume matches the job |
| 🌐 Web Dashboard | Beautiful browser-based interface |

---

## 🚀 Quick Start

### 1. Clone / extract the project

```bash
cd job-tracker
```

### 2. Set up the backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# OR
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Get your Anthropic API key

1. Go to https://console.anthropic.com
2. Create an API key
3. Add it to `backend/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
   ```

### 4. Start the backend server

```bash
python app.py
```

You should see:
```
🚀 Job Tracker Backend started!
⏰ Scheduled daily scrape at 5:00 AM
 * Running on http://0.0.0.0:5000
```

### 5. Open the frontend

Open `frontend/index.html` in your browser.

> **Or** serve it locally:
> ```bash
> cd frontend
> python -m http.server 8080
> # Open http://localhost:8080
> ```

---

## 📋 How to Use

### 1. Add Your Resume
- Click **"My Resume"** in the sidebar
- Paste your base resume (plain text)
- Click **"Save Resume"**

### 2. Scrape Jobs Now
- Click **"⚡ Scrape Now"** in the header
- Wait ~30 seconds for results to load
- New jobs appear with a **"NEW"** badge

### 3. Tailor Your Resume
- Click any job card to open it
- Read the job description
- Click **"✨ Tailor My Resume"**
- Claude generates a targeted resume with:
  - Match score (0–100%)
  - Keywords matched
  - Skills you're missing
  - Tailoring tips applied

### 4. Enable Desktop Notifications
- Go to **Settings**
- Click **"Enable Desktop Notifications"**
- Accept the browser permission prompt
- Next time the 5 AM scrape runs, you'll get notified!

---

## ⚙️ Configuration

Edit `backend/.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Filter jobs by location
JOB_LOCATION=United States

# Optional: Flask port
FLASK_PORT=5000
```

---

## 📁 Project Structure

```
job-tracker/
├── backend/
│   ├── app.py            ← Flask API server + scheduler
│   ├── scraper.py        ← LinkedIn job scraper
│   ├── tailor.py         ← Claude AI resume tailoring
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html        ← Web dashboard (open in browser)
└── README.md
```

---

## 🤔 Troubleshooting

**"Backend is offline" error**
→ Make sure `python app.py` is running in the `backend/` folder

**LinkedIn returns no jobs**
→ LinkedIn occasionally blocks scrapers. Wait a few minutes and retry.
→ Consider using a VPN or rotating user agents.

**Resume tailoring fails**
→ Check your `ANTHROPIC_API_KEY` in `.env`
→ Make sure you've saved your base resume first

**Desktop notifications not working**
→ Go to Settings and click "Enable Desktop Notifications"
→ The browser tab must be open at 5 AM (or service worker must be registered)

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, APScheduler, BeautifulSoup, Anthropic SDK
- **Frontend**: Vanilla HTML/CSS/JS, SSE for real-time updates
- **AI**: Claude Sonnet via Anthropic API
- **Database**: SQLite (auto-created as `jobs.db`)
- **Scheduler**: APScheduler CronTrigger (5:00 AM daily)

---

## 📝 Notes

- The scraper uses LinkedIn's public (unauthenticated) job search API
- Jobs are deduplicated by ID — no duplicates stored
- All data is stored locally in `backend/jobs.db`
- Resume text is stored in `backend/base_resume.txt`

---

*Built with ❤️ and Claude AI*
