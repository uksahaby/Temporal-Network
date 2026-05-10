"""Submit one analysis request and poll until complete."""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"

# Login
r = requests.post(f"{BASE}/api/auth/login", json={"email": "demo@test.com", "password": "demo1234"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Logged in. Token: {token[:20]}...")

# Submit analysis
payload = {
    "file_id": "15f0d51c93872b9a",
    "column_mapping": {"source": "source", "target": "target", "weight": "weight", "timestamp": "timestamp"},
    "num_windows": 10,
    "compute_communities": True,
}
r = requests.post(f"{BASE}/api/analyze", json=payload, headers=headers)
print(f"Analyze response: {r.status_code}")
data = r.json()
task_id = data.get("task_id")
status = data.get("status")
print(f"Task ID: {task_id}")
print(f"Initial status: {status}")

if not task_id:
    print("No task ID returned!")
    sys.exit(1)

# Poll every 10 seconds for up to 20 minutes
MAX_POLLS = 120
for i in range(MAX_POLLS):
    time.sleep(10)
    try:
        r = requests.get(f"{BASE}/api/analysis/{task_id}", headers=headers, timeout=30)
        d = r.json()
        st = d.get("status")
        progress = d.get("progress", "")
        print(f"[{i+1:3d}] status={st}  progress={progress}")
        
        if st == "completed":
            summary = d.get("summary", {})
            print(f"\n=== COMPLETED ===")
            print(f"  Nodes: {summary.get('total_nodes', '?')}")
            print(f"  Edges: {summary.get('total_edges', '?')}")
            print(f"  Windows: {summary.get('num_windows', '?')}")
            
            # Check communities - use the NEW per-window endpoint
            # Dynamically pick test indices based on actual window count
            total_w = summary.get('num_windows', 500)
            test_indices = [0, 1, total_w // 4, total_w // 2, total_w - 1]
            for win_idx in test_indices:
                rc = requests.get(f"{BASE}/api/analysis/{task_id}/communities/{win_idx}",
                                  headers=headers, timeout=30)
                if rc.status_code == 200:
                    wd = rc.json()
                    w = wd.get("window", {})
                    comms = w.get("communities", [])
                    edges = w.get("communityEdges", [])
                    print(f"  Window {win_idx}: {len(comms)} communities, "
                          f"{len(edges)} community edges, "
                          f"{w.get('totalNodes', 0):,} nodes, "
                          f"{w.get('totalEdges', 0):,} edges "
                          f"(total_windows={wd.get('total_windows')})")
                    if comms:
                        print(f"    Largest: {comms[0].get('nodeCount', '?')} nodes, "
                              f"ID={comms[0].get('communityId', '?')}")
                elif rc.status_code == 404:
                    print(f"  Window {win_idx}: not found (beyond range)")
                else:
                    print(f"  Window {win_idx}: HTTP {rc.status_code}")
            
            # Skip bulk endpoint - with dynamic windows it returns too much data
            break
        elif st == "failed":
            print(f"\n=== FAILED ===")
            print(f"  Error: {d.get('error', '?')}")
            break
    except Exception as e:
        print(f"[{i+1:3d}] Poll error: {e}")

else:
    print("\n=== TIMEOUT (20 min) ===")
