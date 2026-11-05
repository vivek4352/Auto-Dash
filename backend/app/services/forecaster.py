import numpy as np, pandas as pd
from .layout import agg_for

def forecast(df, date_col, measure, periods=6):
    """Linear trend, plus an additive month-of-year seasonal profile when >= 24 months of history."""
    s = df.set_index(date_col)[measure].resample("MS").agg(agg_for(measure)).dropna()
    if len(s) < 4:
        raise ValueError("Need at least 4 monthly data points to forecast")
    x = np.arange(len(s)); k, b = np.polyfit(x, s.values, 1)
    resid = s.values - (k * x + b); moy = {}
    if len(s) >= 24:
        moy = pd.Series(resid, index=s.index.month).groupby(level=0).mean().to_dict()
        resid = resid - np.array([moy.get(d.month, 0) for d in s.index])
    sd = float(np.std(resid))
    dates = pd.date_range(s.index[-1], periods=periods + 1, freq="MS")[1:]
    out = []
    for d, i in zip(dates, range(len(s), len(s) + periods)):
        v = float(k * i + b + moy.get(d.month, 0))
        out.append({"date": f"{d:%Y-%m}", "value": v, "lower": v - 1.96 * sd, "upper": v + 1.96 * sd})
    h = s.iloc[-36:]
    return {"history": [{"date": f"{d:%Y-%m}", "value": float(v)} for d, v in h.items()], "forecast": out,
            "method": "linear trend + monthly seasonality" if moy else "linear trend on monthly aggregates"}
