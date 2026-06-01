import sys, pymysql, requests, re, pickle, os, time
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'cookies.pkl')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.extract_original_date import get_original_date

def load_cookies():
    if not os.path.exists(COOKIE_PATH):
        return None
    with open(COOKIE_PATH, 'rb') as f:
        return pickle.load(f)

cookies = load_cookies()
conn = pymysql.connect(host='127.0.0.1', user='scraper', password='scraper123',
                       database='liangke_scraper', charset='utf8mb4')
c = conn.cursor()
c.execute("SELECT id, liangke_url FROM articles WHERE reference_url = liangke_url ORDER BY id")
rows = c.fetchall()
print(f'Fixing {len(rows)} articles...')

for art_id, url in rows:
    try:
        resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # New reference link extraction
        ref_url = ''
        ref_title = ''
        # Method 1: search by label text
        for el in soup.find_all(['span', 'label', 'div', 'p', 'strong', 'b']):
            text = el.get_text(strip=True)
            if '参考来源' in text or '参考链接' in text:
                parent = el.parent
                for a in parent.find_all('a', href=re.compile(r'^https?://')):
                    ref_url = a.get('href', '').strip()
                    ref_title = a.get_text(strip=True)
                    break
                if ref_url:
                    break
        # Method 2: search the whole page text for "参考来源" and find nearest link
        if not ref_url:
            for tag in soup.find_all(string=re.compile(r'参考来源|参考链接')):
                parent = tag.parent
                for _ in range(3):
                    if parent is None:
                        break
                    link = parent.find('a', href=re.compile(r'^https?://'))
                    if link:
                        ref_url = link.get('href', '').strip()
                        ref_title = link.get_text(strip=True)
                        break
                    parent = parent.parent
                if ref_url:
                    break
        # Method 3: get all external links and use the first non-qtc one (skip site root)
        if not ref_url:
            for a in soup.find_all('a', href=re.compile(r'^https?://')):
                href = a.get('href', '').strip()
                if href and 'qtc.com.cn' not in href and href not in ('http://www.qtc.com.cn', 'http://www.qtc.com.cn/'):
                    if not href.endswith(('.jpg','.png','.pdf')):
                        text = a.get_text(strip=True)
                        if len(text) > 5 and '参考' not in text and '量科网' not in text:
                            ref_url = href
                            ref_title = text
                            break

        if ref_url and 'qtc.com.cn' not in ref_url:
            domain = urlparse(ref_url).netloc
            print(f'  [{art_id}] ref={ref_url[:60]}')
            # Extract original date
            original_date = get_original_date(ref_url)
            try:
                if original_date:
                    c.execute('UPDATE articles SET reference_url=%s, source_domain=%s, original_date=%s WHERE id=%s',
                             (ref_url, domain, original_date, art_id))
                    print(f'    -> date={original_date}')
                else:
                    c.execute('UPDATE articles SET reference_url=%s, source_domain=%s WHERE id=%s',
                             (ref_url, domain, art_id))
                    print(f'    -> date extraction failed, using liangke_date')
                    c.execute('UPDATE articles SET original_date=liangke_date WHERE id=%s', (art_id,))
                conn.commit()
            except Exception as e:
                print(f'    -> SKIP: {e}')
            time.sleep(0.2)
        else:
            print(f'  [{art_id}] NO reference found')
            # Fallback: use liangke_page_time as original_date
            c.execute('UPDATE articles SET original_date=%s WHERE id=%s',
                     ('2026-06-01', art_id))
            conn.commit()
    except Exception as e:
        print(f'  [{art_id}] ERROR: {e}')

conn.close()
print('Done')
