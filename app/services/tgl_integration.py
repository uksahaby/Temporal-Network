import csv
from typing import List, Dict
import os

def export_edges_to_tgl_csv(edges: List[Dict], output_path: str):
    """Export edges to TGL-compatible CSV format."""
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['index', 'src', 'dst', 'time', 'ext_roll'])
        for idx, edge in enumerate(edges):
            src = edge.get('source')
            dst = edge.get('target')
            ts = edge.get('timestamp')
            ext_roll = edge.get('ext_roll', 0)  # Default to training
            writer.writerow([idx, src, dst, ts, ext_roll])

def run_tgl_train(dataset_name: str, config_path: str, tgl_dir: str, python_exec: str):
    """Run TGL's train.py for link prediction."""
    import subprocess
    train_script = os.path.join(tgl_dir, 'train.py')
    cmd = [python_exec, train_script, '--data', dataset_name, '--config', config_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr

def parse_tgl_output(output: str):
    """Parse TGL output for metrics/results (simple example)."""
    # This is a placeholder; actual parsing depends on TGL output format
    lines = output.split('\n')
    summary = [line for line in lines if 'Result' in line or 'Metric' in line]
    return summary
