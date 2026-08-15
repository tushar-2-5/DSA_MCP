import sys
import asyncio
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
db = os.getenv("DATABASE_URL")

async def main():
    async with await psycopg.AsyncConnection.connect(db) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                SELECT p.id, p.title, p.company_tags, p.company_count
                FROM problems p
                WHERE 'amazon' = ANY(p.company_tags)
                ORDER BY p.company_count DESC
                LIMIT 5
            """)
            rows = await cur.fetchall()
            print("Amazon query results:")
            for r in rows:
                print(r['title'], "Contains amazon?", 'amazon' in r['company_tags'], r['company_tags'][:4])

            await cur.execute("""
                SELECT p.id, p.title, p.company_tags, p.company_count
                FROM problems p
                WHERE 'google' = ANY(p.company_tags)
                ORDER BY p.company_count DESC
                LIMIT 5
            """)
            rows_g = await cur.fetchall()
            print("\nGoogle query results:")
            for r in rows_g:
                print(r['title'], "Contains google?", 'google' in r['company_tags'], r['company_tags'][:4])

if __name__ == "__main__":
    asyncio.run(main())
