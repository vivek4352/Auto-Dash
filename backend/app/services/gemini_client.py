"""Gemini wrapper: retries + backoff. Only schema/stats are sent, never raw rows. Returns None if unavailable."""
import json, re, time, requests
from ..core import config

def generate_json(prompt, model=None):
    if not config.GEMINI_API_KEY:
        return None
    model = model or config.GEMINI_MODEL_SPEC
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    for i in range(3):
        try:
            r = requests.post(url, json=body, timeout=30)
            r.raise_for_status()
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(re.sub(r"^```(json)?|```$", "", txt).strip())
        except Exception:
            time.sleep(2 ** i)
    return None
