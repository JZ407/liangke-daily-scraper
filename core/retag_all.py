"""
批量为量科每日数据库中所有已有文章重新打五大标签。
用法: python core/retag_all.py
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from db import get_session, Article
from scrape_daily import auto_tag


def main():
    session = get_session()
    try:
        articles = session.query(Article).all()
        print(f'Found {len(articles)} articles to re-tag.')

        updated = 0
        for art in articles:
            new_tags = auto_tag(art.title, art.content)
            if art.tags != new_tags:
                art.tags = new_tags
                updated += 1
                print(f'[{art.id}] {art.title[:40]}... -> {new_tags[0]}')

        session.commit()
        print(f'\nDone. Total: {len(articles)}, Updated: {updated}')
    except Exception as e:
        session.rollback()
        print(f'Error: {e}')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
