import os, json, datetime
import pandas as pd
from .layout import LOW
TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")

def to_html(df, meta, insights, initial=None):
    """One self-contained interactive HTML file: data is embedded column-wise; every panel re-aggregates in the browser."""
    spec, L = meta["spec"], meta["spec"]["layout"]; prof = {p["name"]: p for p in meta["profile"]}; tgt = L.get("target"); need = []
    def add(c):
        if c and c in df.columns and c not in need: need.append(c)
    add(L.get("time")); [add(f["column"]) for f in spec["filters"] if f["type"] == "multiselect"]
    for k in spec["kpis"]:
        if k["agg"] != "count": add(k["column"])
    for p in spec["panels"]:
        for m in (p.get("query") or {}).get("metrics", []):
            if m["agg"] != "count": add(m["column"])
        for g in (p.get("query") or {}).get("group_by", []): add(g)
    segdims = []
    if tgt:
        add(tgt["column"]); segdims = [p["name"] for p in meta["profile"] if p["type"] in ("categorical", "flag") and 2 <= p["unique"] <= 12 and p["name"] != tgt["column"] and not any(w in p["name"] for w in LOW)]
        [add(d) for d in segdims]
    cols = {}
    for c in need:
        s = df[c]; p = prof.get(c, {})
        if pd.api.types.is_datetime64_any_dtype(s): cols[c] = {"t": "time", "i": ((s - pd.Timestamp("1970-01-01")).dt.days).fillna(-1).astype(int).tolist()}
        elif pd.api.types.is_numeric_dtype(s) and p.get("role") in ("measure", None): cols[c] = {"t": "num", "v": [None if pd.isna(x) else round(float(x), 4) for x in s]}
        else:
            s2 = s.map(lambda x: x if pd.isna(x) else (str(int(x)) if isinstance(x, float) and float(x).is_integer() else str(x))) if pd.api.types.is_numeric_dtype(s) else s.astype(str).where(s.notna())
            codes, uniq = pd.factorize(s2); cols[c] = {"t": "cat", "u": [str(u) for u in uniq], "i": codes.tolist()}
    init = initial or {}
    data = {"title": spec["title"], "file": meta["filename"], "rows": len(df), "cols": cols, "time": L.get("time"), "grain": L.get("grain"), "target": tgt, "segdims": segdims, "flagdims": [p["name"] for p in meta["profile"] if p["type"] == "flag"],
            "records": L["records"]["label"], "profit": L.get("profit"), "kpis": spec["kpis"], "panels": spec["panels"], "strip": spec["strip"], "filters": [f["column"] for f in spec["filters"] if f["type"] == "multiselect" and f["column"] in cols],
            "fmt": {c: prof[c].get("fmt") for c in need if prof.get(c, {}).get("fmt")}, "insights": insights, "reasons": L.get("reasons", {}), "made": datetime.date.today().isoformat(),
            "initial": {k: init.get(k) for k in ("theme", "ind", "sel", "min", "max") if init.get(k) is not None}}
    payload = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    return open(TEMPLATE, encoding="utf-8").read().replace("/*__DATA__*/null", payload)
