import uuid
import pytest
import pytest_asyncio

from database.connection import get_db_connection, close_pool
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt
from tools.suggest_next_problem import suggest_next_problem
from tools.get_or_create_user import get_or_create_user
from tools.get_problem_context import get_problem_context
from tools.flag_recurring_mistake import flag_recurring_mistake


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_get_or_create_user_idempotent():
    test_email = f"pytest_user_{uuid.uuid4().hex[:6]}@example.com"
    res1 = await get_or_create_user(email=test_email, display_name="Test User")
    assert res1["status"] == "created"
    user_id_1 = res1["user_id"]

    res2 = await get_or_create_user(email=test_email, display_name="Test User")
    assert res2["status"] == "existing"
    user_id_2 = res2["user_id"]

    assert user_id_1 == user_id_2

    # Clean up test user
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id_1,))
        await conn.commit()


@pytest.mark.asyncio
async def test_log_attempt_unregistered_user_id():
    random_user_id = str(uuid.uuid4())
    random_problem_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Call get_or_create_user first to register"):
        await log_attempt(
            user_id=random_user_id,
            problem_id=random_problem_id,
            code="print('hello')",
            outcome="pass",
        )


@pytest.mark.asyncio
async def test_get_mastery_report_unregistered_user_id():
    random_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Call get_or_create_user first to register"):
        await get_mastery_report(user_id=random_user_id)


@pytest.mark.asyncio
async def test_get_mastery_report_malformed_user_id():
    with pytest.raises(ValueError, match="user_id must be a valid UUID string"):
        await get_mastery_report(user_id="not-a-uuid")


@pytest.mark.asyncio
async def test_get_mastery_report_valid_user_no_mastery():
    test_email = f"pytest_report_{uuid.uuid4().hex[:6]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Report User")
    user_id = user_res["user_id"]

    result = await get_mastery_report(user_id=user_id)
    assert result == {"topics": []}

    # Clean up test user
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        await conn.commit()


@pytest.mark.asyncio
async def test_log_attempt_malformed_user_id():
    valid_problem_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="user_id and problem_id must be valid UUID strings"):
        await log_attempt(
            user_id="not-a-uuid",
            problem_id=valid_problem_id,
            code="print('hello')",
            outcome="pass",
        )


@pytest.mark.asyncio
async def test_log_attempt_malformed_problem_id():
    valid_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="user_id and problem_id must be valid UUID strings"):
        await log_attempt(
            user_id=valid_user_id,
            problem_id="not-a-uuid",
            code="print('hello')",
            outcome="pass",
        )


@pytest.mark.asyncio
async def test_suggest_next_problem_malformed_user_id():
    with pytest.raises(ValueError, match="user_id must be a valid UUID string"):
        await suggest_next_problem(user_id="not-a-uuid")


@pytest.mark.asyncio
async def test_get_problem_context_malformed_user_id():
    with pytest.raises(ValueError, match="user_id must be a valid UUID string"):
        await get_problem_context(user_id="not-a-uuid", problem_statement="Find target sum in array")


@pytest.mark.asyncio
async def test_get_problem_context_empty_problem_statement():
    valid_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="problem_statement must be a non-empty string"):
        await get_problem_context(user_id=valid_user_id, problem_statement="")

    with pytest.raises(ValueError, match="problem_statement must be a non-empty string"):
        await get_problem_context(user_id=valid_user_id, problem_statement="   ")

    with pytest.raises(ValueError, match="problem_statement must be a non-empty string"):
        await get_problem_context(user_id=valid_user_id, problem_statement=None)


@pytest.mark.asyncio
async def test_get_problem_context_unregistered_user_id():
    random_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Call get_or_create_user first to register"):
        await get_problem_context(user_id=random_user_id, problem_statement="Find target sum in array")


@pytest.mark.asyncio
async def test_flag_recurring_mistake_malformed_user_id():
    with pytest.raises(ValueError, match="user_id must be a valid UUID string"):
        await flag_recurring_mistake(user_id="not-a-uuid", code_in_progress="def test(): pass")


@pytest.mark.asyncio
async def test_flag_recurring_mistake_empty_code_in_progress():
    valid_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="code_in_progress must be a non-empty string"):
        await flag_recurring_mistake(user_id=valid_user_id, code_in_progress="")

    with pytest.raises(ValueError, match="code_in_progress must be a non-empty string"):
        await flag_recurring_mistake(user_id=valid_user_id, code_in_progress="   ")

    with pytest.raises(ValueError, match="code_in_progress must be a non-empty string"):
        await flag_recurring_mistake(user_id=valid_user_id, code_in_progress=None)


@pytest.mark.asyncio
async def test_flag_recurring_mistake_unregistered_user_id():
    random_user_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Call get_or_create_user first to register"):
        await flag_recurring_mistake(user_id=random_user_id, code_in_progress="def test(): pass")


@pytest.mark.asyncio
async def test_log_attempt_gemini_failure_fallback(monkeypatch):
    test_email = f"pytest_gemini_fail_{uuid.uuid4().hex[:6]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Gemini Fail User")
    user_id = user_res["user_id"]

    def mock_embed(self, text):
        raise RuntimeError("Gemini API network timeout")

    monkeypatch.setattr("embeddings.gemini_client.GeminiEmbedder.embed", mock_embed)

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM problems LIMIT 1;")
            prob_row = await cur.fetchone()
            prob_id = str(prob_row[0])

    res = await log_attempt(
        user_id=user_id,
        problem_id=prob_id,
        code="def solve(): pass",
        outcome="pass",
    )
    assert res["status"] == "logged"

    # Cleanup
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM attempts WHERE id = %s", (res["attempt_id"],))
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        await conn.commit()



