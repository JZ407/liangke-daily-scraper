"""
Database layer for 量科网 scraper using SQLAlchemy ORM.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime

Base = declarative_base()

DB_URL = 'mysql+pymysql://scraper:scraper123@127.0.0.1:3306/liangke_scraper?charset=utf8mb4'

engine = create_engine(DB_URL, pool_pre_ping=True, echo=False)
Session = sessionmaker(bind=engine)


class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_url = Column(String(1000), nullable=False, default='')
    liangke_url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(LONGTEXT)
    original_date = Column(Date)
    liangke_date = Column(Date, nullable=False)
    source_domain = Column(String(200))
    reference_title = Column(String(200))
    tags = Column(JSON)
    page_type = Column(String(20), default='')
    first_seen_at = Column(DateTime, default=datetime.now)
    last_seen_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    fetch_count = Column(Integer, default=1)


def get_session():
    return Session()


def article_exists(reference_url: str, liangke_url: str) -> bool:
    """Check if article already exists by reference_url or liangke_url."""
    session = get_session()
    try:
        # Prefer reference_url as unique key
        if reference_url and reference_url.strip():
            return session.query(Article).filter(
                Article.reference_url == reference_url
            ).first() is not None
        # Fallback to liangke_url
        if liangke_url and liangke_url.strip():
            return session.query(Article).filter(
                Article.liangke_url == liangke_url
            ).first() is not None
        return False
    finally:
        session.close()


def insert_or_update_article(
    reference_url: str,
    liangke_url: str,
    title: str,
    content: str,
    original_date,
    liangke_date,
    source_domain: str,
    reference_title: str,
    tags,
    page_type: str = ''
) -> dict:
    """
    Insert new article or update existing one (increment fetch_count).
    Returns {'action': 'inserted' | 'updated', 'id': int}
    """
    session = get_session()
    try:
        # Try to find existing article
        existing = None
        if reference_url and reference_url.strip():
            existing = session.query(Article).filter(
                Article.reference_url == reference_url
            ).first()
        if not existing and liangke_url and liangke_url.strip():
            existing = session.query(Article).filter(
                Article.liangke_url == liangke_url
            ).first()

        if existing:
            existing.fetch_count += 1
            existing.last_seen_at = datetime.now()
            # Also update mutable fields in case they changed
            existing.title = title
            existing.content = content
            existing.reference_url = reference_url.strip() if reference_url and reference_url.strip() else liangke_url
            existing.reference_title = reference_title
            existing.source_domain = source_domain
            existing.original_date = original_date
            # Preserve existing liangke_date if new one is later (likely a fallback to today)
            if liangke_date and (not existing.liangke_date or liangke_date <= existing.liangke_date):
                existing.liangke_date = liangke_date
            existing.tags = tags if tags else None
            if page_type:
                existing.page_type = page_type
            session.commit()
            return {'action': 'updated', 'id': existing.id, 'fetch_count': existing.fetch_count}
        else:
            # Fallback: use liangke_url as reference_url when no external reference exists
            effective_ref_url = reference_url.strip() if reference_url and reference_url.strip() else liangke_url
            article = Article(
                reference_url=effective_ref_url,
                liangke_url=liangke_url,
                title=title,
                content=content,
                original_date=original_date,
                liangke_date=liangke_date,
                source_domain=source_domain,
                reference_title=reference_title,
                tags=tags if tags else None,
                page_type=page_type,
                first_seen_at=datetime.now(),
                last_seen_at=datetime.now(),
                fetch_count=1
            )
            session.add(article)
            session.commit()
            return {'action': 'inserted', 'id': article.id}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_articles_by_date(liangke_date):
    """Get all articles for a specific liangke_date."""
    session = get_session()
    try:
        return session.query(Article).filter(Article.liangke_date == liangke_date).all()
    finally:
        session.close()


def get_article_count() -> int:
    """Get total article count."""
    session = get_session()
    try:
        return session.query(Article).count()
    finally:
        session.close()


if __name__ == '__main__':
    # Test connection
    count = get_article_count()
    print(f'Database connected. Total articles: {count}')
