import json
import os
import sys
from pathlib import Path

TASK_ID = "855c82689571bc2e_1776474805"
ANALYSIS_PATH = Path("data/analysis_cache") / f"{TASK_ID}.json"

print(f"Loading analysis JSON: {ANALYSIS_PATH}")
if not ANALYSIS_PATH.exists():
    print("ERROR: analysis JSON not found", file=sys.stderr)
    sys.exit(2)

with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Top-level keys:", list(data.keys()))

viz = data.get("visualization_data") or data.get("visualization") or {}
comm = data.get("community_visualization_data") or data.get("communities") or {}

# time_windows can be list or dict
def count_time_windows(obj):
    if not obj:
        return 0
    tw = obj.get("time_windows") if isinstance(obj, dict) else None
    if tw is None:
        # maybe the viz itself is a dict mapping window keys
        if isinstance(obj, dict):
            # exclude metadata keys
            keys = [k for k in obj.keys() if isinstance(k, str) and "start" in k or "_" in k]
            return len(obj)
        return 0
    if isinstance(tw, list):
        return len(tw)
    if isinstance(tw, dict):
        return len(tw.keys())
    return 0

viz_count = count_time_windows(viz)
comm_count = count_time_windows(comm)
print(f"visualization_data.time_windows: {viz_count}")
print(f"community_visualization_data.time_windows: {comm_count}")

# Count windows with community summaries
windows_with_comm = 0
sample_windows = []

def iter_windows(obj):
    tw = obj.get("time_windows") if isinstance(obj, dict) else None
    if tw is None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k, v
        return
    if isinstance(tw, list):
        for item in tw:
            key = item.get("window_key") or item.get("key") or None
            yield key, item
    elif isinstance(tw, dict):
        for k, v in tw.items():
            yield k, v

if comm:
    for k, v in iter_windows(comm):
        if not v:
            continue
        # detect community entries
        if (isinstance(v, dict) and (v.get("communities") or v.get("community_summary") or v.get("nodes"))):
            windows_with_comm += 1
            if len(sample_windows) < 5:
                sample_windows.append((k, v))

print(f"windows with community data: {windows_with_comm}")
if sample_windows:
    print("Sample community window keys and summaries:")
    for k, v in sample_windows:
        print("- key:", k, "->", {k: (v.get('communities') or v.get('community_summary') or '...')})

# Now attempt API query
print('\nAttempting HTTP GET to local API for communities endpoint...')
try:
    import requests
    url = f"http://127.0.0.1:8000/api/analysis/{TASK_ID}/communities"
    print("Requesting:", url)
    resp = requests.get(url, timeout=8)
    print("HTTP status:", resp.status_code)
    ct = resp.headers.get('content-type','')
    if 'application/json' in ct:
        j = resp.json()
        # print compact summary
        if isinstance(j, dict):
            print("Response keys:", list(j.keys()))
            if 'status' in j:
                print('status:', j.get('status'))
        else:
            print('Response (json):', type(j), 'len=', len(j))
    else:
        print('Response text:', resp.text[:1000])
except Exception as e:
    print('API request failed:', repr(e))
    sys.exit(0)
