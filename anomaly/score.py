from joblib import load
import pandas as pd
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[0] / "model.joblib"

def score_line_items(line_items: list[dict]) -> dict:
    if not MODEL_PATH.exists():
        return {"anomaly_score": 0.0, "reasons": ["model-not-trained"]}
    model = load(MODEL_PATH)
    rows = []
    for li in line_items:
        price = li.get("rate")
        qty = li.get("qty")
        rows.append({"price": price, "qty": qty})
    X = pd.DataFrame(rows)
    preds = model.decision_function(X)
    # lower score => more anomalous in IsolationForest
    normalized = (preds.max() - preds) / (preds.max() - preds.min() + 1e-9)
    return {"anomaly_scores": normalized.tolist(), "mean_anomaly": float(normalized.mean())}

if __name__ == "__main__":
    sample = [{"rate":350, "qty":50}, {"rate":1000, "qty":5}]
    print(score_line_items(sample))
