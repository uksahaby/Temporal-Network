import sys
import json
from pathlib import Path
import pandas as pd
from app.services.network_analysis import TemporalNetworkAnalyzer
from app.services.data_loader import DataLoader
from app.utils.analysis_cache import load_analysis_result, save_analysis_result


def main(file_id: str):
    upload_dir = Path("data/uploads")
    metadata_path = upload_dir / f"{file_id}_metadata.json"
    if not metadata_path.exists():
        print(f"Metadata for {file_id} not found at {metadata_path}")
        return 1

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    processed = metadata.get('processed_data') or {}
    edges = processed.get('edges')
    stored_path = metadata.get('file_path')
    filename = metadata.get('filename')

    # If edges missing, try to reload via DataLoader
    if not edges:
        print('No processed edges in metadata; attempting to reload source file')
        import asyncio
        dl = DataLoader()
        try:
            refreshed = asyncio.run(dl.load_from_path(Path(stored_path), filename))
        except Exception as e:
            print('Reload via DataLoader failed:', e)
            refreshed = {}
        processed = refreshed.get('processed_data') or {}
        edges = processed.get('edges')

    if not edges:
        print('No edges available after reload; aborting')
        return 1

    # If processed edges appear to be sampled/truncated (sampling_rate < 1 or fewer than total_edges),
    # prefer reloading the full raw data via DataLoader (raw_data) and build from that.
    try:
        sampling_rate = float(processed.get('sampling_rate', 1)) if processed else 1
    except Exception:
        sampling_rate = 1
    if edges and processed.get('total_edges') and len(edges) < int(processed.get('total_edges', 0)):
        need_full = True
    elif edges and sampling_rate < 1.0:
        need_full = True
    else:
        need_full = False

    if need_full:
        print('Detected sampled processed edges; attempting to load full raw file via DataLoader')
        import asyncio
        dl = DataLoader()
        try:
            refreshed = asyncio.run(dl.load_from_path(Path(stored_path), filename))
            raw = refreshed.get('raw_data') or []
            if raw:
                df = pd.DataFrame(raw)
                edges = df.to_dict('records')
                print(f'Reloaded full raw data: {len(edges)} edges available')
            else:
                print('Raw data not returned by DataLoader; falling back to processed edges')
        except Exception as e:
            print('Failed to reload raw data:', e)

    print(f'Loaded {len(edges)} edges; constructing global graph (this may use significant memory)')
    tna = TemporalNetworkAnalyzer()

    # Build DataFrame and create a single graph via internal helper
    df = pd.DataFrame(edges)
    # Normalize column names: ensure 'source','target','timestamp' exist
    if 'source' not in df.columns or 'target' not in df.columns:
        cols = list(df.columns)
        # If columns are positional (0,1,2...) or unnamed, map first three to source/target/timestamp
        if len(cols) >= 2:
            mapping = {}
            if 'source' not in df.columns:
                mapping[cols[0]] = 'source'
            if 'target' not in df.columns and len(cols) > 1:
                mapping[cols[1]] = 'target'
            if 'timestamp' not in df.columns and len(cols) > 2:
                mapping[cols[2]] = 'timestamp'
            if mapping:
                try:
                    df = df.rename(columns=mapping)
                    print(f'Auto-mapped columns: {mapping}')
                except Exception:
                    pass
    # Debugging: print columns and a small sample to help diagnose mapping issues
    try:
        print('DEBUG: df.columns ->', list(df.columns))
        print('DEBUG: sample rows ->')
        print(df.head(3).to_dict('records'))
    except Exception:
        pass
    # If raw reload produced a single string column with comma-separated fields, split it
    if df.shape[1] == 1 and df.iloc[:, 0].dtype == object:
        sample_vals = df.iloc[:5, 0].astype(str).tolist()
        if all(',' in s for s in sample_vals):
            try:
                df = df.iloc[:, 0].str.split(',', expand=True)
                print('Split single-column raw rows into', df.shape[1], 'columns')
            except Exception as e:
                print('Failed to split single-column raw data:', e)
    # After splitting, ensure timestamp column exists and convert to datetime if present
    if 'timestamp' not in df.columns and df.shape[1] >= 3:
        # assume third or fourth column may be timestamp (common formats)
        ts_col = None
        # prefer 3rd index (2) if numeric-looking
        for idx in [3,2]:
            if idx < df.shape[1]:
                sample = str(df.iloc[0, idx])
                if sample.isdigit() or re.match(r"^\d{9,13}$", sample):
                    ts_col = idx
                    break
        if ts_col is not None:
            df = df.rename(columns={df.columns[0]: 'source', df.columns[1]: 'target', df.columns[ts_col]: 'timestamp'})
    # Final normalization pass: map positional columns if still missing
    if 'source' not in df.columns or 'target' not in df.columns:
        cols = list(df.columns)
        if len(cols) >= 2:
            rename_map = {cols[0]: 'source', cols[1]: 'target'}
            try:
                df = df.rename(columns=rename_map)
                print('Final auto-mapped positional columns to source/target')
            except Exception:
                pass
    # Use a dummy window start/end
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    win_start = now
    win_end = now + timedelta(seconds=1)

    # Reuse _create_graph_from_edges to build igraph
    try:
        window_key, G = tna._create_graph_from_edges(df, win_start, win_end)
    except Exception as e:
        print('Failed to build graph:', e)
        return 1

    print(f'Graph built: nodes={G.vcount()}, edges={G.ecount()}')

    print('Running global community detection (this may take time)')
    G = tna._ensure_communities_sync(G)

    # Prepare node->community mapping
    nodes = G.vs['name']
    communities = G.vs['community'] if 'community' in G.vs.attribute_names() else [-1] * G.vcount()

    node_rows = [(str(n), int(c)) for n, c in zip(nodes, communities)]
    node_df = pd.DataFrame(node_rows, columns=['node', 'community'])

    out_dir = Path('data/analysis_cache')
    out_dir.mkdir(parents=True, exist_ok=True)
    node_csv_path = out_dir / f"{file_id}_node_communities.csv"
    node_df.to_csv(node_csv_path, index=False)
    print(f'Wrote node->community CSV to {node_csv_path} ({len(node_df)} rows)')

    # Summarize communities
    from collections import Counter
    counter = Counter(communities)
    summary = []
    for comm_id, count in counter.items():
        members = [nodes[i] for i, c in enumerate(communities) if c == comm_id]
        summary.append({
            'communityId': int(comm_id),
            'size': int(count),
            'sampleMembers': [str(m) for m in members[:100]]
        })

    summary.sort(key=lambda x: x['size'], reverse=True)
    summary_path = out_dir / f"{file_id}_global_communities.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({'communities': summary, 'total_communities': len(summary)}, f)
    print(f'Wrote community summary to {summary_path}')

    # Try to merge into existing analysis result if present
    try:
        existing = load_analysis_result(f"{file_id}_1776479226") or {}
    except Exception:
        existing = None

    # We will not overwrite existing fields; attach pointers
    result_path = out_dir / f"{file_id}_global_result_meta.json"
    meta = {
        'file_id': file_id,
        'node_communities_csv': str(node_csv_path),
        'community_summary_json': str(summary_path),
        'nodes': G.vcount(),
        'edges': G.ecount()
    }
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    print(f'Wrote global result metadata to {result_path}')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tools/run_global_communities.py <file_id>')
        sys.exit(1)
    fid = sys.argv[1]
    sys.exit(main(fid))
