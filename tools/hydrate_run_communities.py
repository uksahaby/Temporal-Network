import json
from pathlib import Path
from app.services.network_analysis import TemporalNetworkAnalyzer
import pandas as pd
from datetime import datetime

TASK_ID = '855c82689571bc2e_1776474805'
CACHE_PATH = Path('data/analysis_cache') / f"{TASK_ID}.json"

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

# We'll process only the first few windows to validate
N = 3
windows_to_process = time_windows[:N]

analyzer = TemporalNetworkAnalyzer()
community_windows = []
metrics = data.get('metrics', {})

for w in windows_to_process:
    window_key = w.get('window_key') or f"{w.get('start')}_{w.get('end')}"
    print('Processing window', window_key)
    edges = w.get('edges', [])
    if not edges:
        print('  no edges in window, skipping')
        continue
    # Build DataFrame compatible with analyzer._create_graph_from_edges
    df = pd.DataFrame(edges)
    # Ensure source/target columns exist
    if 'source' not in df.columns or 'target' not in df.columns:
        print('  missing source/target columns, skipping')
        continue
    # parse window times
    try:
        start_str, end_str = window_key.split('_')
        win_start = datetime.fromisoformat(start_str)
        win_end = datetime.fromisoformat(end_str)
    except Exception:
        win_start = datetime.fromisoformat(w.get('start'))
        win_end = datetime.fromisoformat(w.get('end'))
    # Create graph
    win_key, G = analyzer._create_graph_from_edges(df, win_start, win_end)
    if G is None:
        print('  graph creation failed')
        continue
    print(f'  graph nodes={G.vcount()} edges={G.ecount()}')
    # Run community detection sync
    Gc = analyzer._ensure_communities_sync(G)
    # Summarize community window
    summary = analyzer._summarize_community_window(win_key, Gc, {}, 1000, 2000)
    if summary:
        community_windows.append(summary)
        print(f'  summarized communities: {summary.get("totalCommunities")} communities')
    else:
        print('  summarization returned None')

# Attach community_visualization_data to analysis result and persist
if community_windows:
    community_viz = {
        'time_windows': community_windows,
        'summary': {
            'processed_sample_windows': len(community_windows)
        }
    }
    data['community_visualization_data'] = community_viz
    # Save updated result
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, default=str)
    print('Wrote updated analysis result with community_visualization_data')
else:
    print('No community windows generated')
