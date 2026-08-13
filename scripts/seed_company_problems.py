import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from embeddings.gemini_client import GeminiEmbedder
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def map_topic_from_title(title: str) -> tuple[str, str]:
    t = title.lower()

    if any(k in t for k in ["window", "substring"]):
        return ("sliding-window", "Sliding Window")

    if any(k in t for k in ["lru cache", "merge two sorted lists", "linked list", "list node", "reverse list", "flatten a multilevel"]):
        return ("linked-list", "Linked List")

    if any(k in t for k in ["search in rotated", "koko eating", "binary search", "search a 2d", "first and last position", "search insert", "median of two sorted"]):
        return ("binary-search", "Binary Search")

    if any(k in t for k in ["tree", "bst", "binary tree", "inorder", "preorder", "postorder", "ancestor", "depth of", "invert", "serialize"]):
        return ("trees", "Trees")

    if any(k in t for k in ["dp", "coin change", "house robber", "climbing stairs", "longest common", "knapsack", "decode ways", "partition", "jump game", "edit distance", "maximum subarray"]):
        return ("dynamic-programming", "Dynamic Programming")

    if any(k in t for k in ["graph", "islands", "course schedule", "word ladder", "network", "dijkstra", "bipartite", "clone graph", "cheapest flights"]):
        return ("graphs", "Graphs")

    if any(k in t for k in ["stack", "queue", "parentheses", "expression", "histogram", "next greater"]):
        return ("stack-queue", "Stack & Queue")

    if any(k in t for k in ["heap", "median", "k frequent", "priority", "kth largest", "kth smallest"]):
        return ("heap-priority-queue", "Heap & Priority Queue")

    if any(k in t for k in ["permutation", "combination", "subset", "n-queens", "sudoku", "word search"]):
        return ("backtracking", "Backtracking")

    if any(k in t for k in ["two sum", "3sum", "4sum", "trapping rain water", "container with most water"]):
        return ("two-pointers", "Two Pointers")

    if any(k in t for k in ["move zeroes", "array", "subarray", "duplicate", "matrix", "product of", "rotate image", "sort colors"]):
        return ("arrays-hashing", "Arrays & Hashing")

    if any(k in t for k in ["string", "anagram", "palindrome", "valid ip"]):
        return ("strings", "Strings")

    return ("arrays-hashing", "Arrays & Hashing")


def find_csv_file() -> Path:
    candidates = [
        Path(r"C:\Users\KIIT\Downloads\all_company_leetcode_questions_deduplicated.csv"),
        Path(__file__).parent.parent / "all_company_leetcode_questions_deduplicated.csv",
        Path(__file__).parent.parent / "data" / "all_company_leetcode_questions_deduplicated.csv",
        Path("all_company_leetcode_questions_deduplicated.csv"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Could not locate all_company_leetcode_questions_deduplicated.csv in Downloads or project root.")


async def main():
    csv_path = find_csv_file()
    logger.info(f"Loading LeetCode company problems from CSV: {csv_path}")

    embedder = None
    try:
        embedder = GeminiEmbedder()
    except Exception as e:
        logger.warning(f"GeminiEmbedder disabled: {e}")

    updated_count = 0
    inserted_count = 0
    embedded_count = 0

    async with get_db_connection() as conn:
        # Pre-cache topics into memory
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, slug FROM topics;")
            topic_rows = await cur.fetchall()
            topic_cache = {r["slug"]: str(r["id"]) for r in topic_rows}

        # Pre-cache existing problem titles -> id into memory for speed
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, title FROM problems;")
            existing_rows = await cur.fetchall()
            existing_map = {r["title"].lower(): str(r["id"]) for r in existing_rows}

        logger.info(f"Pre-cached {len(topic_cache)} topics and {len(existing_map)} existing problems.")

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader, 1):
                raw_id = row.get("ID", "").strip()
                title = row.get("Title", "").strip()
                raw_diff = row.get("Difficulty", "").strip()
                raw_acc = row.get("Acceptance %", "").strip()
                raw_count = row.get("Company Count", "").strip()
                raw_companies = row.get("Companies Asking", "").strip()
                url = row.get("URL", "").strip()

                if not title:
                    continue

                leetcode_id = int(raw_id) if raw_id.isdigit() else 0
                difficulty = raw_diff.lower() if raw_diff else "medium"
                if difficulty not in ("easy", "medium", "hard"):
                    difficulty = "medium"

                try:
                    acceptance_rate = float(raw_acc.replace("%", "").strip())
                except (ValueError, AttributeError):
                    acceptance_rate = 0.0

                try:
                    company_count = int(raw_count)
                except (ValueError, TypeError):
                    company_count = 0

                company_tags = [c.strip().lower() for c in raw_companies.split(",") if c.strip()]

                prob_id = existing_map.get(title.lower())

                if prob_id:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            UPDATE problems 
                            SET company_tags = %s,
                                company_count = %s,
                                acceptance_rate = %s,
                                leetcode_id = %s,
                                url = COALESCE(%s, url)
                            WHERE id = %s;
                            """,
                            (company_tags, company_count, acceptance_rate, leetcode_id, url or None, prob_id),
                        )
                    updated_count += 1
                else:
                    topic_slug, topic_display_name = map_topic_from_title(title)
                    topic_id = topic_cache.get(topic_slug)

                    if not topic_id:
                        async with conn.cursor(row_factory=dict_row) as cur:
                            await cur.execute(
                                "INSERT INTO topics (slug, display_name) VALUES (%s, %s) ON CONFLICT (slug) DO UPDATE SET display_name = EXCLUDED.display_name RETURNING id;",
                                (topic_slug, topic_display_name),
                            )
                            row_t = await cur.fetchone()
                            topic_id = str(row_t["id"])
                            topic_cache[topic_slug] = topic_id

                    statement = f"LeetCode problem #{leetcode_id}: {title}. Practice problem frequently asked in technical interviews."

                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            """
                            INSERT INTO problems (title, statement, difficulty, topic_id, source, url, company_tags, company_count, acceptance_rate, leetcode_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id;
                            """,
                            (
                                title,
                                statement,
                                difficulty,
                                topic_id,
                                "leetcode",
                                url or f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}",
                                company_tags,
                                company_count,
                                acceptance_rate,
                                leetcode_id,
                            ),
                        )
                        inserted_row = await cur.fetchone()
                        prob_id = str(inserted_row["id"])
                        existing_map[title.lower()] = prob_id
                    inserted_count += 1

                    # Generate Gemini embedding for newly inserted problems if embedder is active (limit first 50 to avoid hitting API rate limits)
                    if embedder and embedder.api_key and embedded_count < 50:
                        try:
                            embed_text = f"{title} - {topic_slug} - {difficulty}"
                            vector = embedder.embed(embed_text)
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    "INSERT INTO embeddings (source_type, source_id, embedding) VALUES ('problem', %s, %s);",
                                    (prob_id, str(vector)),
                                )
                            embedded_count += 1
                        except Exception as e:
                            logger.debug(f"Skipping embedding for '{title}': {e}")

                if i % 250 == 0:
                    await conn.commit()
                    logger.info(f"Processed {i} problems so far... (Updated: {updated_count}, Inserted: {inserted_count})")

        await conn.commit()

    await close_pool()
    print(f"Updated {updated_count} problems, Inserted {inserted_count} new problems")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
