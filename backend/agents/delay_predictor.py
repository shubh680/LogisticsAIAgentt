"""
Delay Predictor
---------------
Wraps the XGBoost model (risk_model.json) and LabelEncoders (encoders.joblib)
to predict the probability that a shipment will be delayed.

Features expected:
    carrier            (str)  — e.g. "BlueDart", "Swift", "Delhivery"
    weather            (str)  — e.g. "Clear", "Fog", "Heavy Rain", "Cyclone"
    warehouse_load_pct (int)  — 0–100
    traffic_density    (float)— 0–1
"""

import os
import warnings
import numpy as np
import joblib
import xgboost as xgb

warnings.filterwarnings("ignore")

# Paths relative to this file
_BASE = os.path.dirname(__file__)
_ENCODERS_PATH = os.path.join(_BASE, "..", "models", "encoders.joblib")
_MODEL_PATH    = os.path.join(_BASE, "..", "models", "risk_model.json")


class DelayPredictor:
    """Loads the ML model once and exposes a predict() method."""

    def __init__(self):
        self._encoders = joblib.load(_ENCODERS_PATH)
        self._model    = xgb.XGBClassifier()
        self._model.load_model(_MODEL_PATH)

    def predict(self, row: dict) -> float:
        """
        Predict delay probability for a single shipment row.

        Args:
            row: dict with keys carrier, weather, warehouse_load_pct, traffic_density

        Returns:
            float — probability of delay (0.0 to 1.0)
        """
        carrier_enc = self._encoders["carrier"].transform([row["carrier"]])[0]
        weather_enc = self._encoders["weather"].transform([row["weather"]])[0]

        X = np.array([[
            carrier_enc,
            weather_enc,
            int(row["warehouse_load_pct"]),
            float(row["traffic_density"]),
        ]])

        proba = self._model.predict_proba(X)[0]
        return round(float(proba[1]), 4)  # probability of class 1 (delayed)

    def predict_batch(self, rows: list[dict]) -> list[float]:
        """Predict delay probability for a list of shipment rows."""
        return [self.predict(row) for row in rows]


# Singleton — loaded once, reused across calls
_predictor: DelayPredictor | None = None


def get_predictor() -> DelayPredictor:
    global _predictor
    if _predictor is None:
        _predictor = DelayPredictor()
    return _predictor


def predict_delay(row: dict) -> float:
    """Module-level convenience function for single prediction."""
    return get_predictor().predict(row)
