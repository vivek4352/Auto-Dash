import os, sqlite3, datetime as dt
from .core.config import DATA_DIR
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "app.db")

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT, name TEXT, picture TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, filename TEXT, title TEXT, rows INTEGER, created_at TEXT);
    CREATE INDEX IF NOT EXISTS ix_ds_user ON datasets(user_id);"""); return c

def upsert_user(uid, email, name, picture):
    with conn() as c:
        c.execute("INSERT INTO users(id,email,name,picture,created_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET email=excluded.email,name=excluded.name,picture=excluded.picture", (uid, email, name, picture, dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()))
    return get_user(uid)

def get_user(uid):
    with conn() as c: r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None

def add_dataset(i, uid, filename, title, rows):
    with conn() as c: c.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?)", (i, uid, filename, title, rows, dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()))

def list_datasets(uid):
    with conn() as c: return [dict(r) for r in c.execute("SELECT id,filename,title,rows,created_at FROM datasets WHERE user_id=? ORDER BY created_at DESC", (uid,))]

def owns(i, uid):
    with conn() as c: return c.execute("SELECT 1 FROM datasets WHERE id=? AND user_id=?", (i, uid)).fetchone() is not None

def count_datasets(uid):
    with conn() as c: return c.execute("SELECT COUNT(*) FROM datasets WHERE user_id=?", (uid,)).fetchone()[0]

def delete_dataset(i, uid):
    with conn() as c: c.execute("DELETE FROM datasets WHERE id=? AND user_id=?", (i, uid))
