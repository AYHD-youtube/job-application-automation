import re
import sys
import json
import pathlib
from typing import Optional, Dict, Any, List

from bs4 import BeautifulSoup

def _text(el) -> Optional[str]:
    if not el:
        return None
    s = el.get_text(" ", strip=True) if hasattr(el, "get_text") else str(el)
    s = s.strip()
    return s or None

def _attr(tag, name) -> Optional[str]:
    try:
        v = tag.get(name)
        if isinstance(v, list):
            v = v[0]
        return v.strip() if v else None
    except Exception:
        return None

def extract_meta(soup: BeautifulSoup, prop: str, by: str="property") -> Optional[str]:
    tag = soup.find("meta", {by: prop})
    return _attr(tag, "content") if tag else None

def extract_first(soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            t = _text(el)
            if t:
                return t
    return None

def parse_job_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    # canonical + job id
    canonical = None
    tag = soup.find("link", rel="canonical")
    if tag:
        canonical = _attr(tag, "href")
    lnkd_url = extract_meta(soup, "lnkd:url")
    if not canonical and lnkd_url:
        canonical = lnkd_url

    job_id = None
    if canonical:
        m = re.search(r"/jobs/view/[^/]*-(\d+)", canonical) or re.search(r"/jobs/view/(\d+)", canonical)
        if m:
            job_id = m.group(1)

    # quick metadata present in <meta>
    og_title = extract_meta(soup, "og:title")
    og_desc  = extract_meta(soup, "og:description")
    page_title = _text(soup.title) if soup.title else None

    # extra ids from meta
    company_id = extract_meta(soup, "companyId", by="name")
    industry_ids = extract_meta(soup, "industryIds", by="name")
    title_id = extract_meta(soup, "titleId", by="name")

    # title (robust order)
    title = (
        extract_first(soup, [
            'h1[data-test-id="job-details__job-title"]',
            "h1.top-card-layout__title",
            "h1.topcard__title",
        ])
        or og_title or page_title
    )

    # company
    company = extract_first(soup, [
        "a.topcard__org-name-link",
        "a.top-card-layout__company-url",
        ".top-card-layout__entity-info .topcard__flavor a",
        ".topcard__org-name-link",
        'a[data-tracking-control-name="public_jobs_topcard-org-name"]'
    ])

    # location
    location = extract_first(soup, [
        ".top-card-layout__entity-info .topcard__flavor--bullet",
        ".jobs-unified-top-card__bullet",
        ".topcard__flavor--bullet",
        'span[data-test-id="job-details__location"]'
    ])

    # posted text / time-ago
    posted_text = extract_first(soup, [
        "span.jobs-unified-top-card__posted-date",
        ".posted-time-ago__text",
        ".topcard__flavor--metadata",
        "time"
    ])

    # description (expanded markup container)
    description = extract_first(soup, [
        "div.show-more-less-html__markup",
        "div.jobs-description__content",
        "section.jobs-description-content__text"
    ])

    # plain-text description as fallback (strip repeated whitespace)
    if description:
        descr_plain = re.sub(r"\s+\n", "\n", description)
    else:
        descr_plain = None

    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "posted_text": posted_text,
        "canonical_url": canonical,
        "meta_og_title": og_title,
        "meta_og_description": og_desc,
        "company_id": company_id,
        "industry_ids": industry_ids,
        "title_id": title_id,
        "description": descr_plain,
    }

def read_html_from(path_or_dash: str) -> str:
    if path_or_dash == "-" or path_or_dash == "":
        return sys.stdin.read()
    p = pathlib.Path(path_or_dash)
    return p.read_text(encoding="utf-8", errors="ignore")

if __name__ == "__main__":
    # usage:
    #   python parse_linkedin_job_html.py job.html
    #   cat job.html | python parse_linkedin_job_html.py -
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    html = read_html_from(src)
    data = parse_job_html(html)
    print(json.dumps(data, ensure_ascii=False, indent=2))