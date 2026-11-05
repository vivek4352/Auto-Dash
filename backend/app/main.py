import os
import uuid
import json

from collections import Counter
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .core import config
from . import store, db, auth
from .auth import current_user
from .services.file_reader import read_file
from .services.cleaner import clean, add_bands
from .services.profiler import profile
from .services.layout import find_target, build_layout
from .services.domain_detector import detect_domain
from .services.spec_builder import build_spec
from .services.aggregator import run_query, apply_filters
from .services.insights import get_insights
from .services.query_planner import answer
from .services.forecaster import forecast
from .services.segments import segment_table
from .services.html_export import to_html
from .services.powerbi_kit import build_kit


# ---------------- FastAPI initialization ----------------

app = FastAPI(title="Auto Dashboard API")


# Normalize configured origins to avoid trailing-slash mismatches.
def normalize_origin(origin):
    if not origin:
        return None
    return origin.strip().rstrip("/")


# Allowed frontend origins.
allowed_origins = {
    normalize_origin(config.FRONTEND_ORIGIN),
    normalize_origin(os.getenv("FRONTEND_ORIGIN")),
    "https://auto-dash-zeta.vercel.app",
}

# Remove empty values.
allowed_origins.discard(None)


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),

    # Local development support.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Existing application configuration ----------------

MAX_PER_USER = int(os.getenv("MAX_DATASETS_PER_USER", "25"))

lay = lambda m: m["spec"].get("layout") or build_layout(m["profile"])

def get(i, user):
    """Load a dataset only if it belongs to the signed-in user (anyone else gets 404, never a hint that it exists)."""
    if not db.owns(i, user["id"]): raise HTTPException(404, "Dataset not found")
    df, meta = store.load(i)
    if df is None: raise HTTPException(404, "Dataset not found")
    return df, meta

@app.get("/health")
def health(): return {"status": "ok"}

# ---------------- auth ----------------
@app.get("/api/auth/config")
def auth_config(): return {"google_client_id": auth.GOOGLE_CLIENT_ID, "dev_mode": auth.DEV_MODE}

def _session(u): return {"token": auth.make_token(u["id"]), "user": {k: u[k] for k in ("id", "email", "name", "picture")}}

@app.post("/api/auth/google")
def auth_google(body: dict = Body(...)):
    info = auth.verify_google(str(body.get("credential", "")))
    return _session(db.upsert_user(info["sub"], info["email"], info["name"], info["picture"]))

@app.post("/api/auth/dev")
def auth_dev(body: dict = Body(...)):
    if not auth.DEV_MODE: raise HTTPException(404, "Not found")
    email = str(body.get("email") or "demo@example.com")[:120]
    return _session(db.upsert_user("dev:" + email, email, str(body.get("name") or email.split("@")[0]), ""))

@app.get("/api/me")
def me(user=Depends(current_user)): return {k: user[k] for k in ("id", "email", "name", "picture")}

# ---------------- datasets ----------------
@app.get("/api/datasets")
def my_datasets(user=Depends(current_user)): return {"datasets": db.list_datasets(user["id"])}

@app.post("/api/datasets/upload")
async def upload(file: UploadFile = File(...), user=Depends(current_user)):
    if not file.filename.lower().endswith((".csv", ".tsv", ".xlsx", ".xls")): raise HTTPException(415, "Upload a .csv, .tsv, .xlsx or .xls file")
    if db.count_datasets(user["id"]) >= MAX_PER_USER: raise HTTPException(409, f"You have {MAX_PER_USER} saved dashboards. Delete one to upload another.")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024: raise HTTPException(413, f"File exceeds {config.MAX_UPLOAD_MB} MB")
    try: raw = read_file(file.filename, data)
    except Exception as e: raise HTTPException(400, f"Could not read file: {e}")
    if raw.empty or len(raw.columns) < 2: raise HTTPException(400, "The file needs at least two columns and one row of data.")
    truncated = len(raw) > config.MAX_ROWS
    log = ["Column names converted to lower_snake_case (word boundaries such as MonthlyCharges are kept)"]
    df = clean(raw.head(config.MAX_ROWS), log); prof = profile(df); tg = find_target(prof)
    if tg: df = add_bands(df, prof, tg, log); prof = profile(df)
    dom = detect_domain(df, prof); spec = build_spec(df, prof, dom, file.filename)
    i = uuid.uuid4().hex
    pipe = {"format": file.filename.rsplit(".", 1)[-1].lower(), "raw_rows": int(raw.shape[0]), "raw_cols": int(raw.shape[1]), "rows": len(df), "truncated": truncated, "cleaning": log,
            "roles": dict(Counter(p["role"] for p in prof)), "domain": dom, "duplicates": int(df.duplicated().sum()), "ai_spec": False}
    store.save(i, df, {"id": i, "filename": file.filename, "rows": len(df), "truncated": truncated, "status": "ready", "profile": prof, "domain": dom, "spec": spec, "pipeline": pipe})
    db.add_dataset(i, user["id"], file.filename, spec["title"], len(df))
    return {"id": i, "status": "ready", "truncated": truncated}

@app.get("/api/datasets/{i}/status")
def status(i: str, user=Depends(current_user)): _, m = get(i, user); return {"id": i, "status": m["status"]}

@app.get("/api/datasets/{i}/profile")
def get_profile(i: str, user=Depends(current_user)): _, m = get(i, user); return {"rows": m["rows"], "domain": m["domain"], "columns": m["profile"]}

@app.get("/api/dashboards/{i}")
def dashboard(i: str, user=Depends(current_user)):
    _, m = get(i, user); return {"spec": m["spec"], "profile": m["profile"], "filename": m["filename"], "rows": m["rows"], "pipeline": m.get("pipeline")}

@app.post("/api/dashboards/{i}/query")
def query(i: str, q: dict = Body(...), user=Depends(current_user)):
    df, _ = get(i, user)
    try: return {"rows": run_query(df, q)}
    except (ValueError, KeyError) as e: raise HTTPException(422, str(e))

@app.post("/api/dashboards/{i}/segments")
def segments(i: str, body: dict = Body(default={}), user=Depends(current_user)):
    df, m = get(i, user); tgt = lay(m).get("target")
    if not tgt: raise HTTPException(422, "This dataset has no outcome (yes/no) column to analyse.")
    return segment_table(apply_filters(df, body.get("filters")), m["profile"], tgt)

@app.get("/api/datasets/{i}/rows")
def rows(i: str, limit: int = 50, offset: int = 0, user=Depends(current_user)):
    df, _ = get(i, user); return {"total": len(df), "rows": json.loads(df.iloc[offset:offset + min(limit, 500)].to_json(orient="records", date_format="iso"))}

@app.get("/api/datasets/{i}/insights")
def insights(i: str, user=Depends(current_user)): df, m = get(i, user); return get_insights(df, m["profile"], lay(m))

@app.post("/api/datasets/{i}/chat")
def chat(i: str, body: dict = Body(...), user=Depends(current_user)): df, m = get(i, user); return answer(df, m["profile"], str(body.get("message", ""))[:500])

@app.post("/api/datasets/{i}/forecast")
def do_forecast(i: str, body: dict = Body(default={}), user=Depends(current_user)):
    df, m = get(i, user); fc = {**(m["spec"].get("forecast") or {}), **body}
    if not (fc.get("date_column") in df.columns and fc.get("measure") in df.columns): raise HTTPException(422, "This dataset has no date column to forecast over.")
    try: return forecast(df, fc["date_column"], fc["measure"], int(fc.get("periods", 6)))
    except ValueError as e: raise HTTPException(422, str(e))

@app.post("/api/datasets/{i}/export/{kind}")
def export(i: str, kind: str, body: dict = Body(default={}), user=Depends(current_user)):
    df, m = get(i, user); ins = get_insights(df, m["profile"], lay(m))["insights"]
    if kind == "html":
        if len(df) > 100_000: raise HTTPException(413, "Too large for an interactive HTML download (limit 100,000 rows). Use the Power BI kit instead.")
        return Response(to_html(df, m, ins, body), media_type="text/html; charset=utf-8", headers={"Content-Disposition": "attachment; filename=dashboard.html"})
    if kind == "powerbi":
        return Response(build_kit(df, m, ins, body), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=powerbi-kit.zip"})
    raise HTTPException(404, "Unknown export format. Use 'html' or 'powerbi'.")

@app.delete("/api/datasets/{i}")
def delete(i: str, user=Depends(current_user)):
    get(i, user); store.delete(i); db.delete_dataset(i, user["id"]); return {"deleted": True}
