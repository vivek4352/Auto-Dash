import os, json, re, pandas as pd
from .core.config import DATA_DIR
os.makedirs(DATA_DIR, exist_ok=True)

def _p(i, ext):
    if not re.fullmatch(r"[a-f0-9]{32}", i):
        raise ValueError("bad id")
    return os.path.join(DATA_DIR, f"{i}.{ext}")

def save(i, df, meta):
    df.to_pickle(_p(i, "pkl"))
    with open(_p(i, "json"), "w") as f:
        json.dump(meta, f, default=str)

def load(i):
    try:
        if not os.path.exists(_p(i, "pkl")):
            return None, None
    except ValueError:
        return None, None
    with open(_p(i, "json")) as f:
        return pd.read_pickle(_p(i, "pkl")), json.load(f)

def delete(i):
    for e in ("pkl", "json"):
        if os.path.exists(_p(i, e)):
            os.remove(_p(i, e))
