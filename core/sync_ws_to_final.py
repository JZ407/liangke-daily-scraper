"""
Sync websearch articles from MySQL to historical_final.db
"""
import sys, os, json, sqlite3

sys.path.insert(0, r'D:\Claude_code\liangke_daily\core')
from db import get_session, Article

# ── Read from MySQL ──
session = get_session()
articles = session.query(Article).filter(Article.page_type == 'websearch').all()
print(f'Websearch articles in MySQL: {len(articles)}')

# ── Connect to SQLite ──
conn = sqlite3.connect(r'D:\Claude_code\liangke_historical\historical_final.db')

# Check existing
existing = conn.execute("SELECT COUNT(*) FROM articles WHERE article_type = 'websearch'").fetchone()[0]
print(f'Existing websearch in final.db: {existing}')

# Get max ID
max_id = conn.execute("SELECT MAX(id) FROM articles").fetchone()[0] or 0
print(f'Max ID: {max_id}')

CHINESE_COMPANIES = {
    '本源量子', '量旋科技', '相干科技', '逻辑比特', '矩量光启', '武汉超磁科技',
    '玻色量子', '图灵量子', '正则量子', '奇算光启', '华翊量子', '幺正量子',
    '中科酷原', '无量量子', '太一量生', '两仪万象', '无问清芯', '不筹量子', '原子矩阵',
    '国仪量子', '国测量子', '未磁科技', '频准激光', '国光量子',
    '国盾量子', '国科量子', '微观纪元', '量坤科技', '瀚海量子', '隧穿智元',
    '知冷低温', '量羲技术', '森一量子', '硅臻量子', '天芯量子', '矩阵时光',
    '太微量子', '伏曦量子',
}

inserted = 0
skipped = 0

for a in articles:
    # Dedup by liangke_url
    dup = conn.execute(
        "SELECT id FROM articles WHERE liangke_url = ?", (a.liangke_url,)
    ).fetchone()
    if dup:
        skipped += 1
        continue

    tags = a.tags or {}
    f = tags.get('funding', {}) or {}
    company = f.get('company', '') or ''

    area = '中国' if (company in CHINESE_COMPANIES or any('一' <= c <= '鿿' for c in company)) else '海外'

    max_id += 1
    date_str = str(a.original_date) if a.original_date else (str(a.liangke_date) if a.liangke_date else '')
    tags_json = json.dumps(tags, ensure_ascii=False)

    conn.execute(
        """INSERT INTO articles (id, article_type, liangke_url, liangke_id, title, content,
           reference_url, liangke_date, tags, area, source_domain, published_at)
           VALUES (?, 'websearch', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (max_id, a.liangke_url or '', f'ws_{a.id}', a.title or '', a.content or '',
         a.reference_url or '', date_str, tags_json, area, a.source_domain or '', date_str)
    )
    inserted += 1

conn.commit()

# Also populate published_at for existing articles from liangke_date
conn.execute("UPDATE articles SET published_at = liangke_date WHERE published_at IS NULL AND liangke_date IS NOT NULL")
updated = conn.execute("SELECT changes()").fetchone()[0]
print(f'Populated published_at for {updated} existing articles')

# Verify
total = conn.execute("SELECT COUNT(*) FROM articles WHERE article_type = 'websearch'").fetchone()[0]
funding = conn.execute("SELECT COUNT(*) FROM articles WHERE tags LIKE '%融资%'").fetchone()[0]

print(f'\nResults:')
print(f'  Inserted: {inserted}')
print(f'  Skipped: {skipped}')
print(f'  Websearch in final.db: {total}')
print(f'  Total funding articles: {funding}')

conn.close()
session.close()
print('Done.')
