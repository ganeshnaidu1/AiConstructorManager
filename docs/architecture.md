# Phase 1 Architecture

See the user's architecture notes. This file summarizes components and local run guidance.

- Frontend: simple React/Streamlit (not scaffolded here)
- Backend: `backend/app/main.py` (FastAPI prototype)
- MCPs: `mcp/*` FastAPI stubs
- Anomaly: `anomaly/*` training and scoring scripts
- LLM: `llm/reasoner.py` placeholder
- Infra: `infra/schema.sql` and `local.settings.json`

Local run:

1. Start MCP stubs:
   - `uvicorn mcp.material_mcp:app --reload --port 8101`
   - `uvicorn mcp.vendor_mcp:app --reload --port 8102`
   - `uvicorn mcp.accounting_mcp:app --reload --port 8103`
2. Run backend:
   - `uvicorn backend.app.main:app --reload --port 8000`
3. Train anomaly model:
   - `python anomaly/train_model.py`
4. Use endpoints to upload PDF and fetch results.
