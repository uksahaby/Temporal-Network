import asyncio
import time
import json
from pathlib import Path
from app.api.endpoints import _run_community_detection_task, analysis_cache

TASK_ID = '855c82689571bc2e_1776474805'

print('Starting background community detection for', TASK_ID)
try:
    # Run the background community detection
    asyncio.run(_run_community_detection_task(TASK_ID))
except Exception as e:
    print('Community detection task raised:', e)

# Inspect cache and saved file
entry = analysis_cache.get(TASK_ID)
if not entry:
    # try to load from disk
    cache_path = Path('data/analysis_cache') / f"{TASK_ID}.json"
    if cache_path.exists():
        with open(cache_path,'r',encoding='utf-8') as f:
            entry = json.load(f)

if not entry:
    print('No analysis result found in cache or disk for', TASK_ID)
else:
    cv = entry.get('community_visualization_data')
    if cv:
        print('Community visualization data present. windows:', len(cv.get('time_windows', [])))
    else:
        print('Community visualization data still not present; check logs for errors.')
