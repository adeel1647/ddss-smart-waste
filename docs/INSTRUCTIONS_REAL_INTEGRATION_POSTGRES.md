# Real Integration (PostgreSQL) — DDSS Smart Waste Backend

This backend persists:
- `bins` (metadata + location)
- `telemetry` (fill + timestamps)
- `classifications` (optional; saved when you call `/classify?bin_id=...`)
- `decision_runs` + `decision_items` (DDSS ranking outputs)
- `route_plans` + `route_trips` (routing outputs)

## 1) Local setup

### Start Postgres
```bash
docker compose up -d
```

### Configure env
Copy `.env.example` to `.env`.

### Install + run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open docs:
- http://127.0.0.1:8000/docs

## 2) Real DDSS flow (end-to-end)

### A) Register bins (one time)
POST `/api/v1/bins`
```json
{ "bin_id":"bin_1", "sector":"A", "lat":51.5074, "lon":-0.1278, "active":true }
```

### B) Ingest telemetry (repeat)
POST `/api/v1/bins/bin_1/telemetry`
```json
{ "fill_level": 72.3, "last_collection_hours": 12.0 }
```

### C) (Optional) Persist classification
POST `/api/v1/classify?bin_id=bin_1` with multipart image.

### D) Run DDSS ranking
POST `/api/v1/ddss/run`
```json
{ "sector": "A", "limit": 200 }
```

### E) Plan route from latest DDSS results
POST `/api/v1/routing/plan-latest`
```json
{
  "depot_lat": 51.5074,
  "depot_lon": -0.1278,
  "capacity": 300,
  "strategy": "priority_distance",
  "top_n": 50
}
```

## 3) Notes
- Bins with no telemetry are skipped.
- Bins with no classification are included as `predicted_class="unknown"` with default uncertainty.
- Forecast lags are built from the last 3 telemetry values stored per bin.


## Convenience endpoints (for frontend)

- `GET /api/v1/ddss/latest` returns the most recent DDSS decision run and ranked bins.
- `GET /api/v1/routing/latest` returns the most recent stored route plan and trips.
