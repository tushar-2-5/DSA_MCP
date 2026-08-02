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

