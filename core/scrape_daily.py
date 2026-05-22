"""
量科网每日新闻抓取脚本 (MySQL + 去重 + 原始日期提取)
"""
import requests
from bs4 import BeautifulSoup
import pickle
import time
import os
import re
from datetime import datetime
from urllib.parse import urlparse

from extract_original_date import get_original_date
from db import insert_or_update_article, article_exists, get_article_count

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
    """匹配五大分类标签，返回唯一分类。"""
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


def auto_tag(title: str, content: str) -> list:
    """根据标题和正文自动匹配标签。
    返回：原有技术标签 + 一个五大分类标签。
    """
    text = (title or '') + ' ' + (content or '')[:2000]
    text_lower = text.lower()
    tags = []

    # 1. 原有技术标签
    for category, words in KEYWORDS.items():
        for word in words:
            if word.lower() in text_lower:
                tags.append(category)
                break

    for tag, words in SPECIFIC_TAGS.items():
        for word in words:
            if word.lower() in text_lower:
                tags.append(tag)
                break

    # 2. 五大分类标签（必须有且仅有一个）
    category_tag = _match_category(text_lower)
    tags.append(category_tag)

    return list(set(tags))


def load_cookies():
    if not os.path.exists(COOKIE_PATH):
        print(f"ERROR: Cookie file not found: {COOKIE_PATH}")
        print("Please run update_cookie.bat first after logging in to 量科网.")
        return None
    with open(COOKIE_PATH, 'rb') as f:
        return pickle.load(f)


def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')


def fetch_homepage_list(cookies):
    """Fetch homepage and extract today's news URLs."""
    print(f"Fetching homepage: {BASE_URL}")
    resp = requests.get(BASE_URL, cookies=cookies, headers=HEADERS, timeout=30)
    resp.encoding = resp.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')

    today = get_today_str()
    print(f"Looking for news dated: {today}")

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

        # Skip articles with a clear non-today date to avoid fetching stale pages
        if article_date and article_date != today:
            continue

        articles.append({
            'title': title,
            'url': full_url,
            'date': article_date
        })

    print(f"Found {len(articles)} candidate news items on homepage.")
    return articles


def fetch_article_detail(url, cookies):
    """Fetch full article content including reference links."""
    try:
        resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        is_flash = '/flash/' in url
        is_reference = '/reference/' in url

        # Title - try multiple strategies
        title = '无标题'
        if is_flash or is_reference:
            title_tag = soup.find('h2')
            if title_tag:
                title = title_tag.get_text(strip=True)
        else:
            title_tag = soup.find('h1', class_='page-header')
            if title_tag:
                title = title_tag.get_text(strip=True)
        if title == '无标题':
            # Fallback: extract from <title> tag
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Remove site suffix like " | 量子科技中心_量科网"
                title = title_text.split('|')[0].strip()

        # Time
        time_text = ''
        if is_flash or is_reference:
            time_tag = soup.find('time')
            if time_tag:
                time_text = time_tag.get_text(strip=True)
            # Fallback: common date class names on flash/reference pages
            if not time_text:
                for cls in ['time', 'date', 'published', 'post-time', 'post_date']:
                    tag = soup.find('span', class_=cls) or soup.find('div', class_=cls) or soup.find('p', class_=cls)
                    if tag:
                        time_text = tag.get_text(strip=True)
                        break
        else:
            time_tag = soup.find('span', property='schema:dateCreated')
            if time_tag:
                time_text = time_tag.get_text(strip=True)
            else:
                time_tag = soup.find('span', class_='time')
                if time_tag:
                    time_text = time_tag.get_text(strip=True)

        # Content
        content_text = ''
        if is_flash:
            content_div = soup.find('div', class_='txt')
        elif is_reference:
            content_div = soup.find('div', class_='refer-txt')
        else:
            content_div = soup.find('div', class_='content')

        if content_div:
            paragraphs = content_div.find_all(['p', 'h2', 'h3', 'h4', 'li'])
            if not paragraphs:
                content_text = content_div.get_text(separator='\n', strip=True)
            else:
                lines = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        lines.append(text)
                content_text = '\n'.join(lines)

        # Reference links (外部参考链接)
        ref_links = []
        for a in soup.find_all('a'):
            text = a.get_text(strip=True)
            href = a.get('href', '').strip()
            if ('参考链接' in text or '参考来源' in text) and href and href.startswith('http'):
                ref_links.append({'text': text, 'url': href})

        # Primary reference: the first 参考链接
        primary_ref = ref_links[0] if ref_links else None

        # Extract liangke_date from time_text
        liangke_date = None
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_text)
        if date_match:
            try:
                liangke_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass

        return {
            'title': title,
            'time_text': time_text,
            'url': url,
            'content': content_text,
            'primary_reference': primary_ref,
            'liangke_date': liangke_date
        }
    except Exception as e:
        return {'title': 'ERROR', 'time_text': '', 'url': url, 'content': str(e),
                'primary_reference': None, 'liangke_date': None}


def main():
    cookies = load_cookies()
    if not cookies:
        return

    today = get_today_str()
    articles = fetch_homepage_list(cookies)

    if not articles:
        print(f"No candidate articles found for {today}.")
        return

    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    for i, art in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {art['title'][:60]}")

        # Fetch detail
        detail = fetch_article_detail(art['url'], cookies)
        if detail['title'] == 'ERROR':
            print(f"  -> ERROR: {detail['content'][:100]}")
            stats['errors'] += 1
            continue

        # Validate date
        art_date = detail['liangke_date']
        if art_date:
            art_date_str = art_date.strftime('%Y-%m-%d')
        else:
            art_date_str = art.get('date')

        if art_date_str and art_date_str != today:
            print(f"  -> Skipped (date: {art_date_str}, not today)")
            stats['skipped'] += 1
            continue

        # Extract original date from reference link (串行，礼貌延迟)
        ref_url = ''
        ref_title = ''
        original_date = None
        source_domain = ''

        if detail['primary_reference']:
            ref_url = detail['primary_reference']['url']
            ref_title = detail['primary_reference']['text']
            print(f"  -> Extracting original date from: {ref_url[:80]}")
            original_date = get_original_date(ref_url)
            if original_date:
                print(f"  -> Original date: {original_date}")
            else:
                print(f"  -> Original date extraction failed, leaving null")
            try:
                source_domain = urlparse(ref_url).netloc
            except Exception:
                pass
            time.sleep(0.3)  # 礼貌延迟
        else:
            original_date = None

        # Deduplication check
        exists = article_exists(ref_url, detail['url'])

        # Auto-tag
        tags = auto_tag(detail['title'], detail['content'])
        if tags:
            print(f"  -> Tags: {', '.join(tags)}")

        try:
            result = insert_or_update_article(
                reference_url=ref_url,
                liangke_url=detail['url'],
                title=detail['title'],
                content=detail['content'],
                original_date=original_date,
                liangke_date=detail['liangke_date'] or datetime.strptime(today, '%Y-%m-%d').date(),
                source_domain=source_domain,
                reference_title=ref_title,
                tags=tags
            )

            if result['action'] == 'inserted':
                print(f"  -> INSERTED (id={result['id']})")
                stats['inserted'] += 1
            else:
                print(f"  -> UPDATED (id={result['id']}, count={result['fetch_count']})")
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


if __name__ == '__main__':
    main()
