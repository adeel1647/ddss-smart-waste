import pytest

@pytest.mark.anyio
async def test_telemetry_rejects_missing_bin(client):
    payload = {
        "fill_level": 55.0,
        "battery_level": 88.0
    }

    response = await client.post("/api/v1/bins/999999/telemetry", json=payload)
    assert response.status_code in (404, 400, 422)