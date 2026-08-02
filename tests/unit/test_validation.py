import uuid
import pytest
import pytest_asyncio

from database.connection import close_pool
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_get_mastery_report_malformed_user_id():
    with pytest.raises(ValueError, match="user_id must be a valid UUID string"):
        await get_mastery_report(user_id="not-a-uuid")


@pytest.mark.asyncio
async def test_get_mastery_report_valid_uuid_no_mastery():
    random_user_id = str(uuid.uuid4())
    result = await get_mastery_report(user_id=random_user_id)
    assert result == {"topics": []}


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
