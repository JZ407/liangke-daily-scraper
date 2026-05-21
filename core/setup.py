"""
量科网抓取工作流 - 初始化脚本
运行: python setup.py
"""
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def install_deps():
    print("[1/5] Installing Python dependencies...")
    req_file = os.path.join(BASE_DIR, '..', 'requirements.txt')
    if not os.path.exists(req_file):
        print("ERROR: requirements.txt not found.")
        return False
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_file])
    return result.returncode == 0


def create_dirs():
    print("[2/5] Creating project directories...")
    dirs = [
        os.path.join(BASE_DIR, '..', 'data', 'cookies'),
        os.path.join(BASE_DIR, '..', 'mysql_data'),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"  {d}")
    return True


def generate_my_ini():
    print("[3/5] Generating my.ini...")
    # Auto-detect MySQL installation
    mysql_base = None
    candidates = [
        r'C:\Program Files\MySQL\MySQL Server 8.4',
        r'C:\Program Files\MySQL\MySQL Server 8.0',
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, 'bin', 'mysqld.exe')):
            mysql_base = c
            break

    if mysql_base is None:
        print("  WARNING: MySQL installation not found in standard locations.")
        print("  Please install MySQL 8.x first, then re-run setup.py.")
        mysql_base = r'C:\Program Files\MySQL\MySQL Server 8.4'

    datadir = os.path.join(BASE_DIR, '..', 'mysql_data').replace('\\', '/')
    basedir = mysql_base.replace('\\', '/')

    ini_content = f"""[mysqld]
basedir={basedir}
datadir={datadir}
port=3306
max_connections=20
character-set-server=utf8mb4
default-storage-engine=INNODB
bind-address=127.0.0.1

[client]
port=3306
"""
    ini_path = os.path.join(BASE_DIR, '..', 'config', 'my.ini')
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)
    print(f"  Saved: {ini_path}")
    print(f"  MySQL base: {mysql_base}")
    print(f"  Data dir: {datadir}")
    return True


def init_mysql():
    print("[4/5] Initializing MySQL data directory...")
    datadir = os.path.join(BASE_DIR, '..', 'mysql_data')
    if os.path.exists(os.path.join(datadir, 'mysql')):
        print("  MySQL data directory already initialized. Skipping.")
        return True

    # Find mysqld
    mysqld = None
    for ver in ['8.4', '8.0']:
        p = rf'C:\Program Files\MySQL\MySQL Server {ver}\bin\mysqld.exe'
        if os.path.exists(p):
            mysqld = p
            break

    if mysqld is None:
        print("  ERROR: mysqld.exe not found. Please install MySQL first.")
        return False

    result = subprocess.run([mysqld, '--defaults-file=' + os.path.join(BASE_DIR, '..', 'config', 'my.ini'), '--initialize-insecure'])
    if result.returncode == 0:
        print("  MySQL data directory initialized successfully.")
        return True
    else:
        print("  ERROR: MySQL initialization failed.")
        return False


def create_db_user():
    print("[5/5] Creating database and user...")
    print("  NOTE: Please ensure MySQL is running before this step.")
    print("  You can start MySQL by running: start_mysql.bat")
    print("  Then run this script again with: python setup.py --db-only")
    return True


def setup_db_only():
    """Create database and user after MySQL is running."""
    import pymysql
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='')
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS liangke_scraper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cur.execute("CREATE USER IF NOT EXISTS 'scraper'@'localhost' IDENTIFIED BY 'scraper123';")
            cur.execute("GRANT ALL PRIVILEGES ON liangke_scraper.* TO 'scraper'@'localhost';")
            cur.execute("FLUSH PRIVILEGES;")
            conn.commit()
        print("  Database and user created successfully.")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Make sure MySQL is running and root has no password (default after --initialize-insecure).")
        return False


def main():
    if '--db-only' in sys.argv:
        setup_db_only()
        return

    print("=" * 50)
    print("量科网抓取工作流 - 初始化")
    print("=" * 50)
    print()

    install_deps()
    create_dirs()
    generate_my_ini()
    init_mysql()
    create_db_user()

    print()
    print("=" * 50)
    print("Setup complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Run start_mysql.bat to start MySQL server")
    print("  2. Run: python setup.py --db-only")
    print("  3. Log in to http://www.qtc.com.cn in Edge browser")
    print("  4. Run update_cookie.bat to extract cookies")
    print("  5. Run run_daily.bat to start scraping")


if __name__ == '__main__':
    main()
