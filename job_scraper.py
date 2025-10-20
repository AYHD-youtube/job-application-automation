# job_scraper.py
"""LinkedIn job scraping and parsing"""
import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from linkedin import parse_job_html


def scrape_job_list(search_url: str, linkedin_cookie: str = None) -> List[str]:
    """
    Scrape job URLs from LinkedIn search results page
    
    Args:
        search_url: LinkedIn jobs search URL
        linkedin_cookie: Optional LinkedIn session cookie (li_at value)
        
    Returns:
        List of job URLs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    cookies = {}
    if linkedin_cookie:
        cookies['li_at'] = linkedin_cookie
        print(f"  Using authenticated LinkedIn session (cookie length: {len(linkedin_cookie)})")
    else:
        print("  No LinkedIn cookie provided - using anonymous session")
    
    try:
        response = requests.get(search_url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract job URLs from search results
        job_links = []
        
        # Debug: Check if we got a valid response
        print(f"  Response status: {response.status_code}")
        print(f"  Response length: {len(response.text)} characters")
        print(f"  Final URL: {response.url}")
        
        # Check if we got redirected to login or blocked
        if 'login' in response.url.lower() or 'challenge' in response.url.lower():
            print("  WARNING: Redirected to login/challenge page - LinkedIn cookie may be invalid")
        elif response.status_code == 429:
            print("  WARNING: Rate limited by LinkedIn")
        elif len(response.text) < 1000:
            print("  WARNING: Very short response - may be blocked or invalid")
        
        # Try multiple selectors for job cards (LinkedIn changes their structure frequently)
        selectors_to_try = [
            'ul.jobs-search__results-list li div a[class*="base-card"]',  # Old selector
            'ul.jobs-search__results-list li a[href*="/jobs/view/"]',     # More specific
            'div[data-job-id] a[href*="/jobs/view/"]',                    # Alternative
            'a[href*="/jobs/view/"]',                                     # Very broad
            'ul.jobs-search__results-list li a',                         # Even broader
            'div[class*="job-card"] a',                                   # Another variant
            'div[class*="job"] a[href*="/jobs/"]'                        # Generic job links
        ]
        
        for selector in selectors_to_try:
            job_cards = soup.select(selector)
            print(f"  Trying selector '{selector}': found {len(job_cards)} elements")
            
            if job_cards:
                for card in job_cards:
                    href = card.get('href')
                    if href and '/jobs/view/' in href:
                        # Clean up the URL
                        if '?' in href:
                            href = href.split('?')[0]
                        if href not in job_links:  # Avoid duplicates
                            job_links.append(href)
                
                if job_links:
                    print(f"  Found {len(job_links)} job URLs with selector: {selector}")
                    break
        
        # If still no results, try to find any links containing job IDs
        if not job_links:
            all_links = soup.find_all('a', href=True)
            print(f"  Total links found on page: {len(all_links)}")
            
            for link in all_links:
                href = link.get('href')
                if href and '/jobs/view/' in href:
                    if '?' in href:
                        href = href.split('?')[0]
                    if href not in job_links:
                        job_links.append(href)
            
            print(f"  Found {len(job_links)} job URLs by scanning all links")
        
        # If still no results, try to extract from JavaScript/JSON data
        if not job_links:
            print("  Trying to extract job URLs from JavaScript/JSON data...")
            # Look for JSON data in script tags
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'itemListElement' in data:
                        for item in data['itemListElement']:
                            if 'url' in item:
                                url = item['url']
                                if '/jobs/view/' in url:
                                    if '?' in url:
                                        url = url.split('?')[0]
                                    if url not in job_links:
                                        job_links.append(url)
                except:
                    continue
            
            print(f"  Found {len(job_links)} job URLs from JSON data")
        
        return job_links
        
    except Exception as e:
        print(f"Error scraping job list: {e}")
        return []


def scrape_job_details(job_url: str, linkedin_cookie: str = None) -> Dict[str, Any]:
    """
    Scrape detailed information from a job posting
    
    Args:
        job_url: URL of the job posting
        linkedin_cookie: Optional LinkedIn session cookie (li_at value)
        
    Returns:
        Dictionary containing job details
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    cookies = {}
    if linkedin_cookie:
        cookies['li_at'] = linkedin_cookie
    
    try:
        response = requests.get(job_url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        
        # Use the existing parser
        job_data = parse_job_html(response.text)
        
        # Parse additional fields from the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract applicant count
        applicant_elem = soup.select_one('span.num-applicants__caption')
        applicant_text = applicant_elem.get_text(strip=True) if applicant_elem else ""
        
        # Extract salary range
        salary_elem = soup.select_one('div[class*="salary"] span, div.compensation__salary')
        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
        
        # Add extra fields
        job_data['applicant_text'] = applicant_text
        job_data['salary_text'] = salary_text
        job_data['job_url'] = job_url
        
        return job_data
        
    except Exception as e:
        print(f"Error scraping job details from {job_url}: {e}")
        return {
            'job_url': job_url,
            'error': str(e)
        }


def normalize_job_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and clean job data, calculate quality metrics
    
    Args:
        raw_data: Raw scraped job data
        
    Returns:
        Normalized job data with quality metrics
    """
    # Helper to normalize values
    def norm(v):
        if isinstance(v, list):
            return str(v[0]).strip() if v else ""
        if v and isinstance(v, dict):
            if '0' in v:
                return str(v['0']).strip()
            return str(v)
        return str(v or "").strip()
    
    # Extract and normalize text fields
    title = norm(raw_data.get('title', ''))
    company = norm(raw_data.get('company', ''))
    location = norm(raw_data.get('location', ''))
    description = norm(raw_data.get('description', ''))
    job_id = norm(raw_data.get('job_id', ''))
    job_url = norm(raw_data.get('job_url', ''))
    
    # Parse applicant count
    applicant_count = 0
    applicant_text = norm(raw_data.get('applicant_text', ''))
    if applicant_text:
        match = re.search(r'\d+', applicant_text)
        if match:
            applicant_count = int(match.group(0))
    
    # Parse posted date (convert to days ago)
    days_ago = 999
    posted_text = norm(raw_data.get('posted_text', '')).lower()
    if posted_text:
        if 'hour' in posted_text or 'today' in posted_text:
            days_ago = 0
        elif 'yesterday' in posted_text:
            days_ago = 1
        elif 'day' in posted_text:
            match = re.search(r'\d+', posted_text)
            days_ago = int(match.group(0)) if match else 1
        elif 'week' in posted_text:
            match = re.search(r'\d+', posted_text)
            days_ago = (int(match.group(0)) if match else 1) * 7
        elif 'month' in posted_text:
            match = re.search(r'\d+', posted_text)
            days_ago = (int(match.group(0)) if match else 1) * 30
    
    # Parse salary range
    min_salary = 0
    max_salary = 0
    salary_text = norm(raw_data.get('salary_text', ''))
    if salary_text:
        numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_text)
        if len(numbers) >= 2:
            min_salary = int(float(numbers[0].replace(',', '')))
            max_salary = int(float(numbers[1].replace(',', '')))
        elif len(numbers) == 1:
            min_salary = int(float(numbers[0].replace(',', '')))
            max_salary = min_salary
    
    return {
        'Title': title,
        'Company': company,
        'Location': location,
        'Description': description,
        'JobID': job_id,
        'job_url': job_url,
        'applicant_count_num': applicant_count,
        'days_posted_ago': days_ago,
        'salary_min': min_salary,
        'salary_max': max_salary,
        'posted_text': posted_text,
        'applicant_text': applicant_text,
        'salary_text': salary_text,
    }


def check_quality(job_data: Dict[str, Any], config: Dict[str, Any]) -> tuple:
    """
    Check if job meets quality criteria
    
    Args:
        job_data: Normalized job data
        config: Configuration with thresholds
        
    Returns:
        Tuple of (passes_quality_check, skip_reason)
    """
    reasons = []
    
    # Check required fields
    if not job_data.get('Title'):
        reasons.append('Missing title')
    if not job_data.get('Company'):
        reasons.append('Missing company')
    if len(job_data.get('Description', '')) < config.get('MIN_DESCRIPTION_LENGTH', 50):
        reasons.append('Insufficient description')
    
    # Check posting age
    days_ago = job_data.get('days_posted_ago', 999)
    max_days = config.get('MAX_DAYS_POSTED', 14)
    if days_ago > max_days:
        reasons.append(f'Posted {days_ago} days ago (>{max_days} days)')
    
    # Check competition level
    applicant_count = job_data.get('applicant_count_num', 0)
    max_applicants = config.get('MAX_APPLICANTS', 500)
    if applicant_count > max_applicants:
        reasons.append(f'{applicant_count} applicants (>{max_applicants})')
    
    # Check excluded companies
    company = job_data.get('Company', '')
    excluded = config.get('EXCLUDED_COMPANIES', [])
    for excluded_company in excluded:
        if excluded_company.lower() in company.lower():
            reasons.append(f'Excluded company: {excluded_company}')
    
    quality_pass = len(reasons) == 0
    skip_reason = ', '.join(reasons) if reasons else ''
    
    return quality_pass, skip_reason

