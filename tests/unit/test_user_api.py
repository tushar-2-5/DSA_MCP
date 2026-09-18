import pytest
from httpx import AsyncClient, ASGITransport
from server.main import app


@pytest.mark.asyncio
async def test_rest_api_user_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch existing user alex@recall.dev
        res = await client.post(
            "/api/users",
            json={"email": "alex@recall.dev", "password": "recall@demo123"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["email"] == "alex@recall.dev"
        assert data["user_id"] == "77ae399e-31ea-4a84-9fdb-23dab394f2d7"
        assert "token" in data
        assert data["created"] is False

        # 2. Get by email
        res_email = await client.get("/api/users/by-email/alex@recall.dev")
        assert res_email.status_code == 200, res_email.text
        data_email = res_email.json()
        assert data_email["email"] == "alex@recall.dev"
        assert data_email["user_id"] == "77ae399e-31ea-4a84-9fdb-23dab394f2d7"

        # 3. Get by user_id
        res_id = await client.get("/api/users/77ae399e-31ea-4a84-9fdb-23dab394f2d7")
        assert res_id.status_code == 200, res_id.text
        data_id = res_id.json()
        assert data_id["email"] == "alex@recall.dev"
        assert data_id["user_id"] == "77ae399e-31ea-4a84-9fdb-23dab394f2d7"

        # 4. Error cases
        res_invalid_email = await client.post(
            "/api/users",
            json={"email": "not-an-email"},
        )
        assert res_invalid_email.status_code == 400

        res_not_found = await client.get("/api/users/by-email/nonexistent_user_xyz@recall.dev")
        assert res_not_found.status_code == 404

        res_invalid_uuid = await client.get("/api/users/invalid-uuid-123")
        assert res_invalid_uuid.status_code == 400
