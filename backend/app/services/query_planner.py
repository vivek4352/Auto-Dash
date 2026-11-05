import re
from .aggregator import run_query, validate_query
from .gemini_client import generate_json
from .layout import agg_for, nice, m_rank
from ..core import config

def rule_plan(msg, prof):
    m = msg.lower()
    measures = [p["name"] for p in sorted([p for p in prof if p["role"] == "measure"], key=m_rank)]
    dims = [p["name"] for p in prof if p["role"] == "dimension"]
    times = [p["name"] for p in prof if p["type"] == "datetime"]
    tgt = next((p for p in prof if p["type"] == "flag" and (p["name"].replace("_", " ") in m or p["name"] in m)), None)
    if tgt and (re.search(r"rate|percent|%|share|how many|proportion", m) or True):
        g = next((p["name"] for p in prof if p["type"] in ("categorical", "flag") and p["name"] != tgt["name"] and (p["name"].replace("_", " ") in m or p["name"] in m)), None)
        return {"operation": "aggregate", "metrics": [{"column": tgt["name"], "agg": "rate", "positive": tgt["positive"]}], "group_by": [g] if g else [], "order": "desc", "limit": 12}
    if not measures:
        return None
    col = next((c for c in measures if c.replace("_", " ") in m or c in m), measures[0])
    agg = ("sum" if re.search(r"\b(total|sum)\b", m) else "mean" if re.search(r"\b(avg|average|mean)\b", m)
           else "count" if re.search(r"\b(count|how many)\b", m) else agg_for(col))
    if agg == "count":
        col = next((p["name"] for p in prof), col)
    group = next((d for d in dims if d.replace("_", " ") in m), None)
    if not group and re.search(r"trend|over time|monthly|per month", m) and times:
        group = times[0]
    asc = bool(re.search(r"lowest|worst|bottom|least", m))
    return {"operation": "aggregate", "metrics": [{"column": col, "agg": agg}],
            "group_by": [group] if group else [], "order": "asc" if asc else "desc",
            "limit": 5 if re.search(r"top|bottom|highest|lowest|best|worst", m) else 20}

def answer(df, prof, message):
    plan = None
    ai = generate_json(f"Translate the question into a JSON query plan: "
                       '{"operation":"aggregate","metrics":[{"column":"","agg":"sum|mean|count|min|max|median|nunique"}],'
                       '"group_by":[],"order":"asc|desc","limit":10}. Use only these columns: '
                       f"{[(p['name'], p['type']) for p in prof]}. Question: {message}", config.GEMINI_MODEL_CHAT)
    for cand in (ai, rule_plan(message, prof)):          # LLM plan first, validated; rules as fallback
        if isinstance(cand, dict):
            try:
                validate_query(df, cand); plan = cand; break
            except Exception:
                continue
    if not plan:
        return {"answer": "I couldn't map that question to your data. Try naming a measure, e.g. 'total revenue by region'.", "plan": None, "rows": []}
    rows = run_query(df, plan)
    mk = f"{plan['metrics'][0]['column']}_{plan['metrics'][0]['agg']}"; isr = plan["metrics"][0]["agg"] == "rate"; fmtv = (lambda v: f"{v * 100:.1f}%") if isr else (lambda v: f"{v:,.2f}")
    if plan.get("group_by") and rows:
        g = plan["group_by"][0]
        txt = f"{nice(plan['metrics'][0]['agg'])} of {nice(plan['metrics'][0]['column'])} by {nice(g)}: " + \
              ", ".join(f"{r[g]} ({fmtv(r[mk])})" for r in rows[:5])
    else:
        txt = f"The {plan['metrics'][0]['agg']} of {nice(plan['metrics'][0]['column'])} is {fmtv(rows[0][mk])}."
    return {"answer": txt, "plan": plan, "rows": rows}
