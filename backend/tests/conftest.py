import os, tempfile
os.environ["AUTH_DEV_MODE"] = "1"; os.environ["DATA_DIR"] = tempfile.mkdtemp(); os.environ["JWT_SECRET"] = "test-secret"
import io, numpy as np, pandas as pd, pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client(): return TestClient(app)

def login(client, email="a@x.com"):
    return {"Authorization": "Bearer " + client.post("/api/auth/dev", json={"email": email}).json()["token"]}

def upload(client, H, df_or_bytes, name="d.csv"):
    b = df_or_bytes if isinstance(df_or_bytes, bytes) else df_or_bytes.to_csv(index=False).encode()
    r = client.post("/api/datasets/upload", files={"file": (name, b)}, headers=H); assert r.status_code == 200, r.text; return r.json()["id"]

def dash(client, H, i): return client.get(f"/api/dashboards/{i}", headers=H).json()

def churn_df(n=600, seed=0):
    r = np.random.default_rng(seed); contract = r.choice(["Month-to-month", "One year", "Two year"], n, p=[.55, .25, .2]); tenure = r.integers(0, 72, n)
    p = np.where(contract == "Month-to-month", .45, np.where(contract == "One year", .12, .03)); churn = np.where(r.random(n) < p, "Yes", "No")
    return pd.DataFrame({"customerID": [f"C{i:05d}" for i in range(n)], "gender": r.choice(["Female", "Male"], n), "SeniorCitizen": r.choice([0, 1], n, p=[.84, .16]), "Contract": contract,
                         "InternetService": r.choice(["DSL", "Fiber optic", "No"], n), "tenure": tenure, "MonthlyCharges": r.uniform(20, 110, n).round(2), "TotalCharges": (tenure * 60 + r.normal(0, 50, n)).round(2), "Churn": churn})
