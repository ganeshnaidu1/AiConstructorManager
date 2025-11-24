from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Vendor MCP")

class VendorRequest(BaseModel):
    vendor_name: str
    project_id: str | None = None

@app.post("/vendor_info")
async def vendor_info(req: VendorRequest):
    return {
        "vendor_name": req.vendor_name,
        "number_of_previous_bills": 5,
        "average_bill_value": 45000,
        "recurrence_pattern": "monthly",
        "vendor_risk_score": 0.25
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8102)
