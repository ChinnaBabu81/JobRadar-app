"""
LinkedIn Job Scraper
Scrapes AI Engineer Intern & Data Analyst Intern roles from LinkedIn public API
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

JOB_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
JOB_DETAIL_URL = "https://www.linkedin.com/jobs/view/{job_id}/"


def parse_job_card(card):
    """Extract job info from a single LinkedIn job card HTML element."""
    try:
        job = {}

        # Job ID
        entity_urn = card.get("data-entity-urn", "")
        job["id"] = entity_urn.split(":")[-1] if entity_urn else ""

        # Title
        title_el = card.find("h3", class_="base-search-card__title")
        job["title"] = title_el.get_text(strip=True) if title_el else "N/A"

        # Company
        company_el = card.find("h4", class_="base-search-card__subtitle")
        job["company"] = company_el.get_text(strip=True) if company_el else "N/A"

        # Location
        location_el = card.find("span", class_="job-search-card__location")
        job["location"] = location_el.get_text(strip=True) if location_el else "N/A"

        # Posted date
        time_el = card.find("time")
        job["posted_at"] = time_el.get("datetime", "") if time_el else ""
        job["posted_text"] = time_el.get_text(strip=True) if time_el else ""

        # URL
        link_el = card.find("a", class_="base-card__full-link")
        job["url"] = link_el.get("href", "").split("?")[0] if link_el else ""

        job["scraped_at"] = datetime.now().isoformat()
        return job
    except Exception as e:
        logger.error(f"Error parsing job card: {e}")
        return None


def fetch_jobs(keyword, location="", max_results=20):
    """Fetch jobs from LinkedIn public job search API."""
    jobs = []
    start = 0
    batch_size = 10

    while len(jobs) < max_results:
        params = {
            "keywords": keyword,
            "location": location,
            "f_TPR": "r86400",      # Past 24 hours
            "f_JT": "I",            # Internship job type
            "start": start,
        }

        try:
            logger.info(f"Fetching jobs: '{keyword}' | start={start}")
            response = requests.get(
                JOB_SEARCH_URL,
                headers=HEADERS,
                params=params,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("li")

            if not cards:
                logger.info("No more job cards found.")
                break

            for card in cards:
                job = parse_job_card(card)
                if job and job.get("id"):
                    job["keyword"] = keyword
                    jobs.append(job)
                    if len(jobs) >= max_results:
                        break

            start += batch_size
            time.sleep(1.5)  # Be polite to LinkedIn

        except requests.RequestException as e:
            logger.error(f"Request failed for '{keyword}': {e}")
            break

    return jobs


def fetch_job_description(job_url):
    """Fetch full job description from a LinkedIn job page."""
    try:
        response = requests.get(job_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find the job description
        desc_el = soup.find("div", class_="show-more-less-html__markup")
        if not desc_el:
            desc_el = soup.find("section", class_="description")

        if desc_el:
            return desc_el.get_text(separator="\n", strip=True)
        return "Description not available."
    except Exception as e:
        logger.error(f"Failed to fetch job description: {e}")
        return "Description not available."


def scrape_all_jobs(location="", max_per_keyword=15):
    """
    Main entry point — scrapes both AI Engineer Intern & Data Analyst Intern.
    Returns a combined, deduplicated list of jobs.
    """
    keywords = [
        "AI Engineer Intern",
        "Data Analyst Intern",
        "Machine Learning Intern",
        "Data Science Intern",
    ]

    all_jobs = []
    seen_ids = set()

    for keyword in keywords:
        jobs = fetch_jobs(keyword, location=location, max_results=max_per_keyword)
        for job in jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                all_jobs.append(job)
        time.sleep(2)

    logger.info(f"Total unique jobs found: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    results = scrape_all_jobs(location="")
    print(json.dumps(results[:3], indent=2))
