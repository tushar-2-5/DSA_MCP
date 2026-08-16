import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import psycopg
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    db_url = os.getenv("DATABASE_URL")
    print(f"Connecting to database...", flush=True)
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        async with conn.cursor() as cur:
            # Add code_blob column if not exists
            await cur.execute('''
                ALTER TABLE attempts 
                ADD COLUMN IF NOT EXISTS code_blob TEXT,
                ADD COLUMN IF NOT EXISTS code_language VARCHAR(50) DEFAULT 'python',
                ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) DEFAULT 'cockroachdb'
            ''')
            print('Migration done', flush=True)
        await conn.commit()

if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())
