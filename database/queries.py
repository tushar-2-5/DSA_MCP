from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any
from uuid import UUID
import psycopg
from psycopg.rows import dict_row

from database.models import User, Topic, Problem, Mastery, Attempt


async def get_user(
    conn: psycopg.AsyncConnection, user_id: UUID | str
) -> Optional[User]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = %s",
            (str(user_id),),
        )
        row = await cur.fetchone()
        return User.model_validate(row) if row else None


async def get_user_by_email(
    conn: psycopg.AsyncConnection, email: str
) -> Optional[User]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE email = %s",
            (email.lower().strip(),),
        )
        row = await cur.fetchone()
        return User.model_validate(row) if row else None


async def get_user_with_password_by_email(
    conn: psycopg.AsyncConnection, email: str
) -> Optional[dict]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, email, display_name, password_hash, created_at FROM users WHERE email = %s",
            (email.lower().strip(),),
        )
        return await cur.fetchone()


async def create_user_with_password(
    conn: psycopg.AsyncConnection, email: str, password_hash: str, display_name: Optional[str] = None
) -> dict:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO users (email, display_name, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, email, display_name, created_at
            """,
            (email.lower().strip(), display_name, password_hash),
        )
        return await cur.fetchone()


async def update_user_password_hash(
    conn: psycopg.AsyncConnection, user_id: str, password_hash: str, display_name: Optional[str] = None
) -> None:
    async with conn.cursor() as cur:
        if display_name and display_name.strip():
            await cur.execute(
                "UPDATE users SET password_hash = %s, display_name = %s WHERE id = %s",
                (password_hash, display_name.strip(), str(user_id)),
            )
        else:
            await cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (password_hash, str(user_id)),
            )


async def create_user(
    conn: psycopg.AsyncConnection, email: str, display_name: Optional[str] = None
) -> User:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO users (email, display_name)
            VALUES (%s, %s)
            RETURNING id, email, display_name, created_at
            """,
            (email, display_name),
        )
        row = await cur.fetchone()
        return User.model_validate(row)


async def get_topic_by_slug(
    conn: psycopg.AsyncConnection, slug: str
) -> Optional[Topic]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, slug, display_name FROM topics WHERE slug = %s",
            (slug,),
        )
        row = await cur.fetchone()
        return Topic.model_validate(row) if row else None


async def create_topic(
    conn: psycopg.AsyncConnection, slug: str, display_name: str
) -> Topic:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO topics (slug, display_name)
            VALUES (%s, %s)
            ON CONFLICT (slug) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id, slug, display_name
            """,
            (slug, display_name),
        )
        row = await cur.fetchone()
        return Topic.model_validate(row)


async def get_mastery_row(
    conn: psycopg.AsyncConnection, user_id: UUID | str, topic_id: UUID | str
) -> Optional[Mastery]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT user_id, topic_id, mastery_score, last_practiced_at
            FROM mastery
            WHERE user_id = %s AND topic_id = %s
            """,
            (str(user_id), str(topic_id)),
        )
        row = await cur.fetchone()
        return Mastery.model_validate(row) if row else None


async def upsert_mastery(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    topic_id: UUID | str,
    mastery_score: float,
    last_practiced_at: Optional[datetime] = None,
) -> Mastery:
    if last_practiced_at is None:
        last_practiced_at = datetime.now(timezone.utc)

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO mastery (user_id, topic_id, mastery_score, last_practiced_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, topic_id)
            DO UPDATE SET
                mastery_score = EXCLUDED.mastery_score,
                last_practiced_at = EXCLUDED.last_practiced_at
            RETURNING user_id, topic_id, mastery_score, last_practiced_at
            """,
            (str(user_id), str(topic_id), mastery_score, last_practiced_at),
        )
        row = await cur.fetchone()
        return Mastery.model_validate(row)


async def insert_attempt(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    problem_id: UUID | str,
    code_s3_key: Optional[str],
    outcome: str,
    complexity_achieved: Optional[str] = None,
    time_taken_seconds: Optional[int] = None,
) -> Attempt:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO attempts (user_id, problem_id, code_s3_key, outcome, complexity_achieved, time_taken_seconds)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, problem_id, code_s3_key, outcome, complexity_achieved, time_taken_seconds, created_at
            """,
            (
                str(user_id),
                str(problem_id),
                code_s3_key,
                outcome,
                complexity_achieved,
                time_taken_seconds,
            ),
        )
        row = await cur.fetchone()
        return Attempt.model_validate(row)


async def get_recent_attempts(
    conn: psycopg.AsyncConnection, user_id: UUID | str, limit: int = 10
) -> List[Attempt]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, user_id, problem_id, code_s3_key, outcome, complexity_achieved, time_taken_seconds, created_at
            FROM attempts
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (str(user_id), limit),
        )
        rows = await cur.fetchall()
        return [Attempt.model_validate(r) for r in rows]


async def get_problem(
    conn: psycopg.AsyncConnection, problem_id: UUID | str
) -> Optional[Problem]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, title, statement, difficulty, topic_id, source, url, study_priority, tags, prerequisites, interview_relevance, master_id, created_at
            FROM problems
            WHERE id = %s
            """,
            (str(problem_id),),
        )
        row = await cur.fetchone()
        return Problem.model_validate(row) if row else None


async def get_problem_by_title(
    conn: psycopg.AsyncConnection, title: str
) -> Optional[Problem]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, title, statement, difficulty, topic_id, source, url, study_priority, tags, prerequisites, interview_relevance, master_id, created_at
            FROM problems
            WHERE title = %s
            """,
            (title,),
        )
        row = await cur.fetchone()
        return Problem.model_validate(row) if row else None


async def create_problem(
    conn: psycopg.AsyncConnection,
    title: str,
    statement: str,
    difficulty: Optional[str] = None,
    topic_id: Optional[UUID | str] = None,
    source: Optional[str] = None,
    url: Optional[str] = None,
    study_priority: Optional[str] = None,
    tags: Optional[list[str]] = None,
    prerequisites: Optional[list[str]] = None,
    interview_relevance: Optional[str] = None,
    master_id: Optional[int] = None,
) -> Problem:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO problems (title, statement, difficulty, topic_id, source, url, study_priority, tags, prerequisites, interview_relevance, master_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, statement, difficulty, topic_id, source, url, study_priority, tags, prerequisites, interview_relevance, master_id, created_at
            """,
            (
                title,
                statement,
                difficulty,
                str(topic_id) if topic_id else None,
                source,
                url,
                study_priority,
                tags,
                prerequisites,
                interview_relevance,
                master_id,
            ),
        )
        row = await cur.fetchone()
        return Problem.model_validate(row)


async def get_user_mastery_report_rows(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    topic_slug: Optional[str] = None,
) -> List[dict]:
    query = """
        SELECT t.slug, m.mastery_score, m.last_practiced_at
        FROM mastery m
        JOIN topics t ON m.topic_id = t.id
        WHERE m.user_id = %s
    """
    params: List[Any] = [str(user_id)]
    if topic_slug:
        query += " AND t.slug = %s"
        params.append(topic_slug)
    query += " ORDER BY m.last_practiced_at DESC NULLS LAST"

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, params)
        return await cur.fetchall()


async def get_user_topic_masteries(
    conn: psycopg.AsyncConnection, user_id: UUID | str
) -> List[dict]:
    """Get topic masteries for all topics in the database for a given user,
    sorted by mastery_score ascending. Topics without a mastery row default to 0.0.
    """
    query = """
        SELECT t.id AS topic_id, t.slug, COALESCE(m.mastery_score, 0.0) AS mastery_score
        FROM topics t
        LEFT JOIN mastery m ON t.id = m.topic_id AND m.user_id = %s
        ORDER BY mastery_score ASC, t.slug ASC
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, (str(user_id),))
        rows = await cur.fetchall()
        return [
            {
                "topic_id": str(r["topic_id"]),
                "slug": r["slug"],
                "mastery_score": float(r["mastery_score"]),
            }
            for r in rows
        ]


async def get_unattempted_problem_for_topic(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    topic_id: UUID | str,
    difficulties: List[str],
) -> tuple[Optional[Problem], bool]:
    """Find the first unattempted problem for a user in a topic within allowed difficulties.
    If none match difficulty filter, fallback to any unattempted problem in that topic.
    Returns tuple: (Problem or None, fallback_used: bool).
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.source, p.url, p.study_priority, p.tags, p.prerequisites, p.interview_relevance, p.master_id, p.created_at
            FROM problems p
            WHERE p.topic_id = %s
              AND p.difficulty = ANY(%s)
              AND p.id NOT IN (
                  SELECT a.problem_id FROM attempts a WHERE a.user_id = %s
              )
            ORDER BY p.created_at ASC
            LIMIT 1
            """,
            (str(topic_id), difficulties, str(user_id)),
        )
        row = await cur.fetchone()
        if row:
            return Problem.model_validate(row), False

        # Fallback: any unattempted problem in topic regardless of difficulty
        await cur.execute(
            """
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.source, p.url, p.study_priority, p.tags, p.prerequisites, p.interview_relevance, p.master_id, p.created_at
            FROM problems p
            WHERE p.topic_id = %s
              AND p.id NOT IN (
                  SELECT a.problem_id FROM attempts a WHERE a.user_id = %s
              )
            ORDER BY p.created_at ASC
            LIMIT 1
            """,
            (str(topic_id), str(user_id)),
        )
        row = await cur.fetchone()
        if row:
            return Problem.model_validate(row), True

        return None, False


async def get_all_problems_with_topics(
    conn: psycopg.AsyncConnection,
) -> List[dict]:
    """Fetch all problems along with their topic slug."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, t.slug as topic_slug
            FROM problems p
            JOIN topics t ON p.topic_id = t.id
            ORDER BY p.created_at ASC
            """
        )
        return await cur.fetchall()


async def get_embedding_by_source(
    conn: psycopg.AsyncConnection, source_type: str, source_id: UUID | str
) -> Optional[dict]:
    """Fetch existing embedding row by source_type and source_id."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT id, source_type, source_id, embedding, created_at
            FROM embeddings
            WHERE source_type = %s AND source_id = %s
            """,
            (source_type, str(source_id)),
        )
        return await cur.fetchone()


async def insert_embedding(
    conn: psycopg.AsyncConnection,
    source_type: str,
    source_id: UUID | str,
    embedding_vector: list[float],
) -> dict:
    """Insert a new vector embedding for a source entity."""
    vec_str = str(embedding_vector)
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO embeddings (source_type, source_id, embedding)
            VALUES (%s, %s, %s)
            RETURNING id, source_type, source_id, embedding, created_at
            """,
            (source_type, str(source_id), vec_str),
        )
        row = await cur.fetchone()
        return row


async def find_similar_past_attempts(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    query_vector: list[float],
    limit: int = 5,
) -> list[dict]:
    """Find the user's past attempts whose code embeddings are most similar
    to the query vector, using cosine distance (<->).
    """
    vec_str = str(query_vector)
    query = """
        SELECT 
            a.id AS attempt_id,
            a.outcome,
            a.complexity_achieved,
            m.summary AS mistake_summary,
            (e.embedding <-> %s) AS distance
        FROM embeddings e
        JOIN attempts a ON e.source_id = a.id
        LEFT JOIN mistakes m ON m.attempt_id = a.id
        WHERE e.source_type = 'code_submission' AND a.user_id = %s
        ORDER BY distance ASC
        LIMIT %s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, (vec_str, str(user_id), limit))
        rows = await cur.fetchall()
        return [
            {
                "attempt_id": str(r["attempt_id"]),
                "outcome": r["outcome"],
                "complexity_achieved": r["complexity_achieved"],
                "mistake_summary": r["mistake_summary"],
                "distance": float(r["distance"]),
            }
            for r in rows
        ]


async def insert_mistake(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    attempt_id: UUID | str,
    summary: str,
    category: Optional[str] = None,
) -> dict:
    """Insert a new mistake record for a failed or partial attempt."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO mistakes (user_id, attempt_id, summary, category)
            VALUES (%s, %s, %s, %s)
            RETURNING id, user_id, attempt_id, summary, category, created_at
            """,
            (str(user_id), str(attempt_id), summary, category or "logic_error"),
        )
        return await cur.fetchone()


async def find_similar_past_mistakes(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    query_vector: list[float],
    threshold: float = 0.35,
    limit: int = 3,
) -> list[dict]:
    """Find the user's past mistakes whose embeddings are most similar
    to the query vector (the code currently being written), using cosine distance (<->).
    Deduplicates by mistake category, selecting the closest mistake per category.
    """
    vec_str = str(query_vector)
    query = """
        WITH category_counts AS (
            SELECT category, COUNT(*) AS occurrences
            FROM mistakes
            WHERE user_id = %s
            GROUP BY category
        ),
        ranked_mistakes AS (
            SELECT 
                m.summary,
                m.category,
                (e.embedding <-> %s) AS distance,
                cc.occurrences,
                ROW_NUMBER() OVER (
                    PARTITION BY m.category 
                    ORDER BY (e.embedding <-> %s) ASC
                ) AS rn
            FROM embeddings e
            JOIN mistakes m ON e.source_id = m.id
            JOIN category_counts cc ON m.category = cc.category
            WHERE e.source_type = 'mistake'
              AND m.user_id = %s
        )
        SELECT 
            summary,
            category,
            distance,
            occurrences
        FROM ranked_mistakes
        WHERE rn = 1 AND distance < %s
        ORDER BY distance ASC
        LIMIT %s;
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            query,
            (
                str(user_id),
                vec_str,
                vec_str,
                str(user_id),
                threshold,
                limit,
            ),
        )
        rows = await cur.fetchall()
        return [
            {
                "summary": r["summary"],
                "category": r["category"],
                "distance": float(r["distance"]),
                "occurrences": int(r["occurrences"]),
            }
            for r in rows
        ]


async def find_most_recent_mistake_embedding(
    conn: psycopg.AsyncConnection, user_id: UUID | str, topic_id: UUID | str
) -> Optional[list[float]]:
    """
    Find the embedding vector of the most recent mistake for this user 
    in problems belonging to this topic. Returns None if no mistakes exist.
    """
    query = """
        SELECT e.embedding
        FROM mistakes m
        JOIN attempts a ON m.attempt_id = a.id
        JOIN problems p ON a.problem_id = p.id
        JOIN embeddings e ON e.source_id = m.id AND e.source_type = 'mistake'
        WHERE m.user_id = %s AND p.topic_id = %s
        ORDER BY m.created_at DESC
        LIMIT 1
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, (str(user_id), str(topic_id)))
        row = await cur.fetchone()
        if not row or row["embedding"] is None:
            return None
        emb = row["embedding"]
        if isinstance(emb, str):
            import json
            emb = json.loads(emb)
        elif not isinstance(emb, list):
            emb = list(emb)
        return [float(x) for x in emb]


async def find_similar_unattempted_problems(
    conn: psycopg.AsyncConnection,
    user_id: UUID | str,
    topic_id: UUID | str,
    allowed_difficulties: list[str],
    query_vector: list[float],
    limit: int = 5,
) -> list[dict]:
    """
    Among unattempted problems in this topic+difficulty band, rank by 
    similarity to the query vector (cosine distance ASC).
    Returns list of {id, title, difficulty, distance}.
    """
    vec_str = str(query_vector)
    query = """
        SELECT 
            p.id,
            p.title,
            p.difficulty,
            (e.embedding <-> %s) AS distance
        FROM problems p
        JOIN embeddings e ON e.source_id = p.id AND e.source_type = 'problem'
        LEFT JOIN attempts a ON a.problem_id = p.id AND a.user_id = %s AND a.outcome = 'pass'
        WHERE p.topic_id = %s
          AND p.difficulty = ANY(%s)
          AND a.id IS NULL
        ORDER BY distance ASC
        LIMIT %s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            query,
            (vec_str, str(user_id), str(topic_id), allowed_difficulties, limit),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "difficulty": r["difficulty"],
                "distance": float(r["distance"]),
            }
            for r in rows
        ]


async def get_problems_by_company(
    conn: psycopg.AsyncConnection, company_name: str, limit: int = 20
) -> List[dict]:
    """Get top problems asked by a specific company, ordered by company_count desc"""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.url,
                   p.company_tags, p.company_count, p.acceptance_rate, p.leetcode_id,
                   t.slug as topic_slug
            FROM problems p
            LEFT JOIN topics t ON p.topic_id = t.id
            WHERE EXISTS (
                SELECT 1 FROM unnest(p.company_tags) AS tag
                WHERE LOWER(tag) = LOWER(%s)
            )
            ORDER BY p.company_count DESC, p.acceptance_rate DESC
            LIMIT %s
            """,
            (company_name.strip(), limit),
        )
        return await cur.fetchall()


async def get_top_companies(
    conn: psycopg.AsyncConnection, limit: int = 30
) -> List[dict]:
    """Get list of unique companies sorted by total problem count"""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT company, COUNT(*) AS problem_count
            FROM (
                SELECT unnest(company_tags) AS company
                FROM problems
                WHERE company_tags IS NOT NULL AND array_length(company_tags, 1) > 0
            ) sub
            GROUP BY company
            ORDER BY problem_count DESC
            LIMIT %s
            """,
            (limit,),
        )
        return await cur.fetchall()


async def get_problems_filtered(
    conn: psycopg.AsyncConnection,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "company_count_desc",
    page: int = 1,
    limit: int = 50,
) -> tuple[List[dict], int]:
    """Extended version of get_problems_filtered supporting company, topic,
    difficulty, search, sorting, and pagination. Returns (problems_list, total_count)."""
    base_where = " WHERE 1=1"
    params: List[Any] = []

    if topic and topic.lower() != "all":
        base_where += " AND LOWER(t.slug) = %s"
        params.append(topic.lower())

    if difficulty and difficulty.lower() != "all":
        base_where += " AND LOWER(p.difficulty) = %s"
        params.append(difficulty.lower())

    if company and company.lower() != "all":
        base_where += " AND %s::text = ANY(p.company_tags)"
        params.append(company.lower().strip())

    if search:
        base_where += " AND (LOWER(p.title) LIKE %s OR LOWER(p.statement) LIKE %s)"
        s = f"%{search.lower().strip()}%"
        params.extend([s, s])

    order_clause = "ORDER BY p.company_count DESC, p.created_at ASC"
    if sort_by == "difficulty_easy":
        order_clause = "ORDER BY CASE LOWER(p.difficulty) WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 WHEN 'hard' THEN 3 ELSE 4 END ASC, p.company_count DESC"
    elif sort_by == "difficulty_hard":
        order_clause = "ORDER BY CASE LOWER(p.difficulty) WHEN 'hard' THEN 1 WHEN 'medium' THEN 2 WHEN 'easy' THEN 3 ELSE 4 END ASC, p.company_count DESC"
    elif sort_by == "acceptance_desc":
        order_clause = "ORDER BY p.acceptance_rate DESC, p.company_count DESC"
    elif sort_by == "acceptance_asc":
        order_clause = "ORDER BY p.acceptance_rate ASC, p.company_count DESC"
    elif sort_by == "company_count_desc":
        order_clause = "ORDER BY p.company_count DESC, p.created_at ASC"

    count_query = f"""
        SELECT COUNT(*) as total_count
        FROM problems p
        LEFT JOIN topics t ON p.topic_id = t.id
        {base_where}
    """

    offset = max(0, (page - 1) * limit)
    data_query = f"""
        SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.url,
               p.company_tags, p.company_count, p.acceptance_rate, p.leetcode_id, p.study_priority,
               t.slug as topic_slug
        FROM problems p
        LEFT JOIN topics t ON p.topic_id = t.id
        {base_where}
        {order_clause}
        LIMIT %s OFFSET %s
    """
    data_params = params + [limit, offset]

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(count_query, params)
        count_row = await cur.fetchone()
        total = count_row["total_count"] if count_row and "total_count" in count_row else 0

        await cur.execute(data_query, data_params)
        problems = await cur.fetchall()

    return problems, total


async def get_user_streak(conn: psycopg.AsyncConnection, user_id: str) -> dict:
    """
    Calculate current practice streak for a user.
    A streak day = at least 1 attempt logged that day.
    Returns: {
        "current_streak": int,
        "longest_streak": int, 
        "last_practiced": date or None,
        "practiced_today": bool
    }
    """
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT DISTINCT DATE(created_at) as practice_date
            FROM attempts
            WHERE user_id = %s
            ORDER BY practice_date DESC
        """, (str(user_id),))
        
        dates = [row[0] for row in await cur.fetchall()]
        if not dates:
            return {"current_streak": 0, "longest_streak": 0, 
                    "last_practiced": None, "practiced_today": False}
        
        today = datetime.now(timezone.utc).date()
        practiced_today = dates[0] == today
        
        # Calculate current streak
        current_streak = 0
        check_date = today if practiced_today else today - timedelta(days=1)
        
        for date in dates:
            if date == check_date:
                current_streak += 1
                check_date -= timedelta(days=1)
            elif date < check_date:
                break
        
        # Calculate longest streak
        longest = 1
        current = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        
        return {
            "current_streak": current_streak,
            "longest_streak": max(longest, current_streak),
            "last_practiced": str(dates[0]) if dates else None,
            "practiced_today": practiced_today
        }


async def get_user_attempt_history(
    conn: psycopg.AsyncConnection, user_id: str, limit: int = 100
) -> List[dict]:
    """Fetch detailed attempt history for a user ordered by created_at DESC."""
    query = """
        SELECT 
            a.id AS id,
            a.problem_id,
            p.title,
            p.difficulty,
            p.url,
            t.slug AS topic_slug,
            a.outcome,
            COALESCE(a.time_taken_seconds, 0) AS time_taken_seconds,
            a.complexity_achieved,
            COALESCE(m.summary, '') AS notes,
            a.created_at
        FROM attempts a
        JOIN problems p ON a.problem_id = p.id
        LEFT JOIN topics t ON p.topic_id = t.id
        LEFT JOIN mistakes m ON m.attempt_id = a.id
        WHERE a.user_id = %s
        ORDER BY a.created_at DESC
        LIMIT %s
    """
    import math
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, (str(user_id), limit))
        rows = await cur.fetchall()
        results = []
        for r in rows:
            created_at_val = r["created_at"]
            sec = r["time_taken_seconds"] or 0
            mins = max(1, math.ceil(sec / 60)) if sec > 0 else 0
            diff = (r["difficulty"] or "Medium").capitalize()
            results.append({
                "id": str(r["id"]),
                "problem_id": str(r["problem_id"]),
                "title": r["title"],
                "difficulty": diff,
                "topic_slug": r["topic_slug"] or "",
                "url": r["url"] or f"https://leetcode.com/problemset/all/?search={r['title'].replace(' ', '%20')}",
                "outcome": r["outcome"],
                "time_taken_seconds": sec,
                "time_taken_mins": mins,
                "complexity_achieved": r["complexity_achieved"] or "N/A",
                "notes": r["notes"],
                "created_at": created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else str(created_at_val),
            })
        return results


async def get_topic_detail(
    conn: psycopg.AsyncConnection, user_id: str, topic_slug: str
) -> dict:
    """Fetch topic details, user mastery score, and problem list with user attempt metrics."""
    topic_query = """
        SELECT t.id AS topic_id, t.slug, t.display_name,
               COALESCE(m.mastery_score, 0.0) AS mastery_score
        FROM topics t
        LEFT JOIN mastery m ON m.topic_id = t.id AND m.user_id = %s
        WHERE LOWER(t.slug) = %s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(topic_query, (str(user_id), topic_slug.lower().strip()))
        topic_row = await cur.fetchone()

        if not topic_row:
            display_name = topic_slug.replace("-", " ").title()
            return {
                "topic": display_name,
                "mastery_score": 0.0,
                "total_problems": 0,
                "attempted": 0,
                "solved": 0,
                "problems": [],
            }

        topic_id = topic_row["topic_id"]
        topic_name = topic_row["display_name"] or topic_slug.replace("-", " ").title()
        mastery_score = float(topic_row["mastery_score"] or 0.0)

        problems_query = """
            SELECT 
                p.id,
                p.title,
                p.difficulty,
                p.url,
                COUNT(a.id) AS your_attempts,
                COUNT(CASE WHEN a.outcome = 'pass' THEN 1 END) AS pass_count,
                COUNT(CASE WHEN a.outcome = 'partial' THEN 1 END) AS partial_count,
                MAX(a.created_at) AS last_attempted
            FROM problems p
            LEFT JOIN attempts a ON a.problem_id = p.id AND a.user_id = %s
            WHERE p.topic_id = %s
            GROUP BY p.id, p.title, p.difficulty, p.url
            ORDER BY (COUNT(a.id) > 0) DESC, p.title ASC
        """
        await cur.execute(problems_query, (str(user_id), str(topic_id)))
        prob_rows = await cur.fetchall()

        total_problems = len(prob_rows)
        attempted_count = 0
        solved_count = 0
        problems_list = []

        for pr in prob_rows:
            attempts_cnt = pr["your_attempts"] or 0
            pass_cnt = pr["pass_count"] or 0
            part_cnt = pr["partial_count"] or 0
            last_att = pr["last_attempted"]

            if attempts_cnt > 0:
                attempted_count += 1
            if pass_cnt > 0:
                solved_count += 1
                best_outcome = "solved"
            elif part_cnt > 0:
                best_outcome = "partial"
            elif attempts_cnt > 0:
                best_outcome = "failed"
            else:
                best_outcome = None

            diff_str = (pr["difficulty"] or "Medium").capitalize()
            url_str = pr["url"] or f"https://leetcode.com/problemset/all/?search={pr['title'].replace(' ', '%20')}"
            last_att_str = (
                last_att.strftime("%Y-%m-%d")
                if (last_att and hasattr(last_att, "strftime"))
                else (str(last_att) if last_att else None)
            )

            problems_list.append({
                "id": str(pr["id"]),
                "title": pr["title"],
                "difficulty": diff_str,
                "url": url_str,
                "your_attempts": attempts_cnt,
                "best_outcome": best_outcome,
                "last_attempted": last_att_str,
            })

        return {
            "topic": topic_name,
            "mastery_score": round(mastery_score, 2),
            "total_problems": total_problems,
            "attempted": attempted_count,
            "solved": solved_count,
            "problems": problems_list,
        }










