"""Forecasting with statsmodels (Holt's linear trend) - NOT the LLM."""
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

DISCLAIMER = "Forecast is a statistical estimate based on past data, not a guarantee."


def forecast_monthly(monthly: dict[str, float], steps: int = 3) -> dict:
    if len(monthly) < 6:
        return {"available": False, "reason": "At least 6 months of history are needed to forecast.",
                "disclaimer": DISCLAIMER}
    values = np.array(list(monthly.values()), dtype=float)
    fit = ExponentialSmoothing(values, trend="add", seasonal=None).fit()
    pred = fit.forecast(steps)
    err = float(np.std(fit.resid))
    last = pd.Period(list(monthly.keys())[-1], freq="M")
    points = []
    for i, v in enumerate(pred, start=1):
        points.append({"month": str(last + i), "value": round(float(v), 2),
                       "lower": round(float(v - 1.96 * err), 2), "upper": round(float(v + 1.96 * err), 2)})
    return {"available": True, "method": "Holt linear trend (statsmodels)", "points": points,
            "disclaimer": DISCLAIMER}
