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

# ══════════════════════════════════════════
# 搜索策略: 1/2/3 类 × A/B 类关键词
# ══════════════════════════════════════════

# 1. 量子行业公众号
GROUP1_ACCOUNTS = [
    '量子大观', '量子客', '光子盒', '量子之声', '量子前哨', '量子风云',
]

# 2. 量子行业公司
GROUP2_COMPANIES = [
    '本源量子', '国盾量子', '国仪量子', '玻色量子', '图灵量子',
    '量旋科技', '中科酷原', '启科量子', '华翊量子', '弧光量子',
    '不筹量子', '太一量生', '微观纪元', '矩量光启', '原子矩阵',
    '问天量子', '正则量子', '量坤科技', '相干科技', '幺正量子',
    '逻辑比特', '无问清芯', '未磁科技',
]

# 3. 投融资相关公众号
GROUP3_ACCOUNTS = [
    '央企投资协会',
]

# A. 投融资关键词
KEYWORDS_A = ['融资', 'A轮', 'IPO', '估值', '收购', '战略投资']

# B. 量子行业关键词
KEYWORDS_B = ['量子计算', '量子通信', '量子传感', '量子科技', '量子芯片', '量子比特', '量子纠错']

# Only keep today's articles
MAX_AGE_DAYS = 7  # temporary: weekly catch-up run

# 海外公司/机构 — 国内投融资不收录
OVERSEAS_TERMS = [
    'OQC', 'Quantinuum', 'IBM', 'Microsoft', '微软', 'PsiQuantum', 'D-Wave',
    'IonQ', 'Rigetti', 'Xanadu', 'QuEra', 'Alice & Bob', 'IQM',
    'Infleqtion', 'Pasqal', 'Quobly', 'SEALSQ', 'Quantum Motion',
    'Quantum Source', 'Riverlane', 'Oxford Ionics', 'Atom Computing',
    'Bluefors', 'Q-CTRL', 'Qnami', 'Universal Quantum',
    'MIT', '哈佛', 'Stanford', '牛津', '剑桥', '苏黎世', '代尔夫特',
    '欧盟', '欧洲', '英国', '美国', '日本', '韩国', '德国', '法国', '加拿大', '澳大利亚',
    '英镑', '美元', '欧元', '加元',
]

# Macro keywords to skip
MACRO_KEYWORDS = [
    '赛道', '趋势', '盘点', '汇总', 'Q1', '展望', '报告', '回顾',
    '一览', '全景', '格局', '图景', '已有', '又有', '多家', '8家', '10家',
    '融资日报', '投融资日报',
    '周报', '周刊', '月报',
]


def search_sogou(query, max_pages=5):
    """返回 [{title, summary, source, date, redirect_url}, ...]

    翻多页，因为搜狗故意打乱时间顺序，近期文章可能在第2-3页。
    遇到连续重复页则提前停止。
    """
    all_articles = []
    seen_titles = set()
    prev_page_hashes = []

    for page in range(1, max_pages + 1):
        url = f'https://weixin.sogou.com/weixin?type=2&s_from=input&query={urllib.parse.quote(query)}&ie=utf8&page={page}'
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = 'utf-8'
        except Exception as e:
            print(f'  [ERR page {page}] {e}')
            break

        if '验证码' in resp.text or '请输入验证码' in resp.text:
            print(f'  [BLOCKED page {page}] captcha')
            break

        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.find_all('li', id=re.compile(r'sogou_vr_.*_box'))

        if not items:
            break

        # Detect repeat: if this page has the same titles as a previous page, stop
        page_titles = tuple(
            (it.find('a', id=re.compile(r'title')) or it.find('a')).get_text(strip=True)
            for it in items if it.find('a')
        )
        if page_titles in prev_page_hashes:
            break
        prev_page_hashes.append(page_titles)

        for item in items:
            title_a = item.find('a', id=re.compile(r'title'))
            title = title_a.get_text(strip=True) if title_a else ''
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

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

            # Date from Unix timestamp
            pub_date = ''
            ts_match = re.search(r"timeConvert\('(\d+)'\)", str(item))
            if ts_match:
                try:
                    pub_date = datetime.fromtimestamp(int(ts_match.group(1))).strftime('%Y-%m-%d')
                except Exception:
                    pass

            all_articles.append({
                'title': title,
                'summary': summary,
                'source': source,
                'date': pub_date,
                'redirect': redirect,
            })

        # Delay between pages
        if page < max_pages:
            time.sleep(random.uniform(1, 2))

    return all_articles


def is_domestic(title, summary=''):
    """True if article is about Chinese domestic quantum investment."""
    text = (title or '') + ' ' + (summary or '')
    for term in OVERSEAS_TERMS:
        if term.lower() in text.lower():
            return False
    return True


def is_quantum(title, summary=''):
    """True if article is about quantum technology (not just any tech investment)."""
    text = (title or '') + ' ' + (summary or '')[:300]
    return any(kw in text for kw in [
        '量子', '超导量子', '光量子', '离子阱', '中性原子', '硅自旋', '拓扑量子',
        '量子计算', '量子芯片', '量子比特', '量子纠错', '量子密钥', 'QKD',
        '量子通信', '量子传感', '量子精密测量', '量子磁力', '量子雷达',
    ])


def is_specific_event(title, summary=''):
    """True if article is about a specific investment event, not macro analysis."""
    title = title or ''
    summary = summary or ''
    text = title + ' ' + summary

    # Must be quantum-related (non-negotiable)
    if not is_quantum(title, summary):
        return False

    # Must have a specific company name AND specific funding activity
    has_company = bool(extract_company(title, summary))
    if not has_company:
        has_company = bool(re.search(
            r'(「.{2,8}?」|[【].{2,8}?[】]|有限公司|科技公司|初创公司|量子公司)',
            title
        ))

    has_specific = bool(re.search(
        r'(完成|获|获得|宣布|签署|又|再|刚|正式|新一轮|独家).{0,10}'
        r'(融资|投资|A轮|B轮|C轮|天使|种子|Pre-IPO|IPO|上市|Pre-A|Pre-B)',
        text
    ))

    is_macro = any(kw in title for kw in MACRO_KEYWORDS)

    return has_company and has_specific and not is_macro


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


def extract_company(title, summary=''):
    """Extract company name from title+summary for dedup."""
    text = (title or '') + ' ' + (summary or '')
    for c in GROUP2_COMPANIES:
        if c in text:
            return c
    # Fallback: extract quoted names like 「华翊量子」
    m = re.search(r'[「【](.{2,8}?(?:量子|科技|光电|计算|磁科技))[」】]', text)
    if m:
        return m.group(1)
    return None


def title_key(title, date='', summary=''):
    """Dedup key: company + funding round. Same company + same round = same event.

    Uses round (A轮/B轮/天使/...) instead of time, so re-shares of old news
    are correctly deduped even if published months apart.
    """
    company = extract_company(title, summary)
    round_ = extract_round(title + ' ' + (summary or ''))
    if company:
        if round_:
            return f'{company}:{round_}'
        # Fallback: company + first 6 chars of cleaned title
        clean = re.sub(r'[【】「」《》\s\-\|,，。！？、]', '', title)
        return f'{company}:{clean[:6]}'
    # Last resort
    clean = re.sub(r'[【】「」《》\s\-\|,，。！？、]', '', title)
    return clean[:12]


def main():
    session = get_session()
    scorer = get_scorer()

    # Load known URLs and dedup keys from DB
    from core.db import Article
    known_urls = set()
    seen_titles = set()
    for r in session.query(Article).filter(Article.page_type == 'wechat').all():
        known_urls.add(r.reference_url or '')
        known_urls.add(r.liangke_url or '')
        # Also load dedup keys to prevent re-inserting same event
        key = title_key(r.title or '', str(r.liangke_date) if r.liangke_date else '', r.content or '')
        if key:
            seen_titles.add(key)

    today = datetime.now().date()
    cutoff = today - timedelta(days=MAX_AGE_DAYS)

    print(f'=== 搜狗微信搜索: 国内量子投融资 {today} ===')
    print(f'日期范围: {cutoff} ~ {today}\n')

    # Search
    # 构建查询: 1+A 量子公众号 × 投融资关键词
    queries = []
    for acc in GROUP1_ACCOUNTS:
        for kw in KEYWORDS_A:
            queries.append(f'\"{acc}\" \"{kw}\" \"2026年\"')
    all_articles = []
    blocked_count = 0
    qi = 0

    while qi < len(queries):
        q = queries[qi]
        articles = search_sogou(q, max_pages=3)

        # Captcha cooling: pause 60s then retry same query
        if not articles:
            blocked_count += 1
            if blocked_count >= 3:
                cooldown = random.uniform(45, 75)
                print(f'  [{qi+1}/{len(queries)}] {blocked_count} captchas — cooling {cooldown:.0f}s...')
                time.sleep(cooldown)
                blocked_count = 0
            else:
                time.sleep(random.uniform(10, 20))
            continue  # retry same query

        blocked_count = 0  # reset on success
        qi += 1

        for art in articles:
            # Skip overseas
            if not is_domestic(art['title'], art['summary']):
                continue
            # Skip old
            if art['date'] and art['date'] < str(cutoff):
                continue
            # Skip non-investment events (量子相关性现在是硬性要求)
            if not is_specific_event(art['title'], art['summary']):
                continue
            # Dedup
            key = title_key(art['title'], art['date'], art['summary'])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            all_articles.append(art)

        # Delay between queries
        delay = random.uniform(8, 15) if blocked_count == 0 else random.uniform(15, 30)
        time.sleep(delay)

        if qi > 0 and qi % 6 == 0:
            print(f'  [{qi}/{len(queries)}] {len(all_articles)} found')

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
