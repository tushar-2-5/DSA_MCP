import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import (
    get_topic_by_slug,
    create_topic,
    get_problem_by_title,
    create_problem,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_problems():
    data_file = Path(__file__).parent / "seed_data.json"
    if not data_file.exists():
        logger.error(f"Seed data file not found: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        problems_data = json.load(f)

    topics_created = 0
    topics_existed = 0
    problems_created = 0
    problems_existed = 0

    topic_cache = {}

    async with get_db_connection() as conn:
        for item in problems_data:
            slug = item["section"]
            display_name = item.get("display_name")

            if slug not in topic_cache:
                existing_topic = await get_topic_by_slug(conn, slug)
                if existing_topic:
                    topic_cache[slug] = existing_topic
                    topics_existed += 1
                else:
                    derived_display_name = (
                        display_name or slug.replace("-", " ").title()
                    )
                    new_topic = await create_topic(conn, slug, derived_display_name)
                    await conn.commit()
                    topic_cache[slug] = new_topic
                    topics_created += 1

        for item in problems_data:
            title = item["title"]
            existing_problem = await get_problem_by_title(conn, title)
            if existing_problem:
                problems_existed += 1
            else:
                slug = item["section"]
                topic = topic_cache[slug]
                await create_problem(
                    conn=conn,
                    title=title,
                    statement=item["statement"],
                    difficulty=item.get("difficulty"),
                    topic_id=topic.id,
                    source=item.get("source"),
                    url=item.get("url"),
                )
                await conn.commit()
                problems_created += 1

        print("==================================================")
        print("           SEED DATA EXECUTION SUMMARY            ")
        print("==================================================")
        print(f"Topics Created:          {topics_created}")
        print(f"Topics Already Existed:  {topics_existed}")
        print(f"Problems Created:        {problems_created}")
        print(f"Problems Already Existed:{problems_existed}")
        print("--------------------------------------------------")

        print("\n--- Topic Problem Counts Verification Query ---")
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT t.slug, COUNT(p.id) as problem_count
                FROM topics t
                LEFT JOIN problems p ON p.topic_id = t.id
                GROUP BY t.slug
                ORDER BY t.slug;
                """
            )
            rows = await cur.fetchall()
            for r in rows:
                print(f"  slug: {r[0]:<22} | problem_count: {r[1]}")
        print("==================================================")

    await close_pool()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_problems())
