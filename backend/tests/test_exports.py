import io, zipfile
from .conftest import *

def test_downloads_are_html_and_powerbi_only(client):
    H = login(client, "e1@x.com"); i = upload(client, H, churn_df())
    h = client.post(f"/api/datasets/{i}/export/html", json={"theme": "light"}, headers=H); assert h.status_code == 200 and "text/html" in h.headers["content-type"] and "/*__DATA__*/" not in h.text and "Customer Churn Dashboard" in h.text
    z = zipfile.ZipFile(io.BytesIO(client.post(f"/api/datasets/{i}/export/powerbi", json={}, headers=H).content)); names = set(z.namelist())
    assert {"queries.pq", "measures.dax", "theme.json", "README.md"} <= names and any(n.endswith("-data.csv") for n in names) and not any(n.endswith(".xlsx") for n in names)
    dax = z.read("measures.dax").decode(); assert 'Churn Rate = DIVIDE(CALCULATE(COUNTROWS(Data), Data[churn] = "Yes")' in dax and "Senior" not in dax.split("Churn Count")[0]
    assert "Csv.Document" in z.read("queries.pq").decode()
    for kind in ("xlsx", "tableau"): assert client.post(f"/api/datasets/{i}/export/{kind}", json={}, headers=H).status_code == 404     # removed formats
