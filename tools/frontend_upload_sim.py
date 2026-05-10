import requests
from pathlib import Path

URL = "http://127.0.0.1:8000/api/upload"
# Use the uploaded copy already in the project
FILE_PATH = Path("data/uploads/855c82689571bc2e_rec-amazon-ratings.edges")

print(f"Uploading {FILE_PATH} to {URL}...")
if not FILE_PATH.exists():
    print("File not found:", FILE_PATH)
    raise SystemExit(2)

with open(FILE_PATH, "rb") as f:
    files = {"file": (FILE_PATH.name, f, "application/octet-stream")}
    try:
        resp = requests.post(URL, files=files, timeout=120)
    except Exception as e:
        print("Request failed:", e)
        raise

print("HTTP status:", resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text[:2000])
