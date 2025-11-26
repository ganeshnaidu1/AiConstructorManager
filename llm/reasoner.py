import os
from typing import Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Minimal combiner that simulates LLM reasoning. Replace with Azure OpenAI calls in production.

def combine_signals(parsed: dict, mcp_outputs: dict, anomaly: dict) -> dict:
    # Simple heuristic: base fraud score on mean anomaly and vendor risk
    vendor_risk = mcp_outputs.get("vendor", {}).get("vendor_risk_score", 0.0)
    mean_anom = anomaly.get("mean_anomaly", 0.0)
    fraud_score = min(1.0, vendor_risk * 0.6 + mean_anom * 0.9)
    explanation = (
        f"Computed fraud score {fraud_score:.2f} from vendor_risk={vendor_risk:.2f} "
        f"and anomaly_mean={mean_anom:.2f}."
    )
    return {"fraud_score": fraud_score, "explanation": explanation}
