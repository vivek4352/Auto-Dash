"""Google sign-in: the browser gets a Google ID token, we verify it, then issue our own short session token."""
import os, time, jwt
from fastapi import Header, HTTPException
from . import db
SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
DEV_MODE = os.getenv("AUTH_DEV_MODE", "") == "1"      # local testing only: lets you sign in without Google

def make_token(uid): return jwt.encode({"sub": uid, "exp": int(time.time()) + 30 * 86400}, SECRET, algorithm="HS256")

def verify_google(credential):
    from google.oauth2 import id_token
    from google.auth.transport import requests as grequests
    if not GOOGLE_CLIENT_ID: raise HTTPException(503, "Google sign-in is not configured on the server (set GOOGLE_CLIENT_ID).")
    try: info = id_token.verify_oauth2_token(credential, grequests.Request(), GOOGLE_CLIENT_ID)
    except Exception: raise HTTPException(401, "Google sign-in could not be verified. Please try again.")
    if not info.get("email_verified", True): raise HTTPException(401, "Your Google email is not verified.")
    return {"sub": info["sub"], "email": info.get("email", ""), "name": info.get("name") or info.get("email", ""), "picture": info.get("picture", "")}

def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "Please sign in to continue.")
    try: uid = jwt.decode(authorization.split(" ", 1)[1], SECRET, algorithms=["HS256"])["sub"]
    except Exception: raise HTTPException(401, "Your session expired. Please sign in again.")
    u = db.get_user(uid)
    if not u: raise HTTPException(401, "Account not found. Please sign in again.")
    return u
