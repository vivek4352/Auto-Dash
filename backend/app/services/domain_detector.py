KW = {
 "sales": "revenue sales order product customer region discount profit quantity".split(),
 "hr_performance": "employee department salary rating performance attendance designation joining attrition manager".split(),
 "finance": "account transaction debit credit balance expense budget invoice".split(),
 "education": "student marks grade subject class exam score attendance".split(),
 "healthcare": "patient diagnosis admission doctor treatment bed discharge".split(),
 "inventory": "sku stock warehouse supplier reorder unit".split(),
 "marketing": "campaign impressions clicks ctr conversion channel spend".split(),
 "survey": "respondent question satisfaction".split(),
 "customer_churn": "churn tenure contract internet monthly subscriber subscription".split(),
}

def detect_domain(df, prof):
    """Rule-based keyword scoring over column names. Falls back to 'generic'."""
    names = " ".join(df.columns)
    scores = {d: sum(k in names for k in kws) for d, kws in KW.items()}
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top, ts = ranked[0]
    return {"domain": top if ts >= 2 else "generic", "confidence": round(min(1.0, ts / 4), 2),
            "alternatives": [d for d, s in ranked[1:4] if s > 0],
            "column_roles": {p["name"]: p["role"] for p in prof}}
