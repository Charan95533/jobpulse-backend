"""
JobPulse Job Scraper
Scrapes job listings from multiple sources and returns structured data.

Supports:
  - Indeed (via RSS/web)
  - LinkedIn (via public API)
  - Naukri (via web scraping)
  - Google Jobs (via SerpAPI, optional)
  - Custom RSS feeds
"""

import requests
import hashlib
import logging
import time
import re
from datetime import datetime
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger("jobpulse.scraper")


class JobScraper:
    """Multi-source job scraper with rate limiting."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, skills, location="Bangalore"):
        self.skills = skills
        self.location = location
        self.results = []

    def _generate_id(self, title, company, source):
        """Generate unique external ID for deduplication."""
        raw = f"{title}|{company}|{source}".lower().strip()
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _rate_limit(self, seconds=2):
        """Simple rate limiting between requests."""
        time.sleep(seconds)

    # ───────────────────────────────────────────────
    # Source 1: Indeed (via RSS feed — no API key needed)
    # ───────────────────────────────────────────────
    def scrape_indeed(self):
        """Scrape Indeed India RSS feed for job listings."""
        logger.info("Scraping Indeed...")
        jobs = []

        # Build search queries from top skills
        queries = [
            "OpenStack cloud engineer",
            "NFV cloud infrastructure",
            "KVM OpenStack administrator",
        ]

        for query in queries:
            url = (
                f"https://www.indeed.co.in/rss"
                f"?q={quote_plus(query)}"
                f"&l={quote_plus(self.location)}"
                f"&sort=date"
            )
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "xml")
                    items = soup.find_all("item")

                    for item in items[:Config.MAX_RESULTS_PER_SOURCE]:
                        title = item.find("title")
                        company = item.find("source")
                        link = item.find("link")
                        desc = item.find("description")
                        pub_date = item.find("pubDate")

                        if title and link:
                            jobs.append({
                                "external_id": self._generate_id(
                                    title.text,
                                    company.text if company else "Unknown",
                                    "indeed"
                                ),
                                "title": title.text.strip(),
                                "company": company.text.strip() if company else "Unknown",
                                "location": self.location,
                                "description": desc.text.strip() if desc else "",
                                "url": link.text.strip() if link.string else str(link.next_sibling).strip(),
                                "source": "indeed",
                                "posted_at": pub_date.text if pub_date else None,
                            })

                self._rate_limit()
            except Exception as e:
                logger.error(f"Indeed scrape error: {e}")

        logger.info(f"Indeed: found {len(jobs)} jobs")
        return jobs

    # ───────────────────────────────────────────────
    # Source 2: LinkedIn (public job search page)
    # ───────────────────────────────────────────────
    def scrape_linkedin(self):
        """Scrape LinkedIn public job listings."""
        logger.info("Scraping LinkedIn...")
        jobs = []

        queries = ["OpenStack engineer", "cloud infrastructure NFV"]

        for query in queries:
            url = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={quote_plus(query)}"
                f"&location={quote_plus('India')}"
                f"&sortBy=DD"
                f"&start=0"
            )
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("div", class_="base-card")

                    for card in cards[:Config.MAX_RESULTS_PER_SOURCE]:
                        title_el = card.find("h3", class_="base-search-card__title")
                        company_el = card.find("h4", class_="base-search-card__subtitle")
                        location_el = card.find("span", class_="job-search-card__location")
                        link_el = card.find("a", class_="base-card__full-link")

                        if title_el and link_el:
                            title = title_el.text.strip()
                            company = company_el.text.strip() if company_el else "Unknown"
                            jobs.append({
                                "external_id": self._generate_id(title, company, "linkedin"),
                                "title": title,
                                "company": company,
                                "location": location_el.text.strip() if location_el else "India",
                                "description": title,  # LinkedIn doesn't expose full desc in search
                                "url": link_el.get("href", "").split("?")[0],
                                "source": "linkedin",
                                "posted_at": datetime.utcnow().isoformat(),
                            })

                self._rate_limit()
            except Exception as e:
                logger.error(f"LinkedIn scrape error: {e}")

        logger.info(f"LinkedIn: found {len(jobs)} jobs")
        return jobs

    # ───────────────────────────────────────────────
    # Source 3: Naukri.com (web scraping)
    # ───────────────────────────────────────────────
    def scrape_naukri(self):
        """Scrape Naukri.com for job listings."""
        logger.info("Scraping Naukri...")
        jobs = []

        queries = ["openstack-cloud-engineer", "nfv-openstack", "openstack-kvm"]

        for query in queries:
            url = (
                f"https://www.naukri.com/{query}-jobs-in-{self.location.lower()}"
                f"?experience=4"
            )
            try:
                resp = requests.get(url, headers={
                    **self.HEADERS,
                    "Referer": "https://www.naukri.com/",
                }, timeout=15)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.find_all("article", class_="jobTuple")

                    if not articles:
                        # Try alternate selectors (Naukri updates their DOM frequently)
                        articles = soup.find_all("div", attrs={"class": re.compile("srp-jobtuple")})

                    for article in articles[:Config.MAX_RESULTS_PER_SOURCE]:
                        title_el = article.find("a", class_="title")
                        company_el = article.find("a", class_="subTitle")
                        loc_el = article.find("li", class_="location")

                        if title_el:
                            title = title_el.text.strip()
                            company = company_el.text.strip() if company_el else "Unknown"
                            href = title_el.get("href", "")

                            jobs.append({
                                "external_id": self._generate_id(title, company, "naukri"),
                                "title": title,
                                "company": company,
                                "location": loc_el.text.strip() if loc_el else self.location,
                                "description": article.text[:500] if article else "",
                                "url": href if href.startswith("http") else f"https://www.naukri.com{href}",
                                "source": "naukri",
                                "posted_at": datetime.utcnow().isoformat(),
                            })

                self._rate_limit(3)  # Naukri is strict about rate limiting
            except Exception as e:
                logger.error(f"Naukri scrape error: {e}")

        logger.info(f"Naukri: found {len(jobs)} jobs")
        return jobs

    # ───────────────────────────────────────────────
    # Source 4: Google Jobs via SerpAPI (optional, needs API key)
    # ───────────────────────────────────────────────
    def scrape_google_jobs(self, api_key=None):
        """Use SerpAPI to search Google Jobs (optional, free tier available)."""
        if not api_key:
            api_key = Config.__dict__.get("SERPAPI_KEY", "")
        if not api_key:
            logger.info("SerpAPI key not set, skipping Google Jobs")
            return []

        logger.info("Scraping Google Jobs via SerpAPI...")
        jobs = []

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": "OpenStack Cloud Engineer",
            "location": "Bangalore, India",
            "api_key": api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("jobs_results", [])[:Config.MAX_RESULTS_PER_SOURCE]:
                    title = result.get("title", "")
                    company = result.get("company_name", "Unknown")
                    jobs.append({
                        "external_id": self._generate_id(title, company, "google"),
                        "title": title,
                        "company": company,
                        "location": result.get("location", "India"),
                        "description": result.get("description", "")[:500],
                        "url": result.get("share_link", result.get("related_links", [{}])[0].get("link", "")),
                        "source": "google_jobs",
                        "posted_at": datetime.utcnow().isoformat(),
                    })
        except Exception as e:
            logger.error(f"Google Jobs scrape error: {e}")

        logger.info(f"Google Jobs: found {len(jobs)} jobs")
        return jobs

    # ───────────────────────────────────────────────
    # Source 5: Custom RSS feeds (Glassdoor, company career pages)
    # ───────────────────────────────────────────────
    def scrape_rss(self, feed_url, source_name="rss"):
        """Generic RSS feed scraper."""
        logger.info(f"Scraping RSS: {source_name}...")
        jobs = []

        try:
            resp = requests.get(feed_url, headers=self.HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                for item in soup.find_all("item")[:Config.MAX_RESULTS_PER_SOURCE]:
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    if title and link:
                        jobs.append({
                            "external_id": self._generate_id(
                                title.text, source_name, source_name
                            ),
                            "title": title.text.strip(),
                            "company": source_name,
                            "location": "India",
                            "description": desc.text[:500] if desc else "",
                            "url": link.text.strip() if link.string else str(link.next_sibling).strip(),
                            "source": source_name,
                            "posted_at": datetime.utcnow().isoformat(),
                        })
        except Exception as e:
            logger.error(f"RSS scrape error ({source_name}): {e}")

        logger.info(f"{source_name}: found {len(jobs)} jobs")
        return jobs

    # ───────────────────────────────────────────────
    # Run all scrapers
    # ───────────────────────────────────────────────
    def scrape_all(self):
        """Run all scrapers and return combined results."""
        all_jobs = []

        all_jobs.extend(self.scrape_indeed())
        all_jobs.extend(self.scrape_linkedin())
        all_jobs.extend(self.scrape_naukri())
        all_jobs.extend(self.scrape_google_jobs())

        # Deduplicate by external_id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            if job["external_id"] not in seen:
                seen.add(job["external_id"])
                unique_jobs.append(job)

        logger.info(f"Total unique jobs scraped: {len(unique_jobs)}")
        return unique_jobs


# ── Quick test ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = JobScraper(
        skills=Config.DEFAULT_SKILLS,
        location="Bangalore"
    )
    jobs = scraper.scrape_all()
    for job in jobs[:5]:
        print(f"  [{job['source']}] {job['title']} at {job['company']}")
