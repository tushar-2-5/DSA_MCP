import asyncio
import sys
sys.path.insert(0, '.')
from database.connection import get_db_connection

async def audit_db():
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        rows = await cursor.fetchall()
        print("TABLES IN PUBLIC SCHEMA:")
        for r in rows:
            print(f"- {r[0]}")
        
        print("\nTABLE COLUMNS BREAKDOWN:")
        for r in rows:
            t_name = r[0]
            c_cursor = await conn.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = '{t_name}'
                ORDER BY ordinal_position;
            """)
            cols = await c_cursor.fetchall()
            print(f"\n--- Table: {t_name} ---")
            for c in cols:
                print(f"  {c[0]} ({c[1]}) nullable={c[2]}")

asyncio.run(audit_db())
