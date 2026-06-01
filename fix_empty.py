import pymysql, requests, re, pickle, os
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'cookies.pkl')

def load_cookies():
    if not os.path.exists(COOKIE_PATH):
        return None
    with open(COOKIE_PATH, 'rb') as f:
        return pickle.load(f)

cookies = load_cookies()

conn = pymysql.connect(host='127.0.0.1', user='scraper', password='scraper123',
                       database='liangke_scraper', charset='utf8mb4')
c = conn.cursor()
c.execute("SELECT id, liangke_url FROM articles WHERE title='无标题' AND content='' ORDER BY id")
rows = c.fetchall()
print(f'Fixing {len(rows)} articles...')

for art_id, url in rows:
    try:
        resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Title extraction
        title = ''
        # Try h2 (flash/reference)
        for h in soup.find_all(['h2', 'h1']):
            t = h.get_text(strip=True)
            if len(t) > 10 and '量科网' not in t and '量子科技中心' not in t:
                title = t
                break
        # Try og:title
        if not title:
            og = soup.find('meta', property='og:title')
            if og and og.get('content'):
                title = og['content'].split('|')[0].strip()
        # Try <title>
        if not title:
            ttag = soup.find('title')
            if ttag:
                title = ttag.get_text(strip=True).split('|')[0].strip()
        # Body text fallback
        if not title or title == '无标题':
            body = soup.find('body')
            if body:
                for noise in body.find_all(['nav','header','footer','script','style']):
                    noise.decompose()
                text = body.get_text(separator='\n', strip=True)
                lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 15]
                for l in lines:
                    if '量科网' not in l and '量子科技中心' not in l and 'Cookie' not in l:
                        title = l[:200]
                        break

        # Content extraction
        content = ''
        for cls in ['txt', 'refer-txt', 'content']:
            div = soup.find('div', class_=cls)
            if div:
                content = div.get_text(separator='\n', strip=True)
                if len(content) > 50:
                    break

        if not content:
            article = soup.find('article') or soup.find('main')
            if article:
                content = article.get_text(separator='\n', strip=True)

        if not content:
            body = soup.find('body')
            if body:
                for noise in body.find_all(['nav','header','footer','script','style']):
                    noise.decompose()
                content = body.get_text(separator='\n', strip=True)

        if title and title != '无标题':
            c.execute('UPDATE articles SET title=%s, content=%s WHERE id=%s',
                     (title[:500], content[:10000] if content else '', art_id))
            conn.commit()
            print(f'  [{art_id}] {title[:80]} ({len(content)} chars)')
        else:
            print(f'  [{art_id}] STILL FAILED: {url}')
    except Exception as e:
        print(f'  [{art_id}] ERROR: {e}')

conn.close()
print('Done')
