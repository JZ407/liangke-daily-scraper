"""
Export daily MySQL database to Excel.
"""
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

DB_URL = 'mysql+pymysql://scraper:scraper123@127.0.0.1:3306/liangke_scraper?charset=utf8mb4'
OUTPUT_PATH = 'D:/Claude_code/liangke_daily/daily_export.xlsx'

engine = create_engine(DB_URL)

print('Reading articles from MySQL...')
df = pd.read_sql('SELECT * FROM articles ORDER BY liangke_date DESC, id DESC', engine)

# Convert JSON tags to string
df['tags'] = df['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x) if x else '')

print(f'Total articles: {len(df)}')
print(f'Saving to {OUTPUT_PATH}...')

df.to_excel(OUTPUT_PATH, index=False, engine='openpyxl')
print('Export complete.')
