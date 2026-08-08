from datetime import datetime, timezone
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
            (email.lower(),),
        )
        row = await cur.fetchone()
        return User.model_validate(row) if row else None


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
            SELECT id, title, statement, difficulty, topic_id, source, url, created_at
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
            SELECT id, title, statement, difficulty, topic_id, source, url, created_at
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
) -> Problem:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO problems (title, statement, difficulty, topic_id, source, url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, title, statement, difficulty, topic_id, source, url, created_at
            """,
            (
                title,
                statement,
                difficulty,
                str(topic_id) if topic_id else None,
                source,
                url,
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
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.source, p.url, p.created_at
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
            SELECT p.id, p.title, p.statement, p.difficulty, p.topic_id, p.source, p.url, p.created_at
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




