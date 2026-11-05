"""Power BI kit: cleaned data (CSV) + Power Query (M) + DAX measures + theme + a build guide generated from the dashboard's own panels."""
import io, re, json, zipfile
import pandas as pd
from .layout import nice, agg_for, label_for

PAL = ["#2f6bff", "#22c55e", "#f59e0b", "#ec4899", "#8b5cf6", "#94a3b8", "#14b8a6", "#f97316"]
THEMES = {"dark": dict(card="#0d1630", fg="#eef2ff", mut="#8a97b8"), "light": dict(card="#ffffff", fg="#121933", mut="#5b6785")}
mkey = lambda m: f"{m['column']}|{m['agg']}"

def _stem(meta): return re.sub(r"[^a-z0-9]+", "_", meta["filename"].rsplit(".", 1)[0].lower()).strip("_") or "dataset"

def _metrics(spec):
    """every distinct metric used by KPIs and panels, in order"""
    out = {}
    for k in spec["kpis"]: out.setdefault(mkey(k), {"column": k["column"], "agg": k["agg"], **({"positive": k["positive"]} if k.get("positive") is not None else {})})
    for p in spec["panels"]:
        for m in (p.get("query") or {}).get("metrics", []): out.setdefault(mkey(m), m)
    return list(out.values())

def _names(spec, records):
    names = {}
    for m in _metrics(spec):
        names[mkey(m)] = records if m["agg"] == "count" else f"{nice(m['column'])} Rate" if m["agg"] == "rate" else label_for(m["column"], m["agg"]) if m["agg"] in ("sum", "mean") else f"{nice(m['column'])} (distinct)" if m["agg"] == "nunique" else f"{m['agg'].title()} {nice(m['column'])}"
    return names

def _lit(v): return str(v) if re.fullmatch(r"-?\d+(\.\d+)?", str(v)) else '"' + str(v).replace('"', '""') + '"'

def dax_text(meta):
    spec, L = meta["spec"], meta["spec"]["layout"]; rec = L["records"]["label"]; names = _names(spec, rec); out = ["// AutoDash: DAX measures. Home > New measure, paste one measure at a time.", "// The table is called Data (the CSV loaded with queries.pq).", ""]
    for m in _metrics(spec):
        c = f"Data[{m['column']}]"; a = m["agg"]
        expr = {"sum": f"SUM({c})", "mean": f"AVERAGE({c})", "nunique": f"DISTINCTCOUNT({c})", "count": "COUNTROWS(Data)", "min": f"MIN({c})", "max": f"MAX({c})", "median": f"MEDIAN({c})"}.get(a)
        if a == "rate": expr = f"DIVIDE(CALCULATE(COUNTROWS(Data), {c} = {_lit(m['positive'])}), COUNTROWS(Data))"
        out.append(f"{names[mkey(m)]} = {expr}")
    tgt = L.get("target")
    if tgt: out.append(f"{nice(tgt['column'])} Count = CALCULATE(COUNTROWS(Data), Data[{tgt['column']}] = {_lit(tgt['positive'])})")
    m1, t, pf = L.get("m1"), L.get("time"), L.get("profit")
    if m1 and pf and pf != m1 and agg_for(m1) == "sum" and mkey({"column": m1, "agg": "sum"}) in names and mkey({"column": pf, "agg": "sum"}) in names: out.append(f"{nice(pf)} Margin % = DIVIDE([{names[mkey({'column': pf, 'agg': 'sum'})]}], [{names[mkey({'column': m1, 'agg': 'sum'})]}])")
    if t and m1 and agg_for(m1) == "sum":
        mm = names[mkey({"column": m1, "agg": "sum"})]
        out += ["", f"// Time intelligence needs a date table: Modeling > New table, then relate Calendar[Date] to Data[{t}] (many-to-one).", f"Calendar = CALENDAR(DATE(YEAR(MIN(Data[{t}])),1,1), DATE(YEAR(MAX(Data[{t}])),12,31))", "",
                f"{nice(m1)} LY = CALCULATE([{mm}], SAMEPERIODLASTYEAR('Calendar'[Date]))", f"{nice(m1)} YoY % = DIVIDE([{mm}] - [{nice(m1)} LY], [{nice(m1)} LY])",
                f"{nice(m1)} Last 12M = CALCULATE([{mm}], DATESINPERIOD('Calendar'[Date], MAX(Data[{t}]), -12, MONTH))", f"{nice(m1)} Prev 12M = CALCULATE([{mm}], DATESINPERIOD('Calendar'[Date], EOMONTH(MAX(Data[{t}]), -12), -12, MONTH))", f"Growth vs prev 12M % = DIVIDE([{nice(m1)} Last 12M] - [{nice(m1)} Prev 12M], [{nice(m1)} Prev 12M])"]
    return "\n".join(out) + "\n"

def m_text(meta, df, csv_name):
    spec, L = meta["spec"], meta["spec"]["layout"]; prof = {p["name"]: p for p in meta["profile"]}; t = L.get("time")
    def mt(col):
        p = prof[col]; s = df[col]
        if p["type"] == "datetime": return "type date" if (s.dropna() == s.dropna().dt.normalize()).all() else "type datetime"
        if pd.api.types.is_bool_dtype(s): return "type text"
        if pd.api.types.is_numeric_dtype(s): return "Int64.Type" if pd.api.types.is_integer_dtype(s) else "type number"
        return "type text"
    types = ", ".join(f'{{"{c}", {mt(c)}}}' for c in df.columns)
    out = ["// AutoDash: Power Query (M) scripts. For each block: Home > Get data > Blank query > Advanced Editor > paste, then rename the query as shown in the comment.", "",
           "// ===== Query name: Data =====", "let", f'    Source = Csv.Document(File.Contents("C:\\Users\\YOU\\Downloads\\{csv_name}"), [Delimiter=",", Columns={len(df.columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),  // <-- edit this path',
           "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),", f"    Typed = Table.TransformColumnTypes(Promoted, {{{types}}})", "in", "    Typed", ""]
    FN = {"sum": "List.Sum", "mean": "List.Average", "min": "List.Min", "max": "List.Max", "median": "List.Median"}
    def ex(m, src=None):
        col = f"{src}[{m['column']}]" if src else f"[{m['column']}]"; rc = f"Table.RowCount({src})" if src else "Table.RowCount(_)"
        if m["agg"] == "nunique": return f"List.Count(List.Distinct({col}))"
        if m["agg"] == "count": return rc
        if m["agg"] == "rate": return f"List.Count(List.Select({col}, each _ = {_lit(m['positive'])})) / {rc}"
        return f"{FN[m['agg']]}({col})"
    if t: out += ["// ===== Query name: Calendar (optional, instead of the DAX Calendar table) =====", "let", f"    Start = Date.From(List.Min(Data[{t}])),", f"    End = Date.From(List.Max(Data[{t}])),", "    Dates = List.Dates(Start, Duration.Days(End - Start) + 1, #duration(1,0,0,0)),", '    T = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),', '    Typed = Table.TransformColumnTypes(T, {{"Date", type date}}),', '    WithYear = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),', '    WithMonth = Table.AddColumn(WithYear, "Month", each Date.MonthName([Date]), type text)', "in", "    WithMonth", ""]
    for p in spec["panels"]:
        q = p.get("query")
        if not q: continue
        G = list(q.get("group_by", [])); prev = "Source"; steps = ["    Source = Data"]
        if t in G:
            fn = {"D": "Date.From", "M": "Date.StartOfMonth", "Q": "Date.StartOfQuarter", "Y": "Date.StartOfYear"}[q.get("time_grain", "M")]
            steps.append(f'    WithPeriod = Table.AddColumn(Source, "{t}_period", each {fn}([{t}]), type date)'); prev = "WithPeriod"; G = [f"{t}_period" if g == t else g for g in G]
        aggs = ", ".join(f'{{"{m["column"]}_{m["agg"]}", each {ex(m)}, type nullable number}}' for m in q["metrics"])
        steps.append(f'    Grouped = Table.Group({prev}, {{{", ".join(chr(34) + g + chr(34) for g in G)}}}, {{{aggs}}})'); first = f'{q["metrics"][0]["column"]}_{q["metrics"][0]["agg"]}'
        steps.append(f'    Sorted = Table.Sort(Grouped, {{{{"{G[0]}", Order.Ascending}}}})' if G[0].endswith("_period") else f'    Sorted = Table.Sort(Grouped, {{{{"{first}", Order.Descending}}}})'); steps.append(f'    Result = Table.FirstN(Sorted, {q.get("limit", 100)})')
        out += [f"// ===== Query name: {re.sub(r'[^A-Za-z0-9 ]+', '', p['title'])[:40]} =====", "let", ",\n".join(steps), "in", "    Result", ""]
    return "\n".join(out)

def readme_text(meta, csv_name):
    spec, L = meta["spec"], meta["spec"]["layout"]; rec = L["records"]["label"]; names = _names(spec, rec); tgt = L.get("target"); M = lambda m: f"[{names[mkey(m)]}]"; vis = []
    flt = [f["column"] for f in spec["filters"] if f["type"] == "multiselect"]
    vis.append(("Slicers", ", ".join(f"Data[{c}]" for c in flt) + (f" · Calendar[Date]" if L.get("time") else ""), "Left or top"))
    vis.append((f"Card x{len(spec['kpis'])}", " · ".join(f"[{names[mkey(k)]}]" for k in spec["kpis"]), "Top row"))
    for p in spec["panels"]:
        q = p.get("query"); ty = p["type"]
        if ty == "trend": vis.append(("Line and clustered column chart", f"Axis = Calendar[Date] (Year > Month) · Columns = {M(q['metrics'][0])}" + (f" · Line = {M(q['metrics'][1])}" if len(q["metrics"]) > 1 else ""), p["title"]))
        elif ty == "yearly": vis.append(("Clustered column + line", f"Axis = Calendar[Year] · {M(q['metrics'][0])}" + (f" · Line = {M(q['metrics'][1])}" if len(q["metrics"]) > 1 else ""), p["title"]))
        elif ty == "bar": vis.append(("Clustered bar chart", f"Y-axis = Data[{q['group_by'][0]}] · X-axis = {M(q['metrics'][0])} (sort descending)", p["title"]))
        elif ty == "list": vis.append(("Bar chart", f"Axis = Data[{q['group_by'][0]}] · Values = {M(q['metrics'][0])}", p["title"]))
        elif ty == "donut": vis.append(("Donut chart", f"Legend = Data[{q['group_by'][0]}] · Values = {M(q['metrics'][0])}", p["title"]))
        elif ty == "top": vis.append(("Table", f"Data[{q['group_by'][0]}] · " + " · ".join(M(m) for m in q["metrics"]) + f" → Filters pane: Top N = 5 by {M(q['metrics'][0])}", p["title"]))
        elif ty == "segments": vis.append(("Key influencers", f"Analyze = Data[{tgt['column']}] (value {tgt['positive']}) · Explain by = the category columns and the *_band columns", p["title"]))
    tbl = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in vis); stem = csv_name.rsplit(".", 1)[0]
    return f"""# Power BI kit: {spec['title']}

Built from **{meta['filename']}** ({len(meta['profile'])} columns, {meta['rows']:,} rows). A native `.pbix` file is a closed binary format that cannot be generated safely outside Power BI Desktop, so this kit gives you everything needed to recreate the dashboard in a few minutes. Every visual below matches a panel of the AutoDash dashboard, and each panel's title says exactly what it shows.

## Files
| File | What it is |
|---|---|
| `{csv_name}` | Your cleaned data (dates as ISO text, numbers as numbers){' including the derived *_band columns used for ' + tgt['column'] + ' analysis' if tgt else ''} |
| `queries.pq` | Power Query (M) scripts: the Data query, an optional Calendar, and one summary query per panel |
| `measures.dax` | DAX measures{' (including ' + nice(tgt['column']) + ' Rate)' if tgt else ''} |
| `theme.json` | A Power BI report theme that matches the AutoDash look |

## Steps (about 5 minutes)
1. **Load the data.** Power BI Desktop > Get data > Text/CSV > pick `{csv_name}` > Transform Data. Rename the query to **Data** and make sure column types look right (or paste the first block of `queries.pq` into a Blank Query and edit the file path). Close & Apply.
2. **Add a date table** (only if the data has dates). Modeling > New table > paste the `Calendar = ...` line from `measures.dax`, then relate `Calendar[Date]` to `Data[{L.get('time') or 'date'}]` in Model view.
3. **Add the measures.** Modeling > New measure, paste each line of `measures.dax`.
4. **Apply the theme.** View > Themes > Browse for themes > `theme.json`.
5. **Build the visuals** using this table:

| Visual | Fields | Dashboard panel |
|---|---|---|
{tbl}

## Why these choices
Sum measures add up the column, rate/price/duration columns use averages, yes/no outcome columns are shown as a **rate** (share of rows), and identifier columns use distinct counts. Share-of-total visuals only use sums or row counts, because shares of averages are meaningless. The dashboard's **How it was built** panel lists the reason for every choice.
"""

def build_kit(df, meta, insights, opts=None):
    opts = opts or {}; stem = _stem(meta); csv_name = f"{stem}-data.csv"; out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]): out[c] = out[c].dt.strftime("%Y-%m-%d" if (out[c].dropna() == out[c].dropna().dt.normalize()).all() else "%Y-%m-%d %H:%M:%S")
    th = THEMES.get(opts.get("theme"), THEMES["dark"]); buf = io.BytesIO()
    theme = json.dumps({"name": "AutoDash", "dataColors": PAL, "background": th["card"], "foreground": th["fg"], "tableAccent": PAL[0], "textClasses": {"label": {"color": th["mut"]}, "title": {"color": th["fg"]}}}, indent=2)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(csv_name, out.to_csv(index=False)); z.writestr("queries.pq", m_text(meta, df, csv_name)); z.writestr("measures.dax", dax_text(meta)); z.writestr("theme.json", theme); z.writestr("README.md", readme_text(meta, csv_name))
    return buf.getvalue()
