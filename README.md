# ddss-smart-waste — Real Integration (PostgreSQL)

FastAPI backend with Postgres persistence for real DDSS integration.

## Run locally
```bash
docker compose up -d
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docs:
- http://127.0.0.1:8000/docs

Real flow:
- `docs/INSTRUCTIONS_REAL_INTEGRATION_POSTGRES.md`
