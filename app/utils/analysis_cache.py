import os
import json
from datetime import datetime
from typing import Any, Dict

PERSIST_DIR = os.path.join(os.getcwd(), "data", "analysis_cache")
os.makedirs(PERSIST_DIR, exist_ok=True)

def get_cache_path(task_id: str) -> str:
    return os.path.join(PERSIST_DIR, f"{task_id}.json")

def save_analysis_result(task_id: str, result: Dict[str, Any]):
    path = get_cache_path(task_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, default=str)

def load_analysis_result(task_id: str) -> Dict[str, Any]:
    path = get_cache_path(task_id)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def delete_analysis_result(task_id: str):
    path = get_cache_path(task_id)
    if os.path.exists(path):
        os.remove(path)
