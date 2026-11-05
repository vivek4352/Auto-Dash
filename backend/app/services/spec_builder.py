import re
from .layout import build_layout, build_kpis, nice, LOW
from .planner import plan_panels

def build_spec(df, prof, dom, filename=""):
    L = build_layout(prof, df); kpis = build_kpis(prof, L, len(df)); panels, strip = plan_panels(df, prof, L, kpis); tgt = L.get("target")
    low = lambda n: any(w in n for w in LOW); cats = [p["name"] for p in prof if p["type"] in ("categorical", "flag") and 2 <= p["unique"] <= 30 and not low(p["name"])]
    order = ([tgt["column"]] if tgt else []) + L.get("drivers", []) + [x for x in (L["breakdown"], L["composition"]) if x] + cats
    filters = [{"column": c, "type": "multiselect"} for c in list(dict.fromkeys(order)) if c in cats][:4] + ([{"column": L["time"], "type": "date_range"}] if L["time"] else [])
    stem = re.sub(r"[_\-]+", " ", re.sub(r"\.[^.]+$", "", filename or "")).strip()
    title = (nice(dom["domain"]) + " Dashboard") if dom["domain"] != "generic" else (f"{stem.title()} Dashboard" if stem else "Data Dashboard")
    return {"domain": dom["domain"], "title": title, "kpis": kpis, "panels": panels, "strip": strip, "filters": filters, "layout": L,
            "forecast": {"enabled": True, "date_column": L["time"], "measure": L["m1"]} if L["time"] and L["m1"] else {"enabled": False}}
