"""
Sync websearch articles from MySQL (liangke_scraper) to SQLite (liangke_historical/historical.db)
"""
import sys, os, json, sqlite3

sys.path.insert(0, r'D:\Claude_code\liangke_daily\core')
from db import get_session, Article

# ── Read from MySQL ──
session = get_session()
articles = session.query(Article).filter(Article.page_type == 'websearch').all()
print(f'Websearch articles in MySQL: {len(articles)}')

# ── Connect to SQLite ──
sqlite_path = r'D:\Claude_code\liangke_historical\historical.db'
conn = sqlite3.connect(sqlite_path)
conn.row_factory = sqlite3.Row

# Check existing websearch articles
existing = conn.execute("SELECT COUNT(*) FROM articles WHERE article_type = 'websearch'").fetchone()[0]
print(f'Existing websearch in SQLite: {existing}')

# Get max ID
max_id = conn.execute("SELECT MAX(id) FROM articles").fetchone()[0] or 0
print(f'Max ID in SQLite: {max_id}')

# ── Insert websearch articles ──
inserted = 0
skipped = 0

CHINESE_COMPANIES = {
    '本源量子', '量旋科技', '相干科技', '逻辑比特', '矩量光启', '武汉超磁科技',
    '玻色量子', '图灵量子', '正则量子', '奇算光启', '华翊量子', '幺正量子',
    '中科酷原', '无量量子', '太一量生', '两仪万象', '无问清芯', '不筹量子', '原子矩阵',
    '国仪量子', '国测量子', '未磁科技', '频准激光', '国光量子',
    '国盾量子', '国科量子', '微观纪元', '量坤科技', '瀚海量子', '隧穿智元',
    '知冷低温', '量羲技术', '森一量子', '硅臻量子', '天芯量子', '矩阵时光',
    '太微量子', '伏曦量子',
}

for a in articles:
    # Check dedup by liangke_url
    dup = conn.execute(
        "SELECT id FROM articles WHERE liangke_url = ?",
        (a.liangke_url,)
    ).fetchone()
    if dup:
        skipped += 1
        continue

    tags = a.tags or {}
    f = tags.get('funding', {}) or {}
    company = f.get('company', '') or ''

    # Determine area
    if company in CHINESE_COMPANIES:
        area = '中国'
    elif any('一' <= c <= '鿿' for c in company):
        area = '中国'
    else:
        area = '海外'

    # Build row
    max_id += 1
    tags_json = json.dumps(tags, ensure_ascii=False)
    content = a.content or ''
    title = a.title or ''
    liangke_url = a.liangke_url or ''
    reference_url = a.reference_url or ''
    liangke_date = str(a.original_date) if a.original_date else (str(a.liangke_date) if a.liangke_date else '')
    source_domain = a.source_domain or ''

    conn.execute(
        """INSERT INTO articles (id, article_type, liangke_url, liangke_id, title, content, reference_url,
           tags, area, source_domain, published_at)
           VALUES (?, 'websearch', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (max_id, liangke_url, f'ws_{a.id}', title, content, reference_url,
         tags_json, area, source_domain, liangke_date)
    )
    inserted += 1

conn.commit()

# Verify
total = conn.execute("SELECT COUNT(*) FROM articles WHERE article_type = 'websearch'").fetchone()[0]
funding_count = conn.execute(
    "SELECT COUNT(*) FROM articles WHERE article_type = 'websearch' AND tags LIKE '%融资%'"
).fetchone()[0]

print(f'\nSync results:')
print(f'  Inserted: {inserted}')
print(f'  Skipped (dup): {skipped}')
print(f'  Total websearch in SQLite: {total}')
print(f'  With funding tag: {funding_count}')

conn.close()
session.close()
print('\nDone.')
