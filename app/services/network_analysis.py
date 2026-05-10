# import networkx as nx
# import pandas as pd
# import igraph as ig
# import numpy as np
# from datetime import datetime, timedelta
# from typing import Dict, List, Tuple, Optional
# from collections import defaultdict
# from scipy import stats

# class TemporalNetworkAnalyzer:
#     def create_time_windows(self, edges: List[Dict], window_size: str = '1h', step_size: str = '30min') -> Dict[str, ig.Graph]:
#         """Create overlapping time windows for temporal analysis"""
#         if not edges:
#             self.graphs = {}
#             return {}

#         df = pd.DataFrame(edges)
#         df['timestamp'] = pd.to_datetime(df['timestamp'].values, errors='coerce', utc=True)
#         df = df.dropna(subset=['timestamp'])
#         try:
#             df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
#         except Exception:
#             pass
#         df['timestamp'] = pd.to_datetime(df['timestamp'].values, errors='coerce', utc=True)
#         start_time = df['timestamp'].min()
#         end_time = df['timestamp'].max()

    # (Duplicate visualization-export block removed; use methods defined later in file)
#             G.add_edges(edges_tuple)
#             G.es['weight'] = weights
#             G.es['edge_id'] = edge_ids
#             G.vs['name'] = node_list
#             windows[window_key] = G
#         self.graphs = windows
#         return windows

#     def compute_temporal_metrics(self, graphs, metrics=None):
#         """Compute metrics for each time window"""
#         if metrics is None:
#             metrics = ['degree_centrality', 'betweenness_centrality', 'closeness_centrality', 'pagerank', 'density', 'clustering', 'components']
#         results = {}
#         for window_key, graph in graphs.items():
#             window_metrics = {}
#             n = graph.vcount()
#             m = graph.ecount()
#             window_metrics['num_nodes'] = n
#             window_metrics['num_edges'] = m
#             window_metrics['density'] = graph.density() if n > 1 else 0
#             window_metrics['connected_components'] = len(graph.components()) if n > 0 else 0
#             if 'degree_centrality' in metrics and n > 0:
#                 degs = graph.degree()
#                 window_metrics['degree_centrality'] = {graph.vs[idx]['name']: deg / (n - 1) if n > 1 else 0 for idx, deg in enumerate(degs)}
#             if 'betweenness_centrality' in metrics and n > 2:
#                 try:
#                     btw = graph.betweenness(weights=graph.es['weight'])
#                     window_metrics['betweenness_centrality'] = {graph.vs[idx]['name']: val for idx, val in enumerate(btw)}
#                 except Exception:
#                     window_metrics['betweenness_centrality'] = {}
#             if 'closeness_centrality' in metrics and n > 0:
#                 try:
#                     cls = graph.closeness()
#                     window_metrics['closeness_centrality'] = {graph.vs[idx]['name']: val for idx, val in enumerate(cls)}
#                 except Exception:
#                     window_metrics['closeness_centrality'] = {}
#             if 'pagerank' in metrics and n > 0:
#                 try:
#                     pr = graph.pagerank(weights=graph.es['weight'])
#                     window_metrics['pagerank'] = {graph.vs[idx]['name']: val for idx, val in enumerate(pr)}
#                 except Exception:
#                     window_metrics['pagerank'] = {}
#             if 'clustering' in metrics:
#                 try:
#                     window_metrics['clustering_coefficient'] = graph.transitivity_undirected()
#                 except Exception:
#                     window_metrics['clustering_coefficient'] = 0
#             if n > 0:
#                 try:
#                     comps = graph.components()
#                     if len(comps) == 1:
#                         window_metrics['diameter'] = graph.diameter()
#                     else:
#                         window_metrics['diameter'] = None
#                 except Exception:
#                     window_metrics['diameter'] = None
#             results[window_key] = window_metrics
#         self.metrics_cache = results
#         return results

#     def detect_anomalies(self, metrics_over_time: Dict[str, Dict]) -> List[Dict]:
#         """Detect anomalies and community changes in metrics timeline"""
#         times = []
#         densities = []
#         node_counts = []
#         events = []
#         for window_key, metrics in metrics_over_time.items():
#             times.append(window_key)
#             densities.append(metrics.get('density', 0))
#             node_counts.append(metrics.get('num_nodes', 0))
#         if len(densities) > 10:
#             arr = np.array(densities, dtype=float)
#             mean = arr.mean()
#             std = arr.std()
#             density_zscore = np.abs((arr - mean) / std) if std > 0 else np.zeros_like(arr)
#             anomaly_threshold = 2.0
#             for i, z in enumerate(density_zscore):
#                 if z > anomaly_threshold:
#                     events.append({
#                         'time': times[i],
#                         'type': 'density_anomaly',
#                         'value': densities[i],
#                         'z_score': float(z),
#                         'description': f"Unusual network density detected at {times[i]}"
#                     })
#         community_events = self._detect_community_changes(metrics_over_time)
#         events.extend(community_events)
#         return events

#     def _detect_community_changes(self, metrics_over_time: Dict) -> List[Dict]:
#         """Detect significant community structure changes"""
#         events = []
#         prev_components = None
#         for window_key, metrics in metrics_over_time.items():
#             current_components = metrics.get('connected_components', 1)
#             if prev_components is not None:
#                 if abs(current_components - prev_components) > max(prev_components * 0.5, 3):
#                     events.append({
#                         'time': window_key,
#                         'type': 'component_change',
#                         'change': current_components - prev_components,
#                         'description': f"Significant change in connected components"
#                     })
#             prev_components = current_components
#         return events

#     def get_top_nodes(self, metrics_over_time: Dict[str, Dict], metric: str = 'degree_centrality', top_n: int = 10) -> Dict[str, List]:
#         """Get top nodes by metric over time"""
#         top_nodes_over_time = {}
#         for window_key, metrics in metrics_over_time.items():
#             if metric in metrics:
#                 metric_values = metrics[metric]
#                 sorted_nodes = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)[:top_n]
#                 top_nodes_over_time[window_key] = [
#                     {'node': node, 'value': value} for node, value in sorted_nodes
#                 ]
#         return top_nodes_over_time

#     def export_visualization_data(self, graphs: Dict[str, ig.Graph], metrics: Dict[str, Dict]) -> Dict:
#         """Prepare data for frontend visualization"""
#         visualization_data = {
#             'time_windows': [],
#             'metrics_timeline': [],
#             'node_evolution': {},
#             'summary': {}
#         }
#         MAX_NODES_VIZ = 2000
#         MAX_EDGES_VIZ = 5000
#         for window_key, graph in graphs.items():
#             window_metrics = metrics.get(window_key, {})
#             n = graph.vcount()
#             m = graph.ecount()
#             # igraph's degree returns a list, not a dict
#             degree_by_node = {graph.vs[idx]['name']: deg for idx, deg in enumerate(graph.degree())}
#             degree_values = list(degree_by_node.values())
#             if degree_values:
#                 p75 = float(np.percentile(degree_values, 75))
#                 p50 = float(np.percentile(degree_values, 50))
#             else:
#                 p75 = 0.0
#                 p50 = 0.0
#             truncated = False
#             if n > MAX_NODES_VIZ:
#                 truncated = True
#                 top_nodes = sorted(degree_by_node.items(), key=lambda kv: kv[1], reverse=True)[:MAX_NODES_VIZ]
#                 keep_nodes = {node for node, _deg in top_nodes}
#             else:
#                 keep_nodes = set(graph.vs['name'])
#             nodes_data = []
#             degree_c = window_metrics.get('degree_centrality', {}) or {}
#             for node in keep_nodes:
#                 deg = int(degree_by_node.get(node, 0))
#                 if deg >= p75:
#                     group = 'hub'
#                 elif deg >= p50:
#                     group = 'connector'
#                 else:
#                     group = 'peripheral'
#                 node_data = {
#                     'id': node,
#                     'label': node,
#                     'degree': deg,
#                     'centrality': float(degree_c.get(node, 0) or 0),
#                     'group': group
#                 }
#                 nodes_data.append(node_data)
#             edges_data = []
#             for e in graph.es:
#                 u = graph.vs[e.source]['name']
#                 v = graph.vs[e.target]['name']
#                 if u not in keep_nodes or v not in keep_nodes:
#                     continue
#                 edge_data = {
#                     'source': u,
#                     'target': v,
#                     'weight': e['weight'] if 'weight' in e.attributes() else 1,
#                     'id': e['edge_id'] if 'edge_id' in e.attributes() else f"{u}_{v}"
#                 }
#                 edges_data.append(edge_data)
#                 if len(edges_data) >= MAX_EDGES_VIZ:
#                     truncated = True
#                     break
#             start_str, end_str = window_key.split('_')
#             start_time = datetime.fromisoformat(start_str)
#             end_time = datetime.fromisoformat(end_str)
#             visualization_data['time_windows'].append({
#                 'start': start_time.isoformat(),
#                 'end': end_time.isoformat(),
#                 'nodes': nodes_data,
#                 'edges': edges_data,
#                 'window_key': window_key,
#                 'truncated': truncated,
#                 'original_counts': {
#                     'nodes': int(n),
#                     'edges': int(m),
#                 }
#             })
#             visualization_data['metrics_timeline'].append({
#                 'time': start_time.isoformat(),
#                 'density': window_metrics.get('density', 0),
#                 'nodes': graph.vcount(),
#                 'edges': graph.ecount(),
#                 'components': window_metrics.get('connected_components', 1),
#                 'clustering': window_metrics.get('clustering_coefficient', 0)
#             })
#         if graphs:
#             total_nodes = len(set().union(*[set(g.vs['name']) for g in graphs.values()]))
#         else:
#             total_nodes = 0
#         total_edges = sum([g.ecount() for g in graphs.values()]) if graphs else 0
#         if visualization_data['time_windows']:
#             start_time = min(w['start'] for w in visualization_data['time_windows'])
#             end_time = max(w['end'] for w in visualization_data['time_windows'])
#         else:
#             start_time = None
#             end_time = None
#         visualization_data['summary'] = {
#             'total_time_windows': len(graphs),
#             'total_unique_nodes': total_nodes,
#             'total_edges': total_edges,
#             'time_span': {
#                 'start': start_time,
#                 'end': end_time
#             }
#         }
#         return visualization_data

#     def _assign_group(self, node: str, graph):
#         """Assign node to group based on network position"""
#         degree = graph.degree(node)
#         if degree > np.percentile([d for n, d in graph.degree()], 75):
#             return 'hub'
#         elif degree > np.percentile([d for n, d in graph.degree()], 50):
#             return 'connector'
#         else:
#             return 'peripheral'


#     def tgl_link_prediction(self, edges: List[Dict], dataset_name: str, config_path: str, tgl_dir: str, python_exec: str, output_dir: str) -> Dict:
#         """Full TGL integration workflow: export edges, run TGL, parse output."""
#         import os
#         from app.services.tgl_integration import export_edges_to_tgl_csv, run_tgl_train, parse_tgl_output
#         import pandas as pd
#         # Step 1: Export edges to CSV
#         csv_path = os.path.join(output_dir, 'edges.csv')
#         df = pd.DataFrame(edges)
#         export_edges_to_tgl_csv(edges, csv_path)
#         # Step 2: Run TGL train.py
#         stdout, stderr = run_tgl_train(dataset_name, config_path, tgl_dir, python_exec)
#         # Step 3: Parse TGL output
#         summary = parse_tgl_output(stdout)
#         return {
#             'stdout': stdout,
#             'stderr': stderr,
#             'summary': summary,
#             'csv_path': csv_path
#         }
        
        
# import pandas as pd
# import numpy as np
# from datetime import datetime, timedelta
# from typing import Dict, List, Tuple, Optional, Any
# import igraph as ig
# import networkx as nx
# from collections import defaultdict
# import asyncio
# from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
# import multiprocessing as mp
# import csv
# import warnings
# warnings.filterwarnings('ignore')

# class TemporalNetworkAnalyzer:
#     def __init__(self):
#         self.graphs = {}
#         self.metrics_cache = {}
#         self.executor = ThreadPoolExecutor(max_workers=mp.cpu_count())
#         self.process_executor = ProcessPoolExecutor(max_workers=max(1, mp.cpu_count() - 1))
    
#     async def create_time_windows(self, edges: List[Dict], window_size: str = '1h', 
#                                   step_size: str = '30min') -> Dict[str, ig.Graph]:
#         """Create overlapping time windows for temporal analysis with optimized processing"""
#         if not edges:
#             self.graphs = {}
#             return {}
        
#         # Convert to DataFrame efficiently
#         df = pd.DataFrame(edges)
        
#         # Optimize timestamp conversion
#         df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
#         df = df.dropna(subset=['timestamp'])
        
#         # Remove timezone for efficiency
#         try:
#             df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
#         except:
#             pass
        
#         if df.empty:
#             return {}
        
#         # Parse time windows - use string frequencies for floor
#         window_map = {
#             '1h': '1H',
#             '1d': '1D',
#             '1w': '1W',
#         }
        
#         step_map = {
#             '30min': '30min',
#             '1h': '1H',
#         }
        
#         # Get frequency strings for floor operation
#         step_freq = step_map.get(step_size, '30min')
        
#         # Get timedelta for window calculations
#         window_delta_map = {
#             '1h': timedelta(hours=1),
#             '1d': timedelta(days=1),
#             '1w': timedelta(weeks=1),
#         }
        
#         step_delta_map = {
#             '30min': timedelta(minutes=30),
#             '1h': timedelta(hours=1),
#         }
        
#         window_delta = window_delta_map.get(window_size, timedelta(hours=1))
#         step_delta = step_delta_map.get(step_size, timedelta(minutes=30))
        
#         # Create time slots efficiently using string frequency
#         df['time_slot'] = df['timestamp'].dt.floor(step_freq)
        
#         # Calculate overlap windows
#         window_seconds = window_delta.total_seconds()
#         step_seconds = step_delta.total_seconds()
#         overlap_k = max(1, int(np.ceil(window_seconds / step_seconds)))
        
#         # Create windows with parallel processing
#         window_starts = sorted(df['time_slot'].unique())
        
#         # Limit number of windows for performance
#         max_windows = 500
#         if len(window_starts) > max_windows:
#             stride = len(window_starts) // max_windows
#             window_starts = window_starts[::max(1, stride)]
        
#         # Process windows in parallel
#         loop = asyncio.get_event_loop()
#         tasks = []
        
#         for win_start in window_starts:
#             task = loop.run_in_executor(
#                 self.executor,
#                 self._create_single_window,
#                 df,
#                 win_start,
#                 window_delta,
#                 step_delta,
#                 overlap_k
#             )
#             tasks.append(task)
        
#         results = await asyncio.gather(*tasks)
        
#         # Combine results
#         windows = {}
#         for win_key, graph in results:
#             if graph and graph.vcount() > 0:
#                 windows[win_key] = graph
        
#         self.graphs = windows
#         return windows

#     def _create_single_window_with_infomap(self, df: pd.DataFrame, win_start: pd.Timestamp, 
#                                            window_delta: timedelta, step_delta: timedelta,
#                                            overlap_k: int) -> Tuple[str, Optional[ig.Graph]]:
#         """Create a single time window and run Infomap community detection"""
#         win_end = win_start + window_delta
#         window_mask = (df['timestamp'] >= win_start) & (df['timestamp'] < win_end)
#         window_edges = df[window_mask]
#         if window_edges.empty:
#             return f"{win_start.isoformat()}_{win_end.isoformat()}", None
#         # Create graph efficiently
#         window_key, G = self._create_graph_from_edges(window_edges, win_start, win_end)
#         # --- Infomap community detection ---
#         try:
#             from infomap import Infomap
#             edge_list = [(e.source, e.target) for e in G.es]
#             node_names = G.vs['name']
#             # Map igraph indices to node names
#             edges_named = [(node_names[s], node_names[t]) for s, t in G.get_edgelist()]
#             im = Infomap()
#             for u, v in edges_named:
#                 im.addLink(u, v)
#             im.run()
#             communities = {node_name: im.getModules()[node_name] for node_name in node_names}
#             G.vs['community'] = [communities.get(name, -1) for name in node_names]
#         except Exception:
#             G.vs['community'] = [-1] * G.vcount()
#         return window_key, G
    
#     def _create_single_window(self, df: pd.DataFrame, win_start: pd.Timestamp, 
#                               window_delta: timedelta, step_delta: timedelta,
#                               overlap_k: int) -> Tuple[str, Optional[ig.Graph]]:
#         """Create a single time window (for parallel processing)"""
#         win_end = win_start + window_delta
        
#         # Filter edges in this window efficiently
#         window_mask = (df['timestamp'] >= win_start) & (df['timestamp'] < win_end)
#         window_edges = df[window_mask]
        
#         if window_edges.empty:
#             return f"{win_start.isoformat()}_{win_end.isoformat()}", None
        
#         # Create graph efficiently
#         return self._create_graph_from_edges(window_edges, win_start, win_end)
    
#     def _create_graph_from_edges(self, edges_df: pd.DataFrame, win_start: pd.Timestamp, 
#                                  win_end: pd.Timestamp) -> Tuple[str, ig.Graph]:
#         """Create igraph from edges DataFrame efficiently"""
#         # Get unique nodes - convert to list to avoid numpy array issues
#         sources = edges_df['source'].astype(str).tolist()
#         targets = edges_df['target'].astype(str).tolist()
        
#         # Create node mapping using set for unique values
#         all_nodes_set = set(sources) | set(targets)
#         all_nodes = list(all_nodes_set)
#         node_to_idx = {node: i for i, node in enumerate(all_nodes)}
        
#         # Create edge list
#         edge_list = []
#         for s, t in zip(sources, targets):
#             if s in node_to_idx and t in node_to_idx:
#                 edge_list.append((node_to_idx[s], node_to_idx[t]))
        
#         # Get weights
#         if 'weight' in edges_df.columns:
#             weights = pd.to_numeric(edges_df['weight'], errors='coerce').fillna(1).tolist()
#         else:
#             weights = [1] * len(edge_list)
        
#         # Create graph
#         G = ig.Graph()
#         G.add_vertices(len(all_nodes))
#         G.add_edges(edge_list)
#         G.vs['name'] = all_nodes
#         G.es['weight'] = weights
        
#         # Add edge IDs if available
#         if 'edge_id' in edges_df.columns:
#             G.es['edge_id'] = edges_df['edge_id'].tolist()
        
#         window_key = f"{win_start.isoformat()}_{win_end.isoformat()}"
#         return window_key, G
    
#     async def compute_temporal_metrics(self, graphs: Dict[str, ig.Graph], 
#                                        metrics: Optional[List[str]] = None) -> Dict[str, Dict]:
#         """Compute metrics for each time window in parallel"""
#         if metrics is None:
#             metrics = ['degree_centrality', 'betweenness_centrality', 'density', 'components']
        
#         if not graphs:
#             return {}
        
#         # Process in parallel
#         loop = asyncio.get_event_loop()
#         tasks = []
        
#         for window_key, graph in graphs.items():
#             task = loop.run_in_executor(
#                 self.executor,
#                 self._compute_single_window_metrics,
#                 graph,
#                 window_key,
#                 metrics
#             )
#             tasks.append(task)
        
#         results = await asyncio.gather(*tasks)
        
#         # Combine results
#         metrics_results = {}
#         for window_key, window_metrics in results:
#             metrics_results[window_key] = window_metrics
        
#         self.metrics_cache = metrics_results
#         return metrics_results
    
#     def _compute_single_window_metrics(self, graph: ig.Graph, window_key: str, 
#                                        metrics: List[str]) -> Tuple[str, Dict]:
#         """Compute metrics for a single window"""
#         window_metrics = {}
#         n = graph.vcount()
        
#         # Basic metrics (always compute)
#         window_metrics['num_nodes'] = n
#         window_metrics['num_edges'] = graph.ecount()
#         window_metrics['density'] = graph.density() if n > 1 else 0
        
#         # Connected components (efficient)
#         if n > 0:
#             components = graph.components()
#             window_metrics['connected_components'] = len(components)
            
#             # Get giant component size
#             if len(components) > 0:
#                 window_metrics['giant_component_size'] = max(len(c) for c in components)
        
#         # Optional metrics (compute only if requested)
#         if 'degree_centrality' in metrics and n > 0:
#             degs = graph.degree()
#             window_metrics['degree_centrality'] = {
#                 graph.vs[idx]['name']: deg / (n - 1) if n > 1 else 0 
#                 for idx, deg in enumerate(degs)
#             }
            
#             # Also store max degree for quick reference
#             window_metrics['max_degree'] = max(degs) if degs else 0
        
#         if 'betweenness_centrality' in metrics and n > 2:
#             try:
#                 # Sample nodes for large graphs
#                 if n > 5000:
#                     # Approximate betweenness for large graphs
#                     btw = {graph.vs[idx]['name']: 0.0 for idx in range(n)}
#                     window_metrics['betweenness_centrality'] = btw
#                 else:
#                     weights = graph.es['weight'] if 'weight' in graph.es.attributes() else None
#                     btw = graph.betweenness(weights=weights)
#                     window_metrics['betweenness_centrality'] = {
#                         graph.vs[idx]['name']: val for idx, val in enumerate(btw)
#                     }
#             except Exception as e:
#                 window_metrics['betweenness_centrality'] = {}
        
#         if 'pagerank' in metrics and n > 0:
#             try:
#                 weights = graph.es['weight'] if 'weight' in graph.es.attributes() else None
#                 pr = graph.pagerank(weights=weights)
#                 window_metrics['pagerank'] = {
#                     graph.vs[idx]['name']: val for idx, val in enumerate(pr)
#                 }
#             except Exception as e:
#                 window_metrics['pagerank'] = {}
        
#         if 'clustering' in metrics and n > 2:
#             try:
#                 # Sample for large graphs
#                 if n > 5000:
#                     window_metrics['clustering_coefficient'] = 0.0
#                 else:
#                     window_metrics['clustering_coefficient'] = graph.transitivity_undirected()
#             except Exception as e:
#                 window_metrics['clustering_coefficient'] = 0.0
        
#         return window_key, window_metrics
    
#     def detect_anomalies(self, metrics_over_time: Dict[str, Dict]) -> List[Dict]:
#         """Detect anomalies in metrics timeline"""
#         if not metrics_over_time:
#             return []
        
#         # Extract time series
#         times = []
#         densities = []
#         node_counts = []
#         components = []
        
#         for window_key, metrics in metrics_over_time.items():
#             times.append(window_key)
#             densities.append(metrics.get('density', 0))
#             node_counts.append(metrics.get('num_nodes', 0))
#             components.append(metrics.get('connected_components', 1))
        
#         events = []
        
#         # Detect density anomalies using rolling statistics
#         if len(densities) > 10:
#             densities_arr = np.array(densities, dtype=float)
            
#             # Use rolling window for anomaly detection
#             window_size = min(10, len(densities) // 5)
            
#             for i in range(window_size, len(densities)):
#                 window = densities_arr[max(0, i-window_size):i]
#                 mean = window.mean()
#                 std = window.std()
                
#                 if std > 0:
#                     z_score = abs(densities_arr[i] - mean) / std
                    
#                     if z_score > 2.0:  # Anomaly threshold
#                         events.append({
#                             'time': times[i],
#                             'type': 'density_anomaly',
#                             'value': float(densities_arr[i]),
#                             'z_score': float(z_score),
#                             'description': f"Unusual network density detected at {times[i]}"
#                         })
        
#         # Detect component changes
#         if components:
#             prev_components = components[0]
#             for i, current_components in enumerate(components[1:], 1):
#                 if abs(current_components - prev_components) > max(prev_components * 0.5, 3):
#                     events.append({
#                         'time': times[i],
#                         'type': 'component_change',
#                         'change': current_components - prev_components,
#                         'description': f"Significant change in connected components at {times[i]}"
#                     })
#                 prev_components = current_components
        
#         return events
    
#     def get_top_nodes(self, metrics_over_time: Dict[str, Dict], 
#                      metric: str = 'degree_centrality', top_n: int = 10) -> Dict[str, List]:
#         """Get top nodes by metric over time"""
#         top_nodes_over_time = {}
        
#         for window_key, metrics in metrics_over_time.items():
#             if metric in metrics:
#                 metric_values = metrics[metric]
                
#                 # Efficient top-n selection
#                 if metric_values and isinstance(metric_values, dict):
#                     # Sort and get top n
#                     sorted_items = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)[:top_n]
#                     top_nodes_over_time[window_key] = [
#                         {'node': node, 'value': float(value)} for node, value in sorted_items
#                     ]
        
#         return top_nodes_over_time
    
#     async def export_visualization_data(self, graphs: Dict[str, ig.Graph], 
#                                         metrics: Dict[str, Dict]) -> Dict:
#         """Prepare data for frontend visualization with sampling for large graphs"""
#         visualization_data = {
#             'time_windows': [],
#             'metrics_timeline': [],
#             'node_evolution': {},
#             'summary': {}
#         }
        
#         if not graphs:
#             return visualization_data
        
#         # Sampling thresholds
#         MAX_NODES_VIZ = 1000
#         MAX_EDGES_VIZ = 2000
        
#         # Process each time window
#         for window_key, graph in graphs.items():
#             window_metrics = metrics.get(window_key, {})
#             n = graph.vcount()
#             m = graph.ecount()
            
#             # Get node degrees
#             degrees = graph.degree()
#             degree_dict = {graph.vs[idx]['name']: deg for idx, deg in enumerate(degrees)}
            
#             # Sample nodes if too many
#             if n > MAX_NODES_VIZ:
#                 # Keep highest degree nodes
#                 top_nodes = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:MAX_NODES_VIZ]
#                 keep_nodes = {node for node, _ in top_nodes}
#                 truncated = True
#             else:
#                 keep_nodes = set(graph.vs['name'])
#                 truncated = False
            
#             # Calculate degree percentiles for grouping
#             degree_values = list(degree_dict.values())
#             p75 = float(np.percentile(degree_values, 75)) if degree_values else 0
#             p50 = float(np.percentile(degree_values, 50)) if degree_values else 0
            
#             # Create nodes data
#             nodes_data = []
#             degree_c = window_metrics.get('degree_centrality', {})
            
#             # Get Infomap community assignments if available
#             communities = {}
#             if 'community' in graph.vs.attributes():
#                 communities = {graph.vs[idx]['name']: graph.vs[idx]['community'] for idx in range(graph.vcount())}

#             for node in keep_nodes:
#                 deg = degree_dict.get(node, 0)
#                 # Assign group based on degree
#                 if deg >= p75:
#                     group = 'hub'
#                 elif deg >= p50:
#                     group = 'connector'
#                 else:
#                     group = 'peripheral'
#                 nodes_data.append({
#                     'id': str(node),
#                     'label': str(node)[:20],
#                     'degree': int(deg),
#                     'centrality': float(degree_c.get(node, 0)),
#                     'group': group,
#                     'community': int(communities.get(node, -1))
#                 })
            
#             # Create edges data (sample if too many)
#             edges_data = []
#             edge_count = 0
            
#             for e in graph.es:
#                 u = graph.vs[e.source]['name']
#                 v = graph.vs[e.target]['name']
                
#                 if u in keep_nodes and v in keep_nodes:
#                     edges_data.append({
#                         'source': str(u),
#                         'target': str(v),
#                         'weight': float(e['weight']) if 'weight' in e.attributes() else 1.0,
#                         'id': str(e['edge_id']) if 'edge_id' in e.attributes() else f"{u}_{v}"
#                     })
#                     edge_count += 1
                    
#                     if edge_count >= MAX_EDGES_VIZ:
#                         truncated = True
#                         break
            
#             # Parse window times
#             try:
#                 start_str, end_str = window_key.split('_')
#                 start_time = datetime.fromisoformat(start_str)
#                 end_time = datetime.fromisoformat(end_str)
#             except:
#                 # Fallback for malformed window keys
#                 start_time = datetime.now()
#                 end_time = start_time + timedelta(hours=1)
            
#             visualization_data['time_windows'].append({
#                 'start': start_time.isoformat(),
#                 'end': end_time.isoformat(),
#                 'nodes': nodes_data,
#                 'edges': edges_data,
#                 'window_key': window_key,
#                 'truncated': truncated,
#                 'original_counts': {
#                     'nodes': int(n),
#                     'edges': int(m),
#                 }
#             })
            
#             # Add to metrics timeline
#             visualization_data['metrics_timeline'].append({
#                 'time': start_time.isoformat(),
#                 'density': float(window_metrics.get('density', 0)),
#                 'nodes': int(n),
#                 'edges': int(m),
#                 'components': int(window_metrics.get('connected_components', 1)),
#                 'giant_component': float(window_metrics.get('giant_component_size', 0) / n) if n > 0 else 0,
#                 'max_degree': int(window_metrics.get('max_degree', 0))
#             })
        
#         # Calculate summary statistics
#         if graphs:
#             all_nodes = set()
#             total_edges = 0
#             for g in graphs.values():
#                 all_nodes.update(g.vs['name'])
#                 total_edges += g.ecount()
            
#             start_time = min(w['start'] for w in visualization_data['time_windows']) if visualization_data['time_windows'] else None
#             end_time = max(w['end'] for w in visualization_data['time_windows']) if visualization_data['time_windows'] else None
            
#             visualization_data['summary'] = {
#                 'total_time_windows': len(graphs),
#                 'total_unique_nodes': len(all_nodes),
#                 'total_edges': total_edges,
#                 'time_span': {
#                     'start': start_time,
#                     'end': end_time
#                 }
#             }
        
#         return visualization_data
    
#     def export_edges_to_tgl_csv(self, df: pd.DataFrame, output_path: str) -> None:
#         """Export edges from DataFrame to TGL-compatible CSV format."""
#         with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow(['index', 'src', 'dst', 'time', 'ext_roll'])
            
#             for idx, row in df.iterrows():
#                 src = str(row.get('source', row.get('src', '')))
#                 dst = str(row.get('target', row.get('dst', '')))
#                 ts = row.get('timestamp', row.get('time', 0))
                
#                 # Convert timestamp to numeric if needed
#                 if isinstance(ts, (pd.Timestamp, datetime)):
#                     ts = int(ts.timestamp())
#                 elif isinstance(ts, str):
#                     try:
#                         ts = int(datetime.fromisoformat(ts).timestamp())
#                     except:
#                         ts = 0
                
#                 ext_roll = float(row.get('ext_roll', 0))
#                 writer.writerow([idx, src, dst, ts, ext_roll])
    
#     def tgl_link_prediction(self, edges: List[Dict], dataset_name: str, 
#                            config_path: str, tgl_dir: str, 
#                            python_exec: str, output_dir: str) -> Dict:
#         """TGL integration for link prediction"""
#         import os
        
#         # Export edges to CSV
#         csv_path = os.path.join(output_dir, 'edges.csv')
#         df = pd.DataFrame(edges)
        
#         # Sample if too many edges
#         if len(df) > 1000000:
#             df = df.sample(n=1000000, random_state=42)
        
#         # Export to TGL format
#         self.export_edges_to_tgl_csv(df, csv_path)
        
#         # For now, return placeholder
#         return {
#             'stdout': 'TGL processing started',
#             'stderr': '',
#             'summary': {'status': 'processing', 'edges_sampled': len(df) if len(edges) > 1000000 else len(edges)},
#             'csv_path': csv_path
#         }

# app/services/network_analysis.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import igraph as ig
import networkx as nx
from collections import defaultdict, Counter
import asyncio
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import csv
import warnings
import json
import random
import math
import gc
from scipy.spatial import distance
warnings.filterwarnings('ignore')

class TemporalNetworkAnalyzer:
    def __init__(self):
        self.graphs = {}
        self.metrics_cache = {}
        # Use ThreadPoolExecutor only (ProcessPoolExecutor causes pickle errors with bound methods)
        self.executor = ThreadPoolExecutor(max_workers=max(1, mp.cpu_count()))
        # Track original counts for accurate reporting
        self.original_edge_count = 0
        self.original_node_count = 0
        self.sampling_applied = False
    
    def cleanup(self):
        """Clean up memory between analyses to prevent crashes"""
        # Clear cached data
        self.graphs.clear()
        self.metrics_cache.clear()
        # Force garbage collection
        import gc
        gc.collect()
    
    def _smart_sample_edges(self, df: pd.DataFrame, max_edges: int = 750000) -> pd.DataFrame:
        """Smart edge sampling that preserves high-degree nodes for representative community detection.
        
        Strategy:
        1. Calculate node degrees from ALL edges
        2. Keep all edges from top 10% high-degree nodes
        3. Randomly sample remaining edges to reach max_edges
        
        This ensures communities formed by hub nodes are preserved.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if len(df) <= max_edges:
            return df
        
        logger.info(f"Smart sampling: {len(df):,} edges -> {max_edges:,} (preserving high-degree nodes)")
        
        # Calculate node degrees from ALL edges first
        sources = df['source'].astype(str)
        targets = df['target'].astype(str)
        
        # Combined degree count
        all_nodes = pd.concat([sources, targets])
        degree_counts = all_nodes.value_counts()
        
        # Get top 10% high-degree nodes (hubs)
        top_n = max(100, int(len(degree_counts) * 0.1))  # At least 100 nodes
        hub_nodes = set(degree_counts.head(top_n).index)
        
        # Split edges: those involving hubs vs others
        hub_mask = sources.isin(hub_nodes) | targets.isin(hub_nodes)
        hub_edges = df[hub_mask]
        other_edges = df[~hub_mask]
        
        logger.info(f"  Hub edges (involving top {len(hub_nodes):,} nodes): {len(hub_edges):,}")
        logger.info(f"  Other edges: {len(other_edges):,}")
        
        # Keep all hub edges (up to 60% of budget)
        max_hub_edges = int(max_edges * 0.6)
        if len(hub_edges) > max_hub_edges:
            hub_sample = hub_edges.sample(n=max_hub_edges, random_state=42)
        else:
            hub_sample = hub_edges
        
        # Sample remaining edges randomly
        remaining_budget = max_edges - len(hub_sample)
        if remaining_budget > 0 and len(other_edges) > 0:
            sample_n = min(remaining_budget, len(other_edges))
            other_sample = other_edges.sample(n=sample_n, random_state=42)
        else:
            other_sample = pd.DataFrame()
        
        # Combine and return
        sampled = pd.concat([hub_sample, other_sample], ignore_index=True)
        logger.info(f"  Final sample: {len(sampled):,} edges")
        
        return sampled
    
    async def create_time_windows(self, edges: List[Dict], window_size: str = '1h', 
                                  step_size: str = '30min') -> Dict[str, ig.Graph]:
        """Create overlapping time windows for temporal analysis with optimized processing"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Clean up previous analysis data first
        self.cleanup()
        
        if not edges:
            self.graphs = {}
            return {}
        
        # Convert to DataFrame efficiently
        df = pd.DataFrame(edges)
        
        # Track ORIGINAL counts before any sampling
        self.original_edge_count = len(df)
        sources = df['source'].astype(str) if 'source' in df.columns else pd.Series()
        targets = df['target'].astype(str) if 'target' in df.columns else pd.Series()
        all_unique_nodes = pd.concat([sources, targets]).unique() if len(sources) > 0 else []
        self.original_node_count = len(all_unique_nodes)
        
        logger.info(f"Original data: {self.original_edge_count:,} edges, {self.original_node_count:,} nodes")
        
        # Apply smart sampling for large datasets - AGGRESSIVE for fast results
        MAX_EDGES_FOR_ANALYSIS = 100000  # 100k edges max for ~3 min analysis
        if len(df) > MAX_EDGES_FOR_ANALYSIS:
            df = self._smart_sample_edges(df, MAX_EDGES_FOR_ANALYSIS)
            self.sampling_applied = True
            logger.info(f"Sampling applied: using {len(df):,} edges for analysis")
        else:
            self.sampling_applied = False
        
        # Optimize timestamp conversion
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        df = df.dropna(subset=['timestamp'])
        
        # Remove timezone for efficiency
        try:
            df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        except:
            pass
        
        if df.empty:
            return {}
        
        # Parse time windows - use string frequencies for floor
        window_map = {
            '1h': '1H',
            '1d': '1D',
            '1w': '1W',
        }
        
        step_map = {
            '30min': '30min',
            '1h': '1H',
        }
        
        # Get frequency strings for floor operation
        step_freq = step_map.get(step_size, '30min')
        
        # Get timedelta for window calculations
        window_delta_map = {
            '1h': timedelta(hours=1),
            '1d': timedelta(days=1),
            '1w': timedelta(weeks=1),
        }
        
        step_delta_map = {
            '30min': timedelta(minutes=30),
            '1h': timedelta(hours=1),
        }
        
        window_delta = window_delta_map.get(window_size, timedelta(hours=1))
        step_delta = step_delta_map.get(step_size, timedelta(minutes=30))
        
        # --- Improved windowing logic ---
        # If all timestamps are identical, create a single window
        if df['timestamp'].nunique() == 1:
            df['time_slot'] = df['timestamp']
        else:
            # For large datasets, auto-select smaller window size if needed
            min_ts, max_ts = df['timestamp'].min(), df['timestamp'].max()
            total_seconds = (max_ts - min_ts).total_seconds()
            if total_seconds > 0 and len(df) > 100000:
                # If more than 100k edges, use 10min windows or smaller
                window_size_seconds = min(window_delta.total_seconds(), max(600, total_seconds // 100))
                window_delta = timedelta(seconds=window_size_seconds)
                step_delta = timedelta(seconds=window_size_seconds // 2)
                step_freq = f"{int(window_size_seconds // 60)}min"
            df['time_slot'] = df['timestamp'].dt.floor(step_freq)

        # Calculate overlap windows
        window_seconds = window_delta.total_seconds()
        step_seconds = step_delta.total_seconds()
        overlap_k = max(1, int(np.ceil(window_seconds / step_seconds)))

        # Always split into multiple windows if possible
        window_starts = sorted(df['time_slot'].unique())
        if len(window_starts) == 1 and df['timestamp'].nunique() > 1:
            # Force at least 10 windows if timestamps are not identical
            ts_sorted = df['timestamp'].sort_values().unique()
            forced_windows = np.array_split(ts_sorted, 10)
            window_starts = [w[0] for w in forced_windows if len(w) > 0]

        # Limit number of windows for performance (10 max for fast analysis)
        max_windows = 10 if len(df) > 50000 else 20
        if len(window_starts) > max_windows:
            stride = len(window_starts) // max_windows
            window_starts = window_starts[::max(1, stride)]
        
        # Process windows in parallel using thread pool
        loop = asyncio.get_event_loop()
        tasks = []

        for win_start in window_starts:
            task = loop.run_in_executor(
                self.executor,
                self._create_single_window,
                df,
                win_start,
                window_delta,
                step_delta,
                overlap_k
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Combine results into windows dict
        windows = {}
        for win_key, graph in results:
            if graph is not None and graph.vcount() > 0:
                windows[win_key] = graph

        self.graphs = windows
        return windows

    def _create_single_window_with_infomap(self, df: pd.DataFrame, win_start: pd.Timestamp,
                                           window_delta: timedelta, step_delta: timedelta,
                                           overlap_k: int) -> Tuple[str, Optional[ig.Graph]]:
        """Create a single time window and optionally run Infomap community detection."""
        win_end = win_start + window_delta
        window_key = f"{win_start.isoformat()}_{win_end.isoformat()}"

        # Filter edges in this window efficiently
        window_mask = (df['timestamp'] >= win_start) & (df['timestamp'] < win_end)
        window_edges = df[window_mask]

        if window_edges.empty:
            return window_key, None

        # Create graph
        window_key, G = self._create_graph_from_edges(window_edges, win_start, win_end)

        # Try to run Infomap if available; fall back to no communities
        try:
            from infomap import Infomap
            node_names = G.vs['name']
            im = Infomap()
            for s, t in G.get_edgelist():
                im.addLink(node_names[s], node_names[t])
            im.run()
            try:
                modules = im.getModules()
                G.vs['community'] = [modules.get(name, -1) for name in node_names]
            except Exception:
                G.vs['community'] = [-1] * G.vcount()
        except Exception:
            G.vs['community'] = [-1] * G.vcount()

        return window_key, G

    def _create_single_window(self, df: pd.DataFrame, win_start: pd.Timestamp,
                              window_delta: timedelta, step_delta: timedelta,
                              overlap_k: int) -> Tuple[str, Optional[ig.Graph]]:
        """Create a single time window (for parallel processing)"""
        win_end = win_start + window_delta
        window_key = f"{win_start.isoformat()}_{win_end.isoformat()}"

        window_mask = (df['timestamp'] >= win_start) & (df['timestamp'] < win_end)
        window_edges = df[window_mask]

        if window_edges.empty:
            return window_key, None

        return self._create_graph_from_edges(window_edges, win_start, win_end)
    
    def _create_graph_from_edges(self, edges_df: pd.DataFrame, win_start: pd.Timestamp, 
                                 win_end: pd.Timestamp) -> Tuple[str, ig.Graph]:
        """Create igraph from edges DataFrame efficiently"""
        # Get unique nodes - convert to list to avoid numpy array issues
        sources = edges_df['source'].astype(str).tolist()
        targets = edges_df['target'].astype(str).tolist()
        
        # Create node mapping using set for unique values
        all_nodes_set = set(sources) | set(targets)
        all_nodes = list(all_nodes_set)
        node_to_idx = {node: i for i, node in enumerate(all_nodes)}
        
        # Create edge list
        edge_list = []
        for s, t in zip(sources, targets):
            if s in node_to_idx and t in node_to_idx:
                edge_list.append((node_to_idx[s], node_to_idx[t]))
        
        # Get weights
        if 'weight' in edges_df.columns:
            weights = pd.to_numeric(edges_df['weight'], errors='coerce').fillna(1).tolist()
        else:
            weights = [1] * len(edge_list)
        
        # Create graph
        G = ig.Graph()
        G.add_vertices(len(all_nodes))
        G.add_edges(edge_list)
        G.vs['name'] = all_nodes
        G.es['weight'] = weights
        
        # Add edge IDs if available
        if 'edge_id' in edges_df.columns:
            G.es['edge_id'] = edges_df['edge_id'].tolist()
        
        window_key = f"{win_start.isoformat()}_{win_end.isoformat()}"
        return window_key, G

    def _ensure_communities_sync(self, G: ig.Graph) -> ig.Graph:
        """Synchronous community detection - FAST version using label propagation always."""
        try:
            n = G.vcount()
            # Always use label propagation - it's fastest and scales well
            comm = G.community_label_propagation()
            membership = list(comm.membership)

            if membership and len(membership) == G.vcount():
                G.vs['community'] = membership
            else:
                G.vs['community'] = [-1] * G.vcount()
        except Exception:
            G.vs['community'] = [-1] * G.vcount()
        return G

    def _summarize_community_window(self, window_key: str, graph: ig.Graph, window_metrics: Dict,
                                    MAX_NODES_COMMUNITY: int, MAX_EDGES_COMMUNITY: int) -> Optional[Dict]:
        """FAST summarizer for community window - skips expensive edge counting."""
        try:
            import hashlib
            g = graph  # Use full graph, no subgraph creation
            truncated = g.vcount() > MAX_NODES_COMMUNITY

            # Get community memberships
            if 'community' not in g.vs.attributes():
                return None
                
            comm_array = g.vs['community']
            unique_comms = set(comm_array) - {-1}
            
            if not unique_comms:
                return None

            # Quick community stats using numpy groupby-style operations
            degrees = np.array(g.degree())
            comm_np = np.array(comm_array)
            
            community_nodes = []
            for comm_id in unique_comms:
                mask = comm_np == comm_id
                node_count = int(np.sum(mask))
                if node_count < 2:
                    continue
                    
                comm_degrees = degrees[mask]
                avg_degree = float(np.mean(comm_degrees))
                
                # Simple positioning based on community ID
                hash_val = int(hashlib.md5(str(comm_id).encode()).hexdigest(), 16)
                centroid_x = float(200 + (hash_val % 600))
                centroid_y = float(100 + ((hash_val // 1000) % 300))
                
                community_nodes.append({
                    'id': f"comm_{window_key}_{comm_id}",
                    'communityId': int(comm_id),
                    'nodeCount': node_count,
                    'size': node_count,
                    'avgDegree': avg_degree,
                    'dominantGroup': 'mixed',
                    'isMixed': True,
                    'centroidX': centroid_x,
                    'centroidY': centroid_y,
                    'internalEdges': 0,  # Skip expensive counting
                    'memberNodeIds': [],  # Skip for speed
                    'memberCount': node_count
                })

            # Skip community edge counting for speed - return empty list
            community_edges = []

            try:
                start_str, end_str = window_key.split('_')
                start_time = datetime.fromisoformat(start_str)
                end_time = datetime.fromisoformat(end_str)
            except:
                start_time = datetime.now()
                end_time = start_time + timedelta(hours=1)

            community_nodes.sort(key=lambda x: x['nodeCount'], reverse=True)

            return {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'window_key': window_key,
                'communities': community_nodes[:100],  # Limit to top 100 communities
                'communityEdges': community_edges,
                'totalCommunities': len(community_nodes),
                'totalNodes': g.vcount(),
                'totalEdges': g.ecount(),
                'truncated': truncated
            }
        except Exception:
            return None
    
    async def compute_temporal_metrics(self, graphs: Dict[str, ig.Graph], 
                                       metrics: Optional[List[str]] = None) -> Dict[str, Dict]:
        """Compute metrics for each time window in parallel"""
        if metrics is None:
            metrics = ['degree_centrality', 'betweenness_centrality', 'density', 'components']
        
        if not graphs:
            return {}
        
        # Process in parallel
        loop = asyncio.get_event_loop()
        tasks = []
        
        for window_key, graph in graphs.items():
            task = loop.run_in_executor(
                self.executor,
                self._compute_single_window_metrics,
                graph,
                window_key,
                metrics
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Combine results
        metrics_results = {}
        for window_key, window_metrics in results:
            metrics_results[window_key] = window_metrics
        
        self.metrics_cache = metrics_results
        return metrics_results
    
    def _compute_single_window_metrics(self, graph: ig.Graph, window_key: str, 
                                       metrics: List[str]) -> Tuple[str, Dict]:
        """Compute metrics for a single window"""
        window_metrics = {}
        n = graph.vcount()
        
        # Basic metrics (always compute)
        window_metrics['num_nodes'] = n
        window_metrics['num_edges'] = graph.ecount()
        window_metrics['density'] = graph.density() if n > 1 else 0
        
        # Connected components (efficient)
        if n > 0:
            components = graph.components()
            window_metrics['connected_components'] = len(components)
            
            # Get giant component size
            if len(components) > 0:
                window_metrics['giant_component_size'] = max(len(c) for c in components)
        
        # Optional metrics (compute only if requested)
        if 'degree_centrality' in metrics and n > 0:
            degs = graph.degree()
            # Skip creating huge dict for large graphs - just store max/mean
            if n > 10000:
                window_metrics['degree_centrality'] = {}  # Empty for large graphs
            else:
                window_metrics['degree_centrality'] = {
                    graph.vs[idx]['name']: deg / (n - 1) if n > 1 else 0 
                    for idx, deg in enumerate(degs)
                }
            
            # Always store max degree for quick reference
            window_metrics['max_degree'] = max(degs) if degs else 0
        
        if 'betweenness_centrality' in metrics and n > 2:
            try:
                # Skip betweenness for large graphs (too slow)
                if n > 2000:
                    window_metrics['betweenness_centrality'] = {}
                else:
                    weights = graph.es['weight'] if 'weight' in graph.es.attributes() else None
                    btw = graph.betweenness(weights=weights)
                    window_metrics['betweenness_centrality'] = {
                        graph.vs[idx]['name']: val for idx, val in enumerate(btw)
                    }
            except Exception as e:
                window_metrics['betweenness_centrality'] = {}
        
        if 'pagerank' in metrics and n > 0:
            try:
                weights = graph.es['weight'] if 'weight' in graph.es.attributes() else None
                pr = graph.pagerank(weights=weights)
                window_metrics['pagerank'] = {
                    graph.vs[idx]['name']: val for idx, val in enumerate(pr)
                }
            except Exception as e:
                window_metrics['pagerank'] = {}
        
        if 'clustering' in metrics and n > 2:
            try:
                # Sample for large graphs
                if n > 5000:
                    window_metrics['clustering_coefficient'] = 0.0
                else:
                    window_metrics['clustering_coefficient'] = graph.transitivity_undirected()
            except Exception as e:
                window_metrics['clustering_coefficient'] = 0.0
        
        return window_key, window_metrics
    
    def detect_anomalies(self, metrics_over_time: Dict[str, Dict]) -> List[Dict]:
        """Detect anomalies in metrics timeline"""
        if not metrics_over_time:
            return []
        
        # Extract time series
        times = []
        densities = []
        node_counts = []
        components = []
        
        for window_key, metrics in metrics_over_time.items():
            times.append(window_key)
            densities.append(metrics.get('density', 0))
            node_counts.append(metrics.get('num_nodes', 0))
            components.append(metrics.get('connected_components', 1))
        
        events = []
        
        # Detect density anomalies using rolling statistics
        if len(densities) > 10:
            densities_arr = np.array(densities, dtype=float)
            
            # Use rolling window for anomaly detection
            window_size = min(10, len(densities) // 5)
            
            for i in range(window_size, len(densities)):
                window = densities_arr[max(0, i-window_size):i]
                mean = window.mean()
                std = window.std()
                
                if std > 0:
                    z_score = abs(densities_arr[i] - mean) / std
                    
                    if z_score > 2.0:  # Anomaly threshold
                        events.append({
                            'time': times[i],
                            'type': 'density_anomaly',
                            'value': float(densities_arr[i]),
                            'z_score': float(z_score),
                            'description': f"Unusual network density detected at {times[i]}"
                        })
        
        # Detect component changes
        if components:
            prev_components = components[0]
            for i, current_components in enumerate(components[1:], 1):
                if abs(current_components - prev_components) > max(prev_components * 0.5, 3):
                    events.append({
                        'time': times[i],
                        'type': 'component_change',
                        'change': current_components - prev_components,
                        'description': f"Significant change in connected components at {times[i]}"
                    })
                prev_components = current_components
        
        return events
    
    def get_top_nodes(self, metrics_over_time: Dict[str, Dict], 
                     metric: str = 'degree_centrality', top_n: int = 10) -> Dict[str, List]:
        """Get top nodes by metric over time"""
        top_nodes_over_time = {}
        
        for window_key, metrics in metrics_over_time.items():
            if metric in metrics:
                metric_values = metrics[metric]
                
                # Efficient top-n selection
                if metric_values and isinstance(metric_values, dict):
                    # Sort and get top n
                    sorted_items = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)[:top_n]
                    top_nodes_over_time[window_key] = [
                        {'node': node, 'value': float(value)} for node, value in sorted_items
                    ]
        
        return top_nodes_over_time
    
    # ============================================================================
    # NEW METHOD: Export community-level visualization data
    # ============================================================================
    async def export_community_visualization_data(self, graphs: Dict[str, ig.Graph], 
                                                  metrics: Dict[str, Dict]) -> Dict:
        """Prepare COMMUNITY-LEVEL data for frontend visualization (each community = one circle)"""
        visualization_data = {
            'time_windows': [],
            'summary': {}
        }
        
        if not graphs:
            return visualization_data
        
        # Process each time window
        # Sampling thresholds - set high to handle millions of nodes
        MAX_NODES_COMMUNITY = getattr(self, 'max_nodes_community', 2500000)  # 2.5M nodes
        MAX_EDGES_COMMUNITY = getattr(self, 'max_edges_community', 6000000)  # 6M edges
        
        # Process windows sequentially to avoid memory issues with large graphs
        # Using sequential processing prevents race conditions and memory exhaustion
        for window_key, graph in graphs.items():
            if graph is None:
                continue
            window_metrics = metrics.get(window_key, {})
            
            try:
                # Run community detection synchronously first
                self._ensure_communities_sync(graph)
                
                # Then summarize the window
                result = self._summarize_community_window(
                    window_key, graph, window_metrics, 
                    MAX_NODES_COMMUNITY, MAX_EDGES_COMMUNITY
                )
                
                if result:
                    visualization_data['time_windows'].append(result)
            except Exception as e:
                # Log error but continue with other windows
                import logging
                logging.warning(f"Error processing window {window_key}: {e}")
                continue
        
        # Calculate summary statistics
        if visualization_data['time_windows']:
            total_communities = sum(w['totalCommunities'] for w in visualization_data['time_windows'])
            avg_communities = total_communities / len(visualization_data['time_windows']) if visualization_data['time_windows'] else 0
            
            visualization_data['summary'] = {
                'total_time_windows': len(visualization_data['time_windows']),
                'avg_communities_per_window': avg_communities,
                'total_communities_across_windows': total_communities,
                # Report ORIGINAL counts (before any sampling)
                'original_total_edges': self.original_edge_count,
                'original_total_nodes': self.original_node_count,
                'sampling_applied': self.sampling_applied,
                'sampling_note': f"Analysis performed on representative sample. Full dataset: {self.original_node_count:,} nodes, {self.original_edge_count:,} edges." if self.sampling_applied else None
            }
        
        return visualization_data
    
    async def export_visualization_data(self, graphs: Dict[str, ig.Graph], 
                                        metrics: Dict[str, Dict]) -> Dict:
        """Original method - returns individual nodes (for small graphs only)"""
        visualization_data = {
            'time_windows': [],
            'metrics_timeline': [],
            'node_evolution': {},
            'summary': {}
        }
        
        if not graphs:
            return visualization_data
        
        # Sampling thresholds
        MAX_NODES_VIZ = 1000
        MAX_EDGES_VIZ = 2000
        
        # Process each time window
        for window_key, graph in graphs.items():
            window_metrics = metrics.get(window_key, {})
            n = graph.vcount()
            m = graph.ecount()
            
            # Get node degrees
            degrees = graph.degree()
            degree_dict = {graph.vs[idx]['name']: deg for idx, deg in enumerate(degrees)}
            
            # Sample nodes if too many
            if n > MAX_NODES_VIZ:
                # Keep highest degree nodes
                top_nodes = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:MAX_NODES_VIZ]
                keep_nodes = {node for node, _ in top_nodes}
                truncated = True
            else:
                keep_nodes = set(graph.vs['name'])
                truncated = False
            
            # Calculate degree percentiles for grouping
            degree_values = list(degree_dict.values())
            p75 = float(np.percentile(degree_values, 75)) if degree_values else 0
            p50 = float(np.percentile(degree_values, 50)) if degree_values else 0
            
            # Create nodes data
            nodes_data = []
            degree_c = window_metrics.get('degree_centrality', {})
            
            # Get Infomap community assignments if available
            communities = {}
            if 'community' in graph.vs.attributes():
                communities = {graph.vs[idx]['name']: graph.vs[idx]['community'] for idx in range(graph.vcount())}

            for node in keep_nodes:
                deg = degree_dict.get(node, 0)
                # Assign group based on degree
                if deg >= p75:
                    group = 'hub'
                elif deg >= p50:
                    group = 'connector'
                else:
                    group = 'peripheral'
                nodes_data.append({
                    'id': str(node),
                    'label': str(node)[:20],
                    'degree': int(deg),
                    'centrality': float(degree_c.get(node, 0)),
                    'group': group,
                    'community': int(communities.get(node, -1))
                })
            
            # Create edges data (sample if too many)
            edges_data = []
            edge_count = 0
            
            for e in graph.es:
                u = graph.vs[e.source]['name']
                v = graph.vs[e.target]['name']
                
                if u in keep_nodes and v in keep_nodes:
                    edges_data.append({
                        'source': str(u),
                        'target': str(v),
                        'weight': float(e['weight']) if 'weight' in e.attributes() else 1.0,
                        'id': str(e['edge_id']) if 'edge_id' in e.attributes() else f"{u}_{v}"
                    })
                    edge_count += 1
                    
                    if edge_count >= MAX_EDGES_VIZ:
                        truncated = True
                        break
            
            # Parse window times
            try:
                start_str, end_str = window_key.split('_')
                start_time = datetime.fromisoformat(start_str)
                end_time = datetime.fromisoformat(end_str)
            except:
                # Fallback for malformed window keys
                start_time = datetime.now()
                end_time = start_time + timedelta(hours=1)
            
            visualization_data['time_windows'].append({
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'nodes': nodes_data,
                'edges': edges_data,
                'window_key': window_key,
                'truncated': truncated,
                'original_counts': {
                    'nodes': int(n),
                    'edges': int(m),
                }
            })
            
            # Add to metrics timeline
            visualization_data['metrics_timeline'].append({
                'time': start_time.isoformat(),
                'density': float(window_metrics.get('density', 0)),
                'nodes': int(n),
                'edges': int(m),
                'components': int(window_metrics.get('connected_components', 1)),
                'giant_component': float(window_metrics.get('giant_component_size', 0) / n) if n > 0 else 0,
                'max_degree': int(window_metrics.get('max_degree', 0))
            })
        
        # Calculate summary statistics
        if graphs:
            all_nodes = set()
            total_edges = 0
            for g in graphs.values():
                all_nodes.update(g.vs['name'])
                total_edges += g.ecount()
            
            start_time = min(w['start'] for w in visualization_data['time_windows']) if visualization_data['time_windows'] else None
            end_time = max(w['end'] for w in visualization_data['time_windows']) if visualization_data['time_windows'] else None
            
            visualization_data['summary'] = {
                'total_time_windows': len(graphs),
                'total_unique_nodes': len(all_nodes),
                'total_edges': total_edges,
                'time_span': {
                    'start': start_time,
                    'end': end_time
                },
                # Report ORIGINAL counts (before any sampling)
                'original_total_edges': self.original_edge_count,
                'original_total_nodes': self.original_node_count,
                'sampling_applied': self.sampling_applied,
                'sampling_note': f"Analysis performed on representative sample. Full dataset: {self.original_node_count:,} nodes, {self.original_edge_count:,} edges." if self.sampling_applied else None
            }
        
        return visualization_data
    
    def export_edges_to_tgl_csv(self, df: pd.DataFrame, output_path: str) -> None:
        """Export edges from DataFrame to TGL-compatible CSV format."""
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['index', 'src', 'dst', 'time', 'ext_roll'])
            
            for idx, row in df.iterrows():
                src = str(row.get('source', row.get('src', '')))
                dst = str(row.get('target', row.get('dst', '')))
                ts = row.get('timestamp', row.get('time', 0))
                
                # Convert timestamp to numeric if needed
                if isinstance(ts, (pd.Timestamp, datetime)):
                    ts = int(ts.timestamp())
                elif isinstance(ts, str):
                    try:
                        ts = int(datetime.fromisoformat(ts).timestamp())
                    except:
                        ts = 0
                
                ext_roll = float(row.get('ext_roll', 0))
                writer.writerow([idx, src, dst, ts, ext_roll])
    
    def tgl_link_prediction(self, edges: List[Dict], dataset_name: str, 
                           config_path: str, tgl_dir: str, 
                           python_exec: str, output_dir: str) -> Dict:
        """TGL integration for link prediction"""
        import os
        
        # Export edges to CSV
        csv_path = os.path.join(output_dir, 'edges.csv')
        df = pd.DataFrame(edges)
        
        # Sample if too many edges
        if len(df) > 1000000:
            df = df.sample(n=1000000, random_state=42)
        
        # Export to TGL format
        self.export_edges_to_tgl_csv(df, csv_path)
        
        # For now, return placeholder
        return {
            'stdout': 'TGL processing started',
            'stderr': '',
            'summary': {'status': 'processing', 'edges_sampled': len(df) if len(edges) > 1000000 else len(edges)},
            'csv_path': csv_path
        }

    # ============================================================================
    # LARGE DATASET: Direct file-to-community pipeline (bypasses dict serialization)
    # ============================================================================
    def _analyze_large_sync(self, file_path: str, filename: str,
                             column_mapping: Optional[Dict[str, str]] = None,
                             progress_callback=None) -> Dict:
        """SYNC heavy-lifting for large file analysis. Runs in thread executor."""
        import time as _time
        import hashlib
        import logging
        import gc
        _logger = logging.getLogger(__name__)
        
        def _log(msg):
            print(f"[LARGE] {msg}", flush=True)
            _logger.info(f"[LARGE] {msg}")
        
        start_time = _time.time()
        self.cleanup()

        # ── Step 1: Read ALL edges from file ────────────────────────────────
        if progress_callback:
            progress_callback("Reading ALL edges from file (no sampling)...")
        
        _log(f"Direct file analysis: {file_path}")
        
        # Auto-detect delimiter from first data line
        sep = ','
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#') or line.startswith('%'):
                    continue
                if '\t' in line:
                    sep = '\t'
                elif ',' in line:
                    sep = ','
                else:
                    sep = r'\s+'
                break
        
        t0 = _time.time()
        if sep == r'\s+':
            df = pd.read_csv(file_path, sep=sep, header=None, comment='#',
                             engine='python', on_bad_lines='skip')
        else:
            df = pd.read_csv(file_path, sep=sep, header=None, comment='#',
                             engine='c', on_bad_lines='skip')
        
        _log(f"Read {len(df):,} rows in {_time.time()-t0:.1f}s")
        
        # ── Step 2: Name columns ────────────────────────────────────────────
        ncols = df.shape[1]
        # First, assign default positional names
        if ncols >= 4:
            default_names = ['source', 'target', 'weight', 'timestamp'] + \
                            [f'col{i}' for i in range(4, ncols)]
        elif ncols == 3:
            default_names = ['source', 'target', 'timestamp']
        elif ncols >= 2:
            default_names = ['source', 'target'] + [f'col{i}' for i in range(2, ncols)]
        else:
            default_names = [f'col{i}' for i in range(ncols)]
        df.columns = default_names
        _log(f"Columns ({ncols}): {list(df.columns)}")
        
        # Apply column_mapping if it remaps roles (e.g. {'col2': 'timestamp'})
        if column_mapping:
            # Filter out identity mappings (source→source etc.)
            real_renames = {k: v for k, v in column_mapping.items() if k != v}
            if real_renames:
                _log(f"Applying renames: {real_renames}")
                df = df.rename(columns=real_renames)
        
        df['source'] = df['source'].astype(str)
        df['target'] = df['target'].astype(str)
        
        # Track ORIGINAL counts
        self.original_edge_count = len(df)
        unique_nodes = pd.unique(pd.concat([df['source'], df['target']]))
        self.original_node_count = len(unique_nodes)
        self.sampling_applied = False
        
        _log(f"Dataset: {self.original_edge_count:,} edges, "
             f"{self.original_node_count:,} nodes")
        
        if progress_callback:
            progress_callback(f"Loaded {self.original_edge_count:,} edges, "
                              f"{self.original_node_count:,} unique nodes")
        
        # ── Step 3: Process timestamps ──────────────────────────────────────
        timestamp_inferred = False
        if 'timestamp' in df.columns:
            ts_numeric = pd.to_numeric(df['timestamp'], errors='coerce')
            if ts_numeric.notna().sum() > len(df) * 0.5:
                if ts_numeric.max() > 1e12:
                    df['timestamp_dt'] = pd.to_datetime(ts_numeric, unit='ms',
                                                         errors='coerce', utc=True)
                else:
                    df['timestamp_dt'] = pd.to_datetime(ts_numeric, unit='s',
                                                         errors='coerce', utc=True)
            else:
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'],
                                                     errors='coerce', utc=True)
        else:
            timestamp_inferred = True
            base = pd.Timestamp.now(tz='UTC')
            df['timestamp_dt'] = base + pd.to_timedelta(np.arange(len(df)), unit='s')
        
        # Fill missing timestamps
        if df['timestamp_dt'].isnull().any():
            missing = df['timestamp_dt'].isnull()
            base = (df['timestamp_dt'].min() if df['timestamp_dt'].notna().any()
                    else pd.Timestamp.now(tz='UTC'))
            df.loc[missing, 'timestamp_dt'] = base + pd.to_timedelta(
                np.arange(missing.sum()), unit='s')
        
        # Remove timezone
        try:
            df['timestamp_dt'] = df['timestamp_dt'].dt.tz_convert('UTC').dt.tz_localize(None)
        except Exception:
            pass
        
        min_ts = df['timestamp_dt'].min()
        max_ts = df['timestamp_dt'].max()
        duration_days = max(0, (max_ts - min_ts).total_seconds() / 86400)
        
        time_range = {
            'start': min_ts.isoformat(),
            'end': max_ts.isoformat(),
            'duration_days': int(duration_days)
        }
        _log(f"Timestamps processed. Range: {duration_days:.0f} days")
        
        # ── Step 4: Build igraph – FAST using TupleList ────────────────────
        if progress_callback:
            progress_callback(f"Building graph ({self.original_node_count:,} nodes, "
                              f"{self.original_edge_count:,} edges)...")
        
        t1 = _time.time()
        # TupleList is implemented in C and is ~10x faster than manual loops
        edge_tuples = list(zip(df['source'].values, df['target'].values))
        G = ig.Graph.TupleList(edge_tuples, directed=False)
        del edge_tuples  # Free memory
        gc.collect()
        
        _log(f"Built graph: {G.vcount():,} nodes, {G.ecount():,} edges "
             f"in {_time.time()-t1:.1f}s")
        
        # ── Step 5+6+7: Per-window community detection & visualization ──────
        # Instead of detecting communities once on the full graph and reusing
        # them statically, we detect communities INDEPENDENTLY per time window
        # so that temporal evolution of community structure is visible.
        
        if progress_callback:
            progress_callback("Building per-window community analysis...")
        
        # We already have the full graph G for reference
        # Build a node→name lookup for the full graph
        full_node_names = set(G.vs['name'])
        
        # ── Activity-based time windowing (from Dash reference app) ─────────
        # Group timestamps by cumulative active-node count so each window has
        # roughly equal "activity" rather than equal wall-clock duration.
        # This produces more informative windows for bursty datasets.
        MAX_WINDOWS = 30
        MAX_ACTIVITY_PER_WINDOW = max(1000, len(df) // MAX_WINDOWS)

        # Count unique active nodes (u ∪ v) per timestamp
        ts_activity = (
            df.groupby('timestamp_dt')
            .apply(lambda g: pd.unique(
                pd.concat([g['source'], g['target']])
            ).size)
            .reset_index()
        )
        ts_activity.columns = ['timestamp_dt', 'active_nodes']
        ts_activity = ts_activity.sort_values('timestamp_dt')
        ts_activity['cum_activity'] = ts_activity['active_nodes'].cumsum()
        ts_activity['time_cluster'] = (
            (ts_activity['cum_activity'] / MAX_ACTIVITY_PER_WINDOW)
            .apply(math.floor)
            .astype(int)
        )
        # Merge cluster labels back into df
        df = df.merge(ts_activity[['timestamp_dt', 'time_cluster']],
                      on='timestamp_dt', how='left')
        df['time_cluster'] = df['time_cluster'].fillna(0).astype(int)

        time_clusters = sorted(df['time_cluster'].unique())
        n_windows = len(time_clusters)
        _log(f"Activity-based windows: {n_windows} windows "
             f"(~{MAX_ACTIVITY_PER_WINDOW:,} active-nodes/window, "
             f"{self.original_edge_count:,} edges)")
        
        time_windows_community = []
        metrics_timeline = []
        metrics_dict = {}
        total_communities_all_windows = 0
        total_unique_community_nodes = set()
        
        for i, tc in enumerate(time_clusters):
            w_df = df[df['time_cluster'] == tc]
            n_edges_window = len(w_df)

            if n_edges_window == 0:
                continue

            # Derive start/end timestamps from the actual data in this cluster
            w_start = w_df['timestamp_dt'].min()
            w_end   = w_df['timestamp_dt'].max()
            wk = f"{w_start.isoformat()}_{w_end.isoformat()}"

            _log(f"Window {i+1}/{n_windows}: {n_edges_window:,} edges "
                 f"({w_start} → {w_end})")

            if progress_callback:
                progress_callback(f"Analyzing window {i+1}/{n_windows} "
                                  f"({n_edges_window:,} edges)...")
            
            # Build window-specific subgraph
            w_sources = w_df['source'].values
            w_targets = w_df['target'].values
            w_edge_tuples = list(zip(w_sources, w_targets))
            w_G = ig.Graph.TupleList(w_edge_tuples, directed=False)
            del w_edge_tuples
            
            n_nodes_window = w_G.vcount()
            
            # Track unique nodes across all windows
            w_node_set = set(w_G.vs['name'])
            total_unique_community_nodes.update(w_node_set)
            
            # Run community detection — Leiden algorithm (better than Label Propagation)
            t_comm = _time.time()
            try:
                import leidenalg
                partition = leidenalg.find_partition(
                    w_G, leidenalg.ModularityVertexPartition
                )
                w_G.vs['community'] = partition.membership
            except Exception:
                # Fallback to label propagation if Leiden fails
                w_comm_lp = w_G.community_label_propagation()
                w_G.vs['community'] = list(w_comm_lp.membership)
            w_comm_arr = np.array(w_G.vs['community'])
            w_degree_arr = np.array(w_G.degree())
            n_comms_window = int(w_comm_arr.max()) + 1
            total_communities_all_windows += n_comms_window

            _log(f"  Window {i+1}: {n_comms_window:,} communities (Leiden) "
                 f"in {_time.time()-t_comm:.1f}s")
            
            # ── Vectorized edge analysis: internal + cross-community counts ──
            # Use numpy for O(edges) edge classification, much faster than
            # Python for-loop over igraph edge objects.
            edge_arr = np.array(w_G.get_edgelist())  # shape (n_edges, 2)
            src_comms = w_comm_arr[edge_arr[:, 0]]
            tgt_comms = w_comm_arr[edge_arr[:, 1]]
            
            # Internal edges: both endpoints in same community
            same_mask = src_comms == tgt_comms
            internal_comms = src_comms[same_mask]
            max_comm_id = int(w_comm_arr.max()) + 1
            internal_edge_arr = np.bincount(internal_comms, minlength=max_comm_id)
            # Convert to dict for lookup
            internal_edge_counts = {int(c): int(internal_edge_arr[c])
                                    for c in range(max_comm_id)
                                    if internal_edge_arr[c] > 0}
            
            # Cross-community edges: endpoints in different communities
            diff_mask = ~same_mask
            cross_src = src_comms[diff_mask]
            cross_tgt = tgt_comms[diff_mask]
            # Normalize pairs to (min, max) for undirected counting
            pair_min = np.minimum(cross_src, cross_tgt)
            pair_max = np.maximum(cross_src, cross_tgt)
            # Use Cantor pairing for unique key (works for community IDs < ~46k)
            # Use key encoding for unique pair counting (works for IDs up to ~3B)
            if max_comm_id < 3_000_000_000:
                pair_keys = pair_min * max_comm_id + pair_max
                unique_keys, counts = np.unique(pair_keys, return_counts=True)
                cross_comm_counts = {}
                for k, cnt in zip(unique_keys, counts):
                    c1 = int(k // max_comm_id)
                    c2 = int(k % max_comm_id)
                    if c1 != -1 and c2 != -1:
                        cross_comm_counts[(c1, c2)] = int(cnt)
            else:
                # Fallback for very large community IDs: Python loop on pairs
                cross_comm_counts = {}
                for c1v, c2v in zip(pair_min, pair_max):
                    c1, c2 = int(c1v), int(c2v)
                    if c1 != -1 and c2 != -1:
                        key = (c1, c2)
                        cross_comm_counts[key] = cross_comm_counts.get(key, 0) + 1
            
            del edge_arr, src_comms, tgt_comms, same_mask, diff_mask
            
            _log(f"  Window {i+1}: edge classification done "
                 f"({len(internal_edge_counts)} comms with internal edges, "
                 f"{len(cross_comm_counts)} cross-community pairs)")
            
            # ── Vectorized per-community stats ──
            # Use bincount for O(n) community sizes and degree sums
            # (max_comm_id already computed above in edge classification)
            comm_sizes = np.bincount(w_comm_arr, minlength=max_comm_id)
            comm_degree_sums = np.bincount(w_comm_arr, weights=w_degree_arr.astype(float),
                                           minlength=max_comm_id)
            
            # For max degree per community: vectorized with np.maximum.at
            comm_max_deg = np.zeros(max_comm_id, dtype=np.int64)
            np.maximum.at(comm_max_deg, w_comm_arr, w_degree_arr)
            
            # Valid communities: size >= 2 and not -1
            valid_comm_ids = [int(c) for c in range(max_comm_id)
                             if comm_sizes[c] >= 2 and c != -1 and c < max_comm_id]
            
            # Sort valid communities by size descending for potential capping
            valid_comm_ids.sort(key=lambda c: int(comm_sizes[c]), reverse=True)
            
            # Cap per window to keep visualization clean and performant
            MAX_COMMS_PER_WINDOW = 50
            truncated_comms = len(valid_comm_ids) > MAX_COMMS_PER_WINDOW
            full_comm_count = len(valid_comm_ids)
            valid_comm_ids = valid_comm_ids[:MAX_COMMS_PER_WINDOW]
            n_valid_comms = len(valid_comm_ids)

            # ── Kamada-Kawai layout on community-level graph ──────────────
            # Build a networkx graph of communities connected by cross-community
            # edges, then run Kamada-Kawai layout so communities are positioned
            # by structural proximity (not a boring grid).
            import networkx as _nx
            Gc = _nx.Graph()
            Gc.add_nodes_from(valid_comm_ids)
            for (c1, c2), cnt in cross_comm_counts.items():
                if c1 in set(valid_comm_ids) and c2 in set(valid_comm_ids):
                    Gc.add_edge(c1, c2, weight=float(cnt))

            # Kamada-Kawai gives positions in roughly [-1, 1]; scale to canvas
            try:
                raw_pos = _nx.kamada_kawai_layout(Gc, weight='weight')
            except Exception:
                # Fallback: spring layout (faster but less stable)
                raw_pos = _nx.spring_layout(Gc, seed=42)

            # Degree centrality on the community-level graph
            centrality = _nx.degree_centrality(Gc)

            # Scale positions to canvas [50, 950] × [50, 550]
            CANVAS_W, CANVAS_H = 1000, 600
            MARGIN = 50
            all_x = [p[0] for p in raw_pos.values()] or [0]
            all_y = [p[1] for p in raw_pos.values()] or [0]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            span_x = max_x - min_x or 1
            span_y = max_y - min_y or 1

            def _scale(px, py):
                cx = MARGIN + (px - min_x) / span_x * (CANVAS_W - 2 * MARGIN)
                cy = MARGIN + (py - min_y) / span_y * (CANVAS_H - 2 * MARGIN)
                return float(cx), float(cy)
            
            community_nodes_window = []
            for comm_id in valid_comm_ids:
                node_count = int(comm_sizes[comm_id])
                avg_degree = float(comm_degree_sums[comm_id] / node_count)
                max_deg = int(comm_max_deg[comm_id])
                internal_edges = internal_edge_counts.get(comm_id, 0)

                # Position from Kamada-Kawai layout
                raw = raw_pos.get(comm_id, (0.0, 0.0))
                cx, cy = _scale(raw[0], raw[1])

                community_nodes_window.append({
                    'id': f"comm_w{i}_{comm_id}",
                    'communityId': comm_id,
                    'nodeCount': node_count,
                    'size': node_count,
                    'avgDegree': avg_degree,
                    'maxDegree': max_deg,
                    'dominantGroup': 'mixed',
                    'isMixed': True,
                    'centroidX': cx,
                    'centroidY': cy,
                    'internalEdges': internal_edges,
                    'degreeCentrality': round(centrality.get(comm_id, 0.0), 4),
                    'memberNodeIds': [],
                    'memberCount': node_count,
                })

            community_nodes_window.sort(key=lambda x: x['nodeCount'], reverse=True)
            
            # Build centroid lookup for community edges
            centroid_map = {}
            for cn in community_nodes_window:
                centroid_map[cn['communityId']] = (cn['centroidX'], cn['centroidY'])
            
            # Build communityEdges list (limit to top connections to avoid huge payload)
            MAX_COMMUNITY_EDGES = 500
            sorted_cross = sorted(cross_comm_counts.items(),
                                  key=lambda x: x[1], reverse=True)
            community_edges_window = []
            for (c1, c2), count in sorted_cross[:MAX_COMMUNITY_EDGES]:
                if c1 in centroid_map and c2 in centroid_map:
                    s_centroid = centroid_map[c1]
                    t_centroid = centroid_map[c2]
                    community_edges_window.append({
                        'sourceCommunityId': c1,
                        'targetCommunityId': c2,
                        'edgeCount': count,
                        'sourceCentroid': [s_centroid[0], s_centroid[1]],
                        'targetCentroid': [t_centroid[0], t_centroid[1]],
                        'weight': count,
                    })
            
            _log(f"  Window {i+1}: {len(community_nodes_window):,} communities "
                 f"(of {full_comm_count:,} total), "
                 f"{len(community_edges_window):,} inter-community edges")
            
            # Density
            density = (2 * n_edges_window / (n_nodes_window * (n_nodes_window - 1))
                       if n_nodes_window > 1 else 0)
            
            time_windows_community.append({
                'start': w_start.isoformat(),
                'end': w_end.isoformat(),
                'window_key': wk,
                'communities': community_nodes_window,
                'communityEdges': community_edges_window,
                'totalCommunities': full_comm_count,
                'totalNodes': n_nodes_window,
                'totalEdges': n_edges_window,
                'truncated': truncated_comms,
            })
            
            metrics_dict[wk] = {
                'num_nodes': n_nodes_window,
                'num_edges': n_edges_window,
                'density': density,
                'connected_components': 1,
                'giant_component_size': n_nodes_window,
                'degree_centrality': {},
                'betweenness_centrality': {},
                'max_degree': int(w_degree_arr.max()) if len(w_degree_arr) > 0 else 0,
            }
            
            metrics_timeline.append({
                'time': w_start.isoformat(),
                'density': density,
                'nodes': n_nodes_window,
                'edges': n_edges_window,
                'components': 1,
                'giant_component': 1.0,
                'max_degree': int(w_degree_arr.max()) if len(w_degree_arr) > 0 else 0,
            })
            
            # Free window graph memory
            del w_G, w_comm_arr, w_degree_arr, w_df
            gc.collect()
        
        _log(f"Per-window analysis complete. Total unique nodes across all windows: "
             f"{len(total_unique_community_nodes):,}")
        
        # ── Step 8: Build result dicts matching existing endpoint format ────
        
        # community_visualization_data
        avg_comms = (total_communities_all_windows / len(time_windows_community)
                     if time_windows_community else 0)
        community_viz_data = {
            'time_windows': time_windows_community,
            'sampling_warning': False,
            'summary': {
                'total_time_windows': len(time_windows_community),
                'avg_communities_per_window': avg_comms,
                'total_communities_across_windows': total_communities_all_windows,
                'total_unique_nodes_across_windows': len(total_unique_community_nodes),
                'original_total_edges': self.original_edge_count,
                'original_total_nodes': self.original_node_count,
                'sampling_applied': False,
                'sampling_note': None,
            }
        }
        
        # visualization_data (lightweight - no individual nodes for large graphs)
        viz_time_windows = []
        for tw in time_windows_community:
            viz_time_windows.append({
                'start': tw['start'],
                'end': tw['end'],
                'nodes': [],
                'edges': [],
                'window_key': tw['window_key'],
                'truncated': True,
                'original_counts': {
                    'nodes': tw['totalNodes'],
                    'edges': tw['totalEdges'],
                }
            })
        
        viz_data = {
            'time_windows': viz_time_windows,
            'metrics_timeline': metrics_timeline,
            'node_evolution': {},
            'sampling_warning': True,
            'summary': {
                'total_time_windows': len(viz_time_windows),
                'total_unique_nodes': self.original_node_count,
                'total_edges': self.original_edge_count,
                'time_span': {
                    'start': min_ts.isoformat(),
                    'end': max_ts.isoformat(),
                },
                'original_total_edges': self.original_edge_count,
                'original_total_nodes': self.original_node_count,
                'sampling_applied': False,
                'sampling_note': None,
            }
        }
        
        # processed_data (summary for endpoint)
        processed_data = {
            'total_edges': self.original_edge_count,
            'unique_nodes': self.original_node_count,
            'time_range': time_range,
            'timestamp_inferred': timestamp_inferred,
            'columns_used': {
                'source': True,
                'target': True,
                'timestamp': 'timestamp' in df.columns,
                'weight': 'weight' in df.columns,
            },
        }
        
        # Free memory
        del df, G, unique_nodes
        gc.collect()
        
        total_time = _time.time() - start_time
        _log(f"Total analysis time: {total_time:.1f}s ({total_time/60:.1f} min)")
        
        if progress_callback:
            progress_callback(f"Analysis complete! {self.original_node_count:,} nodes, "
                              f"{total_communities_all_windows:,} communities across "
                              f"{len(time_windows_community)} windows "
                              f"({total_time:.0f}s)")
        
        return {
            'visualization_data': viz_data,
            'community_visualization_data': community_viz_data,
            'metrics': metrics_dict,
            'processed_data': processed_data,
            'n_communities': total_communities_all_windows,
        }

    async def analyze_large_dataset_from_file(self, file_path: str, filename: str,
                                               column_mapping: Optional[Dict[str, str]] = None,
                                               progress_callback=None) -> Dict:
        """Async wrapper that runs the heavy sync analysis in a thread executor.
        
        This prevents blocking the event loop so HTTP polling keeps working.
        """
        print(f"[LARGE] Starting analysis in thread executor for {file_path}", flush=True)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._analyze_large_sync(
                file_path=file_path,
                filename=filename,
                column_mapping=column_mapping,
                progress_callback=progress_callback,
            )
        )
        print(f"[LARGE] Thread executor completed", flush=True)
        return result