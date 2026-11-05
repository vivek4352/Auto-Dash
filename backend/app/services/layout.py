"""Semantic layout: decides WHICH columns drive each part of the dashboard from column meaning (never from column order)."""
import re
import pandas as pd
SUMMABLE = "revenue sales profit amount quantity spend cost expense debit credit impressions clicks salary units orders".split()
MEAN_WORDS = "discount rate ratio pct percent price rating score age margin avg average monthly tenure".split()
M_PRI = [("sales", "revenue", "amount", "turnover", "income", "gmv", "charge", "fee", "billing", "premium"), ("profit", "net"),
         ("quantity", "units", "volume", "orders", "spend", "cost", "expense", "salary", "clicks", "impressions")]
T_PRI = ("order", "invoice", "sale", "transaction", "date", "created", "booking")
T_LOW = ("ship", "deliver", "due", "birth", "expire", "update", "modified", "return")
GEO = ("region", "zone", "state", "territory", "area", "country", "branch", "store", "city")
COMP = ("category", "segment", "type", "channel", "department", "class", "group", "contract", "plan", "service", "tier", "package", "subscription", "payment", "gender")
LOW = ("ship", "mode", "priority", "flag", "return", "status", "method")
ITEM = ("product", "item", "sku", "service", "course", "employee", "campaign", "customer", "student", "patient", "doctor", "supplier")
ID_ORDER = ("order", "invoice", "transaction", "ticket", "booking")
ID_PARTY = ("customer", "client", "user", "patient", "student", "employee", "member")
TARGET_WORDS = ("churn", "attrition", "fraud", "default", "converted", "conversion", "cancel", "exited", "dropout", "readmit", "survived", "response", "clicked", "purchased", "returned", "target", "outcome", "label", "left")
ACR = {"tv", "id", "ip", "crm", "sku", "ui", "roi", "kpi", "usd", "api", "url", "vip", "gps", "sms", "upi"}
nice = lambda s: " ".join(w.upper() if w.lower() in ACR else w.capitalize() for w in str(s).replace("_", " ").split())

def agg_for(name):
    n = name.lower()
    if any(w in n for w in MEAN_WORDS): return "mean"
    return "sum" if (n.startswith("total") or any(k in n for k in SUMMABLE)) else "mean"

def label_for(col, agg):
    b = nice(col)
    if agg == "sum": return b if b.lower().startswith("total") else f"Total {b}"
    return f"Average {b}" if agg == "mean" else b

def m_rank(p):
    if p.get("fmt") == "percent": return 90
    for i, ws in enumerate(M_PRI):
        if any(w in p["name"] for w in ws): return i
    return 50

def t_rank(n): return (any(w in n for w in T_LOW), next((i for i, w in enumerate(T_PRI) if w in n), 9))

def find_target(prof):
    """The outcome column of the dataset (churn, attrition, fraud ...): a binary flag whose name says so."""
    flags = [p for p in prof if p["type"] == "flag"]
    for w in TARGET_WORDS:
        for p in flags:
            if re.search(rf"(^|_){w}", p["name"]): return {"column": p["name"], "positive": p["positive"], "rate": p.get("rate")}
    return None

def _drivers(df, prof, tgt, n=5):
    """Dimensions that separate the target rate the most (spread between best and worst group, with enough rows per group)."""
    from .profiler import pos_mask
    y = pos_mask(df[tgt["column"]], tgt["positive"]).astype(float); minsup = max(30, int(.01 * len(df))); scored = []
    for p in prof:
        if p["type"] in ("categorical", "flag") and 2 <= p["unique"] <= 12 and p["name"] != tgt["column"] and not any(w in p["name"] for w in LOW):
            g = y.groupby(df[p["name"]]).agg(["mean", "size"]); g = g[g["size"] >= minsup]
            if len(g) >= 2: scored.append((float(g["mean"].max() - g["mean"].min()), p["name"]))
    return [c for _, c in sorted(scored, reverse=True)[:n]]

def build_layout(prof, df=None):
    low = lambda n: any(w in n for w in LOW); geo = lambda n: any(w in n for w in GEO)
    measures = [p["name"] for p in sorted([p for p in prof if p["role"] == "measure"], key=m_rank)]
    times = sorted([p["name"] for p in prof if p["type"] == "datetime"], key=t_rank)
    pool = [p for p in prof if p["type"] == "categorical" and 2 <= p["unique"] <= 30 and not low(p["name"])]
    comp = next((p["name"] for w in COMP for p in pool if w in p["name"] and not geo(p["name"]) and p["unique"] <= 10), None) \
        or next((p["name"] for p in sorted(pool, key=lambda p: p["unique"]) if not geo(p["name"]) and p["unique"] <= 10), None)
    brk = next((p["name"] for w in GEO for p in pool if w in p["name"] and p["unique"] <= 20 and p["name"] != comp), None) \
        or next((p["name"] for p in sorted(pool, key=lambda p: p["unique"]) if p["name"] != comp), None)
    rp = [p for p in prof if p["role"] == "dimension" and p["type"] in ("categorical", "text") and 8 <= p["unique"] <= 5000 and p["name"] not in (comp, brk) and not low(p["name"])]
    rank = next((p["name"] for w in ITEM for p in rp if w in p["name"]), None) or (max(rp, key=lambda p: p["unique"])["name"] if rp else None)   # None: never fall back to a 2-value column
    m1 = measures[0] if measures else None; m2 = next((m for m in measures[1:] if m != m1), None)
    tgt = find_target(prof); n = len(df) if df is not None else 0
    ids = [p for p in prof if p["type"] == "identifier" and (not n or p["unique"] >= 0.9 * n)]
    rid = next((p for p in ids if p["name"] != "row_id"), ids[0] if ids else None)
    base = re.sub(r"_(id|code|no|number|ref)$", "", rid["name"]) if rid else ""
    records = {"column": rid["name"] if rid else prof[0]["name"], "agg": "count", "label": (nice(base) + "s") if base and base != "row" else "Rows"}
    u = lambda c: next((p["unique"] for p in prof if p["name"] == c), 0)
    L = {"time": times[0] if times else None, "m1": m1, "m2": m2, "profit": next((m for m in measures if "profit" in m), None), "composition": comp, "breakdown": brk, "ranking": rank,
         "target": tgt, "drivers": _drivers(df, prof, tgt) if (tgt and df is not None) else [], "records": records, "grain": None, "span": 0}
    if L["time"] and df is not None and df[L["time"]].notna().any():
        span = (df[L["time"]].max() - df[L["time"]].min()).days; L.update(span=int(span), grain="D" if span <= 120 else "M" if span <= 1900 else "Q")
    R = {}
    if L["time"]:
        w = next((w for w in T_PRI if w in L["time"]), None)
        R["time"] = f"'{L['time']}' is the primary date" + (f" (its name contains '{w}')" if w else " (first date column found)") + (f"; {', '.join(times[1:])} ignored as secondary/delivery dates" if len(times) > 1 else "") + ". It becomes the X-axis of trends, the date filter and the forecast."
    else: R["time"] = "No date column was found, so trend, growth, period and forecast widgets are left out instead of being drawn empty."
    if m1: R["m1"] = f"'{m1}' is the main measure ({'summed, because it is an additive amount' if agg_for(m1) == 'sum' else 'averaged, because it is a rate/price/duration and adding it up would be meaningless'}); picked from {len(measures)} numeric columns."
    if tgt: R["target"] = f"'{tgt['column']}' is a yes/no outcome column whose name says so, so the dashboard measures its rate ({(tgt.get('rate') or 0) * 100:.1f}% overall) and what drives it."
    if L["drivers"]: R["drivers"] = f"Ranked by how far the {tgt['column']} rate differs between their groups: {', '.join(L['drivers'][:4])}."
    if comp: R["composition"] = f"'{comp}' has {u(comp)} values, few enough for a share-of-total donut."
    if rank: R["ranking"] = f"'{rank}' has {u(rank):,} distinct values, too many to chart, so the Top 5 are shown in a table."
    else: R["ranking"] = "No column has enough distinct values (8 or more) to justify a Top 5 table, so none is drawn."
    flags = [p["name"] for p in prof if p["type"] == "flag" and (not tgt or p["name"] != tgt["column"])]
    if flags: R["flags"] = f"{', '.join(flags)} are yes/no (or 0/1) columns. They are treated as categories, never averaged like numbers."
    ign = [p["name"] for p in prof if p["type"] == "categorical" and low(p["name"])]
    if ign: R["ignored"] = f"{', '.join(ign)} skipped as headline dimensions: operational fields rarely explain results. They remain available as filters."
    L["reasons"] = R; return L

def icon_for(col, agg):
    n = (col or "").lower()
    if agg == "rate": return "📉"
    if agg in ("count", "nunique"): return "👥"
    if any(w in n for w in ("sales", "revenue", "charge", "amount", "profit", "price", "salary", "cost", "income", "fee")): return "💰"
    if any(w in n for w in ("tenure", "duration", "days", "age", "time")): return "⏱"
    if any(w in n for w in ("quantity", "units", "volume")): return "📦"
    return "📊"

def build_kpis(prof, L, n_rows):
    ks = []; WHY = {"sum": "an additive amount, so values are summed", "mean": "a rate/score/price/duration, so values are averaged (adding them up would be meaningless)", "nunique": "an identifier: counted as distinct values, never summed", "count": "counted", "rate": "a yes/no outcome, shown as the share of rows that are positive"}
    def add(col, agg, label, **kw): ks.append({"id": f"k{len(ks)+1}", "label": label, "column": col, "agg": agg, "icon": icon_for(col, agg), "fmt": "percent" if agg == "rate" else None, "why": f"'{col}' is {WHY.get(agg, '')}.", **kw})
    tgt = L.get("target")
    if tgt:
        add(L["records"]["column"], "count", L["records"]["label"]); add(tgt["column"], "rate", f"{nice(tgt['column'])} Rate", positive=tgt["positive"])
    for m in [L["m1"], L["m2"]]:
        if m: add(m, agg_for(m), label_for(m, agg_for(m)))
    ids = [p for p in prof if p["type"] == "identifier" and p["name"] != "row_id" and 1 < p["unique"] < 0.95 * n_rows]
    for words in (ID_ORDER, ID_PARTY):
        p = next((p for w in words for p in ids if w in p["name"]), None)
        if p: add(p["name"], "nunique", "Total " + nice(re.sub(r"_(id|code|no|number|ref)$", "", p["name"])) + "s")
    for m in [p["name"] for p in sorted([p for p in prof if p["role"] == "measure"], key=m_rank)]:
        if len(ks) >= 5: break
        if not any(k["column"] == m for k in ks): add(m, agg_for(m), label_for(m, agg_for(m)))
    return ks[:5]
