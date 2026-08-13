import os, psycopg
from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv('DATABASE_URL')

with psycopg.connect(db_url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'problems'
            ORDER BY ordinal_position;
        """)
        cols = [r[0] for r in cur.fetchall()]
        print('Current columns:', cols)
        
        if 'company_tags' not in cols:
            print('Adding company_tags...')
            cur.execute("ALTER TABLE problems ADD COLUMN company_tags TEXT[] DEFAULT '{}'")
            print('Done.')
        
        if 'company_count' not in cols:
            print('Adding company_count...')
            cur.execute("ALTER TABLE problems ADD COLUMN company_count INTEGER DEFAULT 0")
            print('Done.')
            
        if 'acceptance_rate' not in cols:
            print('Adding acceptance_rate...')
            cur.execute("ALTER TABLE problems ADD COLUMN acceptance_rate FLOAT DEFAULT 0.0")
            print('Done.')
            
        if 'leetcode_id' not in cols:
            print('Adding leetcode_id...')
            cur.execute("ALTER TABLE problems ADD COLUMN leetcode_id INTEGER DEFAULT 0")
            print('Done.')
        
        print('Creating index...')
        cur.execute("CREATE INDEX IF NOT EXISTS idx_problems_company_count ON problems(company_count DESC)")
        print('ALL DONE!')
