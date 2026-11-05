try:
    from dotenv import load_dotenv; load_dotenv()      # reads backend/.env (GOOGLE_CLIENT_ID, JWT_SECRET ...)
except ImportError: pass
import os
DATA_DIR = os.getenv("DATA_DIR", "./data")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "200000"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_SPEC = os.getenv("GEMINI_MODEL_SPEC", "gemini-1.5-flash")
GEMINI_MODEL_CHAT = os.getenv("GEMINI_MODEL_CHAT", "gemini-1.5-flash")
