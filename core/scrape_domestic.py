"""Domestic quantum investment news scraper.

Discovery: DuckDuckGo search → detail page scraping → daily DB.
Runs as part of the daily scrape pipeline (after scrape_daily.py).
"""
import sys, os, re, time, random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from ddgs import DDGS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_session, insert_or_update_article
from core.category_scorer import get_scorer

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Chinese quantum company names for targeted search
DOMESTIC_COMPANIES = [
    '本源量子', '国盾量子', '国仪量子', '玻色量子', '图灵量子',
    '量旋科技', '中科酷原', '启科量子', '华翊量子', '弧光量子',
    '不筹量子', '太一量生', '微观纪元', '矩量光启', '原子矩阵',
    '问天量子', '正则量子', '合肥幺正', '苏州华杨',
]

# Search for each company + financing keyword
SEARCH_QUERIES = [
    f'{company} 融资' for company in DOMESTIC_COMPANIES[:5]  # rotate daily
] + [
    f'{company} 投资 轮' for company in DOMESTIC_COMPANIES[5:10]
] + [
    '量子 国内 融资 亿元',
    '量子计算 人民币 融资',
]

# Chinese location/company indicators for strict domestic filtering
DOMESTIC_MARKERS = [
    '中国', '上海', '北京', '深圳', '苏州', '合肥', '武汉', '南京', '杭州',
    '成都', '济南', '西安', '广州', '无锡', '常州', '宁波',
    '本源', '国盾', '国仪', '玻色', '图灵', '量旋', '中科酷原', '启科',
    '华翊', '弧光', '不筹', '太一', '微观纪元', '矩量', '原子矩阵',
    '问天', '正则', '幺正', '华杨', '阿里巴巴', '腾讯', '百度', '华为',
    '中移动', '中国移动', '中电信', '中国电信', '人民币', '亿元', '万元',
    '中科院', '中国科学技术大学', '清华', '北大', '浙大', '上海交大',
    '合肥国家实验室', '北京量子院', '之江实验室',
]

# Source domains and their article selectors
DOMAIN_HANDLERS = {
    '36kr.com': {
        'title': 'h1',
        'date': 'meta[property="article:published_time"]',
        'content': 'div.article-main, div.common-width',
        'encoding': 'utf-8',
    },
    'pedaily.cn': {
        'title': 'h1',
        'date': 'span.date, span.time',
        'content': 'div.news-content, div.article-content',
        'encoding': None,  # auto-detect
    },
    'jiqizhixin.com': {
        'title': 'h1',
        'date': 'meta[property="article:published_time"]',
        'content': 'div.article-content',
        'encoding': 'utf-8',
    },
    'leiphone.com': {
        'title': 'h1',
        'date': 'meta[property="article:published_time"]',
        'content': 'div.article-content',
        'encoding': 'utf-8',
    },
    'huxiu.com': {
        'title': 'h1',
        'date': 'meta[property="article:published_time"]',
        'content': 'div.article-content, div.article__content',
        'encoding': 'utf-8',
    },
    'qq.com': {
        'title': 'h1',
        'date': 'meta[property="article:published_time"]',
        'content': 'div.article-content, div.content-article',
        'encoding': 'utf-8',
    },
}


def is_domestic_quantum_finance(title: str) -> bool:
    """Strict filter: only Chinese domestic quantum investment news.

    Requires ALL THREE: quantum keyword + finance keyword + domestic marker.
    """
    title = title or ''
    has_quantum = any(kw in title for kw in [
        '量子', '超导量子', '光量子', '离子阱', '中性原子',
        '量子计算', '量子芯片', '量子比特', '量子纠错',
    ])
    has_finance = any(kw in title for kw in [
        '融资', '投资', '估值', '收购', '并购', 'IPO', '上市',
        'A轮', 'B轮', 'C轮', '天使', '种子', '战略',
        '亿', '轮', '美元', '人民币',
    ])
    has_domestic = any(kw in title for kw in DOMESTIC_MARKERS)
    return has_quantum and has_finance and has_domestic


def discover_articles(days_back=3):
    """Search DuckDuckGo for recent domestic quantum investment articles."""
    discovered = []  # list of {url, title, snippet, date}
    seen_urls = set()

    for query in SEARCH_QUERIES:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=15, region='cn-zh'))
            for r in results:
                url = r.get('href', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = r.get('title', '')
                if not is_domestic_quantum_finance(title):
                    continue

                # Only include known-domains (we know how to scrape these)
                domain = ''
                for d in DOMAIN_HANDLERS:
                    if d in url:
                        domain = d
                        break
                if not domain:
                    continue

                discovered.append({
                    'url': url,
                    'title': title,
                    'snippet': r.get('body', ''),
                    'date': r.get('date', ''),
                    'domain': domain,
                })
        except Exception as e:
            print(f'  Search error for "{query}": {e}')
            continue

    print(f'  Discovered {len(discovered)} articles from DuckDuckGo')
    return discovered


def scrape_detail(url, domain):
    """Scrape a single article detail page."""
    handler = DOMAIN_HANDLERS.get(domain, {})
    encoding = handler.get('encoding')

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if encoding:
            resp.encoding = encoding
        else:
            resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        return {'title': '', 'date': '', 'content': '', 'error': str(e)}

    # Title
    title = ''
    title_sel = handler.get('title', 'h1')
    try:
        el = soup.select_one(title_sel)
        if el:
            title = el.get_text(strip=True)
    except Exception:
        pass

    # Date
    date_str = ''
    date_sel = handler.get('date', '')
    if date_sel:
        try:
            el = soup.select_one(date_sel)
            if el:
                if el.name == 'meta':
                    date_str = el.get('content', '')[:19]
                else:
                    date_str = el.get_text(strip=True)
        except Exception:
            pass
    if not date_str:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', soup.get_text()[:2000])
        if m:
            date_str = m.group(1)

    # Content
    content = ''
    content_sel = handler.get('content', '')
    if content_sel:
        try:
            div = soup.select_one(content_sel)
            if div:
                for noise in div.find_all(['script', 'style']):
                    noise.decompose()
                content = div.get_text(separator='\n', strip=True)
        except Exception:
            pass

    if not content:
        body = soup.find('body')
        if body:
            for noise in body.find_all(['nav', 'header', 'footer', 'script', 'style']):
                noise.decompose()
            content = body.get_text(separator='\n', strip=True)
            # Trim at common footers
            for kw in ['转载声明', '本文来源', '声明：', 'Copyright', '投资界']:
                pos = content.find(kw, len(content) * 2 // 3)
                if pos != -1:
                    content = content[:pos].strip()
                    break

    return {
        'title': title,
        'date': date_str[:10] if date_str else '',
        'content': content,
        'url': url,
    }


def main():
    session = get_session()
    scorer = get_scorer()

    # Load known URLs
    from core.db import Article
    known = set()
    for r in session.query(Article.reference_url).filter(Article.reference_url != '').all():
        known.add(r[0])

    today = datetime.now().date()
    recent = today - timedelta(days=3)

    print(f'=== Domestic quantum investment scrape: {today} ===')

    # Step 1: Discover
    articles = discover_articles(days_back=3)

    stats = {'new': 0, 'skipped': 0, 'errors': 0}

    # Step 2: Scrape & Insert
    for i, art in enumerate(articles):
        print(f"\n[{i+1}/{len(articles)}] {art['title'][:80].encode('gbk', errors='replace').decode('gbk', errors='replace')}")

        if art['url'] in known:
            print(f'  -> SKIPPED (already in DB)')
            stats['skipped'] += 1
            continue

        detail = scrape_detail(art['url'], art['domain'])
        if detail.get('error'):
            print(f'  -> ERROR: {detail["error"]}')
            stats['errors'] += 1
            continue

        if not detail['title'] or len(detail['title']) < 5:
            print(f'  -> ERROR: empty title')
            stats['errors'] += 1
            continue

        title_short = detail['title'][:100].encode('gbk', errors='replace').decode('gbk', errors='replace')
        print(f'  Title: {title_short}')
        print(f'  Date: {detail["date"] or "N/A"} | Content: {len(detail["content"])} chars')

        # Parse date
        liangke_date = today
        if detail['date']:
            try:
                liangke_date = datetime.strptime(detail['date'], '%Y-%m-%d').date()
            except ValueError:
                try:
                    liangke_date = datetime.strptime(detail['date'][:10], '%Y-%m-%d').date()
                except ValueError:
                    pass

        # Classify with dictionary scorer
        cat = scorer.classify(detail['title'], detail['content'], art['url'])
        if cat is None:
            cat = '资本运作'  # default for domestic invest scraper

        try:
            result = insert_or_update_article(
                reference_url=art['url'],
                liangke_url=art['url'],
                title=detail['title'],
                content=detail['content'],
                original_date=liangke_date,
                liangke_date=liangke_date,
                source_domain=art['domain'],
                reference_title=detail['title'],
                tags={'weekly': [cat], 'search_tags': ['国内投融资']},
                page_type='reference'
            )
            stats['new'] += 1
            rid = result.get('id', '?')
            print(f'  -> INSERTED (id={rid}, cat={cat})')
            known.add(art['url'])
        except Exception as e:
            print(f'  -> DB ERROR: {e}')
            stats['errors'] += 1

        time.sleep(random.uniform(2, 4))  # polite delay

    session.close()
    print(f"\nDone. New: {stats['new']}  Skipped: {stats['skipped']}  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
