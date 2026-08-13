import os
import sys
import random
import psycopg
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.gemini_client import GeminiEmbedder

load_dotenv()

TARGET_MASTERYS = {
    "arrays-hashing": 0.82,
    "linked-list": 0.74,
    "binary-search": 0.68,
    "sliding-window": 0.61,
    "stack-queue": 0.55,
    "trees": 0.45,
    "heap-priority-queue": 0.38,
    "dynamic-programming": 0.28,
    "graphs": 0.21,
    "backtracking": 0.19,
}

ATTEMPT_SCHEDULE = [
    # topic_slug, outcome, days_ago
    # Arrays (8 attempts: 6 PASS, 1 PARTIAL, 1 FAIL)
    ("arrays-hashing", "pass", 10),
    ("arrays-hashing", "pass", 8),
    ("arrays-hashing", "pass", 6),
    ("arrays-hashing", "pass", 4),
    ("arrays-hashing", "partial", 3),
    ("arrays-hashing", "fail", 2),
    ("arrays-hashing", "pass", 1),
    ("arrays-hashing", "pass", 0),
    # Linked Lists (5 attempts: 4 PASS, 1 PARTIAL)
    ("linked-list", "pass", 15),
    ("linked-list", "pass", 12),
    ("linked-list", "pass", 9),
    ("linked-list", "partial", 6),
    ("linked-list", "pass", 3),
    # Binary Search (4 attempts: 3 PASS, 1 PARTIAL)
    ("binary-search", "pass", 14),
    ("binary-search", "pass", 10),
    ("binary-search", "partial", 7),
    ("binary-search", "pass", 2),
    # Trees (4 attempts: 2 PASS, 1 PARTIAL, 1 FAIL)
    ("trees", "pass", 18),
    ("trees", "partial", 14),
    ("trees", "fail", 8),
    ("trees", "pass", 3),
    # Dynamic Programming (5 attempts: 1 PASS, 2 PARTIAL, 2 FAIL)
    ("dynamic-programming", "fail", 20),
    ("dynamic-programming", "partial", 16),
    ("dynamic-programming", "fail", 12),
    ("dynamic-programming", "partial", 7),
    ("dynamic-programming", "pass", 2),
    # Graphs (4 attempts: 1 PASS, 1 PARTIAL, 2 FAIL)
    ("graphs", "fail", 19),
    ("graphs", "fail", 15),
    ("graphs", "partial", 10),
    ("graphs", "pass", 4),
    # Sliding Window (3 attempts: 2 PASS, 1 PARTIAL)
    ("sliding-window", "pass", 11),
    ("sliding-window", "partial", 6),
    ("sliding-window", "pass", 1),
    # Stack & Queue (2 attempts: 1 PASS, 1 PARTIAL)
    ("stack-queue", "partial", 13),
    ("stack-queue", "pass", 5),
    # Heap (2 attempts: 1 PARTIAL, 1 FAIL)
    ("heap-priority-queue", "fail", 17),
    ("heap-priority-queue", "partial", 9),
    # Backtracking (3 attempts: 0 PASS, 1 PARTIAL, 2 FAIL)
    ("backtracking", "fail", 21),
    ("backtracking", "fail", 14),
    ("backtracking", "partial", 7),
]

MISTAKES_DATA = [
    {
        "summary": "Off-by-one error in DP table initialization",
        "category": "boundary_condition",
        "topic_slug": "dynamic-programming",
        "days_ago": 12,
    },
    {
        "summary": "Not handling disconnected graph components in BFS",
        "category": "logic_error",
        "topic_slug": "graphs",
        "days_ago": 15,
    },
    {
        "summary": "Forgetting to handle null pointer in linked list traversal",
        "category": "boundary_condition",
        "topic_slug": "linked-list",
        "days_ago": 6,
    },
    {
        "summary": "Wrong base case in recursive backtracking",
        "category": "logic_error",
        "topic_slug": "backtracking",
        "days_ago": 14,
    },
    {
        "summary": "Not resetting window variables between test cases",
        "category": "sliding_window_off_by_one",
        "topic_slug": "sliding-window",
        "days_ago": 6,
    },
    {
        "summary": "Stack overflow due to missing base case in tree recursion",
        "category": "boundary_condition",
        "topic_slug": "trees",
        "days_ago": 8,
    },
    {
        "summary": "Binary search boundary off by one — using < instead of <=",
        "category": "boundary_condition",
        "topic_slug": "binary-search",
        "days_ago": 7,
    },
    {
        "summary": "Heap not properly heapified after deletion",
        "category": "logic_error",
        "topic_slug": "heap-priority-queue",
        "days_ago": 17,
    },
]


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in environment.")

    print("Connecting to live CockroachDB...", flush=True)
    now = datetime.now(timezone.utc)

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Get or Create Demo User
            cur.execute("SELECT id FROM users WHERE email = %s;", ("alex@recall.dev",))
            row = cur.fetchone()
            if row:
                user_id = str(row[0])
                print(f"✅ Demo user 'Alex Chen' (alex@recall.dev) exists. User ID: {user_id}", flush=True)
            else:
                cur.execute(
                    "INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id;",
                    ("alex@recall.dev", "Alex Chen"),
                )
                user_id = str(cur.fetchone()[0])
                print(f"✅ Created demo user 'Alex Chen' (alex@recall.dev). User ID: {user_id}", flush=True)

            # Pre-cache topics (slug -> id)
            cur.execute("SELECT slug, id FROM topics;")
            topic_rows = cur.fetchall()
            topic_map = {r[0]: str(r[1]) for r in topic_rows}

            # Pre-cache problems per topic
            topic_problems = {}
            for slug, topic_id in topic_map.items():
                cur.execute("SELECT id FROM problems WHERE topic_id = %s;", (topic_id,))
                probs = [str(r[0]) for r in cur.fetchall()]
                if probs:
                    topic_problems[slug] = probs

            # Clear existing demo data for clean idempotent re-seeding
            print("Cleaning previous attempt & mistake data for Alex Chen...", flush=True)
            cur.execute(
                """
                DELETE FROM embeddings 
                WHERE source_type = 'mistake' AND source_id IN (
                    SELECT id FROM mistakes WHERE user_id = %s
                );
                """,
                (user_id,),
            )
            cur.execute("DELETE FROM mistakes WHERE user_id = %s;", (user_id,))
            cur.execute("DELETE FROM attempts WHERE user_id = %s;", (user_id,))

            # 2. Seed 35 Attempts
            print("Seeding 35 practice attempts...", flush=True)
            attempt_map = {}  # key: (topic_slug, days_ago) -> attempt_id
            attempts_created = 0

            for topic_slug, outcome, days_ago in ATTEMPT_SCHEDULE:
                probs = topic_problems.get(topic_slug)
                if not probs:
                    # fallback to any problem
                    cur.execute("SELECT id FROM problems LIMIT 10;")
                    probs = [str(r[0]) for r in cur.fetchall()]

                prob_id = random.choice(probs)
                attempt_time = now - timedelta(days=days_ago, minutes=random.randint(10, 120))
                time_taken = random.randint(12, 45) * 60
                complexity = "O(N)" if outcome == "pass" else "O(N^2)"

                cur.execute(
                    """
                    INSERT INTO attempts (user_id, problem_id, outcome, complexity_achieved, time_taken_seconds, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, prob_id, outcome, complexity, time_taken, attempt_time),
                )
                att_id = str(cur.fetchone()[0])
                attempt_map[(topic_slug, days_ago)] = att_id
                attempts_created += 1

            print(f"✅ Created {attempts_created} attempts.", flush=True)

            # 3. Seed 8 Mistakes & Gemini Embeddings
            print("Seeding 8 mistake logs with Gemini embeddings...", flush=True)
            embedder = None
            try:
                embedder = GeminiEmbedder()
            except Exception as e:
                print(f"Warning: GeminiEmbedder init: {e}", flush=True)

            mistakes_created = 0
            embeddings_created = 0

            for m in MISTAKES_DATA:
                att_id = attempt_map.get((m["topic_slug"], m["days_ago"]))
                if not att_id:
                    # pick any attempt for user
                    cur.execute("SELECT id FROM attempts WHERE user_id = %s LIMIT 1;", (user_id,))
                    att_row = cur.fetchone()
                    att_id = str(att_row[0]) if att_row else None

                mistake_time = now - timedelta(days=m["days_ago"])
                cur.execute(
                    """
                    INSERT INTO mistakes (user_id, attempt_id, summary, category, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, att_id, m["summary"], m["category"], mistake_time),
                )
                mistake_id = str(cur.fetchone()[0])
                mistakes_created += 1

                # Generate Gemini vector embedding
                if embedder and embedder.api_key:
                    try:
                        vector = embedder.embed(m["summary"])
                        cur.execute(
                            """
                            INSERT INTO embeddings (source_type, source_id, embedding)
                            VALUES ('mistake', %s, %s);
                            """,
                            (mistake_id, str(vector)),
                        )
                        embeddings_created += 1
                    except Exception as e:
                        print(f"Error embedding mistake '{m['summary']}': {e}", flush=True)

            print(f"✅ Created {mistakes_created} mistakes with {embeddings_created} Gemini embeddings.", flush=True)

            # 4. Set Direct Topic Mastery Scores
            print("Setting target topic mastery scores...", flush=True)
            mastery_updated = 0
            for slug, target_score in TARGET_MASTERYS.items():
                topic_id = topic_map.get(slug)
                if not topic_id:
                    continue

                last_practiced = now - timedelta(days=random.randint(1, 4))
                cur.execute(
                    """
                    INSERT INTO mastery (user_id, topic_id, mastery_score, last_practiced_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, topic_id) DO UPDATE 
                    SET mastery_score = EXCLUDED.mastery_score,
                        last_practiced_at = EXCLUDED.last_practiced_at;
                    """,
                    (user_id, topic_id, target_score, last_practiced),
                )
                mastery_updated += 1

            print(f"✅ Set mastery scores for {mastery_updated} topics.", flush=True)

    print("\n" + "=" * 60, flush=True)
    print(f"🎉 DEMO USER SEED COMPLETE! User: Alex Chen (alex@recall.dev)", flush=True)
    print(f"   - User ID: {user_id}", flush=True)
    print(f"   - Attempts: {attempts_created}", flush=True)
    print(f"   - Mistakes: {mistakes_created} (Embeddings: {embeddings_created})", flush=True)
    print(f"   - Mastery Scores: {mastery_updated} topics set", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
