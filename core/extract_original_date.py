"""
Extract original publication date from reference link pages.
Uses multiple strategies in priority order.
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from urllib.parse import urlparse
from datetime import datetime, date

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def parse_date(date_str: str):
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    date_str = re.sub(r'[+-]\d{2}:\d{2}$', '', date_str)
    date_str = re.sub(r'Z$', '', date_str)
    date_str = re.sub(r'\.\d+$', '', date_str)

    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d %b %Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%Y%m%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue
    return None


def is_valid_date(d: date) -> bool:
    """Reject future dates and unreasonably old dates."""
    if not d:
        return False
    today = date.today()
    if d > today:
        return False
    if d < date(2010, 1, 1):
        return False
    return True


def extract_from_meta(soup: BeautifulSoup):
    """Strategy 1: Extract date from meta tags. PUBLISHED only."""
    # ONLY published_time variants — never modified/updated
    published_props = [
        'article:published_time',
        'og:published_time',
        'published_time',
        'datePublished',
    ]
    for prop in published_props:
        tag = soup.find('meta', attrs={'property': prop}) or soup.find('meta', attrs={'name': prop})
        if tag and tag.get('content'):
            result = parse_date(tag['content'])
            if is_valid_date(result):
                return result

    # Generic meta name as last resort
    for name in ['date', 'pubdate', 'publish-date', 'creation_date']:
        tag = soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'):
            result = parse_date(tag['content'])
            if is_valid_date(result):
                return result

    return None


def extract_from_time_tag(soup: BeautifulSoup):
    """Strategy 2: Extract date from <time> tags."""
    for time_tag in soup.find_all('time'):
        dt_attr = time_tag.get('datetime', '')
        if dt_attr:
            result = parse_date(dt_attr)
            if is_valid_date(result):
                return result
        text = time_tag.get_text(strip=True)
        if text:
            result = parse_date(text)
            if is_valid_date(result):
                return result
    return None


def extract_from_json_ld(soup: BeautifulSoup):
    """Strategy 3: Extract date from JSON-LD script tags."""
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    for key in ['datePublished', 'dateCreated']:
                        if key in item and item[key]:
                            result = parse_date(item[key])
                            if is_valid_date(result):
                                return result
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def extract_from_url(url: str):
    """Strategy 4: Extract date from URL path patterns."""
    patterns = [
        r'/(\d{4})/(\d{2})/(\d{2})/',
        r'/(\d{4})-(\d{2})-(\d{2})/',
        r'/(\d{4})(\d{2})(\d{2})/',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            year, month, day = match.groups()
            try:
                result = datetime(int(year), int(month), int(day)).date()
                if is_valid_date(result):
                    return result
            except ValueError:
                continue
    return None


def get_original_date(reference_url: str, fallback_date=None):
    """
    Main entry point: try all strategies to extract original date.
    Returns a date object or None.
    NEVER returns fallback_date if extraction fails — caller decides.
    """
    if not reference_url or not reference_url.startswith('http'):
        return None

    try:
        resp = requests.get(reference_url, headers=HEADERS, timeout=10)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        for extractor in [extract_from_meta, extract_from_time_tag, extract_from_json_ld]:
            result = extractor(soup)
            if result:
                return result

        result = extract_from_url(reference_url)
        if result:
            return result

    except Exception as e:
        print(f"  [DateExtractor] Failed to fetch {reference_url}: {e}")

    return None


if __name__ == '__main__':
    test_urls = [
        'https://thequantuminsider.com/2026/05/18/sitehop-post-quantum-encryption-pqc-device/',
    ]
    for url in test_urls:
        d = get_original_date(url)
        print(f'{url} -> {d}')
