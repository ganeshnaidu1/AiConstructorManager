from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from functools import lru_cache
from typing import Optional
import math

app = FastAPI(title="Vendor MCP")


class VendorRequest(BaseModel):
    vendor_name: str
    project_id: Optional[str] = None


@lru_cache(maxsize=256)
def _seed_vendors():
    # Sample vendor history store; replace with real DB in prod
    return {
        "example vendor": {
            "previous_bills": [40000, 50000, 45000, 47000, 42000],
            "recurrence": "monthly",
            "blacklisted": False,
        },
        "new supplier": {"previous_bills": [], "recurrence": "none", "blacklisted": False},
        "risky trader": {"previous_bills": [100000, 95000], "recurrence": "irregular", "blacklisted": True},
    }


@app.post("/vendor_info")
async def vendor_info(req: VendorRequest):
    if not req.vendor_name:
        raise HTTPException(status_code=400, detail="vendor_name is required")

    vendors = _seed_vendors()
    key = req.vendor_name.lower()
    # simple fuzzy match
    match = None
    for k in vendors.keys():
        if k in key or key in k:
            match = k
            break

    if not match:
        # unknown vendor: treat as new with higher risk
        return {
            "vendor_name": req.vendor_name,
            "number_of_previous_bills": 0,
            "average_bill_value": None,
            "recurrence_pattern": "none",
            "vendor_risk_score": 0.6,
            "notes": "vendor not found in history; treat as medium-high risk",
        }

    data = vendors[match]
    prev = data["previous_bills"]
    num = len(prev)
    avg = sum(prev) / num if num > 0 else None
    recurrence = data.get("recurrence", "unknown")
    # heuristic risk: fewer bills => higher risk; blacklisted => 1.0
    if data.get("blacklisted"):
        risk = 1.0
    else:
        # scaled: 0 bills -> 0.6, 1-3 bills -> 0.4, >5 bills -> 0.15
        if num == 0:
            risk = 0.6
        elif num <= 3:
            risk = 0.4
        elif num <= 7:
            risk = 0.25
        else:
            risk = 0.15

    # slightly adjust based on average bill value volatility
    if avg:
        stddev = math.sqrt(sum((x - avg) ** 2 for x in prev) / num) if num > 0 else 0
        vol_factor = min(0.2, stddev / (avg + 1e-9))
        risk = min(1.0, risk + vol_factor)

    return {
        "vendor_name": req.vendor_name,
        "matched_vendor": match,
        "number_of_previous_bills": num,
        "average_bill_value": avg,
        "recurrence_pattern": recurrence,
        "vendor_risk_score": round(risk, 3),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8102)
