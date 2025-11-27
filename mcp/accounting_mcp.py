from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from functools import lru_cache
import datetime

app = FastAPI(title="Accounting MCP")


class AccountingRequest(BaseModel):
    project_id: str
    vendor_name: str


@lru_cache(maxsize=256)
def _seed_accounting():
    # Replace with real accounting DB in production
    return {
        "proj-123": {
            "example vendor": [
                {"date": "2025-10-01", "amount": 40000, "paid": True},
                {"date": "2025-08-15", "amount": 42000, "paid": True},
            ],
            "risky trader": [
                {"date": "2025-11-01", "amount": 100000, "paid": False}
            ]
        }
    }


@app.post("/accounting_info")
async def accounting_info(req: AccountingRequest):
    if not req.project_id or not req.vendor_name:
        raise HTTPException(status_code=400, detail="project_id and vendor_name are required")

    store = _seed_accounting()
    project = store.get(req.project_id, {})
    # case-insensitive match
    history = []
    for k, v in project.items():
        if k.lower() == req.vendor_name.lower() or k.lower() in req.vendor_name.lower() or req.vendor_name.lower() in k.lower():
            history = v
            break

    # Convert history to normalized list
    payment_history = []
    delayed = 0
    duplicates = 0
    seen_amounts = set()
    for entry in history:
        payment_history.append({"date": entry["date"], "amount": entry["amount"], "paid": entry.get("paid", False)})
        if not entry.get("paid", False):
            delayed += 1
        # simple duplicate heuristic: same amount earlier
        if entry["amount"] in seen_amounts:
            duplicates += 1
        seen_amounts.add(entry["amount"])

    # Budget utilization: synthetic example
    budget_utilization = 0.45 if payment_history else 0.0

    return {
        "project_id": req.project_id,
        "vendor_name": req.vendor_name,
        "payment_history": payment_history,
        "delayed_payments": delayed,
        "duplicate_payments": duplicates,
        "budget_utilization": budget_utilization,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8103)
