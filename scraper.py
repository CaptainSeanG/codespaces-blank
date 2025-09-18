import requests
from bs4 import BeautifulSoup
import datetime, json, os

# Job board URLs for Phoenix / AZ pilot jobs
JOB_SOURCES = {
    "Indeed": "https://www.indeed.com/jobs?q=pilot+caravan+pc-12+cargo&l=Phoenix%2C+AZ",
    "ZipRecruiter": "https://www.ziprecruiter.com/candidate/search?search=pilot&location=Phoenix%2C+AZ",
    "PilotCareerCenter": "https://pilotcareercenter.com/PHOENIX-PILOT-JOBS/KIWA-KDVT-KPHX-KSDL",
    "Glassdoor": "https://www.glassdoor.com/Job/phoenix-pilot-jobs-SRCH_IL.0,7_IC1133904_KO8,13.htm",
}

KEYWORDS = ["caravan", "pc-12", "sky courier", "cargo", "part 135"]
HISTORY_FILE = "jobs_history.json"
DAYS_TO_KEEP = 30

# -------------------
# Source-specific parsers
# -------------------

def fetch_indeed(url):
    jobs = []
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    for card in soup.select("div.job_seen_beacon"):
        title = card.select_one("h2").get_text(strip=True)
        company = card.select_one("span.companyName").get_text(strip=True) if card.select_one("span.companyName") else "Unknown"
        link = "https://www.indeed.com" + card.select_one("a")["href"]
        jobs.append({"title": title, "company": company, "link": link, "source": "Indeed"})
    return jobs

def fetch_zip(url):
    jobs = []
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    for card in soup.select("article.job_content"):
        title_tag = card.select_one("a")
        if not title_tag: continue
        title = title_tag.get_text(strip=True)
        link = title_tag["href"] if title_tag["href"].startswith("http") else "https://www.ziprecruiter.com" + title_tag["href"]
        company = card.select_one("a.t_org_link").get_text(strip=True) if card.select_one("a.t_org_link") else "Unknown"
        jobs.append({"title": title, "company": company, "link": link, "source": "ZipRecruiter"})
    return jobs

def fetch_pilotcareercenter(url):
    jobs = []
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) >= 2:
            title = cols[0].get_text(strip=True)
            company = cols[1].get_text(strip=True)
            link = url
            jobs.append({"title": title, "company": company, "link": link, "source": "PilotCareerCenter"})
    return jobs

def fetch_glassdoor(url):
    jobs = []
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    for card in soup.select("li.react-job-listing"):
        title = card.get("data-normalize-job-title", "Pilot Job")
        company = card.get("data-company", "Unknown")
        link = "https://www.glassdoor.com" + card.get("data-link", "")
        jobs.append({"title": title, "company": company, "link": link, "source": "Glassdoor"})
    return jobs

# -------------------
# Filtering & History
# -------------------

def filter_jobs(jobs):
    filtered = []
    for job in jobs:
        text = (job["title"] + " " + job["company"]).lower()
        if any(k in text for k in KEYWORDS):
            filtered.append(job)
    return filtered

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def update_history(today_jobs):
    today_str = datetime.date.today().isoformat()
    history = load_history()
    history[today_str] = today_jobs

    # Keep only last N days
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    history = {day: jobs for day, jobs in history.items() if datetime.date.fromisoformat(day) >= cutoff}

    save_history(history)
    return history

# -------------------
# HTML Output
# -------------------

def generate_html(today_jobs, history):
    today = datetime.date.today().strftime("%B %d, %Y")
    html = f"<html><head><title>Phoenix Pilot Jobs</title></head><body>"
    html += f"<h1>Phoenix Low-Time Pilot Jobs</h1><p>Updated {today}</p>"

    # Today's jobs
    html += "<h2>Today’s Jobs</h2><ul>"
    if today_jobs:
        for job in today_jobs:
            html += f"<li><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} ({job['source']})</li>"
    else:
        html += "<li>No new jobs found today.</li>"
    html += "</ul>"

    # History
    html += "<h2>Job History (Last 30 Days)</h2>"
    for day, jobs in sorted(history.items(), reverse=True):
        html += f"<h3>{day}</h3><ul>"
        for job in jobs:
            html += f"<li><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} ({job['source']})</li>"
        html += "</ul>"

    html += "</body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

# -------------------
# Main
# -------------------

def main():
    all_jobs = []
    all_jobs.extend(fetch_indeed(JOB_SOURCES["Indeed"]))
    all_jobs.extend(fetch_zip(JOB_SOURCES["ZipRecruiter"]))
    all_jobs.extend(fetch_pilotcareercenter(JOB_SOURCES["PilotCareerCenter"]))
    all_jobs.extend(fetch_glassdoor(JOB_SOURCES["Glassdoor"]))

    today_jobs = filter_jobs(all_jobs)
    history = update_history(today_jobs)
    generate_html(today_jobs, history)
    print(f"✅ Saved {len(today_jobs)} new jobs, {len(history)} days in archive.")

if __name__ == "__main__":
    main()
