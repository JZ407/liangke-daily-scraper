"""
Fix incorrectly marked liangke_date for articles that were fallback to 'today'.
Usage: python core/fix_liangke_dates.py
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import pickle
from datetime import datetime
from scrape_daily import fetch_article_detail, load_cookies
from db import get_session, Article


def main():
    cookies = load_cookies()
    if not cookies:
        print("ERROR: No cookies found.")
        return

    session = get_session()
    try:
        articles = session.query(Article).filter(Article.liangke_date == datetime.now().date()).all()
        print(f'Found {len(articles)} articles marked as today ({datetime.now().date()}).')

        fixed = 0
        for art in articles:
            print(f'[{art.id}] {art.title[:50]}...')
            detail = fetch_article_detail(art.liangke_url, cookies)
            if detail['title'] == 'ERROR':
                print(f'  -> Fetch failed, skipping.')
                continue

            new_date = detail['liangke_date']
            if new_date and new_date != art.liangke_date:
                print(f'  -> Fixed: {art.liangke_date} -> {new_date}')
                art.liangke_date = new_date
                fixed += 1
            elif new_date:
                print(f'  -> Confirmed: {new_date}')
            else:
                print(f'  -> Still no date found, keeping {art.liangke_date}')

        session.commit()
        print(f'\nDone. Fixed {fixed} articles.')
    except Exception as e:
        session.rollback()
        print(f'Error: {e}')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
