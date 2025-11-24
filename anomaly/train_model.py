import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from joblib import dump

# Synthetic training data for price-per-unit and qty
rng = np.random.RandomState(42)
prices = rng.normal(loc=350, scale=50, size=1000)
qtys = rng.normal(loc=50, scale=20, size=1000)

X = pd.DataFrame({"price": prices, "qty": qtys})
model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
model.fit(X)

dump(model, "anomaly/model.joblib")
print("Saved model to anomaly/model.joblib")
