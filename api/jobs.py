# api/jobs.py
import json
import re
import hashlib
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from datetime import datetime

# ==================== HTML Parser ====================
class HTMLTagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
    
    def handle_data(self, data):
        self.text_parts.append(data)
    
    def get_text(self):
        return ' '.join(p.strip() for p in self.text_parts if p.strip())

def strip_html(html_content):
    """HTML ট্যাগ সরিয়ে টেক্সট রিটার্ন করে"""
    stripper = HTMLTagStripper()
    stripper.feed(html_content)
    return stripper.get_text()

# ==================== Utility Functions ====================
def generate_job_id(title, company, source):
    """ইউনিক job ID জেনারেট করে"""
    unique_string = f"{title.lower()}{company.lower()}{source}{datetime.now().strftime('%Y%m%d')}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

def extract_skills(text):
    """টেক্সট থেকে টেক স্কিল এক্সট্রাক্ট করে"""
    skills_list = [
        "Python", "JavaScript", "Java", "C++", "Ruby", "PHP", "Swift", "Kotlin",
        "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring",
        "TensorFlow", "PyTorch", "Machine Learning", "AI", "Data Science",
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "DevOps",
        "SQL", "MongoDB", "PostgreSQL", "MySQL", "Redis",
        "HTML", "CSS", "SASS", "Tailwind", "Bootstrap",
        "Git", "GitHub", "GitLab", "Jira", "Agile"
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in skills_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)
            if len(found_skills) >= 5:
                break
    
    return found_skills

def determine_experience(text):
    """Job description থেকে experience level নির্ধারণ করে"""
    text_lower = text.lower()
    if any(word in text_lower for word in ['senior', 'lead', 'principal', '5+', '7+']):
        return "Senior"
    elif any(word in text_lower for word in ['junior', 'entry', 'fresher', '0-2', 'graduate']):
        return "Entry Level"
    else:
        return "Mid Level"

def determine_job_type(text):
    """Job type নির্ধারণ করে"""
    text_lower = text.lower()
    if 'part-time' in text_lower or 'part time' in text_lower:
        return "Part-time"
    elif 'contract' in text_lower:
        return "Contract"
    elif 'intern' in text_lower:
        return "Internship"
    else:
        return "Full-time"

def fetch_url(url, params=None):
    """URL থেকে ডাটা ফেচ করে"""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            try:
                return html.decode('utf-8')
            except:
                return html.decode('latin-1', errors='ignore')
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}")

# ==================== BDJobs Scraper ====================
def scrape_bdjobs(keyword, location):
    """BDJobs থেকে job scrape করে"""
    jobs = []
    errors = []
    
    try:
        # Search URL
        search_params = {"Keyword": keyword, "Country": "1"}
        if location and location not in ["", "all", "bangladesh"]:
            search_params["Location"] = location
        
        search_url = "https://jobs.bdjobs.com/jobsearch.asp"
        search_html = fetch_url(search_url, search_params)
        
        # Job links extract
        job_links = re.findall(r'href="(jobdetails\.asp\?id=\d+[^"]*)"', search_html)
        job_links = list(dict.fromkeys(job_links))[:15]  # Remove duplicates and limit
        
        for link in job_links:
            try:
                full_url = f"https://jobs.bdjobs.com/{link}"
                job_html = fetch_url(full_url)
                
                # Extract job details
                title = re.search(r'<h1[^>]*>(.*?)</h1>', job_html, re.DOTALL | re.IGNORECASE)
                title = strip_html(title.group(1)) if title else ""
                
                company = re.search(r'class="[^"]*company[^"]*"[^>]*>(.*?)</', job_html, re.DOTALL | re.IGNORECASE)
                company = strip_html(company.group(1)) if company else "Unknown Company"
                
                location_match = re.search(r'Location[^<]*<[^>]+>([^<]+)<', job_html, re.IGNORECASE)
                job_location = strip_html(location_match.group(1)) if location_match else location or "Dhaka"
                
                salary = re.search(r'Salary[^<]*<[^>]+>([^<]+)<', job_html, re.IGNORECASE)
                salary = strip_html(salary.group(1)) if salary else "Negotiable"
                
                deadline = re.search(r'Deadline[^<]*<[^>]+>([^<]+)<', job_html, re.IGNORECASE)
                deadline = strip_html(deadline.group(1)) if deadline else ""
                
                description_match = re.search(r'id="[^"]*desc[^"]*"[^>]*>(.*?)</div>', job_html, re.DOTALL | re.IGNORECASE)
                description = strip_html(description_match.group(1))[:500] if description_match else ""
                
                full_text = title + " " + description + " " + company
                
                job = {
                    "id": generate_job_id(title, company, "BDJobs"),
                    "title": title[:100],
                    "company": company[:80],
                    "location": job_location[:50],
                    "job_type": determine_job_type(full_text),
                    "experience": determine_experience(full_text),
                    "salary": salary[:50],
                    "description": description,
                    "skills": extract_skills(full_text),
                    "apply_url": full_url,
                    "source": "BDJobs",
                    "posted_date": "Today",
                    "deadline": deadline,
                    "is_remote": "remote" in full_text.lower(),
                    "is_new": True
                }
                
                if job["title"] and len(job["title"]) > 5:
                    jobs.append(job)
                    
            except Exception as e:
                errors.append(f"Error parsing BDJobs detail: {str(e)}")
                continue
                
    except Exception as e:
        errors.append(f"BDJobs search error: {str(e)}")
    
    return jobs, errors

# ==================== Chakri.com Scraper ====================
def scrape_chakri(keyword, location):
    """Chakri.com থেকে job scrape করে"""
    jobs = []
    errors = []
    
    try:
        search_params = {"q": keyword}
        if location and location not in ["", "all", "bangladesh"]:
            search_params["location"] = location
        
        search_url = "https://www.chakri.com/jobs"
        search_html = fetch_url(search_url, search_params)
        
        # Job links extract
        job_links = re.findall(r'href="(https://www\.chakri\.com/jobs/[^"?#]+)"', search_html)
        job_links = list(dict.fromkeys(job_links))[:12]
        
        for link in job_links:
            try:
                job_html = fetch_url(link)
                
                title = re.search(r'<h1[^>]*>(.*?)</h1>', job_html, re.DOTALL)
                title = strip_html(title.group(1)) if title else ""
                
                company = re.search(r'class="[^"]*company[^"]*"[^>]*>(.*?)</', job_html, re.DOTALL)
                company = strip_html(company.group(1)) if company else "Unknown Company"
                
                location_match = re.search(r'location[^<]*<[^>]+>([^<]+)<', job_html, re.DOTALL | re.IGNORECASE)
                job_location = strip_html(location_match.group(1)) if location_match else location or "Dhaka"
                
                # Remove scripts for clean text
                clean_html = re.sub(r'<script[^>]*>.*?</script>', '', job_html, flags=re.DOTALL)
                description = strip_html(clean_html)[:500]
                
                full_text = title + " " + description
                
                job = {
                    "id": generate_job_id(title, company, "Chakri"),
                    "title": title[:100],
                    "company": company[:80],
                    "location": job_location[:50],
                    "job_type": determine_job_type(full_text),
                    "experience": determine_experience(full_text),
                    "salary": "Negotiable",
                    "description": description,
                    "skills": extract_skills(full_text),
                    "apply_url": link,
                    "source": "Chakri.com",
                    "posted_date": "Recently",
                    "deadline": "",
                    "is_remote": "remote" in full_text.lower(),
                    "is_new": True
                }
                
                if job["title"] and len(job["title"]) > 5:
                    jobs.append(job)
                    
            except Exception as e:
                errors.append(f"Error parsing Chakri detail: {str(e)}")
                continue
                
    except Exception as e:
        errors.append(f"Chakri search error: {str(e)}")
    
    return jobs, errors

# ==================== Indeed BD Scraper ====================
def scrape_indeed(keyword, location):
    """Indeed BD থেকে job scrape করে"""
    jobs = []
    errors = []
    
    try:
        search_location = location if location and location not in ["", "all", "bangladesh"] else "Dhaka"
        search_params = {"q": keyword, "l": search_location, "sort": "date"}
        
        search_url = "https://bd.indeed.com/jobs"
        search_html = fetch_url(search_url, search_params)
        
        # Find job cards
        job_pattern = r'data-jk="([^"]+)".*?<span[^>]*>([^<]+)</span>.*?class="companyName"[^>]*>(.*?)</.*?class="companyLocation"[^>]*>([^<]+)<'
        job_cards = re.findall(job_pattern, search_html, re.DOTALL)
        
        for jk, title, company, job_location in job_cards[:12]:
            try:
                title = strip_html(title).strip()
                company = strip_html(company).strip()
                job_location = strip_html(job_location).strip()
                
                # Find salary if available
                salary_pattern = rf'data-jk="{re.escape(jk)}".*?class="[^"]*salary[^"]*"[^>]*>([^<]+)<'
                salary_match = re.search(salary_pattern, search_html, re.DOTALL)
                salary = strip_html(salary_match.group(1)) if salary_match else "Negotiable"
                
                full_text = title + " " + company + " " + job_location
                
                job = {
                    "id": generate_job_id(title, company, "Indeed"),
                    "title": title[:100],
                    "company": company[:80],
                    "location": job_location[:50],
                    "job_type": determine_job_type(full_text),
                    "experience": determine_experience(full_text),
                    "salary": salary[:50],
                    "description": "",
                    "skills": extract_skills(full_text),
                    "apply_url": f"https://bd.indeed.com/viewjob?jk={jk}",
                    "source": "Indeed BD",
                    "posted_date": "Today",
                    "deadline": "",
                    "is_remote": "remote" in full_text.lower(),
                    "is_new": True
                }
                
                if job["title"] and len(job["title"]) > 5:
                    jobs.append(job)
                    
            except Exception as e:
                errors.append(f"Error parsing Indeed job: {str(e)}")
                continue
                
    except Exception as e:
        errors.append(f"Indeed search error: {str(e)}")
    
    return jobs, errors

# ==================== Vercel Handler ====================
def handler(request):
    """Vercel serverless function handler"""
    try:
        # Parse query parameters
        from urllib.parse import parse_qs, urlparse
        
        query_params = parse_qs(urlparse(request.url).query)
        
        def get_param(key, default=""):
            return query_params.get(key, [default])[0]
        
        keyword = get_param("keyword", "Machine Learning Engineer")
        location = get_param("location", "Dhaka")
        source = get_param("source", "all")
        
        all_jobs = []
        all_errors = []
        
        # Scrape from selected sources
        if source in ["all", "bdjobs"]:
            jobs, errors = scrape_bdjobs(keyword, location)
            all_jobs.extend(jobs)
            all_errors.extend(errors)
        
        if source in ["all", "chakri"]:
            jobs, errors = scrape_chakri(keyword, location)
            all_jobs.extend(jobs)
            all_errors.extend(errors)
        
        if source in ["all", "indeed"]:
            jobs, errors = scrape_indeed(keyword, location)
            all_jobs.extend(jobs)
            all_errors.extend(errors)
        
        # Remove duplicates based on ID
        unique_jobs = []
        seen_ids = set()
        
        for job in all_jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                unique_jobs.append(job)
        
        # Calculate stats
        new_today = sum(1 for job in unique_jobs if job.get("is_new"))
        remote_count = sum(1 for job in unique_jobs if job.get("is_remote"))
        
        response = {
            "status": "success",
            "total": len(unique_jobs),
            "new_today": new_today,
            "remote_count": remote_count,
            "jobs": unique_jobs,
            "errors": all_errors[:5]  # Limit errors to 5
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps(response, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "error",
                "message": str(e),
                "jobs": []
            })
        }

# For OPTIONS request
def options_handler(request):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": ""
    }