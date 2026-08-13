import os
import sys
import pandas as pd
import psycopg
from dotenv import load_dotenv
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.gemini_client import GeminiEmbedder

load_dotenv()


def map_topic_from_title(title: str) -> tuple[str, str]:
    t = title.lower()

    # 1. Sliding Window: "window", "substring", "sliding"
    if any(k in t for k in ["window", "substring", "sliding"]):
        return ("sliding-window", "Sliding Window")

    # 2. Linked Lists: "linked", "list", "lru", "merge sorted"
    if any(k in t for k in ["linked", "list", "lru", "merge sorted"]):
        return ("linked-list", "Linked List")

    # 3. Binary Search: "search", "binary", "koko", "rotated"
    if any(k in t for k in ["search", "binary", "koko", "rotated"]):
        return ("binary-search", "Binary Search")

    # 4. Trees: "tree", "bst", "trie", "leaf", "root", "node"
    if any(k in t for k in ["tree", "bst", "trie", "leaf", "root", "node"]):
        return ("trees", "Trees")

    # 5. Dynamic Programming: "dp", "coin", "house robber", "climbing", "jump", "knapsack"
    if any(k in t for k in ["dp", "coin", "house robber", "climbing", "jump", "knapsack"]):
        return ("dynamic-programming", "Dynamic Programming")

    # 6. Graphs: "graph", "island", "course", "word ladder", "clone"
    if any(k in t for k in ["graph", "island", "course", "word ladder", "clone"]):
        return ("graphs", "Graphs")

    # 7. Stack & Queue: "stack", "queue", "parenthes", "bracket"
    if any(k in t for k in ["stack", "queue", "parenthes", "bracket"]):
        return ("stack-queue", "Stack & Queue")

    # 8. Heap: "heap", "median", "frequent", "kth largest"
    if any(k in t for k in ["heap", "median", "frequent", "kth largest"]):
        return ("heap-priority-queue", "Heap & Priority Queue")

    # 9. Backtracking: "permut", "combination", "subset", "backtrack"
    if any(k in t for k in ["permut", "combination", "subset", "backtrack"]):
        return ("backtracking", "Backtracking")

    # 10. Arrays: "sum", "array", "subarray", "matrix", "rotate", "spiral"
    if any(k in t for k in ["sum", "array", "subarray", "matrix", "rotate", "spiral"]):
        return ("arrays-hashing", "Arrays & Hashing")

    # Default -> Arrays
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


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    csv_path = find_csv_file()
    print(f"Reading CSV from: {csv_path}", flush=True)

    df = pd.read_csv(csv_path)
    total_rows = len(df)

    updated_count = 0
    inserted_count = 0
    embedded_count = 0
    error_count = 0

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Pre-cache topics from database
            cur.execute("SELECT slug, id FROM topics;")
            topic_rows = cur.fetchall()
            topic_map = {r[0]: str(r[1]) for r in topic_rows}

            # Pre-cache existing problems title -> id for fast lookup
            cur.execute("SELECT id, title FROM problems;")
            existing_rows = cur.fetchall()
            existing_map = {r[1].lower().strip(): str(r[0]) for r in existing_rows}

            batch_updates = []
            batch_inserts = []

            for index, row in df.iterrows():
                try:
                    raw_id = str(row.get("ID", "")).strip()
                    title = str(row.get("Title", "")).strip()
                    raw_diff = str(row.get("Difficulty", "")).strip()
                    raw_acc = str(row.get("Acceptance %", "")).strip()
                    raw_count = str(row.get("Company Count", "")).strip()
                    raw_companies = str(row.get("Companies Asking", "")).strip()
                    url = str(row.get("URL", "")).strip()

                    if not title or title.lower() == "nan":
                        continue

                    leetcode_id = int(float(raw_id)) if raw_id.replace('.', '', 1).isdigit() else 0
                    
                    difficulty = raw_diff.lower() if raw_diff and raw_diff.lower() != "nan" else "medium"
                    if difficulty not in ("easy", "medium", "hard"):
                        difficulty = "medium"

                    try:
                        acc_val = float(raw_acc.replace("%", "").strip())
                        acceptance_rate = acc_val / 100.0 if acc_val > 1.0 else acc_val
                    except (ValueError, AttributeError):
                        acceptance_rate = 0.0

                    try:
                        company_count = int(float(raw_count))
                    except (ValueError, TypeError):
                        company_count = 0

                    if raw_companies and raw_companies.lower() != "nan":
                        company_tags = [c.strip().lower() for c in raw_companies.split(",") if c.strip()]
                    else:
                        company_tags = []

                    prob_id = existing_map.get(title.lower())

                    if prob_id:
                        batch_updates.append((company_tags, company_count, acceptance_rate, leetcode_id, url if url and url.lower() != "nan" else None, prob_id))
                        updated_count += 1
                    else:
                        topic_slug, topic_display_name = map_topic_from_title(title)
                        topic_id = topic_map.get(topic_slug)

                        if not topic_id:
                            cur.execute(
                                "INSERT INTO topics (slug, display_name) VALUES (%s, %s) ON CONFLICT (slug) DO UPDATE SET display_name = EXCLUDED.display_name RETURNING id;",
                                (topic_slug, topic_display_name),
                            )
                            row_t = cur.fetchone()
                            topic_id = str(row_t[0])
                            topic_map[topic_slug] = topic_id

                        statement = f"LeetCode problem #{leetcode_id}: {title}. Practice problem frequently asked in technical interviews."
                        prob_url = url if url and url.lower() != "nan" else f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}"

                        batch_inserts.append((title, statement, difficulty, topic_id, "leetcode", prob_url, company_tags, company_count, acceptance_rate, leetcode_id))
                        inserted_count += 1

                except Exception as e:
                    error_count += 1

                row_idx = index + 1
                if row_idx % 50 == 0 or row_idx == total_rows:
                    if batch_updates:
                        cur.executemany(
                            """
                            UPDATE problems 
                            SET company_tags = %s,
                                company_count = %s,
                                acceptance_rate = %s,
                                leetcode_id = %s,
                                url = COALESCE(%s, url)
                            WHERE id = %s;
                            """,
                            batch_updates
                        )
                        batch_updates.clear()

                    if batch_inserts:
                        cur.executemany(
                            """
                            INSERT INTO problems (title, statement, difficulty, topic_id, source, url, company_tags, company_count, acceptance_rate, leetcode_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            batch_inserts
                        )
                        batch_inserts.clear()

                    print(f"Progress: {row_idx}/{total_rows} — Updated: {updated_count}, Inserted: {inserted_count}", flush=True)

            # Generate Gemini embeddings for missing problems
            embedder = None
            try:
                embedder = GeminiEmbedder()
            except Exception as e:
                pass

            if embedder and embedder.api_key:
                cur.execute(
                    """
                    SELECT p.id, p.title, t.slug 
                    FROM problems p
                    LEFT JOIN topics t ON p.topic_id = t.id
                    LEFT JOIN embeddings e ON e.source_id = p.id AND e.source_type = 'problem'
                    WHERE e.id IS NULL
                    LIMIT 50;
                    """
                )
                unembedded = cur.fetchall()
                for prob_id, prob_title, prob_slug in unembedded:
                    try:
                        embed_text = f"{prob_title} - {prob_slug or 'general'}"
                        vector = embedder.embed(embed_text)
                        cur.execute(
                            "INSERT INTO embeddings (source_type, source_id, embedding) VALUES ('problem', %s, %s);",
                            (str(prob_id), str(vector)),
                        )
                        embedded_count += 1
                    except Exception as e:
                        error_count += 1

    print(f"DONE! Updated: {updated_count}, Inserted: {inserted_count}, Embedded: {embedded_count}, Errors: {error_count}", flush=True)


if __name__ == "__main__":
    main()
