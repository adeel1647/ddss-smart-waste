import pytest

@pytest.mark.anyio
async def test_ddss_latest_endpoint(client):
    response = await client.get("/api/v1/ddss/latest")
    assert response.status_code in (200, 404)