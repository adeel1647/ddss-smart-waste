import pytest

@pytest.mark.anyio
async def test_get_bins(client):
    response = await client.get("/api/v1/bins")
    assert response.status_code == 200
    assert isinstance(response.json(), list)