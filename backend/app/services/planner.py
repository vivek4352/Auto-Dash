"""Decides which panels the dashboard contains. Every panel is only created when the data can support it, and its title is generated from its own query."""
from .layout import nice, agg_for

def M(col, agg, **k): return {"column": col, "agg": agg, **k}

def plan_panels(df, prof, L, kpis):
    P = []; t, m1, m2, comp, brk, rk, tgt = (L.get(k) for k in ("time", "m1", "m2", "composition", "breakdown", "ranking", "target"))
    ag = lambda c: next((k["agg"] for k in kpis if k["column"] == c and k["agg"] != "rate"), agg_for(c))
    rec, drivers = L["records"], L.get("drivers", []); rl = rec["label"]; count_m = M(rec["column"], "count"); additive = bool(m1 and ag(m1) == "sum")
    rate_m = M(tgt["column"], "rate", positive=tgt["positive"]) if tgt else None; rate_name = f"{nice(tgt['column'])} rate" if tgt else ""
    def title_for(m, dim):
        if m["agg"] == "rate": return f"{rate_name} by {nice(dim)}"
        if m["agg"] == "count": return f"{rl} by {nice(dim)}"
        return f"{'Average ' if m['agg'] == 'mean' else ''}{nice(m['column'])} by {nice(dim)}"
    def add(**p): p["id"] = f"p{len(P) + 1}"; P.append(p)
    used = None
    # ---- main slot ----
    if t and m1:
        ms = [M(m1, ag(m1))] + ([M(m2, ag(m2))] if m2 else [])
        add(type="trend", slot="main", title=f"{nice(m1)}{' & ' + nice(m2) if m2 else ''} over time", query={"metrics": ms, "group_by": [t], "time_grain": L["grain"], "limit": 400}, why=f"'{t}' is the date column, so {nice(m1)} is shown over time{' with ' + nice(m2) + ' on its own axis, so different scales never flatten each other' if m2 else ''}.")
    elif tgt and drivers:
        used = drivers[0]; add(type="bar", slot="main", title=title_for(rate_m, used), fmt="percent", query={"metrics": [rate_m], "group_by": [used], "limit": 12, "order": "desc"}, why=f"There is no date column, so instead of a fake trend the main chart shows the strongest driver of {tgt['column']}: '{used}' separates the rates the most.")
    elif m1 and comp:
        m = M(m1, ag(m1)); add(type="bar", slot="main", title=title_for(m, comp), query={"metrics": [m], "group_by": [comp], "limit": 12, "order": "desc"}, why=f"No date column, so the main chart compares {nice(m1)} across '{comp}'.")
    elif comp:
        add(type="bar", slot="main", title=title_for(count_m, comp), query={"metrics": [count_m], "group_by": [comp], "limit": 12, "order": "desc"}, why=f"Only categories were found, so the main chart counts rows per '{comp}'.")
    # ---- side slot: share of total (only for additive measures or row counts, never for averages) ----
    if comp:
        sm = M(m1, "sum") if additive else count_m
        add(type="donut", slot="side", title=title_for(sm, comp), share=True, total_label=("Total" if additive else rl), query={"metrics": [sm], "group_by": [comp], "limit": 6},
            why=f"'{comp}' has few values; a donut shows share of total, so it uses {'the summed ' + nice(m1) if additive else 'row counts'} ({nice(m1) + ' is an average, and shares of averages are meaningless' if m1 and not additive else 'additive'}).")
    add(type="insights", slot="insights", title="Quick Insights", why="Insights are computed with real numbers in pandas; an AI may only rephrase them.")
    # ---- second row (max 3) ----
    row = []
    if tgt: row.append(dict(type="segments", title=f"Highest-risk groups ({nice(tgt['column'])} rate)", why=f"Compares every group of every category column on the {tgt['column']} rate (groups under 1% of rows are ignored) to find where it is highest and lowest."))
    if rk and m1:
        ms = [M(m1, ag(m1))] + ([M(m2, ag(m2))] if m2 else []); row.append(dict(type="top", title=f"Top 5 {nice(rk)} by {nice(m1)}", query={"metrics": ms, "group_by": [rk], "limit": 5}, why=f"'{rk}' has many distinct values, so only the top 5 are listed."))
    if tgt:
        for d in drivers:
            if d != used and len(row) < 3: row.append(dict(type="bar", title=title_for(rate_m, d), fmt="percent", query={"metrics": [rate_m], "group_by": [d], "limit": 12, "order": "desc"}, why=f"'{d}' is the next strongest driver of {tgt['column']}."))
    elif brk and (m1 or True):
        bm = M(m1, ag(m1)) if m1 else count_m
        row.append(dict(type="list", title=title_for(bm, brk), share=(bm["agg"] in ("sum", "count")), query={"metrics": [bm], "group_by": [brk], "limit": 6, "order": "desc"}, why=f"'{brk}' reads like a region/group column, so each value is ranked."))
    if t and m1 and L["span"] > 400:
        ms = [M(m1, ag(m1))] + ([M(m2, ag(m2))] if m2 else []); row.append(dict(type="yearly", title=f"Yearly {nice(m1)}{' & ' + nice(m2) if m2 else ''}", query={"metrics": ms, "group_by": [t], "time_grain": "Y", "limit": 30}, why="More than a year of data, so a yearly comparison is added."))
    for p in row[:3]: add(slot="row", **p)
    # ---- summary strip: only items the data supports ----
    if tgt: strip = ["records", "rate", "risk_high", "risk_low"]
    else:
        strip = (["total"] if additive else []) + (["growth"] if t and m1 else []) + (["margin"] if (L.get("profit") and L["profit"] != m1 and additive) else ["records"]) + (["best"] if t and m1 else [])
        if "records" not in strip: strip.append("records")
        strip = list(dict.fromkeys(strip))[:4]
    return P, strip
