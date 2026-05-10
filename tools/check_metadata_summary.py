import json

path = 'data/uploads/855c82689571bc2e_metadata.json'
with open(path, 'r', encoding='utf-8') as f:
    j = json.load(f)
proc = j.get('processed_data') or {}
print('rows', j.get('rows'))
print('size', j.get('size'))
print('total_edges', proc.get('total_edges'))
print('unique_nodes', proc.get('unique_nodes'))
edges = proc.get('edges')
print('edges_in_metadata_len', len(edges) if isinstance(edges, list) else type(edges))
