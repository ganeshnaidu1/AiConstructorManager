from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Accounting MCP")

class AccountingRequest(BaseModel):
    project_id: str
    vendor_name: str

@app.post("/accounting_info")
async def accounting_info(req: AccountingRequest):
    return {
        "payment_history": [{"date": "2025-10-01", "amount": 40000}],
        "delayed_payments": 1,
        "duplicate_payments": 0,
        "budget_utilization": 0.45
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8103)
