import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv('DATABASE_URL')
with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email, id FROM users WHERE email IN ('alex@recall.dev', 'tushar.7694.7@gmail.com')")
        for row in cur.fetchall():
            print(row[0], '->', row[1], flush=True)
