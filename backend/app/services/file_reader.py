import io, re, csv, pandas as pd

def read_file(name, data):
    ext = name.lower().rsplit(".", 1)[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(data))
    else:
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = data.decode(enc); break
            except UnicodeDecodeError:
                pass
        try:
            sep = csv.Sniffer().sniff(text[:5000], delimiters=",;\t|").delimiter
        except csv.Error:
            sep = ","
        df = pd.read_csv(io.StringIO(text), sep=sep)
    df.columns = _norm(df.columns)
    return df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

def _snake(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(s).strip())        # monthlyCharges -> monthly_Charges
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)                 # TVShows -> TV_Shows
    return re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower() or "col"

def _norm(cols):
    out, seen = [], {}
    for c in cols:
        n = _snake(c); k = seen.get(n, 0); seen[n] = k + 1
        out.append(n if k == 0 else f"{n}_{k+1}")
    return out
