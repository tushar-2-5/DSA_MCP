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
    mock_conn = AsyncMock()
    mock_get_db_connection.return_value.__aenter__.return_value = mock_conn
    mock_get_problems_filtered.return_value = [
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
    ]
    response = client.get("/api/problems?search=Two")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["problems"][0]["title"] == "Two Sum"
