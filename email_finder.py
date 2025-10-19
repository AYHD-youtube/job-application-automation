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
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Find company domain and emails using Hunter.io company search
    
    Args:
        company_name: Company name
        api_key: Hunter.io API key
        limit: Maximum number of emails to return
        max_retries: Maximum retry attempts
        
    Returns:
        Dictionary with 'domain' and 'emails' keys
    """
    if not api_key:
        raise ValueError("Hunter API key is required")
    
    url = "https://api.hunter.io/v2/domain-search"
    
    # Try searching by company name directly
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
            
            return {
                'domain': domain,
                'emails': emails
            }
            
        except requests.exceptions.RequestException as e:
            print(f"  Error searching company (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                return {'domain': '', 'emails': []}
    
    return {'domain': '', 'emails': []}


def find_emails_with_fallback(
    company_name: str,
    domain: Optional[str],
    api_key: str
) -> List[str]:
    """
    Find emails with fallback strategy
    
    Args:
        company_name: Company name
        domain: Extracted domain (may be None or 'UNKNOWN')
        api_key: Hunter.io API key
        
    Returns:
        List of email addresses
    """
    emails = []
    
    # Try with extracted domain first
    if domain and domain != 'UNKNOWN':
        print(f"Searching for emails at domain: {domain}")
        emails = find_hr_emails(domain, api_key)
    
    # Fallback: try .com domain
    if not emails:
        fallback_domain = f"{company_name.lower().replace(' ', '')}.com"
        print(f"Trying fallback domain: {fallback_domain}")
        emails = find_hr_emails(fallback_domain, api_key)
    
    return emails

