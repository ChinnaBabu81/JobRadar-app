"""
Job Tracker Backend — Flask API Server
Handles job scraping, resume tailoring, scheduling & notifications
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

# Local modules
from scraper import scrape_all_jobs, fetch_job_description
from tailor import tailor_resume, analyze_job_fit

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "jobs.db"
RESUME_PATH = Path(__file__).parent / "base_resume.txt"

# SSE subscribers (for real-time notifications)
sse_subscribers = []


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            keyword TEXT,
            posted_at TEXT,
            posted_text TEXT,
            description TEXT,
            scraped_at TEXT,
            is_new INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            jobs_found INTEGER,
            status TEXT
        )
    """)
    con.commit()
    con.close()


def save_jobs(jobs):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    new_count = 0
    for job in jobs:
        existing = cur.execute("SELECT id FROM jobs WHERE id=?", (job["id"],)).fetchone()
        if not existing:
            cur.execute("""
                INSERT INTO jobs (id, title, company, location, url, keyword, posted_at, posted_text, scraped_at, is_new)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                job.get("id"), job.get("title"), job.get("company"),
                job.get("location"), job.get("url"), job.get("keyword"),
                job.get("posted_at"), job.get("posted_text"), job.get("scraped_at")
            ))
            new_count += 1
    con.commit()
    con.close()
    return new_count


def get_jobs(limit=50, only_new=False):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    query = "SELECT * FROM jobs"
    if only_new:
        query += " WHERE is_new=1"
    query += " ORDER BY scraped_at DESC LIMIT ?"
    rows = cur.execute(query, (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def mark_jobs_seen():
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE jobs SET is_new=0")
    con.commit()
    con.close()


# ─────────────────────────────────────────────
# Scraping Job
# ─────────────────────────────────────────────
def run_scrape_job():
    """Main scheduled scrape function — runs at 5:00 AM."""
    logger.info("⏰ Scheduled scrape started...")
    try:
        location = os.getenv("JOB_LOCATION", "")
        jobs = scrape_all_jobs(location=location)
        new_count = save_jobs(jobs)

        # Log the run
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO scrape_runs (run_at, jobs_found, status) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), new_count, "success")
        )
        con.commit()
        con.close()

        # Notify SSE subscribers
        notify_subscribers({
            "type": "new_jobs",
            "count": new_count,
            "total": len(jobs),
            "time": datetime.now().strftime("%I:%M %p")
        })

        logger.info(f"✅ Scrape complete. {new_count} new jobs saved.")
    except Exception as e:
        logger.error(f"❌ Scrape job failed: {e}")
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO scrape_runs (run_at, jobs_found, status) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), 0, f"failed: {e}")
        )
        con.commit()
        con.close()


# ─────────────────────────────────────────────
# SSE (Server-Sent Events)
# ─────────────────────────────────────────────
def notify_subscribers(data):
    msg = f"data: {json.dumps(data)}\n\n"
    for q in sse_subscribers:
        q.append(msg)


@app.route("/api/events")
def sse_stream():
    """SSE endpoint for real-time job notifications."""
    import queue

    q = []
    sse_subscribers.append(q)

    def generate():
        yield "data: {\"type\": \"connected\"}\n\n"
        while True:
            if q:
                yield q.pop(0)
            import time
            time.sleep(0.5)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/api/jobs")
def get_all_jobs():
    limit = request.args.get("limit", 50, type=int)
    only_new = request.args.get("new", "false").lower() == "true"
    jobs = get_jobs(limit=limit, only_new=only_new)
    return jsonify({"jobs": jobs, "count": len(jobs)})


@app.route("/api/jobs/mark-seen", methods=["POST"])
def mark_seen():
    mark_jobs_seen()
    return jsonify({"success": True})


@app.route("/api/scrape", methods=["POST"])
def manual_scrape():
    """Manually trigger a scrape."""
    try:
        location = request.json.get("location", "") if request.json else ""
        jobs = scrape_all_jobs(location=location)
        new_count = save_jobs(jobs)

        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO scrape_runs (run_at, jobs_found, status) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), new_count, "manual")
        )
        con.commit()
        con.close()

        return jsonify({
            "success": True,
            "new_jobs": new_count,
            "total_found": len(jobs)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/jobs/<job_id>/description")
def get_description(job_id):
    """Fetch full job description for a specific job."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    con.close()

    if not row:
        return jsonify({"error": "Job not found"}), 404

    job = dict(row)
    if not job.get("description"):
        desc = fetch_job_description(job["url"])
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE jobs SET description=? WHERE id=?", (desc, job_id))
        con.commit()
        con.close()
        job["description"] = desc

    return jsonify(job)


@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    """Save the user's base resume text."""
    data = request.json
    if not data or "resume" not in data:
        return jsonify({"error": "No resume provided"}), 400

    RESUME_PATH.write_text(data["resume"], encoding="utf-8")
    return jsonify({"success": True, "message": "Resume saved!"})


@app.route("/api/resume/base")
def get_base_resume():
    if RESUME_PATH.exists():
        return jsonify({"resume": RESUME_PATH.read_text(encoding="utf-8")})
    return jsonify({"resume": ""})


@app.route("/api/resume/tailor", methods=["POST"])
def tailor():
    """Generate a tailored resume for a specific job."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    base_resume = data.get("base_resume") or (
        RESUME_PATH.read_text(encoding="utf-8") if RESUME_PATH.exists() else ""
    )

    if not base_resume:
        return jsonify({"error": "No base resume found. Please upload your resume first."}), 400

    result = tailor_resume(
        base_resume=base_resume,
        job_title=data.get("job_title", ""),
        company=data.get("company", ""),
        job_description=data.get("job_description", "")
    )

    return jsonify(result)


@app.route("/api/resume/analyze", methods=["POST"])
def analyze():
    """Quick fit analysis without full resume rewrite."""
    data = request.json
    base_resume = data.get("base_resume") or (
        RESUME_PATH.read_text(encoding="utf-8") if RESUME_PATH.exists() else ""
    )
    result = analyze_job_fit(base_resume, data.get("job_description", ""))
    return jsonify(result)


@app.route("/api/stats")
def stats():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    total = con.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
    new = con.execute("SELECT COUNT(*) as c FROM jobs WHERE is_new=1").fetchone()["c"]
    last_run = con.execute(
        "SELECT * FROM scrape_runs ORDER BY run_at DESC LIMIT 1"
    ).fetchone()
    con.close()
    return jsonify({
        "total_jobs": total,
        "new_jobs": new,
        "last_scrape": dict(last_run) if last_run else None
    })


@app.route("/api/schedule/status")
def schedule_status():
    jobs = scheduler.get_jobs()
    return jsonify({
        "scheduled_jobs": [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time)
            } for j in jobs
        ]
    })


# ─────────────────────────────────────────────
# Scheduler Setup
# ─────────────────────────────────────────────
scheduler = BackgroundScheduler()
scheduler.add_job(
    run_scrape_job,
    trigger=CronTrigger(hour=5, minute=0),   # Every day at 5:00 AM
    id="morning_scrape",
    name="Morning LinkedIn Job Scrape",
    replace_existing=True
)


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    scheduler.start()
    logger.info("🚀 Job Tracker Backend started!")
    logger.info("⏰ Scheduled daily scrape at 5:00 AM")
    app.run(host="0.0.0.0", port=5000, debug=False)
