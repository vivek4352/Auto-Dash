import re, pandas as pd
ID_RE = re.compile(r"(^|_)(id|code|no|number|ref)$")
MEASURE_WORDS = re.compile(r"sales|revenue|amount|profit|price|salary|cost|quantity|units|score|rating|spend|income|expense")
YES, NO = {"yes", "y", "true", "t"}, {"no", "n", "false", "f"}

def flag_positive(s):
    """If s is a binary yes/no or 0/1 column, return the label that counts as 'positive' (as text), else None."""
    if pd.api.types.is_bool_dtype(s): return "True"
    v = s.dropna()
    if v.empty: return None
    if pd.api.types.is_numeric_dtype(s):
        return "1" if set(v.unique().tolist()) == {0, 1} else None
    u = {str(x) for x in v.unique()}
    if len(u) != 2: return None
    low = {x.lower(): x for x in u}
    if set(low) <= (YES | NO) and set(low) & YES and set(low) & NO: return next(low[k] for k in low if k in YES)
    return None

def pos_mask(s, pos):
    if pd.api.types.is_bool_dtype(s): return s.astype(bool)
    if pd.api.types.is_numeric_dtype(s):
        try: return s == float(pos)
        except (TypeError, ValueError): pass
    return s.astype(str).str.lower() == str(pos).lower()

def profile(df):
    out, n = [], len(df)
    for c in df.columns:
        s = df[c]; nu = int(s.nunique()); pos = None
        if pd.api.types.is_datetime64_any_dtype(s): t, r = "datetime", "time"
        elif (pos := flag_positive(s)) is not None: t, r = "flag", "flag"
        elif pd.api.types.is_numeric_dtype(s):
            if ID_RE.search(c) or (pd.api.types.is_integer_dtype(s) and nu == n and n > 20 and not MEASURE_WORDS.search(c) and (s.is_monotonic_increasing or s.is_monotonic_decreasing or s.max() - s.min() + 1 == n)):
                t, r = "identifier", "identifier"
            else: t = "integer" if pd.api.types.is_integer_dtype(s) else "decimal"; r = "measure"
        elif ID_RE.search(c) or (nu > 0.9 * n and n > 20): t, r = "identifier", "identifier"
        elif nu <= max(20, 0.05 * n): t, r = "categorical", "dimension"
        else: t, r = "text", "dimension"
        p = {"name": c, "type": t, "role": r, "unique": nu, "missing_pct": round(float(s.isna().mean()) * 100, 2)}
        if r == "measure":
            p["stats"] = {k: float(getattr(s, k)()) for k in ("min", "max", "mean", "median", "sum") if pd.notna(getattr(s, k)())}
            st = p["stats"]; p["fmt"] = "percent" if re.search(r"discount|rate|pct|percent|ratio|margin", c) and st.get("min", 0) >= 0 and st.get("max", 2) <= 1 else "number"
        elif t == "flag":
            p["positive"] = pos; p["rate"] = round(float(pos_mask(s.dropna(), pos).mean()), 4)
            others = [str(v) for v in s.dropna().unique() if str(v).lower() != str(pos).lower() and str(v) != pos]
            p["top_values"] = [pos] + others[:1]
        elif t == "categorical": p["top_values"] = [str(v) for v in s.value_counts().head(20).index]
        elif t == "datetime" and s.notna().any(): p["stats"] = {"min": str(s.min().date()), "max": str(s.max().date())}
        out.append(p)
    return out
