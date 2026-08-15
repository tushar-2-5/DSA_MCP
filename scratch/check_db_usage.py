import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")
if not db:
    print("DATABASE_URL not set")
    exit(1)

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print("=== TABLE ROW COUNTS ===")
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}";')
            cnt = cur.fetchone()[0]
            print(f"{t} : {cnt} rows")

        cur.execute("SELECT COUNT(*) FROM embeddings;")
        print("Total embeddings:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM problems;")
        print("Total problems:", cur.fetchone()[0])
