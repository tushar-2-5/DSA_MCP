import os
import uuid
import pytest
import pytest_asyncio

from database.connection import get_db_connection, close_pool
from tools.get_or_create_user import get_or_create_user
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt
from tools.study_plan import study_plan
from database.queries import get_problems_by_company

db_url = os.getenv("DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not db_url, reason="DATABASE_URL not set"),
]


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_user_lifecycle():
    test_email = f"int_user_{uuid.uuid4().hex[:8]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Integration User")
    assert user_res["status"] == "created"
    user_id = user_res["user_id"]

    try:
        report = await get_mastery_report(user_id=user_id)
        assert isinstance(report, dict)
        assert "topics" in report

        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM problems LIMIT 1;")
                prob_row = await cur.fetchone()
                assert prob_row is not None
                problem_id = str(prob_row[0])

        attempt_res = await log_attempt(
            user_id=user_id,
            problem_id=problem_id,
            code="def solution(): pass",
            outcome="pass",
        )
        assert attempt_res["status"] == "logged"
        attempt_id = attempt_res["attempt_id"]

        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM attempts WHERE id = %s;", (attempt_id,))
                found = await cur.fetchone()
                assert found is not None
    finally:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM attempts WHERE user_id = %s;", (user_id,))
                await cur.execute("DELETE FROM mastery WHERE user_id = %s;", (user_id,))
                await cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            await conn.commit()


@pytest.mark.asyncio
async def test_study_plan_integration():
    test_email = f"int_study_{uuid.uuid4().hex[:8]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Study Plan User")
    user_id = user_res["user_id"]

    try:
        plan = await study_plan(user_id, target_company="amazon")
        assert isinstance(plan, str)
        assert "Study Plan" in plan
        assert "[" in plan and "]" in plan
    finally:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            await conn.commit()


@pytest.mark.asyncio
async def test_company_filtering():
    async with get_db_connection() as conn:
        problems = await get_problems_by_company(conn, company_name="amazon", limit=10)
    assert len(problems) > 0
    for p in problems:
        tags = p.get("company_tags") or []
        assert "amazon" in [t.lower() for t in tags]


@pytest.mark.asyncio
async def test_error_recovery(monkeypatch):
    test_email = f"int_err_{uuid.uuid4().hex[:8]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Error Recovery User")
    user_id = user_res["user_id"]

    def mock_embed(self, text):
        raise RuntimeError("Simulated Gemini API failure")

    monkeypatch.setattr("embeddings.gemini_client.GeminiEmbedder.embed", mock_embed)

    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM problems LIMIT 1;")
                prob_row = await cur.fetchone()
                assert prob_row is not None
                problem_id = str(prob_row[0])

        attempt_res = await log_attempt(
            user_id=user_id,
            problem_id=problem_id,
            code="def solution(): pass",
            outcome="pass",
        )
        assert attempt_res["status"] == "logged"
        attempt_id = attempt_res["attempt_id"]

        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM attempts WHERE id = %s;", (attempt_id,))
                found = await cur.fetchone()
                assert found is not None
    finally:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM attempts WHERE user_id = %s;", (user_id,))
                await cur.execute("DELETE FROM mastery WHERE user_id = %s;", (user_id,))
                await cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            await conn.commit()
