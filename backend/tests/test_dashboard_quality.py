import os, pytest
from .conftest import *

TITLES = lambda d: [p["title"] for p in d["spec"]["panels"]]

def test_names_flags_and_outcome_are_understood(client):
    H = login(client, "q1@x.com"); i = upload(client, H, churn_df()); d = dash(client, H, i); P = {p["name"]: p for p in d["profile"]}
    assert {"customer_id", "senior_citizen", "monthly_charges", "total_charges", "internet_service"} <= set(P)          # camelCase split into words
    assert P["senior_citizen"]["type"] == "flag" and P["senior_citizen"]["role"] == "flag" and P["churn"]["type"] == "flag"  # a 0/1 column is never a measure
    L = d["spec"]["layout"]; assert L["target"]["column"] == "churn" and L["target"]["positive"] == "Yes" and L["drivers"][0] == "contract"
    k = {x["label"]: x for x in d["spec"]["kpis"]}; assert "Churn Rate" in k and k["Churn Rate"]["agg"] == "rate" and not any("Senior" in x for x in k)
    assert d["spec"]["title"] == "Customer Churn Dashboard"

def test_no_misleading_panels_without_dates(client):
    H = login(client, "q2@x.com"); d = dash(client, H, upload(client, H, churn_df())); S = d["spec"]; types = [p["type"] for p in S["panels"]]; T = TITLES(d)
    assert not {"trend", "yearly"} & set(types) and S["layout"]["time"] is None and not S["forecast"]["enabled"]      # no date column: no trend, period or forecast
    assert not any(w in " ".join(T).lower() for w in ("trend", "over time", "period", "yearly", "top 5"))               # no 'Top 5 by Gender'
    assert not any(k in S["strip"] for k in ("growth", "best"))
    for p in S["panels"]:
        if p["type"] == "donut": assert all(m["agg"] in ("sum", "count") for m in p["query"]["metrics"])               # never a donut of averages
        if p.get("query"): assert client.post(f"/api/dashboards/{d['spec'] and client.get('/api/datasets',headers=H).json()['datasets'][0]['id']}/query", json=p["query"], headers=H).json()["rows"]

def test_numbers_are_right(client):
    H = login(client, "q3@x.com"); df = churn_df(); i = upload(client, H, df); d = dash(client, H, i)
    body = {"metrics": [{"column": "churn", "agg": "rate", "positive": "Yes"}, {"column": "tenure", "agg": "mean"}]}; r = client.post(f"/api/dashboards/{i}/query", json=body, headers=H).json()["rows"][0]
    assert abs(r["churn_rate"] - (df["Churn"] == "Yes").mean()) < 1e-9 and abs(r["tenure_mean"] - df["tenure"].mean()) < 1e-9
    g = client.post(f"/api/dashboards/{i}/query", json={"metrics": [body["metrics"][0]], "group_by": ["contract"]}, headers=H).json()["rows"]
    assert {x["contract"]: round(x["churn_rate"], 6) for x in g} == {k: round(v, 6) for k, v in (df.assign(y=df.Churn == "Yes").groupby("Contract").y.mean()).items()}
    s = client.post(f"/api/dashboards/{i}/segments", json={}, headers=H).json(); assert s["top"][0]["label"].startswith(("Contract: Month-to-month", "Tenure")) and s["top"][0]["rate"] > s["overall"]
    assert client.post(f"/api/dashboards/{i}/query", json={"metrics": [{"column": "churn", "agg": "rate"}]}, headers=H).status_code == 422       # rate needs its positive value

def test_sales_data_still_gets_a_trend(client):
    H = login(client, "q4@x.com"); r = np.random.default_rng(2); n = 500
    df = pd.DataFrame({"Order Date": pd.date_range("2022-01-01", periods=n, freq="2D").astype(str), "Sales": r.uniform(10, 500, n).round(2), "Profit": r.normal(40, 30, n).round(2), "Region": r.choice(["N", "S", "E", "W"], n), "Category": r.choice(["A", "B", "C"], n), "Product Name": [f"P{x}" for x in r.integers(0, 60, n)]})
    d = dash(client, H, upload(client, H, df)); T = TITLES(d); assert "Sales & Profit over time" in T and any(t.startswith("Top 5 Product Name") for t in T) and d["spec"]["forecast"]["enabled"]

def test_edge_files_do_not_crash(client):
    H = login(client, "q5@x.com"); r = np.random.default_rng(3)
    for df in (pd.DataFrame({"a": r.random(60), "b": r.random(60) * 100}), pd.DataFrame({"city": r.choice(["x", "y", "z"], 80), "kind": r.choice(["p", "q"], 80)}), pd.DataFrame({"flag": r.choice(["Yes", "No"], 50), "v": r.random(50)})):
        i = upload(client, H, df); d = dash(client, H, i); assert d["spec"]["panels"] and client.get(f"/api/datasets/{i}/insights", headers=H).status_code == 200
        assert client.post(f"/api/datasets/{i}/chat", json={"message": "total by city"}, headers=H).status_code == 200
        for kind in ("html", "powerbi"): assert client.post(f"/api/datasets/{i}/export/{kind}", json={}, headers=H).status_code == 200

REAL = "/mnt/user-data/uploads/Telco_Customer_Churn_Dataset___2_.csv"
@pytest.mark.skipif(not os.path.exists(REAL), reason="telco file not present")
def test_real_telco_file(client):
    H = login(client, "q6@x.com"); i = upload(client, H, open(REAL, "rb").read(), "Telco.csv"); d = dash(client, H, i); S = d["spec"]
    t = client.post(f"/api/dashboards/{i}/query", json={"metrics": [{"column": c["column"], "agg": c["agg"], **({"positive": c["positive"]} if "positive" in c else {})} for c in S["kpis"]]}, headers=H).json()["rows"][0]
    assert t["customer_id_count"] == 7043 and abs(t["churn_rate"] - 0.2654) < 0.001 and "Seniorcitizen" not in " ".join(k["label"] for k in S["kpis"]) and S["layout"]["time"] is None
    assert "Churn rate by Contract" in TITLES(d) and not any("Top 5" in x for x in TITLES(d))
