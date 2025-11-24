from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Material Price MCP")

class MaterialRequest(BaseModel):
    material_name: str
    location: str | None = None

@app.post("/material_price")
async def material_price(req: MaterialRequest):
    # In Phase 1, return synthetic market prices.
    return {
        "material_name": req.material_name,
        "avg_price": 350,
        "min_price": 300,
        "max_price": 400,
        "confidence": 0.85
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8101)
