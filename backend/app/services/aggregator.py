import json, pandas as pd
from .profiler import pos_mask
AGGS = {"sum", "mean", "count", "min", "max", "median", "nunique", "rate"}
NUMERIC_ONLY = {"sum", "mean", "min", "max", "median"}

def apply_filters(df, filters):
    for f in filters or []:
        c = f.get("column")
        if c not in df.columns: continue
        if f.get("values"): df = df[df[c].astype(str).isin([str(v) for v in f["values"]])]
        if f.get("min") or f.get("max"):
            col = df[c]
            if pd.api.types.is_datetime64_any_dtype(col):
                if f.get("min"): df = df[col >= pd.to_datetime(f["min"])]
                if f.get("max"): df = df[col <= pd.to_datetime(f["max"])]
            else:
                if f.get("min") is not None: df = df[col >= f["min"]]
                if f.get("max") is not None: df = df[col <= f["max"]]
    return df

def validate_query(df, q):
    """Whitelist validation: only known columns and aggregations are ever executed."""
    if q.get("operation", "aggregate") != "aggregate": raise ValueError("unsupported operation")
    if not q.get("metrics"): raise ValueError("metrics required")
    for m in q["metrics"]:
        if m.get("column") not in df.columns or m.get("agg") not in AGGS: raise ValueError(f"invalid metric {m}")
        if m["agg"] in NUMERIC_ONLY and not pd.api.types.is_numeric_dtype(df[m["column"]]): raise ValueError(f"{m['agg']} needs numeric column {m['column']}")
        if m["agg"] == "rate" and m.get("positive") is None: raise ValueError("rate needs a positive value")
    for g in q.get("group_by", []):
        if g not in df.columns: raise ValueError(f"invalid group_by {g}")

def _rate(s, pos):
    s = s.dropna(); return float(pos_mask(s, pos).mean()) if len(s) else 0.0

def run_query(df, q):
    validate_query(df, q); df = apply_filters(df, q.get("filters")); groups = list(q.get("group_by", []))
    named = {f"{m['column']}_{m['agg']}": (m["column"], m["agg"], m.get("positive")) for m in q["metrics"]}
    limit = min(int(q.get("limit", 50)), 1000)
    if not groups:
        row = {k: (_rate(df[c], p) if a == "rate" else df[c].nunique() if a == "nunique" else df[c].notna().sum() if a == "count" else getattr(df[c], a)()) for k, (c, a, p) in named.items()}
        return json.loads(pd.DataFrame([row]).to_json(orient="records"))
    d, is_time = df.copy(), False
    for g in groups:
        if pd.api.types.is_datetime64_any_dtype(d[g]): d[g] = d[g].dt.to_period(q.get("time_grain", "M")).astype(str); is_time = True
    spec = {k: (c, (lambda s, p=p: _rate(s, p)) if a == "rate" else a) for k, (c, a, p) in named.items()}
    out = d.groupby(groups, dropna=False).agg(**spec).reset_index(); first = list(named)[0]
    out = out.sort_values(groups) if is_time else out.sort_values(first, ascending=q.get("order") == "asc")
    return json.loads(out.head(limit).to_json(orient="records", date_format="iso"))
