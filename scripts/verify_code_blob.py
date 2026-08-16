import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from database.connection import get_db_connection, close_pool

async def test():
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('''
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'attempts' 
                AND column_name IN ('code_blob', 'storage_backend')
            ''')
            print('Columns:', await cur.fetchall(), flush=True)
            
            # Check if existing attempts have code
            await cur.execute('''
                SELECT id, code_blob IS NOT NULL as has_code,
                       storage_backend
                FROM attempts LIMIT 5
            ''')
            print('Sample attempts:', await cur.fetchall(), flush=True)
    await close_pool()

if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
