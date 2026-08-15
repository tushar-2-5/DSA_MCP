import os, sys, asyncio, logging
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recall.decay")

async def run_decay():
    from database.connection import get_db_connection, close_pool
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT m.user_id, m.topic_id, m.mastery_score,
                       MAX(a.created_at) as last_attempt
                FROM mastery m
                LEFT JOIN attempts a ON a.user_id = m.user_id
                LEFT JOIN problems p ON a.problem_id = p.id 
                    AND p.topic_id = m.topic_id
                GROUP BY m.user_id, m.topic_id, m.mastery_score
            """)
            rows = await cur.fetchall()
            updated = 0
            now = datetime.now(timezone.utc)
            for row in rows:
                user_id, topic_id, mastery_score, last_attempt = row
                if last_attempt is None:
                    continue
                days_elapsed = (now - last_attempt).days
                if days_elapsed <= 0:
                    continue
                decayed = float(mastery_score) * (0.5 ** (days_elapsed / 14))
                decayed = max(0.05, min(1.0, decayed))
                await cur.execute(
                    "UPDATE mastery SET mastery_score = %s WHERE user_id = %s AND topic_id = %s",
                    (decayed, str(user_id), str(topic_id))
                )
                updated += 1
            await conn.commit()
            logger.info(f"Decay applied: {updated} mastery records updated")
            print(f"DONE! Updated {updated} mastery records out of {len(rows)} total")
    await close_pool()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_decay())
