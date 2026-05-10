# # app/api/endpoints.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
import os
import shutil
from pathlib import Path
import logging
import re

from app.services.data_loader import DataLoader
from app.services.network_analysis import TemporalNetworkAnalyzer
from app.utils.analysis_cache import save_analysis_result, load_analysis_result, delete_analysis_result
import pandas as pd

router = APIRouter()
data_loader = DataLoader()
logger = logging.getLogger(__name__)

# # Store analysis results in memory (use Redis in production)
analysis_cache = {}


def _safe_load_metadata(path) -> dict:
    """Load metadata JSON, handling corrupted files with extra data or BOM."""
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract the first valid JSON object
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(raw.lstrip())
        # Rewrite the file with clean JSON
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, default=str)
        logger.warning(f"Repaired corrupted metadata file: {path}")
        return obj



# class AnalyzeRequest(BaseModel):
#     file_id: str
#     time_resolution: str = "hour"
#     sampling_rate: Optional[int] = None
#     metrics_to_compute: Optional[List[str]] = None


# def _normalize_time_resolution(value: str) -> str:
#     if value is None:
#         return "1h"

#     normalized = value.strip().lower()
#     mapping = {
#         "minute": "1m",
#         "hour": "1h",
#         "day": "1d",
#         "week": "1w",
#     }
#     normalized = mapping.get(normalized, normalized)

#     # Accept values like "30min" and convert to "30m" (expected by create_time_windows).
#     if normalized.endswith("min") and normalized[:-3].isdigit():
#         normalized = f"{normalized[:-3]}m"

#     return normalized


# def _get_step_size(window_size: str) -> str:
#     """Pick a step size that always advances time windows.

#     Important: TemporalNetworkAnalyzer.create_time_windows only supports:
#     - step_size == '30min'
#     - step_size == '1h'
#     - or an '<int>m' minutes string (it treats all other values as minutes)
#     """

#     if window_size == "1h":
#         return "30min"
#     if window_size == "1d":
#         return "720m"  # 12 hours
#     if window_size == "1w":
#         return "1440m"  # 1 day

#     match = re.match(r"^(\d+)m$", window_size)
#     if match:
#         minutes = int(match.group(1))
#         # Ensure step is at least 1 minute to avoid infinite loops.
#         return f"{max(1, minutes // 2)}m" if minutes > 1 else "1m"

#     # Safe fallback
#     return "30min"


# async def _run_analysis_task(
#     *,
#     task_id: str,
#     metadata_path: str,
#     file_id: str,
#     window_size: str,
#     step_size: str,
#     metrics_to_compute: List[str],
# ) -> None:
#     try:
#         try:
#             with open(metadata_path, "r") as f:
#                 metadata = json.load(f)
#         except FileNotFoundError:
#             analysis_cache[task_id] = {
#                 "status": "failed",
#                 "error": "File not found",
#                 "failed_at": datetime.now().isoformat(),
#             }
#             return

#         processed_data = metadata.get("processed_data") or {}
#         edges = processed_data.get("edges")
#         parsing_error = metadata.get("parsing_error")

#         if not isinstance(edges, list) or len(edges) == 0:
#             stored_path = metadata.get("file_path")
#             stored_name = metadata.get("filename")
#             if stored_path:
#                 refreshed = await data_loader.load_from_path(Path(stored_path), stored_name)
#                 metadata.update(
#                     {
#                         "processed_data": refreshed.get("processed_data", {}),
#                         "parsing_error": refreshed.get("parsing_error"),
#                         "rows": refreshed.get("rows", metadata.get("rows", 0)),
#                         "columns": refreshed.get("columns", metadata.get("columns", [])),
#                     }
#                 )
#                 with open(metadata_path, "w") as f:
#                     json.dump(metadata, f, default=str)

#                 processed_data = metadata.get("processed_data") or {}
#                 edges = processed_data.get("edges")
#                 parsing_error = metadata.get("parsing_error")

#         if not isinstance(edges, list) or len(edges) == 0:
#             error_message = parsing_error or "No edges available for analysis."
#             analysis_cache[task_id] = {
#                 "status": "failed",
#                 "error": error_message,
#                 "failed_at": datetime.now().isoformat(),
#             }
#             return

#         def _compute() -> Dict[str, Any]:
#             # Create a per-task analyzer instance to avoid shared mutable state.
#             local_analyzer = TemporalNetworkAnalyzer()
#             graphs = local_analyzer.create_time_windows(
#                 edges,
#                 window_size=window_size,
#                 step_size=step_size,
#             )
#             metrics = local_analyzer.compute_temporal_metrics(graphs, metrics=metrics_to_compute)
#             viz_data = local_analyzer.export_visualization_data(graphs, metrics)
#             return {
#                 "graphs_count": len(graphs),
#                 "metrics": metrics,
#                 "viz_data": viz_data,
#             }

#         computed = await asyncio.to_thread(_compute)

#         analysis_cache[task_id] = {
#             "status": "completed",
#             "visualization_data": computed["viz_data"],
#             "metrics": computed["metrics"],
#             "summary": processed_data,
#             "completed_at": datetime.now().isoformat(),
#         }

#     except Exception as e:
#         logger.exception("Analysis failed for file_id=%s", file_id)
#         analysis_cache[task_id] = {
#             "status": "failed",
#             "error": str(e),
#             "failed_at": datetime.now().isoformat(),
#         }


# @router.post("/analyze")
# async def analyze_network(payload: AnalyzeRequest):
#     """Start network analysis"""

#     file_id = payload.file_id
#     time_resolution = _normalize_time_resolution(payload.time_resolution)
#     sampling_rate = payload.sampling_rate
#     metrics_to_compute = payload.metrics_to_compute or [
#         "degree_centrality",
#         "betweenness_centrality",
#         "closeness_centrality",
#         "pagerank",
#     ]
    
#     metadata_path = f"data/uploads/{file_id}_metadata.json"
#     if not os.path.exists(metadata_path):
#         raise HTTPException(status_code=404, detail="File not found")

#     task_id = f"{file_id}_{datetime.now().timestamp()}"
#     step_size = _get_step_size(time_resolution)

#     analysis_cache[task_id] = {
#         "status": "processing",
#         "submitted_at": datetime.now().isoformat(),
#         "file_id": file_id,
#         "window_size": time_resolution,
#         "step_size": step_size,
#     }

#     task = asyncio.create_task(
#         _run_analysis_task(
#             task_id=task_id,
#             metadata_path=metadata_path,
#             file_id=file_id,
#             window_size=time_resolution,
#             step_size=step_size,
#             metrics_to_compute=metrics_to_compute,
#         )
#     )

#     # If the analysis is quick, return completed data; otherwise return a task_id for polling.
#     try:
#         await asyncio.wait_for(task, timeout=12.0)
#     except asyncio.TimeoutError:
#         return {
#             "task_id": task_id,
#             "status": "processing",
#             "message": "Analysis started",
#         }

#     result = analysis_cache.get(task_id, {})
#     if result.get("status") == "failed":
#         raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))

#     return {
#         "task_id": task_id,
#         "status": "completed",
#         "message": "Analysis completed successfully",
#         "data": result.get("visualization_data", {}),
#     }

# @router.get("/analysis/{task_id}")
# async def get_analysis_results(task_id: str):
#     """Get analysis results"""
    
#     if task_id not in analysis_cache:
#         raise HTTPException(status_code=404, detail="Analysis not found")
    
#     result = analysis_cache[task_id]
    
#     if result.get("status") == "failed":
#         return {
#             "status": "failed",
#             "error": result.get("error"),
#         }

#     if result.get("status") == "processing":
#         return {
#             "status": "processing",
#             "submitted_at": result.get("submitted_at"),
#         }

#     return {
#         "status": "completed",
#         "data": result.get("visualization_data", {}),
#         "completed_at": result.get("completed_at"),
#     }

# @router.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# app/api/routes.py

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import logging
import re
import uuid
import traceback

from app.services.data_loader import DataLoader
from app.services.network_analysis import TemporalNetworkAnalyzer

router = APIRouter()
data_loader = DataLoader()
logger = logging.getLogger(__name__)

# Store analysis results in memory (use Redis in production)
analysis_cache = {}
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class AnalyzeRequest(BaseModel):
    file_id: str
    time_resolution: str = "hour"
    sampling_rate: Optional[int] = None
    metrics_to_compute: Optional[List[str]] = None
    column_mapping: Optional[Dict[str, str]] = None
    generate_missing: bool = True
    max_nodes_viz: Optional[int] = None
    max_edges_viz: Optional[int] = None
    max_nodes_community: Optional[int] = None
    max_edges_community: Optional[int] = None
    compute_communities: bool = True

class ColumnMappingResponse(BaseModel):
    status: str
    message: str
    file_id: str
    available_columns: List[str]
    suggested_mapping: Dict[str, str]
    required_columns: List[str]
    optional_columns: List[str]

class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    duration_days: Optional[int] = None

class ColumnsUsed(BaseModel):
    source: bool = False
    target: bool = False
    timestamp: bool = False
    weight: bool = False

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    rows: int
    columns: List[str]
    time_range: Optional[TimeRange] = None
    parsing_error: Optional[str] = None
    columns_used: Optional[ColumnsUsed] = None
    timestamp_inferred: Optional[bool] = None
    estimated_processing_time: str
    uploaded_at: str

class ProcessedSummary(BaseModel):
    total_edges: int = 0
    unique_nodes: int = 0
    time_range: Optional[TimeRange] = None
    columns_used: Optional[ColumnsUsed] = None

class AnalysisSummary(BaseModel):
    num_windows: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    time_range: Optional[TimeRange] = None
    columns_used: Optional[ColumnsUsed] = None
    timestamp_inferred: Optional[bool] = None

class AnalysisStatusResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[str] = None
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    summary: Optional[AnalysisSummary] = None
    available_columns: Optional[List[str]] = None
    suggested_mapping: Optional[Dict[str, str]] = None
    required_columns: Optional[List[str]] = None
    optional_columns: Optional[List[str]] = None

class FileInfoResponse(BaseModel):
    file_id: str
    filename: str
    columns: List[str]
    rows: int
    has_processed_data: bool
    suggested_mapping: Dict[str, str]
    processed_summary: Optional[ProcessedSummary] = None

class FileListItem(BaseModel):
    file_id: str
    filename: str
    size: int
    rows: int
    columns: List[str]
    has_processed_data: bool
    upload_time: str

class FilesListResponse(BaseModel):
    files: List[FileListItem]

class DeleteFileResponse(BaseModel):
    status: str
    file_id: str

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    active_tasks: int

# ============================================================================
# NEW: Community Visualization Response Models
# ============================================================================
class CommunityNode(BaseModel):
    id: str
    communityId: int
    nodeCount: int
    size: int
    avgDegree: float
    dominantGroup: str
    isMixed: bool
    centroidX: float
    centroidY: float
    internalEdges: int
    memberNodeIds: List[str]
    memberCount: int

class CommunityEdge(BaseModel):
    sourceCommunityId: int
    targetCommunityId: int
    edgeCount: int
    sourceCentroid: List[float]
    targetCentroid: List[float]
    weight: int

class CommunityTimeWindow(BaseModel):
    start: str
    end: str
    window_key: str
    communities: List[CommunityNode]
    communityEdges: List[CommunityEdge]
    totalCommunities: int
    totalNodes: int
    totalEdges: int
    truncated: bool = False  # Added missing field

class CommunityVisualizationResponse(BaseModel):
    task_id: str
    time_windows: List[CommunityTimeWindow]
    summary: Dict[str, Any]


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV/Excel file for analysis - fast mode for large files"""
    try:
        logger.info(f"Received upload request for file: {file.filename}")
        
        # Use fast upload that only saves file and extracts minimal metadata
        # Full processing is deferred to analyze endpoint
        metadata = await data_loader.fast_upload(file)
        
        processed_data = metadata.get("processed_data", {})
        parsing_error = metadata.get("parsing_error")
        file_id = metadata.get("file_id")
        columns = metadata.get("columns", [])
        rows = metadata.get("rows", 0)
        size = metadata.get("size", 0)
        uploaded_at = datetime.now().isoformat()

        # Ensure file_id is a string
        if file_id is None:
            file_id = str(uuid.uuid4())[:8]

        # Check if columns were auto-detected
        columns_used_dict = processed_data.get("columns_used", {}) if processed_data else {}
        columns_used = ColumnsUsed(
            source=columns_used_dict.get("source", False),
            target=columns_used_dict.get("target", False),
            timestamp=columns_used_dict.get("timestamp", False),
            weight=columns_used_dict.get("weight", False)
        )

        timestamp_inferred = processed_data.get("timestamp_inferred", False) if processed_data else False
        
        # For fast uploads, we skip timestamp validation here
        # It will be validated during the analyze phase
        # If timestamp column is not detected, assume it will be inferred
        if not columns_used.timestamp:
            logger.info("Timestamp column not detected - will be inferred/generated during analysis")
            columns_used.timestamp = True  # Will be generated during analysis
            timestamp_inferred = True

        # Get time range if available (may be None for fast uploads)
        time_range_dict = processed_data.get("time_range") if processed_data else None
        time_range = None
        if time_range_dict:
            time_range = TimeRange(
                start=time_range_dict.get("start"),
                end=time_range_dict.get("end"),
                duration_days=time_range_dict.get("duration_days")
            )

        # Estimate processing time based on rows
        estimated_time = "seconds"
        if rows > 1000000:
            estimated_time = "5-10 minutes"
        elif rows > 500000:
            estimated_time = "2-5 minutes"
        elif rows > 100000:
            estimated_time = "1-2 minutes"
        elif rows > 10000:
            estimated_time = "30-60 seconds"

        response = UploadResponse(
            file_id=file_id,
            filename=file.filename or "unknown",
            size=size,
            rows=rows,
            columns=columns,
            time_range=time_range,
            parsing_error=parsing_error,
            columns_used=columns_used,
            timestamp_inferred=timestamp_inferred,
            estimated_processing_time=estimated_time,
            uploaded_at=uploaded_at
        )

        logger.info(f"File uploaded successfully: {file_id}")
        return response

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


def _normalize_time_resolution(value: str) -> str:
    """Normalize time resolution string to backend format"""
    if not value:
        return "1h"

    normalized = value.strip().lower()
    mapping = {
        "minute": "1m",
        "hour": "1h",
        "day": "1d",
        "week": "1w",
        "minutes": "1m",
        "hours": "1h",
        "days": "1d",
        "weeks": "1w",
    }
    
    normalized = mapping.get(normalized, normalized)

    # Accept values like "30min" and convert to "30m"
    if normalized.endswith("min") and normalized[:-3].isdigit():
        normalized = f"{normalized[:-3]}m"
    elif normalized.endswith("minutes") and normalized[:-7].isdigit():
        normalized = f"{normalized[:-7]}m"
    elif normalized.endswith("hours") and normalized[:-5].isdigit():
        normalized = f"{normalized[:-5]}h"
    elif normalized.endswith("days") and normalized[:-4].isdigit():
        normalized = f"{normalized[:-4]}d"

    return normalized


def _get_step_size(window_size: str) -> str:
    """Pick a step size that always advances time windows."""
    if window_size == "1h":
        return "30min"
    if window_size == "1d":
        return "720m"  # 12 hours
    if window_size == "1w":
        return "1440m"  # 1 day

    match = re.match(r"^(\d+)m$", window_size)
    if match:
        minutes = int(match.group(1))
        return f"{max(1, minutes // 2)}m" if minutes > 1 else "1m"
    
    match = re.match(r"^(\d+)h$", window_size)
    if match:
        hours = int(match.group(1))
        return f"{max(1, hours * 30)}m"

    return "30min"


def suggest_column_mapping(columns: List[str]) -> Dict[str, str]:
    """Suggest column mapping based on column names"""
    mapping = {}
    
    if not columns:
        return mapping
    
    # Common patterns with priority
    source_patterns = ['source', 'from', 'src', 'sender', 'origin', 'user_a', 'node1', 'source_id', 'from_id', 'source_node']
    target_patterns = ['target', 'to', 'dst', 'receiver', 'destination', 'user_b', 'node2', 'target_id', 'to_id', 'target_node']
    time_patterns = ['time', 'date', 'timestamp', 'datetime', 'created', 'event', 'logged', 'ts', 'time_stamp', 'event_time']
    weight_patterns = ['weight', 'value', 'count', 'amount', 'strength', 'score', 'frequency', 'magnitude']
    
    # First pass: exact matches
    for col in columns:
        col_lower = col.lower().strip()
        
        if col_lower in source_patterns and 'source' not in mapping:
            mapping['source'] = col
        elif col_lower in target_patterns and 'target' not in mapping:
            mapping['target'] = col
        elif col_lower in time_patterns and 'timestamp' not in mapping:
            mapping['timestamp'] = col
        elif col_lower in weight_patterns and 'weight' not in mapping:
            mapping['weight'] = col
    
    # Second pass: partial matches
    if len(mapping) < 4:
        for col in columns:
            col_lower = col.lower().strip()
            
            if 'source' not in mapping and any(p in col_lower for p in source_patterns):
                mapping['source'] = col
            elif 'target' not in mapping and any(p in col_lower for p in target_patterns):
                mapping['target'] = col
            elif 'timestamp' not in mapping and any(p in col_lower for p in time_patterns):
                mapping['timestamp'] = col
            elif 'weight' not in mapping and any(p in col_lower for p in weight_patterns):
                mapping['weight'] = col
    
    # Fill in missing with first columns if needed
    if len(columns) >= 3:
        if 'source' not in mapping:
            mapping['source'] = columns[0]
        if 'target' not in mapping:
            mapping['target'] = columns[1] if len(columns) > 1 else columns[0]
        if 'timestamp' not in mapping:
            mapping['timestamp'] = columns[2] if len(columns) > 2 else columns[-1]
    
    return mapping


async def _run_analysis_task(
    *,
    task_id: str,
    metadata_path: str,
    file_id: str,
    window_size: str,
    step_size: str,
    metrics_to_compute: List[str],
    column_mapping: Optional[Dict[str, str]] = None,
    generate_missing: bool = True,
    max_nodes_viz: Optional[int] = None,
    max_edges_viz: Optional[int] = None,
    max_nodes_community: Optional[int] = None,
    max_edges_community: Optional[int] = None,
    compute_communities: bool = True,
) -> None:
    """Run analysis in background task"""
    try:
        # Update status
        if task_id in analysis_cache:
            analysis_cache[task_id]["progress"] = "Loading metadata..."
        
        # Load metadata
        try:
            metadata = _safe_load_metadata(metadata_path)
        except FileNotFoundError:
            analysis_cache[task_id] = {
                "status": "failed",
                "error": "File not found",
                "failed_at": datetime.now().isoformat(),
            }
            return

        processed_data = metadata.get("processed_data") or {}
        edges = processed_data.get("edges")
        parsing_error = metadata.get("parsing_error")
        stored_path = metadata.get("file_path")
        stored_name = metadata.get("filename")
        
        # ── LARGE FILE DETECTION ────────────────────────────────────────
        # If file has >500k rows, use the direct file-to-graph pipeline
        # which bypasses the slow edge-serialization (list-of-dicts) step.
        estimated_rows = metadata.get("rows", 0) or 0
        LARGE_FILE_THRESHOLD = 500000  # 500k edges
        
        if estimated_rows > LARGE_FILE_THRESHOLD and stored_path and os.path.exists(stored_path):
            print(f"[LARGE FILE] {estimated_rows:,} rows detected – using direct pipeline", flush=True)
            logger.info(f"[LARGE FILE] {estimated_rows:,} rows detected – using direct pipeline")
            
            if task_id in analysis_cache:
                analysis_cache[task_id]["progress"] = (
                    f"Large file detected ({estimated_rows:,} edges). "
                    f"Running full community analysis..."
                )
            
            def _progress(msg):
                if task_id in analysis_cache:
                    analysis_cache[task_id]["progress"] = msg
                logger.info(f"[LARGE] {msg}")
            
            try:
                local_analyzer = TemporalNetworkAnalyzer()
                result_data = await local_analyzer.analyze_large_dataset_from_file(
                    file_path=stored_path,
                    filename=stored_name or "unknown",
                    column_mapping=column_mapping,
                    progress_callback=_progress,
                )
                
                viz_data = result_data['visualization_data']
                community_viz_data = result_data['community_visualization_data']
                metrics = result_data['metrics']
                p_data = result_data['processed_data']
                
                # Build time_range
                tr = p_data.get('time_range', {})
                time_range = None
                if tr:
                    time_range = TimeRange(
                        start=tr.get('start'),
                        end=tr.get('end'),
                        duration_days=tr.get('duration_days', 0)
                    )
                
                cu = p_data.get('columns_used', {})
                columns_used = ColumnsUsed(
                    source=cu.get('source', True),
                    target=cu.get('target', True),
                    timestamp=cu.get('timestamp', False),
                    weight=cu.get('weight', False),
                )
                
                result = {
                    "status": "completed",
                    "visualization_data": viz_data,
                    "community_visualization_data": community_viz_data,
                    "metrics": metrics,
                    "summary": AnalysisSummary(
                        num_windows=len(viz_data.get('time_windows', [])),
                        total_nodes=p_data.get('unique_nodes', 0),
                        total_edges=p_data.get('total_edges', 0),
                        time_range=time_range,
                        columns_used=columns_used,
                        timestamp_inferred=p_data.get('timestamp_inferred', False),
                    ),
                    "completed_at": datetime.now().isoformat(),
                }
                analysis_cache[task_id] = result
                save_analysis_result(task_id, result)
                print(f"[LARGE FILE] Analysis completed for {task_id}", flush=True)
                logger.info(f"[LARGE FILE] Analysis completed for {task_id}")
                return
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[LARGE FILE] Direct analysis failed: {e}", flush=True)
                logger.exception(f"[LARGE FILE] Direct analysis failed: {e}")
                analysis_cache[task_id] = {
                    "status": "failed",
                    "error": f"Large file analysis failed: {str(e)}",
                    "failed_at": datetime.now().isoformat(),
                }
                return
        
        # ── STANDARD PIPELINE (for smaller files) ──────────────────────
        # Check if edges were sampled (for large files)
        sampling_rate = processed_data.get("sampling_rate", 1.0)
        edges_sampled = sampling_rate < 1.0

        # If edges are missing OR were sampled, reload full file for accurate analysis
        if ((not isinstance(edges, list) or len(edges) == 0) or edges_sampled) and stored_path and stored_name:
            if task_id in analysis_cache:
                if edges_sampled:
                    analysis_cache[task_id]["progress"] = f"Loading full dataset (sampled edges found, rate={sampling_rate:.2%})..."
                else:
                    analysis_cache[task_id]["progress"] = "Recreating edges with column mapping..."
            logger.info(f"Reloading full file for analysis (sampled={edges_sampled}, mapping={column_mapping})")
            
            try:
                # Reload the file with optional column mapping (skip sampling for full analysis)
                refreshed = await data_loader.load_from_path(
                    Path(stored_path), 
                    stored_name,
                    column_mapping=column_mapping,
                    skip_sampling=True  # Load all edges for analysis
                )
                
                # Update metadata with new processed data
                metadata.update({
                    "processed_data": refreshed.get("processed_data", {}),
                    "parsing_error": refreshed.get("parsing_error"),
                    "rows": refreshed.get("rows", metadata.get("rows", 0)),
                    "columns": refreshed.get("columns", metadata.get("columns", [])),
                })
                
                # Save updated metadata (strip edges to keep file small)
                save_meta = dict(metadata)
                pd_copy = dict(save_meta.get("processed_data", {}))
                pd_copy.pop("edges", None)
                save_meta["processed_data"] = pd_copy
                with open(metadata_path, "w") as f:
                    json.dump(save_meta, f, default=str)

                processed_data = metadata.get("processed_data") or {}
                edges = processed_data.get("edges")
                parsing_error = metadata.get("parsing_error")
                
                logger.info(f"Recreated {len(edges) if edges else 0} edges")
                
            except Exception as e:
                logger.error(f"Failed to recreate edges: {e}")
                analysis_cache[task_id] = {
                    "status": "failed",
                    "error": f"Failed to process with column mapping: {str(e)}",
                    "failed_at": datetime.now().isoformat(),
                }
                return

        # Final check for edges
        if not isinstance(edges, list) or len(edges) == 0:
            error_message = parsing_error or "No edges available for analysis. Please check your data format."
            analysis_cache[task_id] = {
                "status": "failed",
                "error": error_message,
                "failed_at": datetime.now().isoformat(),
            }
            return

        # Create analyzer instance
        local_analyzer = TemporalNetworkAnalyzer()
        # Set sampling thresholds if provided
        if max_nodes_viz is not None:
            setattr(local_analyzer, 'max_nodes_viz', max_nodes_viz)
        if max_edges_viz is not None:
            setattr(local_analyzer, 'max_edges_viz', max_edges_viz)
        if max_nodes_community is not None:
            setattr(local_analyzer, 'max_nodes_community', max_nodes_community)
        if max_edges_community is not None:
            setattr(local_analyzer, 'max_edges_community', max_edges_community)
        
        try:
            # Update analysis status
            if task_id in analysis_cache:
                analysis_cache[task_id]["progress"] = "Creating time windows..."
            
            # Create time windows
            graphs = await local_analyzer.create_time_windows(
                edges,
                window_size=window_size,
                step_size=step_size,
            )
            
            if not graphs:
                analysis_cache[task_id] = {
                    "status": "failed",
                    "error": "No time windows could be created from the data. Try a different time resolution.",
                    "failed_at": datetime.now().isoformat(),
                }
                return
            
            # Update progress
            if task_id in analysis_cache:
                analysis_cache[task_id]["progress"] = f"Created {len(graphs)} time windows. Computing metrics..."
            
            # Compute metrics
            metrics = await local_analyzer.compute_temporal_metrics(
                graphs, 
                metrics=metrics_to_compute
            )
            
            # Update progress
            if task_id in analysis_cache:
                analysis_cache[task_id]["progress"] = "Generating visualization data..."
            
            # Export visualization data (individual nodes - for small graphs)
            viz_data = await local_analyzer.export_visualization_data(graphs, metrics)
            # Add warning flag if sampling is applied in any window
            viz_data['sampling_warning'] = any(w.get('truncated', False) for w in viz_data.get('time_windows', []))

            # Prepare metadata values used in result
            time_range_dict = processed_data.get("time_range", {})
            time_range = None
            if time_range_dict:
                time_range = TimeRange(
                    start=time_range_dict.get("start"),
                    end=time_range_dict.get("end"),
                    duration_days=time_range_dict.get("duration_days")
                )
            columns_used_dict = processed_data.get("columns_used", {})
            columns_used = ColumnsUsed(
                source=columns_used_dict.get("source", False),
                target=columns_used_dict.get("target", False),
                timestamp=columns_used_dict.get("timestamp", False),
                weight=columns_used_dict.get("weight", False)
            )

            # Export community visualization data (for large graphs) or schedule background processing
            community_viz_data = None
            if compute_communities:
                community_viz_data = await local_analyzer.export_community_visualization_data(graphs, metrics)
                community_viz_data['sampling_warning'] = any(w.get('truncated', False) for w in community_viz_data.get('time_windows', []))
            else:
                # Save interim result and keep graphs in-memory for background community detection
                result = {
                    "status": "completed",
                    "visualization_data": viz_data,
                    "community_visualization_data": None,
                    "metrics": metrics,
                    "summary": AnalysisSummary(
                        num_windows=len(graphs),
                        total_nodes=processed_data.get("unique_nodes", 0),
                        total_edges=processed_data.get("total_edges", 0),
                        time_range=time_range,
                        columns_used=columns_used,
                        timestamp_inferred=processed_data.get("timestamp_inferred", False)
                    ),
                    "completed_at": datetime.now().isoformat(),
                }
                analysis_cache[task_id] = result
                # store graphs in memory only (do not persist)
                analysis_cache[task_id]["graphs"] = graphs
                # persist lightweight result (without graphs)
                save_analysis_result(task_id, result)
                # schedule background community detection
                asyncio.create_task(_run_community_detection_task(task_id))
                logger.info(f"Analysis completed (communities deferred) for task {task_id}")
                return
            
            # Get time range from processed data
            time_range_dict = processed_data.get("time_range", {})
            time_range = None
            if time_range_dict:
                time_range = TimeRange(
                    start=time_range_dict.get("start"),
                    end=time_range_dict.get("end"),
                    duration_days=time_range_dict.get("duration_days")
                )
            
            # Get columns used
            columns_used_dict = processed_data.get("columns_used", {})
            columns_used = ColumnsUsed(
                source=columns_used_dict.get("source", False),
                target=columns_used_dict.get("target", False),
                timestamp=columns_used_dict.get("timestamp", False),
                weight=columns_used_dict.get("weight", False)
            )
            
            # Store results in cache
            result = {
                "status": "completed",
                "visualization_data": viz_data,
                "community_visualization_data": community_viz_data,  # NEW
                "metrics": metrics,
                # 'graphs' is not JSON serializable, so do not persist
                "summary": AnalysisSummary(
                    num_windows=len(graphs),
                    total_nodes=processed_data.get("unique_nodes", 0),
                    total_edges=processed_data.get("total_edges", 0),
                    time_range=time_range,
                    columns_used=columns_used,
                    timestamp_inferred=processed_data.get("timestamp_inferred", False)
                ),
                "completed_at": datetime.now().isoformat(),
            }
            analysis_cache[task_id] = result
            save_analysis_result(task_id, result)
            logger.info(f"Analysis completed for task {task_id}")
            
        except Exception as e:
            logger.exception(f"Analysis computation failed: {str(e)}")
            analysis_cache[task_id] = {
                "status": "failed",
                "error": f"Analysis computation failed: {str(e)}",
                "failed_at": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.exception(f"Analysis failed for file_id={file_id}")
        analysis_cache[task_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
        }


async def _run_community_detection_task(task_id: str) -> None:
    """Background task to run community detection on graphs stored in memory for a task."""
    try:
        result = analysis_cache.get(task_id)
        if not result:
            logger.error(f"Community task: no analysis result for {task_id}")
            return

        graphs = result.get("graphs") or analysis_cache.get(task_id, {}).get("graphs")
        metrics = result.get("metrics", {})
        if not graphs:
            logger.error(f"Community task: no graphs available for {task_id}")
            return

        # Mark progress
        analysis_cache[task_id]["progress"] = "Running community detection in background..."

        local_analyzer = TemporalNetworkAnalyzer()
        loop = asyncio.get_event_loop()
        tasks = []
        for win_key, g in graphs.items():
            # run community detection synchronously in thread executor to avoid pickling issues
            tasks.append(loop.run_in_executor(local_analyzer.executor, local_analyzer._ensure_communities_sync, g))

        completed_graphs = await asyncio.gather(*tasks)

        # Rebuild graph dict
        graphs_by_key = {k: v for k, v in zip(graphs.keys(), completed_graphs)}

        # Export community visualization data
        community_viz_data = await local_analyzer.export_community_visualization_data(graphs_by_key, metrics)
        community_viz_data['sampling_warning'] = any(w.get('truncated', False) for w in community_viz_data.get('time_windows', []))

        # Update cache and persist
        result['community_visualization_data'] = community_viz_data
        analysis_cache[task_id] = result
        # Remove graphs to free memory
        analysis_cache[task_id].pop('graphs', None)

        # Persist updated result (without graphs)
        to_save = dict(result)
        to_save.pop('graphs', None)
        save_analysis_result(task_id, to_save)
        logger.info(f"Background community detection completed for {task_id}")

    except Exception as e:
        logger.exception(f"Background community detection failed for {task_id}: {e}")
        if task_id in analysis_cache:
            analysis_cache[task_id]['progress'] = 'communities_failed'


@router.post("/analyze", response_model=AnalysisStatusResponse)
async def analyze_network(payload: AnalyzeRequest):
    """Start network analysis with optional column mapping"""
    
    file_id = payload.file_id
    time_resolution = _normalize_time_resolution(payload.time_resolution)
    metrics_to_compute = payload.metrics_to_compute or [
        "degree_centrality",
        "betweenness_centrality",
        "closeness_centrality",
        "pagerank",
    ]

    # Sampling thresholds
    max_nodes_viz = payload.max_nodes_viz
    max_edges_viz = payload.max_edges_viz
    max_nodes_community = payload.max_nodes_community
    max_edges_community = payload.max_edges_community

    metadata_path = UPLOAD_DIR / f"{file_id}_metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Validate timestamp mapping before running analysis
    metadata = _safe_load_metadata(metadata_path)
    processed_data = metadata.get("processed_data", {})
    columns_used = processed_data.get("columns_used", {})
    if not columns_used.get("timestamp", False):
        raise HTTPException(status_code=400, detail="No valid timestamp column detected or mapped. Please map your timestamp column during upload.")

    # Load metadata to check columns
    try:
        metadata = _safe_load_metadata(metadata_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load metadata: {str(e)}")
    
    available_columns = metadata.get('columns', [])
    processed_data = metadata.get('processed_data', {})
    
    # Check if we have processed data with edges
    has_edges = bool(processed_data and processed_data.get('edges'))
    
    # If no edges and no column mapping provided, try auto-mapping
    if not has_edges and not payload.column_mapping:
        suggestions = suggest_column_mapping(available_columns)
        # Check if all required columns are present in suggestions
        required = ["source", "target", "timestamp"]
        missing = [col for col in required if col not in suggestions]
        if missing:
            # Still missing required columns, return error with details
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "needs_mapping",
                    "message": f"Could not auto-map required columns: {', '.join(missing)}. Please map your columns to source, target, and timestamp.",
                    "file_id": file_id,
                    "available_columns": available_columns,
                    "suggested_mapping": suggestions,
                    "required_columns": required,
                    "optional_columns": ["weight"]
                }
            )
        else:
            # Auto-mapping found all required columns, proceed with analysis
            payload.column_mapping = suggestions
    
    task_id = f"{file_id}_{int(datetime.now().timestamp())}"
    step_size = _get_step_size(time_resolution)

    # Initialize cache entry
    analysis_cache[task_id] = {
        "status": "processing",
        "submitted_at": datetime.now().isoformat(),
        "file_id": file_id,
        "window_size": time_resolution,
        "step_size": step_size,
        "progress": "Starting analysis...",
    }

    # Start the analysis task
    asyncio.create_task(
        _run_analysis_task(
            task_id=task_id,
            metadata_path=str(metadata_path),
            file_id=file_id,
            window_size=time_resolution,
            step_size=step_size,
            metrics_to_compute=metrics_to_compute,
            column_mapping=payload.column_mapping,
            generate_missing=payload.generate_missing,
            max_nodes_viz=max_nodes_viz,
            max_edges_viz=max_edges_viz,
            max_nodes_community=max_nodes_community,
            max_edges_community=max_edges_community,
            compute_communities=payload.compute_communities,
        )
    )

    return AnalysisStatusResponse(
        status="processing",
        task_id=task_id,
        file_id=file_id,
        message="Analysis started",
        submitted_at=datetime.now().isoformat()
    )


@router.get("/analysis/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_results(task_id: str):
    """Get analysis results by task ID"""
    
    result = analysis_cache.get(task_id)
    if not result:
        # Try to load from disk
        result = load_analysis_result(task_id)
        if result:
            analysis_cache[task_id] = result
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis not found for task_id '{task_id}'. Possible reasons: task_id is invalid, analysis was not started, or backend was restarted and cache was cleared."
        )
    
    if result.get("status") == "failed":
        # Always include a message property in the error response
        error_msg = result.get("error") or "Analysis failed."
        return AnalysisStatusResponse(
            status="failed",
            error=error_msg,
            message=error_msg,
            failed_at=result.get("failed_at")
        )

    if result.get("status") == "processing":
        return AnalysisStatusResponse(
            status="processing",
            task_id=task_id,
            submitted_at=result.get("submitted_at"),
            progress=result.get("progress", "Processing...")
        )

    # Handle completed status
    summary_dict = result.get("summary")
    summary = None
    if summary_dict:
        if isinstance(summary_dict, dict):
            summary = AnalysisSummary(**summary_dict)
        else:
            summary = summary_dict

    return AnalysisStatusResponse(
        status="completed",
        task_id=task_id,
        data=result.get("visualization_data", {}),
        summary=summary,
        completed_at=result.get("completed_at"),
        message="Analysis completed successfully",
        error=None,
        progress=None,
        # Add sampling warning if present
        **({"sampling_warning": result["visualization_data"].get("sampling_warning")}
           if "visualization_data" in result and "sampling_warning" in result["visualization_data"] else {})
    )


# ============================================================================
# NEW ENDPOINT: Get community visualization data
# ============================================================================
@router.get("/analysis/{task_id}/communities", response_model=CommunityVisualizationResponse)
async def get_community_analysis(task_id: str):
    """Get community-level visualization data (each community = one circle)"""
    
    result = analysis_cache.get(task_id)
    if not result:
        # Try to load from disk
        result = load_analysis_result(task_id)
        if result:
            analysis_cache[task_id] = result
    
    if not result:
        logger.warning(f"Community request for unknown task: {task_id}")
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    status = result.get("status")
    if status != "completed":
        logger.info(f"Community request for task {task_id} with status: {status}, progress: {result.get('progress')}")
        if status == "processing":
            raise HTTPException(status_code=202, detail=f"Analysis still processing: {result.get('progress', 'in progress')}")
        elif status == "failed":
            raise HTTPException(status_code=400, detail=f"Analysis failed: {result.get('error', 'unknown error')}")
        else:
            raise HTTPException(status_code=400, detail=f"Analysis not completed. Current status: {status}")
    
    community_data = result.get("community_visualization_data")
    if not community_data:
        # Analysis completed but community data is missing
        logger.warning(f"Task {task_id} completed but no community_visualization_data found")
        raise HTTPException(
            status_code=404, 
            detail="Community data not available. The analysis may have completed without generating community visualizations."
        )
    
    time_windows = community_data.get("time_windows", [])
    logger.info(f"Returning community data for task {task_id}: {len(time_windows)} windows")

    return CommunityVisualizationResponse(
        task_id=task_id,
        time_windows=time_windows,
        summary=community_data.get("summary", {}),
    )


# ============================================================================
# NEW ENDPOINT: Get single community window by index (on-demand loading)
# ============================================================================
@router.get("/analysis/{task_id}/communities/{window_index}")
async def get_community_window(task_id: str, window_index: int):
    """Get community data for a single time window by index.
    
    This endpoint serves one window at a time so the frontend can fetch
    communities on-demand as the user moves the time slider, avoiding
    massive JSON payloads and WebGL memory exhaustion.
    """
    result = analysis_cache.get(task_id)
    if not result:
        result = load_analysis_result(task_id)
        if result:
            analysis_cache[task_id] = result
    
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    status = result.get("status")
    if status != "completed":
        if status == "processing":
            raise HTTPException(status_code=202, detail=f"Analysis still processing: {result.get('progress', 'in progress')}")
        raise HTTPException(status_code=400, detail=f"Analysis not completed. Status: {status}")
    
    community_data = result.get("community_visualization_data")
    if not community_data:
        raise HTTPException(status_code=404, detail="Community data not available")
    
    time_windows = community_data.get("time_windows", [])
    total_windows = len(time_windows)
    
    if window_index < 0 or window_index >= total_windows:
        raise HTTPException(
            status_code=404,
            detail=f"Window index {window_index} out of range. Valid range: 0-{total_windows - 1}"
        )
    
    window = time_windows[window_index]
    summary = community_data.get("summary", {})
    
    return {
        "task_id": task_id,
        "window_index": window_index,
        "total_windows": total_windows,
        "window": window,
        "summary": summary,
    }


@router.get("/file/{file_id}/columns", response_model=FileInfoResponse)
async def get_file_columns(file_id: str):
    """Get column information for a file"""
    metadata_path = UPLOAD_DIR / f"{file_id}_metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        metadata = _safe_load_metadata(metadata_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load metadata: {str(e)}")
    
    columns = metadata.get('columns', [])
    processed_data = metadata.get('processed_data', {})
    has_edges = bool(processed_data and processed_data.get('edges'))
    
    suggestions = suggest_column_mapping(columns)
    
    # Build processed summary if available
    processed_summary = None
    if processed_data:
        time_range_dict = processed_data.get("time_range", {})
        time_range = None
        if time_range_dict:
            time_range = TimeRange(
                start=time_range_dict.get("start"),
                end=time_range_dict.get("end"),
                duration_days=time_range_dict.get("duration_days")
            )
        
        columns_used_dict = processed_data.get("columns_used", {})
        columns_used = ColumnsUsed(
            source=columns_used_dict.get("source", False),
            target=columns_used_dict.get("target", False),
            timestamp=columns_used_dict.get("timestamp", False),
            weight=columns_used_dict.get("weight", False)
        )
        
        processed_summary = ProcessedSummary(
            total_edges=processed_data.get("total_edges", 0),
            unique_nodes=processed_data.get("unique_nodes", 0),
            time_range=time_range,
            columns_used=columns_used
        )
    
    return FileInfoResponse(
        file_id=file_id,
        filename=metadata.get('filename', ''),
        columns=columns,
        rows=metadata.get('rows', 0),
        has_processed_data=has_edges,
        suggested_mapping=suggestions,
        processed_summary=processed_summary
    )


@router.get("/files", response_model=FilesListResponse)
async def list_files():
    """List all uploaded files"""
    files = []
    
    for metadata_file in UPLOAD_DIR.glob("*_metadata.json"):
        try:
            metadata = _safe_load_metadata(metadata_file)
                
            file_item = FileListItem(
                file_id=metadata.get("file_id", ""),
                filename=metadata.get("filename", "unknown"),
                size=metadata.get("size", 0),
                rows=metadata.get("rows", 0),
                columns=metadata.get("columns", []),
                has_processed_data=bool(metadata.get("processed_data")),
                upload_time=datetime.fromtimestamp(metadata_file.stat().st_mtime).isoformat()
            )
            files.append(file_item)
        except Exception as e:
            logger.error(f"Error reading metadata file {metadata_file}: {e}")
    
    # Sort by upload time descending
    files.sort(key=lambda x: x.upload_time, reverse=True)
    
    return FilesListResponse(files=files)


@router.delete("/file/{file_id}", response_model=DeleteFileResponse)
async def delete_file(file_id: str):
    """Delete a file and its metadata"""
    metadata_path = UPLOAD_DIR / f"{file_id}_metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Load metadata to get file path
        metadata = _safe_load_metadata(metadata_path)
        
        # Delete the data file
        file_path = Path(metadata.get("file_path", ""))
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted data file: {file_path}")
        
        # Delete metadata
        metadata_path.unlink()
        logger.info(f"Deleted metadata: {metadata_path}")
        
        # Clean up any analysis tasks for this file
        # Remove all analysis results for this file (by prefix)
        for fname in os.listdir(os.path.join(os.getcwd(), "data", "analysis_cache")):
            if fname.startswith(file_id):
                delete_analysis_result(fname.replace(".json", ""))
        tasks_to_remove = []
        for task_id, task_data in analysis_cache.items():
            if task_data.get("file_id") == file_id:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            analysis_cache.pop(task_id, None)
            logger.info(f"Removed task {task_id} from cache")
        
        return DeleteFileResponse(status="deleted", file_id=file_id)
        
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    active_tasks = len([t for t in analysis_cache.values() if t.get("status") == "processing"])
    
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        active_tasks=active_tasks
    )


@router.delete("/cache")
async def clear_cache():
    """Clear analysis cache (for development/testing)"""
    analysis_cache.clear()
    return {"status": "cache cleared"}


# ------------------------------------------------------------------
# Global community artifacts endpoints
# ------------------------------------------------------------------
@router.get("/file/{file_id}/global", response_model=Dict)
async def get_global_artifacts(file_id: str):
    """List available global analysis artifacts for a file_id"""
    out_dir = Path("data/analysis_cache")
    node_csv = out_dir / f"{file_id}_node_communities.csv"
    summary_json = out_dir / f"{file_id}_global_communities.json"
    meta_json = out_dir / f"{file_id}_global_result_meta.json"

    available = {}
    if node_csv.exists():
        available['node_communities_csv'] = str(node_csv)
    if summary_json.exists():
        available['community_summary_json'] = str(summary_json)
    if meta_json.exists():
        available['meta'] = str(meta_json)

    if not available:
        raise HTTPException(status_code=404, detail="No global artifacts found for this file_id")

    return available


@router.get("/file/{file_id}/global/communities")
async def download_global_communities(file_id: str):
    """Return the community summary JSON for the global result if present"""
    out_dir = Path("data/analysis_cache")
    summary_json = out_dir / f"{file_id}_global_communities.json"
    if not summary_json.exists():
        raise HTTPException(status_code=404, detail="Global community summary not found")
    try:
        with open(summary_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}/global/node_communities.csv")
async def download_node_communities_csv(file_id: str):
    """Send the node->community CSV file for download"""
    out_dir = Path("data/analysis_cache")
    node_csv = out_dir / f"{file_id}_node_communities.csv"
    if not node_csv.exists():
        raise HTTPException(status_code=404, detail="Node communities CSV not found")
    return FileResponse(path=str(node_csv), media_type='text/csv', filename=node_csv.name)


@router.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all registered routes"""
    return {"routes": [getattr(r, 'path', str(r)) for r in router.routes], "count": len(router.routes)}