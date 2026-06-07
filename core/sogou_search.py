"""搜狗微信搜索 - 国内量子投融资自动化抓取。

每天运行一次，搜索已知量子公司+新公司发现，抓取标题/日期/摘要入库。
用法: python sogou_search.py
"""
import sys, os, re, time, random, json, urllib.parse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_session, insert_or_update_article
from core.category_scorer import get_scorer

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://weixin.sogou.com/',
}

# 重点关注的量子行业微信公众号
PRIORITY_ACCOUNTS = ['量子大观', '量子客', '光子盒', '量子之声', '量子前哨']

KNOWN_COMPANIES = [
    '本源量子', '国盾量子', '国仪量子', '玻色量子', '图灵量子',
    '量旋科技', '中科酷原', '启科量子', '华翊量子', '弧光量子',
    '不筹量子', '太一量生', '微观纪元', '矩量光启', '原子矩阵',
    '问天量子', '正则量子', '量坤科技', '相干科技', '幺正量子',
    '逻辑比特',
]

DISCOVERY_QUERIES = [
    '量子计算 天使轮 亿元',
    '量子计算 A轮 亿元',
    '量子计算 Pre-A 融资',
    '量子计算 完成 数千万 融资',
]

# Only keep articles from last N days
MAX_AGE_DAYS = 7

# Macro keywords to skip
MACRO_KEYWORDS = [
    '赛道', '趋势', '盘点', '汇总', 'Q1', '展望', '报告', '回顾',
    '一览', '全景', '格局', '图景', '已有', '又有', '多家', '8家', '10家',
    '融资日报', '投融资日报',
]


def search_sogou(query, max_results=10):
    """返回 [{title, summary, source, date, redirect_url}, ...]"""
    url = f'https://weixin.sogou.com/weixin?type=2&s_from=input&query={urllib.parse.quote(query)}&ie=utf8'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
    except Exception as e:
        print(f'  [ERR] {e}')
        return []

    if '验证码' in resp.text or '请输入验证码' in resp.text:
        print(f'  [BLOCKED] captcha')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []

    for item in soup.find_all('li', id=re.compile(r'sogou_vr_.*_box')):
        title_a = item.find('a', id=re.compile(r'title'))
        title = title_a.get_text(strip=True) if title_a else ''
        if not title:
            continue

        # Redirect link
        redirect = ''
        for a in item.find_all('a', href=True):
            href = a.get('href', '')
            if href.startswith('/link?url='):
                redirect = 'https://weixin.sogou.com' + href
                break

        # Summary
        summary_p = item.find('p', class_='txt-info')
        summary = summary_p.get_text(strip=True) if summary_p else ''

        # Source
        source_span = item.find('span', class_='all-time-y2')
        source = source_span.get_text(strip=True) if source_span else ''

        # Date from Unix timestamp in <script>timeConvert('...')</script>
        pub_date = ''
        ts_match = re.search(r"timeConvert\('(\d+)'\)", str(item))
        if ts_match:
            try:
                pub_date = datetime.fromtimestamp(int(ts_match.group(1))).strftime('%Y-%m-%d')
            except Exception:
                pass

        articles.append({
            'title': title,
            'summary': summary,
            'source': source,
            'date': pub_date,
            'redirect': redirect,
        })

    return articles[:max_results]


def is_specific_event(title, summary=''):
    """True if article is about a specific investment event, not macro analysis."""
    text = title + ' ' + summary
    # Must mention specific company funding activity
    has_specific = bool(re.search(
        r'(完成|获|获得|宣布|签署|完成|又|再|刚|正式|新一轮|独家).{0,10}'
        r'(融资|投资|A轮|B轮|C轮|天使|种子|Pre-IPO|IPO|上市|Pre-A|Pre-B)',
        text
    ))
    is_macro = any(kw in title for kw in MACRO_KEYWORDS)
    return has_specific and not is_macro


def extract_amount(text):
    """Try to extract funding amount from title/summary."""
    m = re.search(r'(\d+\.?\d*)\s*(亿|万|千)\s*(元|美元|美金|欧元|英镑|人民币)?', text)
    if m:
        num = float(m.group(1))
        unit = m.group(2)
        currency = m.group(3) or '人民币'
        return f'{num}{unit}{currency}'
    return ''


def extract_round(text):
    """Try to extract funding round."""
    for pat in ['Pre-IPO', 'IPO', 'C轮', 'C+轮', 'B轮', 'B+轮', 'A轮', 'A+轮',
                'Pre-A', 'Pre-B', '天使轮', '天使+轮', '种子轮', '战略融资', '战略投资']:
        if pat in text:
            return pat
    return ''


def title_key(title):
    """Generate a dedup key: first 8 meaningful characters."""
    # Remove punctuation, spaces, and common prefixes/suffixes
    clean = re.sub(r'[【】「」《》\s\-\|,，。！？、]', '', title)
    return clean[:8]


def main():
    session = get_session()
    scorer = get_scorer()

    # Load known URLs to skip already-inserted
    from core.db import Article
    known_urls = set()
    for r in session.query(Article.reference_url).filter(Article.reference_url.like('%mp.weixin.qq.com%')).all():
        known_urls.add(r[0])

    today = datetime.now().date()
    cutoff = today - timedelta(days=MAX_AGE_DAYS)

    print(f'=== 搜狗微信搜索: 国内量子投融资 {today} ===')
    print(f'日期范围: {cutoff} ~ {today}\n')

    # Search
    queries = (
        [f'{c} 融资' for c in KNOWN_COMPANIES[:8]] +
        ['量子 融资', '量子 投资', '量子 天使轮'] +  # 覆盖优先公众号
        DISCOVERY_QUERIES[:2]
    )
    all_articles = []
    seen_titles = set()

    for q in queries:
        articles = search_sogou(q, max_results=10)
        for art in articles:
            is_priority = art['source'] in PRIORITY_ACCOUNTS
            # Skip macro (unless from priority account)
            if not is_specific_event(art['title'], art['summary']) and not is_priority:
                continue
            # Skip old
            if art['date'] and art['date'] < str(cutoff):
                continue
            # Dedup by title similarity
            key = title_key(art['title'])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            all_articles.append(art)

        time.sleep(random.uniform(1.5, 3))

    # Sort by date
    all_articles.sort(key=lambda a: a['date'] or '0000', reverse=True)

    print(f'找到 {len(all_articles)} 篇近{MAX_AGE_DAYS}天投融资事件\n')

    stats = {'new': 0, 'skipped': 0}

    for i, art in enumerate(all_articles):
        amount = extract_amount(art['title'] + ' ' + art['summary'])
        round_ = extract_round(art['title'] + ' ' + art['summary'])
        info = f'{round_} {amount}'.strip()

        # Show
        idx = f'[{i+1}/{len(all_articles)}]'
        print(f'{idx} {art["date"]} | {art["source"][:10]:10s} | {info:20s} | {art["title"][:70]}')

        # Build liangke_url using the redirect URL
        liangke_url = art['redirect'] or f'https://weixin.sogou.com/weixin?query={urllib.parse.quote(art["title"][:50])}'

        if liangke_url in known_urls:
            print(f'      -> SKIP (already in DB)')
            stats['skipped'] += 1
            continue

        # Build content from summary
        content = f'{art["summary"]}\n\n来源: {art["source"]}'

        # Classify
        cat = scorer.classify(art['title'], content)
        if cat is None:
            cat = '资本运作'

        try:
            liangke_date = datetime.strptime(art['date'], '%Y-%m-%d').date() if art['date'] else today

            insert_or_update_article(
                reference_url=liangke_url,
                liangke_url=liangke_url,
                title=art['title'],
                content=content,
                original_date=liangke_date,
                liangke_date=liangke_date,
                source_domain=art['source'],
                reference_title=art['title'],
                tags={'weekly': [cat], 'search_tags': ['国内投融资', '搜狗微信']},
                page_type='wechat'
            )
            stats['new'] += 1
            known_urls.add(liangke_url)
            print(f'      -> INSERTED ({cat})')
        except Exception as e:
            print(f'      -> DB ERROR: {e}')

        time.sleep(random.uniform(0.5, 1.5))

    session.close()
    print(f'\nDone. New: {stats["new"]}  Skipped: {stats["skipped"]}')


if __name__ == '__main__':
    main()
