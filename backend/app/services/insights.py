import pandas as pd
from .gemini_client import generate_json
from .layout import agg_for, nice, LOW
from .profiler import pos_mask
from .segments import segment_table

def compute_facts(df, prof, L):
    """Every number is computed in pandas; an LLM (if configured) may only rephrase."""
    F, m1, t, comp, brk, rank, pr, tgt = [], L.get("m1"), L.get("time"), L.get("composition"), L.get("breakdown"), L.get("ranking"), L.get("profit"), L.get("target")
    ag = agg_for(m1) if m1 else None; rl = L.get("records", {}).get("label", "Rows")
    def safe(fn):
        try: fn()
        except Exception: pass
    F.append(f"The dataset has {len(df):,} rows and {len(df.columns)} columns" + (f", covering {df[t].min():%b %Y} to {df[t].max():%b %Y}." if t else "."))
    if tgt:
        def outcome():
            col, name = tgt["column"], nice(tgt["column"]); y = pos_mask(df[col], tgt["positive"]); F.append(f"Overall {name.lower()} rate is {y.mean() * 100:.1f}% ({int(y.sum()):,} of {len(df):,} {rl.lower()}).")
            seg = segment_table(df, prof, tgt)
            for r in seg["top"][:3]: F.append(f"Highest {name.lower()} risk: {r['label']} at {r['rate'] * 100:.1f}% ({r['lift']:.1f}x the average, {r['n']:,} {rl.lower()}).")
            for r in seg["bottom"][:2]: F.append(f"Lowest {name.lower()} risk: {r['label']} at {r['rate'] * 100:.1f}%.")
            gaps = []
            for p in prof:
                if p["role"] == "measure" and p["unique"] >= 15:
                    a, b = df.loc[y, p["name"]].mean(), df.loc[~y, p["name"]].mean()
                    if pd.notna(a) and pd.notna(b) and b: gaps.append((abs(a - b) / abs(b), p["name"], a, b))
            for _, c, a, b in sorted(gaps, reverse=True)[:2]: F.append(f"{rl} with {name.lower()} have an average {nice(c).lower()} of {a:,.1f} versus {b:,.1f} for the rest.")
        safe(outcome)
        for p in [p for p in prof if p["type"] == "flag" and p["name"] != tgt["column"]][:2]: F.append(f"{p['rate'] * 100:.1f}% of {rl.lower()} are marked '{nice(p['name'])}'.")
    if m1 and t:
        def trend():
            s = df.set_index(t)[m1].resample("MS").agg(ag).dropna()
            if len(s) >= 24:
                a, b = s.iloc[-12:], s.iloc[-24:-12]; fa, fb = (a.sum(), b.sum()) if ag == "sum" else (a.mean(), b.mean())
                if fb: F.append(f"{nice(m1)} over the last 12 months ({s.index[-12]:%b %Y} to {s.index[-1]:%b %Y}) was {fa:,.0f}, {(fa-fb)/abs(fb)*100:+.1f}% versus the 12 months before.")
                if ag == "sum":
                    moy = s.groupby(s.index.month).mean().sort_values(ascending=False); mn = lambda m: pd.Timestamp(2000, int(m), 1).strftime("%b")
                    F.append(f"Seasonality: {', '.join(mn(m) for m in moy.index[:3])} are the strongest months for {nice(m1)}; {mn(moy.index[-1])} is the weakest.")
        safe(trend)
    if m1 and not tgt:
        def share(dim):
            g = df.groupby(dim)[m1].agg(ag).sort_values(ascending=False)
            if len(g) < 2: return
            if ag == "sum": F.append(f"{g.index[0]} is the top {nice(dim)} with {g.iloc[0]/g.sum()*100:.1f}% of {nice(m1)}; {g.index[-1]} is the lowest at {g.iloc[-1]/g.sum()*100:.1f}%.")
            else: F.append(f"{g.index[0]} has the highest average {nice(m1)} by {nice(dim)} ({g.iloc[0]:,.2f}); {g.index[-1]} the lowest ({g.iloc[-1]:,.2f}).")
        for dim in (comp, brk):
            if dim: safe(lambda d=dim: share(d))
    if m1 and pr and pr != m1 and ag == "sum":
        def profit():
            ts, tp = df[m1].sum(), df[pr].sum()
            if ts: F.append(f"Overall {nice(pr)} margin is {tp/ts*100:.1f}% ({tp:,.0f} on {ts:,.0f} {nice(m1)}).")
            if comp:
                g = df.groupby(comp)[[m1, pr]].sum(); mg = (g[pr] / g[m1] * 100).sort_values()
                if len(mg) > 1: F.append(f"{mg.index[-1]} has the best {nice(pr)} margin ({mg.iloc[-1]:.1f}%) while {mg.index[0]} has the weakest ({mg.iloc[0]:.1f}%).")
            found = []
            for p in sorted(prof, key=lambda p: p["unique"]):
                if p["type"] == "categorical" and 5 <= p["unique"] <= 60 and not any(w in p["name"] for w in LOW):
                    g = df.groupby(p["name"])[pr].sum(); neg = g[g < 0].sort_values()
                    if len(neg): found.append((p["name"], neg))
            for name, neg in found[:2]: F.append(f"{len(neg)} {nice(name)} value(s) lose money overall; the worst: {', '.join(f'{k} ({v:,.0f})' for k, v in neg.head(3).items())}.")
            d = next((p["name"] for p in prof if p["role"] == "measure" and "discount" in p["name"]), None)
            if d and df[d].max() <= 1:
                hi, lo = df[df[d] > 0.2][pr], df[df[d] <= 0.2][pr]
                if len(hi) > 20 and len(lo) > 20: F.append(f"Rows with {nice(d)} above 20% average {hi.mean():,.2f} {nice(pr)} each, versus {lo.mean():,.2f} for the rest.")
        safe(profit)
    if m1 and rank and ag == "sum":
        def conc():
            g = df.groupby(rank)[m1].sum().sort_values(ascending=False)
            if len(g) >= 20: k = max(1, int(len(g) * .2)); F.append(f"The top 20% of {nice(rank)} values ({k:,} of {len(g):,}) generate {g.iloc[:k].sum()/g.sum()*100:.0f}% of {nice(m1)}.")
        safe(conc)
    prof_ = [p for p in prof if not p["name"].endswith("_band")]; bad = [p["name"] for p in prof_ if p["missing_pct"] > 10]
    if bad: F.append(f"Columns with over 10% missing values: {', '.join(bad)}.")
    elif any(p["missing_pct"] > 0 for p in prof_): F.append("Some values are missing: " + ", ".join(f"{p['name']} ({p['missing_pct']:.2f}%)" for p in prof_ if p["missing_pct"] > 0)[:200] + ".")
    dup = int(df.duplicated().sum())
    if dup: F.append(f"{dup:,} fully duplicated rows were found; check whether they are errors.")
    return F

def get_insights(df, prof, L):
    facts = compute_facts(df, prof, L)
    ai = generate_json("Rewrite these verified facts as concise business insights. Do not add or change any numbers. " f'Return JSON {{"insights": [string]}}. Facts: {facts}')
    if isinstance(ai, dict) and isinstance(ai.get("insights"), list) and ai["insights"]: return {"insights": ai["insights"], "source": "gemini"}
    return {"insights": facts, "source": "rules"}
