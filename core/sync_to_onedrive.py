"""
Sync all databases to OneDrive shared folder for colleagues.
- MySQL daily DB → exported to SQLite (portable)
- institutions.db → copied
- historical_v3.db → copied
"""
import os, sys, shutil, sqlite3
from datetime import datetime

ONEDRIVE_DIR = 'C:/Users/zhouj/OneDrive/liangke_database'

# Source paths
INSTITUTION_DB = 'D:/Claude_code/institution_news/institutions.db'
HISTORICAL_DB = 'D:/Claude_code/liangke_historical/historical_final.db'

# MySQL config
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'user': 'scraper',
    'password': 'scraper123',
    'database': 'liangke_scraper',
    'charset': 'utf8mb4',
}


def sync_mysql_to_sqlite():
    """Export MySQL daily DB to SQLite for portability."""
    try:
        import pymysql
    except ImportError:
        print('[SYNC] pymysql not installed, skipping MySQL sync')
        return

    dst = os.path.join(ONEDRIVE_DIR, 'liangke_daily.db')
    tmp = dst + '.tmp'

    conn_mysql = pymysql.connect(**MYSQL_CONFIG)
    conn_sqlite = sqlite3.connect(tmp)

    # Get all MySQL tables
    cur = conn_mysql.cursor()
    cur.execute('SHOW TABLES')
    tables = [r[0] for r in cur.fetchall()]

    for table in tables:
        # Get columns
        cur.execute(f'DESCRIBE {table}')
        cols = [(r[0], r[1]) for r in cur.fetchall()]

        # Create table in SQLite
        col_defs = []
        for name, col_type in cols:
            t = col_type.lower()
            if 'int' in t:
                sql_type = 'INTEGER'
            elif 'float' in t or 'double' in t:
                sql_type = 'REAL'
            elif 'text' in t or 'json' in t or 'char' in t:
                sql_type = 'TEXT'
            elif 'datetime' in t or 'timestamp' in t:
                sql_type = 'TEXT'
            else:
                sql_type = 'TEXT'
            col_defs.append(f'[{name}] {sql_type}')
        conn_sqlite.execute(f'CREATE TABLE IF NOT EXISTS [{table}] ({", ".join(col_defs)})')

        # Copy data
        cur.execute(f'SELECT * FROM {table}')
        col_names = [c[0] for c in cols]
        placeholders = ','.join(['?'] * len(col_names))
        rows = cur.fetchall()
        if rows:
            conn_sqlite.executemany(
                f'INSERT OR REPLACE INTO [{table}] ({",".join(col_names)}) VALUES ({placeholders})',
                rows
            )
        conn_sqlite.commit()

    conn_mysql.close()
    conn_sqlite.close()

    # Atomic replace
    if os.path.exists(tmp):
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(tmp, dst)
        print(f'[SYNC] MySQL → {dst}')


def sync_file(src, filename):
    """Copy a SQLite file to OneDrive."""
    if not os.path.exists(src):
        print(f'[SYNC] SKIP {filename}: source not found')
        return
    dst = os.path.join(ONEDRIVE_DIR, filename)
    shutil.copy2(src, dst)
    print(f'[SYNC] {src} → {dst}')


def sync_all():
    """Sync all databases to OneDrive."""
    os.makedirs(ONEDRIVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[SYNC] === {timestamp} ===')

    sync_mysql_to_sqlite()
    sync_file(INSTITUTION_DB, 'institutions.db')
    sync_file(HISTORICAL_DB, 'historical_final.db')

    # Write last sync time
    with open(os.path.join(ONEDRIVE_DIR, 'last_sync.txt'), 'w') as f:
        f.write(timestamp)
    print(f'[SYNC] Done\n')


if __name__ == '__main__':
    sync_all()
