# email_finder.py
"""Find HR emails using Hunter.io API"""
import time
import requests
from typing import List, Dict, Any, Optional


def find_hr_emails(
    domain: str,
    api_key: str,
    limit: int = 5,
    max_retries: int = 3
) -> List[str]:
    """
    Find HR department emails for a domain using Hunter.io
    
    Args:
        domain: Company domain (e.g., 'example.com')
        api_key: Hunter.io API key
        limit: Maximum number of emails to return
        max_retries: Maximum retry attempts
        
    Returns:
        List of email addresses
    """
    if not api_key:
        raise ValueError("Hunter API key is required")
    
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "api_key": api_key,
        "domain": domain,
        "limit": limit,
        "department": "hr"
    }
    
    # Retry logic for rate limits and transient errors
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=20)
            
            # Handle rate limiting
            if response.status_code in (429, 500, 502, 503, 504):
                wait_time = 1.5 * (attempt + 1)
                print(f"Rate limited or server error, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            # Extract emails from response
            emails = []
            email_data = data.get('data', {}).get('emails', [])
            
            for entry in email_data:
                email = entry.get('value')
                if email:
                    emails.append(email)
            
            return emails
            
        except requests.exceptions.RequestException as e:
            print(f"Error finding emails (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                return []
    
    return []


def find_company_domain_and_emails(
    company_name: str,
    api_key: str,
    limit: int = 5,
    max_retries: int = 3,
    google_api_key: str = None
) -> Dict[str, Any]:
    """
    Find company domain and emails using comprehensive strategies
    
    Args:
        company_name: Company name
        api_key: Hunter.io API key
        limit: Maximum number of emails to return
        max_retries: Maximum retry attempts
        google_api_key: Google API key for AI generation (optional)
        
    Returns:
        Dictionary with 'domain' and 'emails' keys
    """
    if not api_key:
        raise ValueError("Hunter API key is required")
    
    print(f"  Finding emails for company: {company_name}")
    
    # Strategy 1: Try Hunter.io company search
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "api_key": api_key,
        "company": company_name,
        "limit": limit,
        "department": "hr"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=20)
            
            # Handle rate limiting
            if response.status_code in (429, 500, 502, 503, 504):
                wait_time = 1.5 * (attempt + 1)
                print(f"  Rate limited or server error, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            # Extract domain and emails
            domain = data.get('data', {}).get('domain', '')
            emails = []
            email_data = data.get('data', {}).get('emails', [])
            
            for entry in email_data:
                email = entry.get('value')
                if email:
                    emails.append(email)
            
            if domain and emails:
                print(f"  Hunter.io found {len(emails)} emails for domain: {domain}")
                return {'domain': domain, 'emails': emails}
            
        except requests.exceptions.RequestException as e:
            print(f"  Error searching company (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
    
    # Strategy 2: Try comprehensive fallback methods
    print(f"  Hunter.io failed, trying fallback methods...")
    
    # Generate domain variations and try each one
    domain_variations = generate_domain_variations(company_name)
    
    for domain in domain_variations:
        print(f"  Trying domain: {domain}")
        
        # Try Hunter.io with this domain
        try:
            emails = find_hr_emails(domain, api_key)
            if emails:
                print(f"  Found {len(emails)} emails with Hunter.io for {domain}")
                return {'domain': domain, 'emails': emails}
        except:
            pass
        
        # Try generic email patterns
        generic_emails = generate_generic_emails(domain)
        if generic_emails:
            print(f"  Generated {len(generic_emails)} generic email patterns for {domain}")
            return {'domain': domain, 'emails': generic_emails}
        
        # Try web scraping
        scraped_emails = scrape_contact_emails(domain)
        if scraped_emails:
            print(f"  Scraped {len(scraped_emails)} emails from {domain}")
            return {'domain': domain, 'emails': scraped_emails}
    
    # Strategy 3: Try AI generation if API key provided
    if google_api_key and domain_variations:
        best_domain = domain_variations[0]  # Use first domain variation
        print(f"  Trying AI generation for domain: {best_domain}")
        ai_emails = find_emails_with_ai_generation(company_name, best_domain, google_api_key)
        if ai_emails:
            print(f"  AI generated {len(ai_emails)} email patterns")
            return {'domain': best_domain, 'emails': ai_emails}
    
    print(f"  No emails found for {company_name}")
    return {'domain': '', 'emails': []}


def find_emails_with_fallback(
    company_name: str,
    domain: Optional[str],
    api_key: str
) -> List[str]:
    """
    Find emails with comprehensive fallback strategy
    
    Args:
        company_name: Company name
        domain: Extracted domain (may be None or 'UNKNOWN')
        api_key: Hunter.io API key
        
    Returns:
        List of email addresses
    """
    emails = []
    
    # Strategy 1: Try with extracted domain first
    if domain and domain != 'UNKNOWN':
        print(f"Searching for emails at domain: {domain}")
        emails = find_hr_emails(domain, api_key)
    
    # Strategy 2: Try common domain variations
    if not emails:
        domain_variations = generate_domain_variations(company_name)
        for domain_var in domain_variations:
            print(f"Trying domain variation: {domain_var}")
            emails = find_hr_emails(domain_var, api_key)
            if emails:
                break
    
    # Strategy 3: Try generic email patterns
    if not emails and domain and domain != 'UNKNOWN':
        print(f"Trying generic email patterns for domain: {domain}")
        emails = generate_generic_emails(domain)
    
    # Strategy 4: Try web scraping for contact information
    if not emails and domain and domain != 'UNKNOWN':
        print(f"Scraping contact page for domain: {domain}")
        emails = scrape_contact_emails(domain)
    
    return emails


def generate_domain_variations(company_name: str) -> List[str]:
    """
    Generate common domain variations for a company name
    
    Args:
        company_name: Company name
        
    Returns:
        List of potential domain names
    """
    # Clean company name
    clean_name = company_name.lower().strip()
    clean_name = clean_name.replace(' ', '')
    clean_name = clean_name.replace('&', 'and')
    clean_name = clean_name.replace('+', 'plus')
    clean_name = clean_name.replace('.', '')
    clean_name = clean_name.replace(',', '')
    clean_name = clean_name.replace('inc', '')
    clean_name = clean_name.replace('llc', '')
    clean_name = clean_name.replace('corp', '')
    clean_name = clean_name.replace('ltd', '')
    clean_name = clean_name.replace('limited', '')
    
    variations = []
    
    # Basic variations
    variations.extend([
        f"{clean_name}.com",
        f"{clean_name}.org",
        f"{clean_name}.net",
        f"{clean_name}.co",
        f"{clean_name}.io",
        f"{clean_name}.ai",
        f"{clean_name}.tech"
    ])
    
    # Add spaces back for some variations
    spaced_name = company_name.lower().replace(' ', '')
    if spaced_name != clean_name:
        variations.extend([
            f"{spaced_name}.com",
            f"{spaced_name}.org",
            f"{spaced_name}.net"
        ])
    
    # Try with hyphens
    hyphen_name = company_name.lower().replace(' ', '-')
    variations.extend([
        f"{hyphen_name}.com",
        f"{hyphen_name}.org",
        f"{hyphen_name}.net"
    ])
    
    return variations[:10]  # Limit to first 10 variations


def generate_generic_emails(domain: str) -> List[str]:
    """
    Generate generic email patterns for a domain
    
    Args:
        domain: Company domain
        
    Returns:
        List of potential generic email addresses
    """
    generic_patterns = [
        f"hr@{domain}",
        f"humanresources@{domain}",
        f"careers@{domain}",
        f"jobs@{domain}",
        f"recruiting@{domain}",
        f"talent@{domain}",
        f"hiring@{domain}",
        f"info@{domain}",
        f"contact@{domain}",
        f"hello@{domain}",
        f"admin@{domain}",
        f"support@{domain}"
    ]
    
    return generic_patterns


def scrape_contact_emails(domain: str) -> List[str]:
    """
    Scrape contact emails from company website
    
    Args:
        domain: Company domain
        
    Returns:
        List of found email addresses
    """
    import re
    import requests
    from bs4 import BeautifulSoup
    
    emails = []
    
    # Common contact page URLs to try
    contact_urls = [
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/about/contact",
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://{domain}/about",
        f"https://{domain}/team",
        f"https://{domain}/"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for url in contact_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all text content
                text_content = soup.get_text()
                
                # Extract emails using regex
                found_emails = re.findall(email_pattern, text_content)
                
                # Filter for emails from the same domain
                domain_emails = [email for email in found_emails if email.endswith(f'@{domain}')]
                emails.extend(domain_emails)
                
                # Also look in href attributes
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if 'mailto:' in href:
                        email = href.replace('mailto:', '').split('?')[0]
                        if email.endswith(f'@{domain}'):
                            emails.append(email)
                
                if emails:
                    print(f"  Found {len(emails)} emails from {url}")
                    break
                    
        except Exception as e:
            print(f"  Error scraping {url}: {e}")
            continue
    
    # Remove duplicates and return
    return list(set(emails))


def find_emails_with_ai_generation(company_name: str, domain: str, google_api_key: str) -> List[str]:
    """
    Use AI to generate likely email patterns for a company
    
    Args:
        company_name: Company name
        domain: Company domain
        google_api_key: Google API key for Gemini
        
    Returns:
        List of generated email addresses
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=google_api_key)
        
        prompt = f"""Based on the company "{company_name}" with domain "{domain}", generate the most likely HR/recruiting email addresses.

Company: {company_name}
Domain: {domain}

Generate 5-10 realistic email addresses that this company would likely use for:
- HR department
- Recruiting
- Careers
- Job applications
- General contact

Format: Return only the email addresses, one per line, no explanations.

Examples of what to look for:
- hr@domain.com
- careers@domain.com
- jobs@domain.com
- recruiting@domain.com
- humanresources@domain.com
- talent@domain.com
- hiring@domain.com"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse the response
        generated_emails = []
        for line in response.text.strip().split('\n'):
            line = line.strip()
            if '@' in line and line.endswith(f'@{domain}'):
                generated_emails.append(line)
        
        print(f"  AI generated {len(generated_emails)} email patterns")
        return generated_emails
        
    except Exception as e:
        print(f"  Error generating emails with AI: {e}")
        return []

