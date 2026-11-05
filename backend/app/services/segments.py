"""Which groups of rows have the highest / lowest outcome rate (e.g. churn)?"""
import pandas as pd
from .profiler import pos_mask
from .layout import LOW, nice

def segment_table(df, prof, tgt, top=6, bottom=3):
    col = tgt["column"]; y = pos_mask(df[col], tgt["positive"]).astype(float); overall = float(y.mean()) if len(y) else 0.0; minsup = max(30, int(.01 * len(df))); rows = []
    for p in prof:
        if p["type"] in ("categorical", "flag") and 2 <= p["unique"] <= 12 and p["name"] != col and p["name"] in df.columns and not any(w in p["name"] for w in LOW):
            g = y.groupby(df[p["name"]]).agg(["mean", "size"])
            for val, r in g.iterrows():
                if r["size"] >= minsup:
                    shown = ("Yes" if str(val) == "1" else "No" if str(val) == "0" else str(val)) if p["type"] == "flag" and str(val) in ("0", "1") else str(val)
                    rows.append({"dim": p["name"], "label": f"{nice(p['name'])}: {shown}", "n": int(r["size"]), "rate": float(r["mean"]), "lift": float(r["mean"] / overall) if overall else 0.0})
    def pick(lst, k):
        out, used = [], {}
        for r in lst:
            if used.get(r["dim"], 0) < 2 and len(out) < k: out.append(r); used[r["dim"]] = used.get(r["dim"], 0) + 1
        return out
    rows.sort(key=lambda r: -r["rate"])
    return {"overall": overall, "n": int(len(df)), "top": pick(rows, top), "bottom": pick(rows[::-1], bottom)}
