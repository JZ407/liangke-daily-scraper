"""
量科网每日新闻抓取脚本 (MySQL + 去重 + 原始日期提取)
"""
import sys
import requests
from bs4 import BeautifulSoup
import pickle
import time
import random
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from extract_original_date import get_original_date
from db import insert_or_update_article, article_exists, get_article_count

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
]
HEADERS = {'User-Agent': _USER_AGENTS[0]}

def _rotate_ua():
    """Rotate User-Agent header for anti-scraping."""
    HEADERS['User-Agent'] = random.choice(_USER_AGENTS)

COOKIE_PATH = os.path.join(BASE_DIR, '..', 'data', 'cookies', 'qtc_cookies.pkl')
BASE_URL = 'http://www.qtc.com.cn'

# 原有技术标签关键词库
KEYWORDS = {
    '量子计算': ['量子计算', '量子比特', 'qubit', '量子门', '量子电路', '量子算法', '量子优势', '量子霸权', '量子纠错', '逻辑量子比特', '物理量子比特', '量子体积', '量子模拟', '量子机器学习', '变分量子算法', 'vqa', 'vqe', '量子退火', '量子编译', 'nisq', 'ftqc', '容错量子计算', '量子噪声', '量子相干'],
    '量子通信': ['量子通信', '量子密钥分发', 'qkd', '量子隐形传态', '量子纠缠', '量子中继器', '量子网络', '量子互联网', '量子卫星', '自由空间量子通信', '光纤量子通信', '设备无关', 'di-qkd', 'mdi-qkd', '连续变量', 'cv-qkd'],
    '后量子密码': ['后量子密码', 'pqc', '抗量子密码', '格密码', '哈希密码', '编码密码', '多元密码', '同态加密', '零知识证明', '数字签名', '密钥封装', 'kem', 'nist后量子', '密码敏捷性', 'tls', 'ssl', 'pki', '后量子迁移', 'post-quantum'],
    '量子传感': ['量子传感', '量子计量', '量子精密测量', '原子钟', '量子陀螺仪', '量子磁力计', '量子雷达', '重力仪', '干涉仪', '压缩态'],
    '硬件平台': ['超导量子比特', 'transmon', '离子阱', 'ion trap', '光量子', '光子量子', '硅自旋', '中性原子', '拓扑量子比特', '马约拉纳', 'nv色心', 'nv中心', '里德伯', '量子点', '单光子探测器', 'snspd', '超导纳米线', '约瑟夫森结', '稀释制冷机', '光子集成电路'],
    '量子物理': ['量子力学', '量子叠加', '量子态', '波函数', '量子涨落', '退相干', '量子混沌', '贝尔不等式', '量子场论', '多体物理', '凝聚态物理', '冷原子', '腔量子电动力学', '腔qed'],
    '行业应用': ['量子化学', '药物发现', '材料科学', '组合优化', '供应链优化', '金融建模', '密码分析', '量子安全', '量子成像', '量子导航', 'qcaas', '量子计算即服务', '混合量子-经典'],
    '政策标准': ['量子战略', '国家量子计划', '量子技术标准化', '出口管制', '网络安全法规', '量子人才', '产学研合作'],
    '企业与机构': ['ibm', 'google', '谷歌', '英伟达', 'nvidia', '英特尔', 'intel', '微软', 'microsoft', '亚马逊', 'amazon', 'ionq', 'rigetti', 'xanadu', 'pasqal', 'd-wave', 'quera', 'quantinuum', '国盾量子', '本源量子', 'nist', '欧盟量子旗舰', 'arxiv'],
    '融资商业': ['量子投资', '风险投资', 'ipo', '战略合作', '政府资助', '量子初创', '量子生态', '商业化', '营收增长', '市场份额', '融资', '估值', '亿美元', '万美元'],
}

SPECIFIC_TAGS = {
    'QKD': ['qkd', '量子密钥分发'],
    'PQC': ['pqc', '后量子密码'],
    '超导': ['超导', 'transmon', 'snspd', '约瑟夫森'],
    '离子阱': ['离子阱', 'ion trap'],
    '光量子': ['光量子', '光子量子', '单光子'],
    'NIST': ['nist'],
    'arXiv': ['arxiv'],
    '融资': ['融资', '估值', '万美元', '亿美元'],
    '量子计算': ['量子计算', '量子比特', 'qubit'],
    '量子通信': ['量子通信', '量子网络', '量子互联网'],
    '量子纠错': ['量子纠错', '逻辑量子比特'],
    '后量子迁移': ['后量子迁移', '密码迁移'],
    '半导体': ['半导体', '硅自旋', '量子点'],
    'AI/ML': ['机器学习', '人工智能', 'ai', 'ml-'],
}

# 五大分类标签关键词库（每篇文章必须有且仅有一个）
# 优先级：资本运作 > 产品动态 > 企业资讯 > 科技前沿 > 宏观态势
CATEGORY_KEYWORDS = {
    '资本运作': [
        '融资', '投资', '风投', 'vc ', 'pe ', 'ipo', '上市', '招股',
        '估值', '亿美元', '万美元', '人民币', '千万', '百万', '亿元',
        '收购', '并购', '合并', '分拆', '剥离', '整合',
        '资助', '拨款', '补贴', '基金', '预算', '经费',
        '营收', '收入', '利润', '亏损', '财报', '业绩', '增长',
        '股权', '股东', '控股', '参股', '注资', '增资', '扩股',
        'a轮', 'b轮', 'c轮', 'd轮', '种子轮', '天使轮', '战略融资',
        'raise', 'raised', 'raises', 'raising', 'funding', 'fund', 'funds',
        'series', 'equity', 'offering', 'pricing of', 'closes',
        'completes acquisition', 'completes sale', 'acquires',
        'stock', 'shares', 'shareholder', 'market cap', 'market capital',
        'capital', 'backed by', 'led by', 'investor', 'venture',
        'grant', 'awarded', 'contract award', 'million dollar',
        'billion dollar', 'm deal', 'mn deal', 'loan', 'bond',
        'debt', 'credit', 'capital raise', 'capital raising',
    ],
    '产品动态': [
        '产品', '发布', '推出', '上市', '芯片', '处理器', '计算机',
        '量子计算机', '量子芯片', '量子处理器', '原型机', '样机',
        '系统', '平台', '软件', '工具', 'sdk', 'api', '云服务',
        '升级', '迭代', '性能', '指标', '保真度', '相干时间',
        '低温', '制冷机', '测控', '封装', '互联', '模块化',
        '量产', '商用', '部署', '交付', '生产线', '制造',
    ],
    '企业资讯': [
        'ibm', 'google', '谷歌', '微软', 'microsoft', '亚马逊', 'amazon',
        '英伟达', 'nvidia', '英特尔', 'intel', '苹果', 'apple',
        'ionq', 'rigetti', 'xanadu', 'pasqal', 'd-wave', 'quera', 'quantinuum',
        '国盾量子', '本源量子', '国仪量子', '国创中心', '中电科', '华为',
        '合作', '协议', '签约', '伙伴', '联盟', '成员',
        '任命', '高管', 'ceo', 'cto', '总裁', '创始人', '团队', '离职',
        '扩建', '新厂', '研发中心', '总部', '分部', '办事处',
    ],
    '科技前沿': [
        '论文', '研究', '突破', '实验', '发现', '理论', '算法', '模型',
        '量子比特', '量子门', '量子电路', '量子纠缠', '量子叠加',
        '量子纠错', '逻辑量子比特', '物理量子比特', '量子体积',
        '超导', '离子阱', '光量子', '中性原子', '硅自旋', '拓扑',
        '量子模拟', '量子机器学习', '变分量子', 'vqa', 'vqe',
        'arxiv', 'nature', 'science', '物理评论', 'prl',
        '预印本', '实验验证', '原理验证', '科学', '学术', '期刊',
    ],
    '宏观态势': [
        '政策', '战略', '规划', '法规', '标准', '出口管制', '制裁', '法案',
        '人才', '教育', '培训', '科研', '产学研',
        '市场', '产业', '生态', '趋势', '报告', '预测', '全球', '国际',
        '国家量子', '量子计划', '路线图', '白皮书', '指南', '倡议',
        '竞争', '领先', '差距', '挑战', '机遇', '风险',
    ],
}

CATEGORY_PRIORITY = ['资本运作', '产品动态', '企业资讯', '科技前沿', '宏观态势']


def _match_category(text_lower: str) -> str:
    """匹配五大分类标签（关键词兜底），返回唯一分类。"""
    scores = {}
    for tag, words in CATEGORY_KEYWORDS.items():
        score = 0
        for word in words:
            if word.lower() in text_lower:
                score += 1
        scores[tag] = score

    if max(scores.values()) == 0:
        return '宏观态势'

    best_tag = max(CATEGORY_PRIORITY, key=lambda t: (scores[t], CATEGORY_PRIORITY.index(t)))
    return best_tag


def _llm_classify_batch(articles_info):
    """Use LLM to classify a batch of articles into 5 weekly categories.

    articles_info: list of (title + content excerpt) strings.
    Each item should provide enough context: title + first 400 chars of content.
    """
    text_list = '\n'.join(
        f'{i+1}. {info[:400]}' for i, info in enumerate(articles_info)
    )
    prompt = f"""将以下量子科技新闻分类到五大类别之一。

优先级规则：资本运作 > 企业资讯 > 产品动态 > 科技前沿 > 宏观态势。

==== 分类定义（含正例和反例）====

1. 资本运作 —— 钱和所有权的流动
   【属于】融资（A轮/B轮/种子轮）、收购并购、IPO上市、财报营收估值、政府资助/拨款给具体企业
   【不属于】公司发新产品→产品动态 | 公司跟大学合作研究→企业资讯 | 政府发布行业政策→宏观态势
   示例：IQM获芬兰Ilmarinen投资 ✓ | 英国发布量子战略 ✗（→宏观态势）

2. 产品动态 —— 能买能用能部署的东西
   【属于】新芯片/计算机/软件/云服务发布、性能指标突破（量子体积/保真度/量子比特数）、商用落地/量产/客户部署
   【不属于】论文里提了新算法→科技前沿 | 公司说"计划推出"但无实物→企业资讯
   示例：微软发布Majorana 2芯片 ✓ | 论文报道高保真度实验→科技前沿

3. 企业资讯 —— 公司组织层面的变化
   【属于】合作签约/战略联盟、CEO/CTO/高管任命、办公室扩建/裁员、公司战略/愿景宣布
   【不属于】合作研究成果发表→科技前沿 | 获投资→资本运作 | 发布产品→产品动态
   示例：深圳市委调研中科酷原 ✓ | 两家公司联合发表Nature论文 ✗（→科技前沿）

4. 科技前沿 —— 知识层面的推进，不涉及商业产品
   【属于】学术论文（Nature/Science/PRL/arXiv预印本）、实验突破/新物理现象、新算法/新理论方法
   【不属于】量子计算机量产→产品动态 | 行业白皮书→宏观态势 | 某公司实验室成果宣称"可用于产品"→产品动态

5. 宏观态势 —— 影响整个行业，而非单个公司
   【属于】国家量子战略/政策法规、行业路线图、市场研究报告、国际竞争格局、人才教育、行业标准发布
   【不属于】某公司获政府资助→资本运作 | 某公司产品路线图→产品动态 | 某公司白皮书→企业资讯

==== 关键边界规则 ====
- 政府给钱：给具体公司=资本运作，发布行业政策=宏观态势
- 论文研究：学术发表=科技前沿，为产品造势=产品动态
- 合作联合：签合作协议=企业资讯，发表联合论文=科技前沿
- arXiv预印本：一律归科技前沿

每条新闻标题后附有正文前400字（| 分隔）。每篇只输出一个类别。输出格式：编号:类别

{text_list}

输出："""

    try:
        import yaml
        cfg = yaml.safe_load(open('D:/Claude_code/rag_system/config.yaml', encoding='utf-8'))
        llm_cfg = cfg['llm']
        sys.path.insert(0, 'D:/Claude_code/rag_system/rag_system')
        from llm_client import LLMClient
        client = LLMClient(provider='openai', api_key=llm_cfg['api_key'],
                          api_base=llm_cfg['api_base'], model=llm_cfg['model'],
                          max_tokens=2048, timeout=120)
        response = client.chat([{'role': 'user', 'content': prompt}])
        # Parse response: "1:资本运作\n2:企业资讯\n..."
        results = {}
        for line in response.strip().split('\n'):
            m = re.match(r'(\d+)[：:]\s*(\S+)', line.strip())
            if m:
                idx = int(m.group(1)) - 1
                cat = m.group(2).strip()
                if cat in CATEGORY_PRIORITY:
                    results[idx] = cat
        return results
    except Exception as e:
        print(f'  LLM classify failed: {e}')
        return {}


def auto_tag(title: str, content: str) -> list:
    """Project-based auto-tagging using unified tagger.
    Returns project-based tags dict as JSON string.
    """
    sys.path.insert(0, 'D:/Claude_code/knowledge_graph')
    from core.tagger import tag_article
    result = tag_article(title, content, '')
    # Also include old 5-category from local keyword matching
    text = (title or '') + ' ' + (content or '')[:2000]
    text_lower = text.lower()
    old_cat = _match_category(text_lower)
    if old_cat not in result['weekly']:
        result['weekly'].append(old_cat)
    return result


def load_cookies():
    if not os.path.exists(COOKIE_PATH):
        print(f"ERROR: Cookie file not found: {COOKIE_PATH}")
        print("Please run update_cookie.bat first after logging in to 量科网.")
        return None
    with open(COOKIE_PATH, 'rb') as f:
        return pickle.load(f)


def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')


def get_target_dates():
    """Return today + yesterday (to catch any missed in yesterday's run)."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return {today.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d')}


def fetch_homepage_list(cookies):
    """Fetch homepage and extract today's news URLs."""
    print(f"Fetching homepage: {BASE_URL}")
    resp = requests.get(BASE_URL, cookies=cookies, headers=HEADERS, timeout=30)
    resp.encoding = resp.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')

    target_dates = get_target_dates()
    print(f"Looking for news dated: {sorted(target_dates)}")

    articles = []
    seen_urls = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()

        # Skip category/index pages
        if href == '/reference/arxiv':
            continue
        if not (href.startswith('/flash/') or href.startswith('/article/') or href.startswith('/reference/')):
            continue
        # Skip non-specific pages
        if re.match(r'^/(flash|article|reference)/[^/]+$', href) is None:
            continue

        # Look for date pattern in nearby elements
        text_to_search = ''
        elem = a
        for _ in range(4):
            if elem:
                text_to_search += ' ' + elem.get_text(separator=' ', strip=True)
                elem = elem.find_parent()

        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text_to_search)
        article_date = date_match.group(1) if date_match else None

        title = a.get_text(strip=True)
        if not title or len(title) < 5 or len(title) > 200:
            continue

        full_url = href if href.startswith('http') else BASE_URL + href
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Skip articles not from today or yesterday
        if article_date and article_date not in target_dates:
            continue

        articles.append({
            'title': title,
            'url': full_url,
            'date': article_date
        })

    print(f"Found {len(articles)} candidate news items on homepage.")
    return articles


# ── Anti-scraping protection ───────────────────────────────────────

def _polite_delay(min_s=1.0, max_s=3.0):
    """Random delay + UA rotation to avoid triggering anti-scraping detection."""
    time.sleep(random.uniform(min_s, max_s))
    _rotate_ua()


# ── Sub-page list fetchers ──────────────────────────────────────────

def parse_relative_time(text, today_date):
    """Parse relative time strings to approximate dates.

    Handles: 'X小时前' (today), '昨天' (yesterday), 'X天前' (today - X days).
    Returns datetime.date or None if unparseable.
    """
    h_match = re.search(r'(\d+)\s*小时前', text)
    if h_match:
        return today_date

    if '昨天' in text:
        return today_date - timedelta(days=1)

    d_match = re.search(r'(\d+)\s*天前', text)
    if d_match:
        return today_date - timedelta(days=int(d_match.group(1)))

    return None


def fetch_flash_list(cookies, target_dates, max_pages=5):
    """Fetch flash articles from /flash?page=N.

    /flash has explicit <span class='date'>YYYY-MM-DD</span>, so dates are reliable.
    Stops when the earliest date on a page is before min(target_dates).
    """
    min_date = min(datetime.strptime(d, '%Y-%m-%d').date() for d in target_dates)
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/flash?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')
        page_oldest_date = None

        # Find all flash links with their dates
        # Structure: each item has <span class='date'><b class='year'>2026-</b>06-04</span>
        # followed by <a href='/flash/{id}.html'>title</a>
        date_spans = soup.find_all('span', class_='date')
        for ds in date_spans:
            # Parse date from span
            full_text = ds.get_text(strip=True)
            m = re.search(r'(\d{4})-(\d{2})-(\d{2})', full_text)
            if not m:
                continue
            date_str = m.group(0)
            try:
                article_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                continue

            if page_oldest_date is None or article_date < page_oldest_date:
                page_oldest_date = article_date

            # Find the associated link: date span is in div.flash-created,
            # link is in sibling div.txt. Go up to parent first, then next siblings.
            link = None
            date_parent = ds.find_parent()
            if date_parent:
                for sibling in date_parent.find_next_siblings(limit=5):
                    link = sibling.find('a', href=re.compile(r'^/flash/\d+\.html$'))
                    if link:
                        break
            if not link:
                # Fallback: search in the item container
                item_container = ds.find_parent('div', class_=re.compile('item'))
                if item_container:
                    link = item_container.find('a', href=re.compile(r'^/flash/\d+\.html$'))

            if not link:
                continue

            href = link.get('href', '').strip()
            title = link.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            if date_str not in target_dates:
                continue

            articles.append({'title': title, 'url': full_url, 'date': date_str})

        # Stop condition: the oldest date on this page is before our window
        if page_oldest_date and page_oldest_date < min_date:
            print(f"  -> Page {page} oldest date {page_oldest_date} < {min_date}, stopping")
            break

        # If no dates found at all on this page, stop
        if page_oldest_date is None and len(date_spans) == 0:
            print(f"  -> Page {page} has no date spans, stopping")
            break

        _polite_delay()

    print(f"  Flash: {len(articles)} candidates from {page+1} pages")
    return articles


def fetch_news_list(cookies, target_dates, max_pages=5):
    """Fetch article-type news from /news?page=N.

    /news uses relative time ('X小时前', 'X天前', '昨天'). We parse these to
    approximate dates and filter by target_dates. Stop when a page is entirely
    older than 3 days.
    """
    today = datetime.now().date()
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/news?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find article links. The structure is:
        # <a href='/article/{id}.html'>title</a> ... followed by time text nearby
        page_article_links = soup.find_all('a', href=re.compile(r'^/article/\d+\.html$'))

        if not page_article_links:
            print(f"  -> Page {page} has no article links, stopping")
            break

        page_has_recent = False

        for a in page_article_links:
            href = a.get('href', '').strip()
            title = a.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Find time text nearby: go up to <li class='item'> which contains
            # both the link (in <h3>) and time ("X小时前") after it.
            time_text = ''
            # Walk up to <li> or several levels to capture time text
            for ancestor in a.parents:
                if ancestor.name in ('li', 'div') and ancestor.get('class'):
                    cls = ' '.join(ancestor.get('class', []))
                    if 'item' in cls or 'pic-list' in cls:
                        time_text = ancestor.get_text(separator=' ', strip=True)
                        break
            if not time_text:
                # Fallback: just use grandparent
                gp = a.find_parent().find_parent() if a.find_parent() else None
                if gp:
                    time_text = gp.get_text(separator=' ', strip=True)

            approx_date = parse_relative_time(time_text, today)

            if approx_date is None:
                # Can't determine date from listing, include it and verify on detail page
                articles.append({'title': title, 'url': full_url, 'date': None})
                page_has_recent = True
            else:
                approx_str = approx_date.strftime('%Y-%m-%d')
                if approx_str in target_dates:
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})
                    page_has_recent = True
                elif approx_date >= min(datetime.strptime(d, '%Y-%m-%d').date() for d in target_dates) - timedelta(days=1):
                    # Within 1 day of window edge, still include for safety
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})

        if not page_has_recent and page >= 1:
            # Second condition: check if most items are old
            print(f"  -> Page {page}: no recent items, stopping")
            break

        _polite_delay()

    print(f"  News: {len(articles)} candidates from {page+1} pages")
    return articles


def fetch_reference_list(cookies, target_dates, max_pages=15):
    """Fetch reference articles from /reference?page=N.

    /reference uses relative time like /news. 8 pages/day so generous max_pages.
    Stop when a page has no items matching target_dates.
    """
    today = datetime.now().date()
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/reference?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find reference article links: href='/reference/{id}.html'
        ref_links = soup.find_all('a', href=re.compile(r'^/reference/\d+\.html$'))

        if not ref_links:
            print(f"  -> Page {page} has no reference links, stopping")
            break

        page_has_recent = False

        for a in ref_links:
            href = a.get('href', '').strip()
            title = a.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Find time text in parent context: <li class='item'> has "X小时前"
            time_text = ''
            for ancestor in a.parents:
                if ancestor.name == 'li' and 'item' in ' '.join(ancestor.get('class', [])):
                    time_text = ancestor.get_text(separator=' ', strip=True)
                    break
            if not time_text:
                gp = a.find_parent().find_parent() if a.find_parent() else None
                if gp:
                    time_text = gp.get_text(separator=' ', strip=True)

            approx_date = parse_relative_time(time_text, today)

            if approx_date is None:
                articles.append({'title': title, 'url': full_url, 'date': None})
                page_has_recent = True
            else:
                approx_str = approx_date.strftime('%Y-%m-%d')
                if approx_str in target_dates:
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})
                    page_has_recent = True

        if not page_has_recent and page >= 1:
            print(f"  -> Page {page}: no recent reference items, stopping")
            break

        _polite_delay()

    print(f"  Reference: {len(articles)} candidates from {page+1} pages")
    return articles


# ── Page-type-specific extractors ──────────────────────────────────

def _extract_ref_link(soup):
    """Common: extract external reference link from a page."""
    # Method 1: <a> tag with "参考来源" or "参考链接" text
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a.get('href', '').strip()
        if ('参考来源' in text or '参考链接' in text) and href.startswith('http'):
            return {'text': text, 'url': href}
    # Method 2: label element with nearby <a>
    for el in soup.find_all(['span', 'label', 'div', 'p']):
        if '参考来源' in el.get_text(strip=True) or '参考链接' in el.get_text(strip=True):
            for a in el.parent.find_all('a', href=True):
                href = a.get('href', '').strip()
                if href.startswith('http') and 'qtc.com.cn' not in href:
                    return {'text': a.get_text(strip=True), 'url': href}
    return None


def _extract_liangke_date(soup):
    """Common: extract liangke date from time/date tags on detail page.

    Searches ALL matching elements (not just first), since the first <span class='time'>
    may be an institution name rather than a date.
    """
    # Collect ALL candidate elements
    candidates = []
    candidates.extend(soup.find_all('time'))
    candidates.extend(soup.find_all('span', class_='time'))
    for cls in ['date', 'published', 'post-time']:
        candidates.extend(soup.find_all('span', class_=cls))
        candidates.extend(soup.find_all('div', class_=cls))

    for tag in candidates:
        text = tag.get_text(strip=True)
        m = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if m:
            try: return datetime.strptime(m.group(1), '%Y-%m-%d').date()
            except ValueError: pass

    # Fallback 1: <span class='date'> with <b class='year'>YYYY-</b>MM-DD
    for date_span in soup.find_all('span', class_='date'):
        year_tag = date_span.find('b', class_='year')
        full_text = date_span.get_text(strip=True)
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', full_text)
        if m:
            try: return datetime.strptime(m.group(0), '%Y-%m-%d').date()
            except ValueError: pass

    # Fallback 2: Chinese date format "MM月DD日" in body, infer year from context
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','script','style']):
            noise.decompose()
        body_text = body.get_text()
        m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', body_text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            # Infer year: if MM-DD is in the future vs today, use previous year
            today = datetime.now().date()
            year = today.year
            try:
                candidate = datetime(year, month, day).date()
                if candidate > today:
                    candidate = datetime(year - 1, month, day).date()
                return candidate
            except ValueError:
                pass

    return None


def _extract_flash(soup, url):
    """Flash pages: h2 title, body text from page (not div.txt sidebar), external reference link."""
    title = ''
    h2 = soup.find('h2')
    if h2: title = h2.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    # Flash page body: text after h2/date, before related-articles sidebar
    # The content is NOT in div.txt (those are sidebar snippets). Get body text and filter.
    content = ''
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','footer','script','style']):
            noise.decompose()
        lines = [l.strip() for l in body.get_text(separator='\n', strip=True).split('\n') if l.strip()]
        # Find the article body: first long paragraph after date or title
        content = ''
        title_skipped = False
        for l in lines:
            # Skip first occurrence of title (the heading itself)
            if not title_skipped and title and title[:15] in l:
                title_skipped = True; continue
            if re.match(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', l): continue
            if len(l) < 50: continue
            if any(kw in l for kw in ['量科网 - 量子科技中心', '粤ICP', '粤公网', 'Copyright']): break
            content = l; break

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


def _extract_reference(soup, url):
    """Reference pages: h2 title, div.refer-txt content, trim header noise + footer metadata."""
    title = ''
    h2 = soup.find('h2')
    if h2: title = h2.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    content = ''
    content_div = soup.find('div', class_='refer-txt')
    if content_div:
        content = content_div.get_text(separator='\n', strip=True)
    if not content:
        body = soup.find('body')
        if body:
            for noise in body.find_all(['nav','header','footer','script','style']):
                noise.decompose()
            content = body.get_text(separator='\n', strip=True)

    # Trim: everything before the 3rd arrow (参考来源➔ PDF下载➔ HTML版➔ ...)
    arrows = [m.start() for m in re.finditer('➔', content)]
    if len(arrows) >= 3:
        content = content[arrows[2] + 1:].strip()
    # Trim: everything after "作者单位："
    if '作者单位：' in content:
        content = content.split('作者单位：')[0].strip()
    elif '作者单位:' in content:
        content = content.split('作者单位:')[0].strip()

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


def _extract_article(soup, url):
    """Article pages: h1 title + full body, trim only nav crumbs + page footer."""
    title = ''
    h1 = soup.find('h1', class_='page-header') or soup.find('h1')
    if h1: title = h1.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    content = ''
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','footer','script','style']):
            noise.decompose()
        lines = [l.strip() for l in body.get_text(separator='\n').split('\n') if l.strip()]

        # Find start: after the h1 title line
        start_idx = 0
        for i, l in enumerate(lines):
            if title and title[:15] in l:
                start_idx = i + 1
                break

        # Skip a few metadata lines (date, view count, category, institution name)
        skip_count = 0
        while start_idx + skip_count < len(lines) and skip_count < 5:
            l = lines[start_idx + skip_count]
            is_meta = (
                re.match(r'\d{4}-\d{2}-\d{2}', l) or           # date line
                (l.isdigit() and len(l) < 5) or                 # view count
                l in ('技术研究','行业观点','企业动态') or      # category tag
                (len(l) < 30 and not any(p in l for p in '，。！？'))  # short institution name
            )
            if is_meta:
                skip_count += 1
            else:
                break

        # Take everything from article start to page footer
        result_lines = []
        for l in lines[start_idx + skip_count:]:
            # Trim: nav crumbs, short UI labels
            if l in ('首页','快讯','文章','参考','企服','VIP','企业','所有','短讯',
                     '量科快讯','商业情报','一点数据','知识碎片','实时快讯','用户专享：'):
                continue
            # Stop only at definitive page footer (not mid-content sections)
            if any(kw in l for kw in ['量科网 - 量子科技中心', '粤ICP备', '粤公网安备', 'Copyright']):
                break
            result_lines.append(l)

        content = '\n'.join(result_lines).strip()
        if '注册用户以继续' in content:
            content = content.split('注册用户以继续')[0].strip()
        # Trim after "参考链接¹" — everything after is unrelated
        if '参考链接¹' in content:
            content = content.split('参考链接¹')[0].strip()

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


# ── Main fetch function (dispatches to type-specific extractor) ────

def fetch_article_detail(url, cookies):
    """Fetch full article detail using page-type-specific extraction."""
    try:
        resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        if resp.status_code == 404 or '404' in (soup.find('title').get_text(strip=True) if soup.find('title') else ''):
            return {'title': 'ERROR', 'time_text': '', 'url': url,
                    'content': f'404: page not found', 'primary_reference': None, 'liangke_date': None}

        if '/reference/' in url:
            result = _extract_reference(soup, url)
        elif '/flash/' in url:
            result = _extract_flash(soup, url)
        else:
            result = _extract_article(soup, url)

        result['url'] = url
        result['time_text'] = ''
        return result
    except Exception as e:
        return {'title': 'ERROR', 'time_text': '', 'url': url, 'content': str(e),
                'primary_reference': None, 'liangke_date': None}


def _extract_keywords(title):
    """Extract meaningful keywords from a title using jieba for Chinese segmentation."""
    import jieba, re
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                  'and', 'or', 'but', 'not', 'this', 'that', 'it', 'its',
                  'has', 'have', 'had', 'will', 'would', 'could', 'should',
                  'may', 'might', 'can', 'new', 'first', 'more', 'than',
                  '了', '的', '在', '是', '和', '与', '及', '或',
                  '为', '以', '等', '从', '到', '对', '被', '把', '向',
                  '将', '就', '也', '都', '还', '而', '但', '却', '因',
                  '所', '其', '中', '上', '下', '之', '已', '于', '该'}
    words = jieba.lcut((title or '').lower())
    return {w.strip() for w in words if len(w.strip()) >= 2 and w.strip() not in stop_words}


def find_similar_article(title, date_str, window_days=3):
    """Check if a semantically similar article exists within N days.

    Uses jieba keyword overlap. Checks a window of window_days around date_str
    to catch articles that were scraped on different dates but are the same content.
    """
    try:
        from db import get_session, Article
        import jieba
        from datetime import timedelta
        session = get_session()
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_d = d - timedelta(days=window_days)
        end_d = d + timedelta(days=window_days)
        nearby_articles = session.query(Article).filter(
            Article.liangke_date >= start_d,
            Article.liangke_date <= end_d
        ).all()

        new_kw = _extract_keywords(title)
        if len(new_kw) < 3:
            session.close()
            return None

        for art in nearby_articles:
            exist_kw = _extract_keywords(art.title or '')
            if len(exist_kw) < 3:
                continue
            overlap = len(new_kw & exist_kw)
            min_len = min(len(new_kw), len(exist_kw))
            # Require both high overlap ratio AND a minimum number of matching terms
            if min_len > 0 and overlap / min_len >= 0.6 and overlap >= 3:
                session.close()
                return {'id': art.id, 'title': art.title}

        session.close()
    except Exception:
        pass
    return None


def check_cookie_valid(cookies):
    """Verify cookie can access logged-in content (参考来源 links)."""
    try:
        test_url = 'http://www.qtc.com.cn/reference/178028316033556.html'
        resp = requests.get(test_url, cookies=cookies, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # If logged in, "参考来源" link should point to external URL, not /user/login
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = a.get('href', '').strip()
            if ('参考来源' in text or '参考链接' in text):
                if href.startswith('/user/login'):
                    return False, 'Cookie expired — 参考来源指向登录页'
                if href.startswith('http'):
                    return True, 'OK'
        # No 参考来源 found at all
        login_links = len(soup.find_all('a', href='/user/login'))
        if login_links > 0:
            return False, 'Cookie expired — 页面处于未登录状态'
        return False, '参考来源链接未找到'
    except Exception as e:
        return False, f'Cookie check failed: {e}'


def main():
    cookies = load_cookies()
    if not cookies:
        print('ERROR: No cookie file found. Run update_cookie.bat first.')
        return

    cookie_ok, cookie_msg = check_cookie_valid(cookies)
    if not cookie_ok:
        print(f'ERROR: {cookie_msg}')
        print('Please re-login to www.qtc.com.cn and update the cookie.')
        return
    print(f'Cookie check: {cookie_msg}')

    today = get_today_str()
    target_dates = get_target_dates()
    print(f"Target dates: {sorted(target_dates)}")

    # Three sub-page sources (better coverage than mixed homepage)
    print("\n--- Flash ---")
    articles = fetch_flash_list(cookies, target_dates)
    print("\n--- News (article) ---")
    articles += fetch_news_list(cookies, target_dates)
    print("\n--- Reference ---")
    articles += fetch_reference_list(cookies, target_dates)

    # Dedup by URL (same article may appear on multiple sub-pages)
    seen = set()
    deduped = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            deduped.append(a)
    articles = deduped

    print(f"\nTotal candidates across all sources: {len(articles)} (after dedup)")

    if not articles:
        print(f"No candidate articles found for target dates: {sorted(target_dates)}.")
        return

    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    # ── Phase 1: Fetch all details + keyword tags ──
    pending = []  # list of dicts with all info needed for insert
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {art['title'][:60].encode('gbk', errors='replace').decode('gbk', errors='replace')}")

        detail = fetch_article_detail(art['url'], cookies)
        if detail['title'] == 'ERROR':
            print(f"  -> ERROR: {detail['content'][:100]}")
            stats['errors'] += 1
            continue

        art_date = detail['liangke_date']
        if art_date:
            art_date_str = art_date.strftime('%Y-%m-%d')
        else:
            art_date_str = art.get('date')

        if art_date_str and art_date_str not in target_dates:
            print(f"  -> Skipped (date: {art_date_str}, not in target range)")
            stats['skipped'] += 1
            _polite_delay()
            continue

        # Extract original date from reference link
        ref_url = ''
        ref_title = ''
        original_date = None
        source_domain = ''

        if detail['primary_reference']:
            ref_url = detail['primary_reference']['url']
            ref_title = detail['primary_reference']['text']
            print(f"  -> Ref: {ref_url[:80]}")
            original_date = get_original_date(ref_url)
            if original_date:
                print(f"  -> Original date: {original_date}")
            try:
                source_domain = urlparse(ref_url).netloc
            except Exception:
                pass
            time.sleep(0.3)
        else:
            original_date = None

        # Dedup check
        exists = article_exists(ref_url, detail['url'])
        if exists:
            print(f"  -> SKIP (exists in DB)")
            stats['skipped'] += 1
            _polite_delay()
            continue

        if detail['title']:
            similar = find_similar_article(detail['title'], art_date_str or today)
            if similar:
                print(f"  -> DUPLICATE (similar to id={similar['id']})")
                stats['skipped'] += 1
                _polite_delay()
                continue

        # Keyword tag (temporary, will be overridden by LLM)
        kw_tags = auto_tag(detail['title'], detail['content'])
        weekly_kw = kw_tags.get('weekly', ['宏观态势']) if kw_tags else ['宏观态势']

        # Page type
        page_type = ''
        if '/flash/' in art['url']: page_type = 'flash'
        elif '/reference/' in art['url']: page_type = 'reference'
        elif '/article/' in art['url']: page_type = 'article'

        print(f"  KW tag: {weekly_kw[0] if weekly_kw else '?'} | type: {page_type} | {len(detail['content'])}c")

        pending.append({
            'detail': detail,
            'ref_url': ref_url,
            'ref_title': ref_title,
            'original_date': original_date,
            'source_domain': source_domain,
            'kw_tags': kw_tags,
            'page_type': page_type,
            'art_date_str': art_date_str,
        })

        _polite_delay()

    # ── Phase 2: LLM batch classify ──
    llm_cats = {}
    if pending:
        print(f"\n--- LLM classifying {len(pending)} articles ---")
        # Give LLM more context: title + first 400 chars of content
        info_list = [
            f"{p['detail']['title'][:120]} | {((p['detail']['content'] or '')[:300]).strip()}"
            for p in pending
        ]
        llm_results = _llm_classify_batch(info_list)
        if llm_results:
            for idx, cat in llm_results.items():
                if idx < len(pending):
                    llm_cats[idx] = cat
                    old_cat = pending[idx]['kw_tags'].get('weekly', ['?'])[0] if pending[idx]['kw_tags'] else '?'
                    title_short = pending[idx]['detail']['title'][:60]
                    print(f"  [{idx+1}] {old_cat} -> {cat} | {title_short}")
        else:
            print("  LLM classify returned empty, using keyword tags as fallback")

    # ── Phase 3: Insert into DB with LLM tags ──
    if pending:
        print(f"\n--- Inserting {len(pending)} articles ---")
    for idx, p in enumerate(pending):
        # Override weekly tag with LLM result
        final_tags = p['kw_tags'] or {}
        if idx in llm_cats:
            if isinstance(final_tags, dict):
                final_tags['weekly'] = [llm_cats[idx]]
            else:
                final_tags = {'weekly': [llm_cats[idx]], 'search_tags': [], 'knowledge_graph': {}}

        try:
            result = insert_or_update_article(
                reference_url=p['ref_url'],
                liangke_url=p['detail']['url'],
                title=p['detail']['title'],
                content=p['detail']['content'],
                original_date=p['original_date'],
                liangke_date=p['detail']['liangke_date'] or datetime.strptime(today, '%Y-%m-%d').date(),
                source_domain=p['source_domain'],
                reference_title=p['ref_title'],
                tags=final_tags,
                page_type=p['page_type']
            )

            if result['action'] == 'inserted':
                stats['inserted'] += 1
            else:
                stats['updated'] += 1
        except Exception as e:
            print(f"  -> DB ERROR: {e}")
            stats['errors'] += 1

    total = get_article_count()
    print(f"\n{'='*50}")
    print(f"Daily scrape completed for {today}")
    print(f"  New articles:     {stats['inserted']}")
    print(f"  Updated articles: {stats['updated']}")
    print(f"  Skipped (old):    {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"  Total in DB:      {total}")
    print(f"{'='*50}")

    # Sync to OneDrive shared folder
    try:
        from sync_to_onedrive import sync_all
        sync_all()
    except Exception as e:
        print(f'  [WARN] OneDrive sync failed: {e}')


if __name__ == '__main__':
    main()
