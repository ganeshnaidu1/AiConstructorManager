AI Construction Bill Verification & Fraud Detection - Phase 1

Structure scaffold for Phase 1 MVP. Run the backend locally for development.

- `backend/`: FastAPI prototype with endpoints to upload bills and fetch results.
- `mcp/`: Microservice stubs for Material, Vendor, Accounting.
- `anomaly/`: Training and scoring scripts for anomaly detection.
- `llm/`: LLM wrapper (placeholder) for reasoning.
- `infra/`: DB schema and local settings.
- `docs/`: Architecture notes.

Quick start (macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
