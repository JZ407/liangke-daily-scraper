"""
Funding tagger: extracts structured funding data from article title+content.
Outputs tags.funding dict for MySQL JSON column.

Usage:
    from funding_tagger import tag_funding
    funding = tag_funding(title, content)
    # → {'is_funding': True, 'company': '正则量子', 'investors': ['海愿资本'],
    #     'round': 'Pre-A', 'amount': 30000000, 'amount_text': '数千万元'}
    # or None if not funding news
"""

import re
from funding_dict import (
    QUANTUM_COMPANIES, INTERNATIONAL_QUANTUM_COMPANIES, INVESTORS,
    ROUND_PATTERNS, AMOUNT_PATTERNS_NUMERIC, AMOUNT_PATTERNS_VAGUE, USD_RATE,
    normalize_entity,
)

# ── Funding Detection ─────────────────────────────────────────────────

FUNDING_SIGNALS = [
    '融资', '投资', '风投', 'IPO', '上市', '过会', '注册通过',
    '估值', '收购', '并购', '注资', '增资', '天使轮', 'A轮',
    'B轮', 'C轮', 'D轮', 'Pre-A', 'Pre-IPO', '战略融资',
    '种子轮', '基金设立', '产业基金', '创投基金',
    'funding', 'raises', 'raised', 'series', 'IPO',
    'acquires', 'acquisition', 'merger',
]


def is_funding_news(title, content=''):
    """Quick check if article is funding-related."""
    text = (title + ' ' + (content or '')[:500]).lower()
    return any(s.lower() in text for s in FUNDING_SIGNALS)


# ── Company Extraction ────────────────────────────────────────────────

def extract_company(title, content=''):
    """Extract funded company from title (title-only for precision)."""
    text = title  # Company name is reliably in the title; content adds noise

    # 1. Match against all company dictionaries (longest alias first)
    all_companies = {**QUANTUM_COMPANIES, **INTERNATIONAL_QUANTUM_COMPANIES}
    matches = []
    for canonical, aliases in all_companies.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if alias.lower() in text.lower():
                matches.append((len(alias), canonical, alias))
                break
    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

    # 2. Regex: company before funding verb
    m = re.search(
        r'(.{2,20}?)(?:完成|获|获得|宣布|签署|达成|拟|正式)'
        r'.{0,10}(?:轮融资|元融资|融资|IPO|过会|上市)',
        text
    )
    if m:
        name = m.group(1).strip()
        name = re.sub(r'[（(].+[）)]$', '', name)
        return name

    # 3. "XX公司" / "XX科技" - only for acquisitions where pattern differs
    if '收购' in text:
        m = re.search(r'([^\s，。,\.]{2,10}(?:公司|科技|技术)).*?收购', text)
        if m:
            return m.group(1).strip()

    return None


# ── Investor Extraction ───────────────────────────────────────────────

def extract_investors(title, content=''):
    """Extract investor names from text."""
    text = (title + ' ' + (content or '')[:800])
    investors = set()

    # Match against INVESTORS dictionary
    for canonical, aliases in INVESTORS.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if len(alias) >= 3 and alias.lower() in text.lower():
                investors.add(canonical)
                break

    # Also check if any quantum company acted as strategic investor
    all_companies = {**QUANTUM_COMPANIES, **INTERNATIONAL_QUANTUM_COMPANIES}
    for canonical in all_companies:
        if canonical in text:
            # Only add if it appears in an investor context (after 领投/跟投/参投 etc.)
            ctx_patterns = [
                rf'{canonical}.*?(?:领投|跟投|参投|投资|加码|追投)',
                rf'(?:领投|跟投|参投).*?{canonical}',
            ]
            for pat in ctx_patterns:
                if re.search(pat, text):
                    investors.add(canonical)
                    break

    return sorted(investors) if investors else []


def _dedup_investors(investors, company):
    """Remove self-referencing (company that raised funds isn't an investor)."""
    if company:
        return [i for i in investors if i != company]
    return investors


# ── Round Extraction ──────────────────────────────────────────────────

def extract_round(title, content=''):
    """Extract investment round from title."""
    text = title + ' ' + (content or '')[:200]
    for pat, label in ROUND_PATTERNS:
        if re.search(pat, text, re.I):
            return label
    return None


# ── Amount Extraction ─────────────────────────────────────────────────

def extract_amount(title, content=''):
    """Extract funding amount in CNY (int) or None."""
    text = (title + ' ' + (content or '')[:500]).replace(',', '').replace(' ', '')

    # 1. Try numeric patterns
    for pat, scale in AMOUNT_PATTERNS_NUMERIC:
        m = re.search(pat, text)
        if m:
            val = float(m.group(1)) * scale
            ctx = text[max(0, m.start()-10):m.end()+5]
            # Convert foreign currency to CNY
            if '美元' in ctx:
                val *= USD_RATE
            elif '欧元' in ctx:
                val *= 7.8  # EUR to CNY
            elif '英镑' in ctx:
                val *= 9.1  # GBP to CNY
            elif '加元' in ctx:
                val *= 5.3  # CAD to CNY
            return int(val)

    # 2. Try vague patterns
    for pat, estimate in AMOUNT_PATTERNS_VAGUE:
        if re.search(pat, text):
            return int(estimate)

    return None


def format_amount(amount):
    """Format amount integer to readable Chinese text."""
    if amount is None:
        return None
    if amount >= 1e8:
        v = amount / 1e8
        if v >= 10:
            return f'{int(v)}亿元'
        else:
            # e.g. 1.5亿
            s = f'{v:.1f}'
            if s.endswith('.0'):
                return f'{int(v)}亿元'
            return f'{v:.1f}亿元'
    elif amount >= 1e4:
        v = amount / 1e4
        if v >= 10000:
            return f'{v/10000:.1f}亿元'.replace('.0亿', '亿')
        elif v >= 1000:
            s = f'{v/1000:.1f}千万元'
            return s.replace('.0千', '千')
        return f'{int(v)}万元'
    else:
        return f'{amount}元'


# ── Main Tagger ───────────────────────────────────────────────────────

def tag_funding(title, content=''):
    """
    Main entry point: tag a single article for funding data.

    Returns:
        dict with keys: is_funding, company, investors, round, amount, amount_text
        None if article is not funding-related.
    """
    if not is_funding_news(title, content):
        return None

    company = extract_company(title, content)
    investors = extract_investors(title, content)
    round_ = extract_round(title, content)
    amount = extract_amount(title, content)

    # Remove self-referencing (funded company ≠ investor)
    investors = _dedup_investors(investors, company)

    # Require at least company OR investors to consider it valid
    if not company and not investors:
        return None

    return {
        'is_funding': True,
        'company': company,
        'investors': investors,
        'round': round_,
        'amount': amount,
        'amount_text': format_amount(amount),
    }


def merge_funding_tags(existing_tags, funding_data):
    """
    Merge funding data into existing tags dict.
    Preserves ALL existing namespaces (weekly, search_tags, knowledge_graph).
    Only adds/updates the 'funding' key.

    Args:
        existing_tags: current tags dict or None
        funding_data: output from tag_funding() or None

    Returns:
        merged tags dict
    """
    if existing_tags is None:
        tags = {}
    elif isinstance(existing_tags, dict):
        tags = dict(existing_tags)  # shallow copy
    else:
        tags = {}

    if funding_data:
        tags['funding'] = funding_data
    elif 'funding' in tags:
        # Keep existing funding tag if no new data
        pass

    return tags
