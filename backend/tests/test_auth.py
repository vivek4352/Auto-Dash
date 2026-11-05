from .conftest import *
from app import auth

def test_requires_login(client):
    assert client.post("/api/datasets/upload", files={"file": ("a.csv", b"a,b\n1,2")}).status_code == 401
    assert client.get("/api/datasets").status_code == 401
    assert client.get("/api/datasets", headers={"Authorization": "Bearer not.a.token"}).status_code == 401

def test_each_user_only_sees_their_own_data(client):
    A, B = login(client, "alice@x.com"), login(client, "bob@x.com"); i = upload(client, A, churn_df(), "mine.csv")
    assert [d["id"] for d in client.get("/api/datasets", headers=A).json()["datasets"]] == [i] or i in [d["id"] for d in client.get("/api/datasets", headers=A).json()["datasets"]]
    assert i not in [d["id"] for d in client.get("/api/datasets", headers=B).json()["datasets"]]
    for path in (f"/api/dashboards/{i}", f"/api/datasets/{i}/insights", f"/api/datasets/{i}/rows"): assert client.get(path, headers=B).status_code == 404
    assert client.post(f"/api/dashboards/{i}/query", json={"metrics": [{"column": "tenure", "agg": "sum"}]}, headers=B).status_code == 404
    assert client.post(f"/api/datasets/{i}/export/html", json={}, headers=B).status_code == 404
    assert client.delete(f"/api/datasets/{i}", headers=B).status_code == 404 and dash(client, A, i)["spec"]   # B could not delete it
    assert client.delete(f"/api/datasets/{i}", headers=A).status_code == 200 and client.get(f"/api/dashboards/{i}", headers=A).status_code == 404

def test_previous_data_comes_back_after_signing_in_again(client):
    H1 = login(client, "carol@x.com"); i = upload(client, H1, churn_df(), "kept.csv")
    H2 = login(client, "carol@x.com")                       # a brand-new session for the same account
    got = client.get("/api/datasets", headers=H2).json()["datasets"]; assert [d["id"] for d in got] == [i] and got[0]["filename"] == "kept.csv"
    assert dash(client, H2, i)["spec"]["title"]

def test_google_and_dev_login(client, monkeypatch):
    assert client.get("/api/auth/config").json()["dev_mode"] is True
    monkeypatch.setattr(auth, "verify_google", lambda c: {"sub": "g-123", "email": "g@gmail.com", "name": "G User", "picture": "http://p"})
    r = client.post("/api/auth/google", json={"credential": "x"}).json(); H = {"Authorization": "Bearer " + r["token"]}
    assert r["user"]["email"] == "g@gmail.com" and client.get("/api/me", headers=H).json()["name"] == "G User"
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", ""); monkeypatch.undo()
    assert client.post("/api/auth/google", json={"credential": "bad"}).status_code in (401, 503)    # a forged credential never logs in
    monkeypatch.setattr(auth, "DEV_MODE", False); assert client.post("/api/auth/dev", json={"email": "x@x.com"}).status_code == 404   # dev login is off in production
