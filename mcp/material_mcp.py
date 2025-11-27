from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from functools import lru_cache
from typing import Optional
import re

app = FastAPI(title="Material Price MCP")


class MaterialRequest(BaseModel):
    material_name: str
    location: Optional[str] = None


@lru_cache(maxsize=256)
def _load_catalog():
    # Simple in-memory catalog. Replace with DB or external API in production.
    return {
        "cement": {"avg": 385.0, "min": 300.0, "max": 450.0},
        "sand": {"avg": 120.0, "min": 100.0, "max": 150.0},
        "steel": {"avg": 52000.0, "min": 48000.0, "max": 56000.0},
        "gravel": {"avg": 85.0, "min": 70.0, "max": 120.0}
    }


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    # simple token matching
    for key in _load_catalog().keys():
        if key in name:
            return key
    # fallback: return first token
    return name.split()[0]


@app.post("/material_price")
async def material_price(req: MaterialRequest):
    if not req.material_name:
        raise HTTPException(status_code=400, detail="material_name is required")

    catalog = _load_catalog()
    key = _normalize_name(req.material_name)
    if key in catalog:
        entry = catalog[key]
        # simple location adjustment: urban -> +5%, remote -> +10% (example)
        loc_adj = 0.0
        if req.location:
            loc = req.location.lower()
            if "remote" in loc or "rural" in loc:
                loc_adj = 0.10
            elif "urban" in loc or "city" in loc:
                loc_adj = 0.05

        avg_price = round(entry["avg"] * (1 + loc_adj), 2)
        min_price = round(entry["min"] * (1 + loc_adj), 2)
        max_price = round(entry["max"] * (1 + loc_adj), 2)
        # confidence: higher when exact match, lower for fallback guesses
        confidence = 0.95 if key == req.material_name.lower() or key in req.material_name.lower() else 0.75

        return {
            "material_name": req.material_name,
            "normalized_material": key,
            "avg_price": avg_price,
            "min_price": min_price,
            "max_price": max_price,
            "confidence": confidence,
        }

    # fallback synthetic response when material unknown
    return {
        "material_name": req.material_name,
        "normalized_material": key,
        "avg_price": 999.0,
        "min_price": 800.0,
        "max_price": 1200.0,
        "confidence": 0.4,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8101)
