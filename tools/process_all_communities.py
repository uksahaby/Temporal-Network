import json
from pathlib import Path
from app.services.network_analysis import TemporalNetworkAnalyzer
import pandas as pd
from datetime import datetime

TASK_ID = '855c82689571bc2e_1776479226'
CACHE_PATH = Path('data/analysis_cache') / f"{TASK_ID}.json"
BATCH_SIZE = 50
MAX_NODES_COMMUNITY = 2000
MAX_EDGES_COMMUNITY = 5000

if not CACHE_PATH.exists():
    print('analysis cache file not found:', CACHE_PATH)
    raise SystemExit(1)

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

viz = data.get('visualization_data', {})
if not viz:
    print('No visualization_data found in analysis result')
    raise SystemExit(1)

time_windows = viz.get('time_windows', [])
if not time_windows:
    print('No time windows found in visualization_data')
    raise SystemExit(1)

analyzer = TemporalNetworkAnalyzer()
processed = []
# If partial community data exists, resume
existing = data.get('community_visualization_data', {})
existing_windows = existing.get('time_windows', []) if existing else []
processed_keys = {w['window_key'] for w in existing_windows} if existing_windows else set()

total = len(time_windows)
print(f'Total windows to process: {total}. Resuming, already processed: {len(processed_keys)}')

for i in range(0, total, BATCH_SIZE):
    batch = time_windows[i:i+BATCH_SIZE]
    batch_results = []
    for w in batch:
        window_key = w.get('window_key') or f"{w.get('start')}_{w.get('end')}"
        if window_key in processed_keys:
            print('Skipping already processed window', window_key)
            continue
        edges = w.get('edges', [])
        if not edges:
            print('Skipping window with no edges', window_key)
            continue
        df = pd.DataFrame(edges)
        if 'source' not in df.columns or 'target' not in df.columns:
            print('Skipping malformed window', window_key)
            continue
        try:
            # Attempt to parse window times
            start_str, end_str = window_key.split('_')
            win_start = datetime.fromisoformat(start_str)
            win_end = datetime.fromisoformat(end_str)
        except Exception:
            try:
                win_start = datetime.fromisoformat(w.get('start'))
                win_end = datetime.fromisoformat(w.get('end'))
            except Exception:
                win_start = datetime.utcnow()
                win_end = win_start
        try:
            win_key, G = analyzer._create_graph_from_edges(df, win_start, win_end)
            if G is None:
                print('Graph creation failed for', window_key)
                continue
            # Community detection (synchronous)
            Gc = analyzer._ensure_communities_sync(G)
            summary = analyzer._summarize_community_window(win_key, Gc, {}, MAX_NODES_COMMUNITY, MAX_EDGES_COMMUNITY)
            if summary:
                batch_results.append(summary)
                processed_keys.add(window_key)
                print(f'Processed window {window_key}: communities={summary.get("totalCommunities")}, nodes={summary.get("totalNodes")}, edges={summary.get("totalEdges")}')
            else:
                print('No summary for', window_key)
        except Exception as e:
            print('Error processing', window_key, e)

    # Append batch_results to data and persist incrementally
    if batch_results:
        cvd = data.get('community_visualization_data') or {'time_windows': [], 'summary': {}}
        if not isinstance(cvd, dict):
            cvd = {'time_windows': [], 'summary': {}}
        cvd.setdefault('time_windows', [])
        cvd.setdefault('summary', {})
        cvd['time_windows'].extend(batch_results)
        # Update summary
        cvd['summary']['processed_windows'] = len(cvd['time_windows'])
        data['community_visualization_data'] = cvd
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str)
        print(f'Persisted batch up to index {i+BATCH_SIZE} (total processed windows: {len(data["community_visualization_data"]["time_windows"])})')

print('Completed processing all windows')
