"""Quick cookie check for qtc.com.cn. Exit 0=OK, 1=expired, 2=missing."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_daily import load_cookies, check_cookie_valid

cookies = load_cookies()
if not cookies:
    print('COOKIE_MISSING')
    sys.exit(2)

ok, msg = check_cookie_valid(cookies)
if ok:
    print(f'COOKIE_OK: {msg}')
    sys.exit(0)
else:
    print(f'COOKIE_EXPIRED: {msg}')
    print('Update: browser login to www.qtc.com.cn → F12 → Network tab →')
    print('copy Cookie header → paste to D:/Claude_code/liangke_daily/cookies.txt')
    sys.exit(1)
