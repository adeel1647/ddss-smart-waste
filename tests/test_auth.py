import pytest

@pytest.mark.anyio
async def test_login_success(client):
    payload = {
        "email": "admin@hull.ac.uk",
        "password": "admin123"
    }

    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data