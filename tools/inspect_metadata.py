import json
from pathlib import Path
p = Path('data/uploads/15f0d51c93872b9a_metadata.json')
if not p.exists():
    print('metadata not found')
    raise SystemExit(1)
with open(p,'r',encoding='utf-8') as f:
    data = json.load(f)
print('filename:', data.get('filename'))
print('rows:', data.get('rows'))
print('columns:', data.get('columns'))
proc = data.get('processed_data',{})
print('processed keys:', list(proc.keys()))
if 'time_range' in proc:
    print('time_range:', proc.get('time_range'))
if 'columns_used' in proc:
    print('columns_used:', proc.get('columns_used'))
if 'total_edges' in proc:
    print('total_edges:', proc.get('total_edges'))
if 'unique_nodes' in proc:
    print('unique_nodes:', proc.get('unique_nodes'))
edges = proc.get('edges')
if edges is None:
    print('edges: None')
elif isinstance(edges, list):
    print('edges sample count:', len(edges))
    print('sample edge:', edges[0] if len(edges)>0 else None)
else:
    print('edges type:', type(edges))
