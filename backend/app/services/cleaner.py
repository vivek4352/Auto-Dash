import re, warnings, pandas as pd
NUM = re.compile(r"^[\s₹$€£]*-?[\d,]+(\.\d+)?\s*%?$")

def clean(df, log=None):
    """Non-destructive: returns a cleaned copy and appends a human-readable action to `log` for each change."""
    log = log if log is not None else []
    df = df.copy()
    for c in df.columns:
        if not (df[c].dtype == object or pd.api.types.is_string_dtype(df[c])):
            continue
        s = df[c].astype(str).str.strip().where(df[c].notna())
        nn = s.dropna()
        if not len(nn):
            continue
        if nn.str.match(NUM).mean() > 0.9:
            df[c] = pd.to_numeric(nn.str.replace(r"[₹$€£,%\s]", "", regex=True), errors="coerce").reindex(df.index)
            log.append(f"'{c}': text with currency symbols/commas converted to numbers"); continue
        if not re.search(r"(^|_)(id|code|no|number|ref)$", c):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                a = pd.to_datetime(nn, errors="coerce")
                b = pd.to_datetime(nn, errors="coerce", dayfirst=True)
            d = a if a.notna().sum() >= b.notna().sum() else b   # handles dd/mm/yyyy as well as mm/dd/yyyy
            if d.notna().mean() > 0.9:
                df[c] = d.reindex(df.index)
                log.append(f"'{c}': text recognised as dates ({'day-first' if d is b and b.notna().sum() > a.notna().sum() else 'standard'} format)"); continue
        if nn.str.lower().nunique() < nn.nunique():   # only merge case variants; IDs stay untouched
            df[c] = s.str.title()
            log.append(f"'{c}': merged spelling/case variants (e.g. north / North / NORTH)")
    return df

def add_bands(df, prof, tgt, log):
    """For outcome datasets (churn, attrition ...) add equal-sized bands of the main numeric columns, so ranges such as 'tenure 0-9' can be compared."""
    import pandas as pd
    df = df.copy(); n = 0
    for p in prof:
        if p["role"] == "measure" and p["unique"] >= 15 and n < 3:
            try: b = pd.qcut(df[p["name"]], 4, duplicates="drop")
            except ValueError: continue
            if b.nunique() < 3: continue
            f = lambda v: f"{v:.0f}" if abs(v - round(v)) < 1e-9 or abs(v) >= 100 else f"{v:.1f}"
            labels = {iv: f"{f(iv.left if i else df[p['name']].min())}-{f(iv.right)}" for i, iv in enumerate(b.cat.categories)}
            df[p["name"] + "_band"] = b.map(labels).astype(object).where(b.notna(), None); n += 1
            log.append(f"Added '{p['name']}_band': {p['name']} split into {b.nunique()} equal-sized groups, so '{tgt['column']}' can be compared across ranges")
    return df
