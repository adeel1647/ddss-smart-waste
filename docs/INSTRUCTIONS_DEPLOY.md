# DDSS Smart Waste — Backend Deployment Instructions

This repo contains:
- A FastAPI backend (`app/`) exposing APIs for:
  - image classification (TensorFlow/Keras)
  - fill-level forecasting (RandomForest `.pkl`)
  - DDSS bin processing (priority score + alerts)
  - routing optimization (capacity constrained; haversine)

## 1) Local run (Windows / macOS / Linux)

### Create venv
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Install deps
```bash
pip install -r requirements.txt
```

### Put your models in `models/`
- `models/densenet121_final.keras` (or change env var to `.h5`)
- `models/fill_forecast_rf.pkl`

### Run
```bash
uvicorn app.main:app --reload
```

Open:
- http://127.0.0.1:8000/api/v1/health
- http://127.0.0.1:8000/docs

## 2) API summary

Base prefix: `/api/v1`

- `GET /health`
- `POST /classify` (multipart file upload: jpg/png)
- `POST /forecast` (JSON)
- `POST /ddss/process-bin` (multipart optional image + query fields)
- `POST /routing/optimize` (JSON)

## 3) Railway deployment (recommended for TensorFlow)

Use Docker deployment for consistent builds.

Steps:
1. Push this repo to GitHub.
2. Create a new Railway project -> Deploy from GitHub.
3. Railway will detect `Dockerfile` and build.
4. Set environment variables (Project -> Variables):
   - `PORT` is provided automatically by Railway.
   - If you use different model names, set:
     - `CLASSIFIER_MODEL_PATH=models/densenet121_final.keras`
     - `FORECAST_MODEL_PATH=models/fill_forecast_rf.pkl`
   - CORS:
     - set `CORS_ORIGINS=["https://YOUR-VERCEL-APP.vercel.app"]`

Notes:
- If your TF model file is too large, store it in S3 and download at container startup
  (see `app/services/model_store.py` pattern; implement a download step in startup).

## 4) Frontend (Vercel)

In your frontend:
- Set `NEXT_PUBLIC_API_BASE_URL` to your Railway URL, e.g. `https://your-service.up.railway.app`
- Call endpoints with `${NEXT_PUBLIC_API_BASE_URL}/api/v1/...`

## 5) Common issues

### TensorFlow: `module 'tensorflow' has no attribute 'keras'`
Usually caused by:
- a local file/folder named `tensorflow.py` or `tensorflow/` shadowing the library
- wrong interpreter (not using your venv)

Quick check:
```python
import tensorflow as tf
print(tf.__file__)
print(hasattr(tf, "keras"))
```

If `tf.__file__` is not inside `venv/Lib/site-packages/tensorflow`, you have shadowing.

### Memory
TensorFlow models can exceed free-tier memory. If deployments crash:
- reduce image model size, or
- move to a plan with >= 1GB RAM.
