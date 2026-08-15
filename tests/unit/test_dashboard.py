import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from web.app import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_landing_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Your AI coding practice has amnesia." in response.text
    assert "Recall fixes that." in response.text
    assert "Mastery Decay Engine" in response.text
    assert "Recurring Mistake Detector" in response.text
    assert "Vector Recommendations" in response.text


@patch("web.routes.auth.get_db_connection")
@patch("web.routes.auth.get_user_with_password_by_email", new_callable=AsyncMock)
def test_login_flow(mock_get_user_with_password, mock_get_db_connection, client):
    mock_conn = AsyncMock()
    mock_get_db_connection.return_value.__aenter__.return_value = mock_conn
    mock_get_user_with_password.return_value = {
        "id": "12345678-1234-5678-1234-567812345678",
        "email": "test@example.com",
        "display_name": "Test User",
        "password_hash": "$2b$04$i8/yqC9J5b8wV6X2e2J2e.wKzV2c9U1g6Z8Q7R6S5T4U3V2W1X0Y",
    }

    with patch("web.routes.auth.verify_password", return_value=True):
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "secretpassword"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"
        assert "session" in response.headers.get("set-cookie", "").lower()


@patch("web.routes.auth.get_db_connection")
@patch("web.routes.auth.get_user_with_password_by_email", new_callable=AsyncMock)
@patch("web.routes.auth.update_user_password_hash", new_callable=AsyncMock)
def test_login_flow_null_password(mock_update_pass, mock_get_user, mock_get_db, client):
    mock_conn = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_conn
    mock_get_user.return_value = {
        "id": "12345678-1234-5678-1234-567812345678",
        "email": "olduser@example.com",
        "display_name": "Old User",
        "password_hash": None,
    }

    response = client.post(
        "/login",
        data={"email": "olduser@example.com", "password": "newpassword123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "session" in response.headers.get("set-cookie", "").lower()
    mock_update_pass.assert_called_once()


@patch("web.routes.auth.get_db_connection")
@patch("web.routes.auth.get_user_with_password_by_email", new_callable=AsyncMock)
@patch("web.routes.auth.create_user_with_password", new_callable=AsyncMock)
def test_signup_flow(mock_create_user, mock_get_user, mock_get_db, client):
    mock_conn = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_conn
    mock_get_user.return_value = None
    mock_create_user.return_value = {
        "id": "12345678-1234-5678-1234-567812345678",
        "email": "newuser@example.com",
        "display_name": "New User",
    }

    response = client.post(
        "/signup",
        data={"display_name": "New User", "email": "newuser@example.com", "password": "newpassword123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "session" in response.headers.get("set-cookie", "").lower()


@patch("web.routes.dashboard.get_mastery_report", new_callable=AsyncMock)
def test_api_mastery(mock_get_mastery_report, client):
    mock_get_mastery_report.return_value = {
        "topics": [{"slug": "arrays-hashing", "mastery_score": 0.5, "last_practiced_at": None}]
    }
    response = client.get("/api/mastery?user_id=12345678-1234-5678-1234-567812345678")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert data["topics"][0]["slug"] == "arrays-hashing"
    assert data["topics"][0]["mastery_score"] == 0.0


@patch("web.routes.dashboard.suggest_next_problem", new_callable=AsyncMock)
def test_api_suggest(mock_suggest_next_problem, client):
    mock_suggest_next_problem.return_value = {
        "recommendation": {"id": "p1", "title": "Two Sum", "difficulty": "Easy"},
        "targeted_topic": "arrays-hashing",
        "mastery_score": 0.2,
        "reason": "Weak topic test",
    }
    response = client.get("/api/suggest?user_id=12345678-1234-5678-1234-567812345678")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["title"] == "Two Sum"


@patch("web.routes.problems.get_db_connection")
@patch("web.routes.problems.get_problems_filtered", new_callable=AsyncMock)
def test_api_problems(mock_get_problems_filtered, mock_get_db_connection, client):
    from web.auth import require_login
    mock_conn = AsyncMock()
    mock_get_db_connection.return_value.__aenter__.return_value = mock_conn
    mock_user = {"user_id": "12345678-1234-5678-1234-567812345678"}
    app.dependency_overrides[require_login] = lambda: mock_user
    mock_get_problems_filtered.return_value = (
        [
            {
                "id": "p1",
                "title": "Two Sum",
                "statement": "Find target sum",
                "difficulty": "Easy",
                "topic_slug": "arrays-hashing",
                "study_priority": "high",
                "company_tags": ["google", "amazon"],
                "company_count": 2,
                "acceptance_rate": 50.0,
                "leetcode_id": 1,
            }
        ],
        1,
    )
    try:
        response = client.get("/api/problems?search=Two&page=1&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["limit"] == 50
        assert data["total_pages"] == 1
        assert data["has_next"] is False
        assert data["has_prev"] is False
        assert data["problems"][0]["title"] == "Two Sum"
    finally:
        app.dependency_overrides.pop(require_login, None)


@patch("tools.study_plan.study_plan", new_callable=AsyncMock)
@patch("tools.get_mastery_report.get_mastery_report", new_callable=AsyncMock)
@patch("tools.suggest_next_problem.suggest_next_problem", new_callable=AsyncMock)
@patch("tools.flag_recurring_mistake.flag_recurring_mistake", new_callable=AsyncMock)
def test_api_ask(
    mock_flag_recurring_mistake,
    mock_suggest_next_problem,
    mock_get_mastery_report,
    mock_study_plan,
    client,
):
    from web.auth import require_login
    mock_user = {"user_id": "12345678-1234-5678-1234-567812345678"}
    app.dependency_overrides[require_login] = lambda: mock_user
    try:
        mock_study_plan.return_value = "7-Day Amazon Plan"
        mock_get_mastery_report.return_value = {"topics": []}
        mock_suggest_next_problem.return_value = {"recommendation": "Two Sum"}
        mock_flag_recurring_mistake.return_value = "No mistakes found"

        # Case 1: Company + study plan
        res1 = client.post("/api/ask", json={"question": "Give me an Amazon study plan"})
        assert res1.status_code == 200
        assert res1.json()["answer"] == "7-Day Amazon Plan"

        # Case 4: Mastery / progress
        res2 = client.post("/api/ask", json={"question": "Show my progress"})
        assert res2.status_code == 200
        assert "topics" in str(res2.json()["answer"])
    finally:
        app.dependency_overrides.pop(require_login, None)


@patch("web.routes.dashboard.get_db_connection")
@patch("web.routes.dashboard.get_user_streak", new_callable=AsyncMock)
def test_api_streak(mock_get_user_streak, mock_get_db_connection, client):
    from web.auth import require_login
    mock_conn = AsyncMock()
    mock_get_db_connection.return_value.__aenter__.return_value = mock_conn
    mock_user = {"user_id": "12345678-1234-5678-1234-567812345678"}
    app.dependency_overrides[require_login] = lambda: mock_user
    mock_get_user_streak.return_value = {
        "current_streak": 3,
        "longest_streak": 5,
        "last_practiced": "2026-08-15",
        "practiced_today": True,
    }
    try:
        res = client.get("/api/streak")
        assert res.status_code == 200
        data = res.json()
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "practiced_today" in data
        assert "last_practiced" in data
        assert data["current_streak"] == 3
        assert data["longest_streak"] == 5
        assert data["practiced_today"] is True
    finally:
        app.dependency_overrides.pop(require_login, None)


@patch("web.routes.history.get_db_connection")
@patch("web.routes.history.get_user_attempt_history", new_callable=AsyncMock)
def test_api_history(mock_get_history, mock_db_conn, client):
    from web.auth import require_login
    mock_conn = AsyncMock()
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    mock_user = {"user_id": "12345678-1234-5678-1234-567812345678"}
    app.dependency_overrides[require_login] = lambda: mock_user
    mock_get_history.return_value = [
        {
            "id": "att1",
            "problem_id": "p1",
            "title": "Two Sum",
            "difficulty": "Easy",
            "topic_slug": "arrays-hashing",
            "url": "https://leetcode.com/problems/two-sum",
            "outcome": "pass",
            "time_taken_seconds": 900,
            "time_taken_mins": 15,
            "complexity_achieved": "O(N)",
            "notes": "",
            "created_at": "2026-08-15T10:00:00Z",
        }
    ]
    try:
        res = client.get("/api/history")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Two Sum"
    finally:
        app.dependency_overrides.pop(require_login, None)


@patch("web.routes.topics.get_db_connection")
@patch("web.routes.topics.get_topic_detail", new_callable=AsyncMock)
def test_api_topic_detail(mock_get_topic_detail, mock_db_conn, client):
    from web.auth import require_login
    mock_conn = AsyncMock()
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    mock_user = {"user_id": "12345678-1234-5678-1234-567812345678"}
    app.dependency_overrides[require_login] = lambda: mock_user
    mock_get_topic_detail.return_value = {
        "topic": "Arrays & Hashing",
        "mastery_score": 0.74,
        "total_problems": 45,
        "attempted": 12,
        "solved": 8,
        "problems": [
            {
                "id": "p1",
                "title": "Two Sum",
                "difficulty": "Easy",
                "url": "https://leetcode.com/problems/two-sum",
                "your_attempts": 3,
                "best_outcome": "solved",
                "last_attempted": "2026-08-13",
            }
        ],
    }
    try:
        res = client.get("/api/topic/arrays-hashing")
        assert res.status_code == 200
        data = res.json()
        assert "topic" in data
        assert "problems" in data
        assert data["topic"] == "Arrays & Hashing"
        assert len(data["problems"]) == 1
    finally:
        app.dependency_overrides.pop(require_login, None)





