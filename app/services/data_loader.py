
from fastapi import UploadFile
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from uuid import uuid4
import io
import zipfile
import csv
import re
from difflib import get_close_matches
from xml.etree import ElementTree
import logging

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = 50000  # Optimized chunk size

    async def fast_upload(self, file: UploadFile) -> Dict:
        """Fast upload that only saves file and extracts minimal metadata.
        
        Does NOT parse the entire file - just saves it and counts lines.
        Full processing is deferred to the analyze endpoint.
        """
        filename = file.filename or "upload.bin"
        
        # Stream to disk with MD5 hashing
        tmp_path = self.upload_dir / f"tmp_{uuid4().hex}_{filename}"
        hasher = hashlib.md5()
        size = 0
        line_count = 0
        
        with open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
                out.write(chunk)
                # Count newlines for approximate row count
                line_count += chunk.count(b'\n')
        
        file_id = hasher.hexdigest()[:16]
        file_path = self.upload_dir / f"{file_id}_{filename}"
        
        if file_path.exists():
            file_path = self.upload_dir / f"{file_id}_{uuid4().hex}_{filename}"
        
        tmp_path.replace(file_path)
        
        # Quick column detection from first few lines only
        columns = []
        sample_rows = []
        parsing_error = None
        ext = Path(filename).suffix.lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first 100 lines for quick analysis
                for i, line in enumerate(f):
                    if i >= 100:
                        break
                    sample_rows.append(line.strip())
            
            # Detect delimiter and columns
            if sample_rows:
                first_line = sample_rows[0]
                # Try common delimiters
                for delim in [',', '\t', ' ', ';']:
                    parts = first_line.split(delim)
                    if len(parts) >= 2:
                        # Check if first line looks like header (has text) or data (all numeric)
                        is_header = any(not p.replace('.','').replace('-','').isdigit() for p in parts[:3])
                        if is_header:
                            columns = [p.strip() for p in parts]
                        else:
                            # Generate column names for edge list files
                            if len(parts) == 2:
                                columns = ['source', 'target']
                            elif len(parts) == 3:
                                columns = ['source', 'target', 'weight']
                            elif len(parts) >= 4:
                                columns = ['source', 'target', 'weight', 'timestamp']
                        break
        except Exception as e:
            parsing_error = str(e)
            logger.warning(f"Quick column detection failed: {e}")
        
        # Auto-detect column mapping based on column names
        columns_used = {
            'source': False,
            'target': False,
            'timestamp': False,
            'weight': False
        }
        
        # Check for common column name patterns
        col_lower = [c.lower() if isinstance(c, str) else str(c) for c in columns]
        source_names = ['source', 'src', 'from', 'node1', 'u', '0']
        target_names = ['target', 'dst', 'dest', 'to', 'node2', 'v', '1']
        time_names = ['timestamp', 'time', 'date', 'datetime', 'ts', '3']
        weight_names = ['weight', 'value', 'rating', 'score', '2']
        
        for i, col in enumerate(col_lower):
            if any(n in col for n in source_names) or (i == 0 and len(columns) >= 2):
                columns_used['source'] = True
            if any(n in col for n in target_names) or (i == 1 and len(columns) >= 2):
                columns_used['target'] = True
            if any(n in col for n in time_names) or (i == 3 and len(columns) >= 4):
                columns_used['timestamp'] = True
            if any(n in col for n in weight_names) or (i == 2 and len(columns) >= 3):
                columns_used['weight'] = True
        
        # For edge list files (.edges, .edgelist, etc.), assume standard format
        if ext in ['.edges', '.edgelist', '.edge', '.mtx']:
            columns_used['source'] = True
            columns_used['target'] = True
            if len(columns) >= 4:
                columns_used['timestamp'] = True
                columns_used['weight'] = True
            elif len(columns) >= 3:
                # Third column could be weight or timestamp - check sample
                columns_used['weight'] = True
                # Generate timestamps later
                columns_used['timestamp'] = True  # Will be generated
        
        # Save minimal metadata
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "file_path": str(file_path),
            "size": size,
            "rows": max(1, line_count - 1),  # Approximate row count (minus header)
            "columns": columns,
            "processed_data": {
                "columns_used": columns_used,
                "timestamp_inferred": not any(n in str(columns).lower() for n in time_names),
                "edges": None,  # Will be populated during analyze
            },
            "parsing_error": parsing_error,
            "fast_upload": True,  # Flag to indicate deferred processing
        }
        
        # Save metadata to JSON
        metadata_path = self.upload_dir / f"{file_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, default=str)
        
        logger.info(f"Fast upload complete: {file_id}, {size} bytes, ~{line_count} rows")
        return metadata

    async def load_file(self, file: UploadFile) -> Dict:
        """Load CSV, TSV, Excel, JSON, YAML, XML, edge list, or ZIP file with streaming"""
        filename = file.filename or "upload.bin"

        # Stream to disk with MD5 hashing
        tmp_path = self.upload_dir / f"tmp_{uuid4().hex}_{filename}"
        hasher = hashlib.md5()
        size = 0

        with open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
                out.write(chunk)

        file_id = hasher.hexdigest()[:16]
        file_path = self.upload_dir / f"{file_id}_{filename}"

        if file_path.exists():
            file_path = self.upload_dir / f"{file_id}_{uuid4().hex}_{filename}"

        tmp_path.replace(file_path)

        # Process file with memory-efficient loading
        parsing_error: Optional[str] = None
        df = pd.DataFrame()
        raw_data = None

        try:
            ext = Path(filename).suffix.lower()

            # MatrixMarket support
            if ext == '.mtx' or self._is_matrix_market(file_path):
                df = self._load_matrix_market(file_path)
                raw_data = df.to_dict('records') if not df.empty else None
            else:
                if ext == '.csv':
                    df = await self._load_csv_streaming(file_path)
                elif ext == '.tsv':
                    df = await self._load_delimited_streaming(file_path, delimiter="\t")
                elif ext in ['.txt', '.dat', '.edge', '.edgelist', '.edges']:
                    df = await self._load_text_streaming(file_path)
                elif ext in ['.xlsx', '.xls']:
                    df = await self._load_excel_streaming(file_path)
                elif ext == '.json':
                    df = await self._load_json_streaming(file_path)
                elif ext in ['.yaml', '.yml'] and yaml:
                    df = await self._load_yaml_streaming(file_path)
                elif ext == '.xml':
                    df = await self._load_xml_streaming(file_path)
                elif ext == '.zip':
                    df = await self._load_zip_streaming(file_path)
                else:
                    df = await self._load_text_streaming(file_path)
                if not df.empty:
                    raw_data = df.to_dict('records')

            # Store raw data as records for later use
            if not df.empty:
                raw_data = df.to_dict('records')

        except Exception as exc:
            parsing_error = str(exc)
            logger.error(f"Error loading file {filename}: {exc}")

        # Process temporal data efficiently
        processed_data: Dict[str, Any] = {}
        if not df.empty:
            try:
                processed_data = await self._process_temporal_data_optimized(df, filename)
            except Exception as exc:
                parsing_error = parsing_error or str(exc)
                logger.error(f"Error processing temporal data: {exc}")

        # Save metadata
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "file_path": str(file_path),
            "size": size,
            "rows": len(df),
            "columns": [str(c) for c in df.columns] if not df.empty else [],
            "data_summary": self._summarize_data_optimized(df),
            "processed_data": processed_data,
            "raw_data_sample": raw_data[:100] if raw_data and len(raw_data) > 100 else raw_data,  # Store sample
            "parsing_error": parsing_error,
        }

        # Save metadata to JSON
        metadata_path = self.upload_dir / f"{file_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, default=str)

        return metadata

    async def load_from_path(self, file_path: Path, filename: Optional[str] = None, 
                           column_mapping: Optional[Dict[str, str]] = None,
                           skip_sampling: bool = False,
                           max_rows: Optional[int] = 200000) -> Dict:
        """Re-load a stored file by path for analysis with optional column mapping.
        
        Args:
            file_path: Path to the data file
            filename: Optional filename override
            column_mapping: Optional column name mapping
            skip_sampling: If True, return all edges without sampling (for full analysis)
            max_rows: Maximum rows to load (default 200k for performance).
                      When skip_sampling=True, this limit is removed.
        """
        # When skip_sampling is requested, remove the row limit
        if skip_sampling:
            max_rows = None
        
        if not file_path.exists():
            raise ValueError("Stored file not found.")

        size = file_path.stat().st_size
        resolved_name = filename or file_path.name
        file_id = None
        if "_" in file_path.name:
            file_id = file_path.name.split("_", 1)[0]

        parsing_error: Optional[str] = None
        df = pd.DataFrame()

        try:
            ext = Path(resolved_name).suffix.lower()
            if ext == '.csv':
                df = await self._load_csv_streaming(file_path, max_rows=max_rows)
            elif ext == '.tsv':
                df = await self._load_delimited_streaming(file_path, delimiter="\t")
            elif ext in ['.txt', '.dat', '.edge', '.edgelist', '.edges']:
                df = await self._load_text_streaming(file_path, max_rows=max_rows)
            elif ext in ['.xlsx', '.xls']:
                df = await self._load_excel_streaming(file_path)
            elif ext == '.json':
                df = await self._load_json_streaming(file_path)
            elif ext in ['.yaml', '.yml'] and yaml:
                df = await self._load_yaml_streaming(file_path)
            elif ext == '.xml':
                df = await self._load_xml_streaming(file_path)
            elif ext == '.zip':
                df = await self._load_zip_streaming(file_path)
            else:
                df = await self._load_text_streaming(file_path, max_rows=max_rows)
        except Exception as exc:
            parsing_error = str(exc)
            logger.error(f"Error loading from path {file_path}: {exc}")
            if "Length mismatch" in str(exc):
                parsing_error = "Column mismatch: The uploaded file does not match the expected columns. Please check your file format or use column mapping."

        if column_mapping and not df.empty:
            try:
                df = df.rename(columns=column_mapping)
                logger.info(f"Applied column mapping: {column_mapping}")
            except Exception as exc:
                logger.error(f"Error applying column mapping: {exc}")

        processed_data: Dict[str, Any] = {}
        if not df.empty:
            try:
                processed_data = await self._process_temporal_data_optimized(df, resolved_name, skip_sampling=skip_sampling)
            except Exception as exc:
                parsing_error = parsing_error or str(exc)
                logger.error(f"Error processing temporal data in load_from_path: {exc}")

        return {
            "file_id": file_id,
            "filename": resolved_name,
            "file_path": str(file_path),
            "size": size,
            "rows": len(df),
            "columns": [str(c) for c in df.columns] if not df.empty else [],
            "data_summary": self._summarize_data_optimized(df),
            "processed_data": processed_data,
            "raw_data": df.to_dict('records') if not df.empty else [],
            "parsing_error": parsing_error,
        }

    async def _load_csv_streaming(self, file_path: Path, max_rows: Optional[int] = 200000) -> pd.DataFrame:
        """Load CSV with streaming and chunking for memory efficiency.
        
        Args:
            max_rows: Maximum rows to load. Set to 0 or negative for unlimited.
                      Default 200k for fast preview/analysis.
        """
        chunks = []
        dtype_spec = self._infer_dtypes_from_sample(file_path)
        
        unlimited = (max_rows is None or max_rows <= 0)
        effective_max = max_rows if (max_rows and max_rows > 0) else float('inf')

        # If the first non-empty line looks numeric (edge-list without header), read with header=None
        use_header = 'infer'
        try:
            if self._first_line_looks_like_data(file_path, delimiter=','):
                use_header = None
        except Exception:
            pass

        # If we're forcing header=None because the file looked like numeric-only first row,
        # use the python engine which is more flexible about separators/quoting.
        engine_choice = 'python' if use_header is None else 'c'
        total_rows = 0
        
        for chunk in pd.read_csv(
            file_path,
            sep=',',
            chunksize=self.chunk_size,
            low_memory=False,
            dtype=dtype_spec,
            engine=engine_choice,
            header=use_header
        ):
            chunks.append(chunk)
            total_rows += len(chunk)
            
            # Log progress for large files
            if total_rows % 500000 == 0:
                logger.info(f"Loaded {total_rows:,} rows from CSV...")
            
            # Stop early if we have enough rows (skip if unlimited)
            if not unlimited and total_rows >= effective_max:
                logger.info(f"Early stop: loaded {total_rows:,} rows (limit: {effective_max:,})")
                break
                
            if len(chunks) > 10:
                chunks = [pd.concat(chunks, ignore_index=True)]
                
        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        logger.info(f"Loaded {len(df):,} rows from CSV file")
        return df

    def _infer_dtypes_from_sample(self, file_path: Path) -> Optional[Dict]:
        """Infer dtypes from sample to optimize memory"""
        try:
            sample = pd.read_csv(file_path, nrows=1000)
            dtypes = {}
            for col in sample.columns:
                if sample[col].dtype == 'object':
                    if sample[col].nunique() / len(sample) < 0.5:
                        dtypes[col] = 'category'
            return dtypes if dtypes else None
        except:
            return None

    def _first_line_looks_like_data(self, file_path: Path, delimiter: Optional[str] = None) -> bool:
        """Check whether the first non-empty, non-comment line looks like data (no header).

        Returns True when tokens are mostly numeric or look like edge-list rows, suggesting
        the file has no header and should be read with header=None.
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith('#') or line.startswith('%'):
                        continue
                    # Determine delimiter if not provided
                    if delimiter is None:
                        # try common delimiters
                        for d in [',', '\t', ' ']:
                            parts = re.split(r'\s+' if d == ' ' else re.escape(d), line)
                            if len(parts) >= 2:
                                tokens = parts
                                break
                        else:
                            tokens = line.split()
                    else:
                        tokens = re.split(r'\s+' if delimiter == ' ' else re.escape(delimiter), line)

                    # Strip tokens
                    tokens = [t.strip() for t in tokens if t.strip()]
                    if not tokens:
                        continue
                    numeric_like = 0
                    for t in tokens:
                        # treat integers/floats and large epoch-like numbers as numeric
                        if re.fullmatch(r"[-+]?\d+", t) or re.fullmatch(r"[-+]?\d+\.\d+", t):
                            numeric_like += 1
                    # If most tokens are numeric, assume it's data row
                    return (numeric_like / len(tokens)) >= 0.6
        except Exception:
            return False
        return False

    async def _load_delimited_streaming(self, file_path: Path, delimiter: str) -> pd.DataFrame:
        """Load delimited files with streaming"""
        chunks = []
        use_header = 'infer'
        try:
            if self._first_line_looks_like_data(file_path, delimiter=delimiter):
                use_header = None
        except Exception:
            pass

        for chunk in pd.read_csv(
            file_path,
            sep=delimiter,
            chunksize=self.chunk_size,
            low_memory=False,
            engine='c',
            header=use_header
        ):
            chunks.append(chunk)
            if len(chunks) > 10:
                chunks = [pd.concat(chunks, ignore_index=True)]
        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()

    async def _load_text_streaming(self, file_path: Path, max_rows: Optional[int] = None) -> pd.DataFrame:
        """Load text files with flexible parsing"""
        # Prefer edge-list parsing for extensions commonly used for edge lists
        suffix = file_path.suffix.lower()
        if suffix in ['.edge', '.edgelist', '.edges']:
            # If the file actually contains commas (CSV-like), prefer CSV parsing.
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith('#') or line.startswith('%'):
                            continue
                        # If comma present, use CSV parsing
                        if ',' in line:
                            return await self._load_csv_streaming(file_path, max_rows)
                        else:
                            return await self._load_edge_list_streaming(file_path, max_rows)
            except Exception:
                return await self._load_edge_list_streaming(file_path, max_rows)
        try:
            return await self._load_csv_streaming(file_path, max_rows)
        except:
            return await self._load_edge_list_streaming(file_path, max_rows)

    async def _load_edge_list_streaming(self, file_path: Path, max_rows: Optional[int] = 200000) -> pd.DataFrame:
        """Load edge list format efficiently - with optional row limit for fast analysis.
        
        Args:
            max_rows: Maximum rows to load. Set to 0 or negative for unlimited.
                      Default 200k for fast preview/analysis.
        """
        chunks = []
        total_rows = 0
        
        unlimited = (max_rows is None or max_rows <= 0)
        effective_max = max_rows if (max_rows and max_rows > 0) else float('inf')
        
        for chunk in pd.read_csv(
            file_path,
            sep=r'\s+',
            header=None,
            comment='#',
            chunksize=self.chunk_size,
            engine='python'  # Python engine for regex
        ):
            chunks.append(chunk)
            total_rows += len(chunk)
            
            # Log progress for large files
            if total_rows % 500000 == 0:
                logger.info(f"Loaded {total_rows:,} edges...")
            
            # Stop early if we have enough rows (skip if unlimited)
            if not unlimited and total_rows >= effective_max:
                logger.info(f"Early stop: loaded {total_rows:,} edges (limit: {effective_max:,})")
                break
                
            if len(chunks) > 10:
                chunks = [pd.concat(chunks, ignore_index=True)]
                
        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        
        if df.shape[1] >= 2:
            col_names = ['source', 'target']
            if df.shape[1] >= 3:
                col_names.append('timestamp')
            if df.shape[1] >= 4:
                col_names.append('weight')
            df.columns = col_names[:df.shape[1]]
            
        logger.info(f"Loaded {len(df):,} edges from edge list file")
        return df

    async def _load_excel_streaming(self, file_path: Path) -> pd.DataFrame:
        """Load Excel file with memory optimization"""
        return pd.read_excel(file_path)

    async def _load_json_streaming(self, file_path: Path) -> pd.DataFrame:
        """Load JSON with streaming for large files"""
        try:
            chunks = []
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        chunks.append(json.loads(line))
                        if len(chunks) >= self.chunk_size:
                            break
            if chunks:
                return pd.DataFrame(chunks)
        except:
            pass
        with open(file_path, 'r') as f:
            data = json.loads(f.read())
        return self._extract_records_to_df(data)

    async def _load_yaml_streaming(self, file_path: Path) -> pd.DataFrame:
        """Load YAML file"""
        if yaml is None:
            raise ImportError("PyYAML is not installed. Please install pyyaml to load YAML files.")
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return self._extract_records_to_df(data)

    async def _load_xml_streaming(self, file_path: Path) -> pd.DataFrame:
        """Load XML with iterative parsing for large files"""
        records = []
        context = ElementTree.iterparse(file_path, events=('end',))
        for event, elem in context:
            if elem.tag == 'edge' or elem.tag == 'node' or elem.tag == 'record':
                record = dict(elem.attrib)
                for child in elem:
                    if child.text:
                        record[child.tag] = child.text.strip()
                records.append(record)
                elem.clear()  # Free memory
            if len(records) >= self.chunk_size:
                break
        return pd.DataFrame(records) if records else pd.DataFrame()

    async def _load_zip_streaming(self, file_path: Path) -> pd.DataFrame:
        """Load ZIP with streaming"""
        with zipfile.ZipFile(file_path, 'r') as zf:
            for name in zf.namelist():
                if any(name.endswith(ext) for ext in ['.csv', '.tsv', '.txt', '.json']):
                    with zf.open(name) as f:
                        first_bytes = f.read(4096)
                        f.seek(0)
                        if name.endswith('.csv'):
                            return pd.read_csv(f)
                        elif name.endswith('.json'):
                            return pd.read_json(f)
                        else:
                            return pd.read_csv(f, sep='\t' if name.endswith('.tsv') else None)
        return pd.DataFrame()

    def _extract_records_to_df(self, data: Any) -> pd.DataFrame:
        """Extract records from various data structures"""
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                return pd.DataFrame(data)
            elif data and isinstance(data[0], list):
                return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ['edges', 'data', 'records', 'items', 'nodes', 'links']:
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
        return pd.DataFrame()


    def _is_matrix_market(self, file_path: Path) -> bool:
        """Detect MatrixMarket format by header."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(5):
                line = f.readline()
                if line.startswith("%%MatrixMarket"):
                    return True
        return False

    def _load_matrix_market(self, file_path: Path) -> pd.DataFrame:
        """Load MatrixMarket (.mtx) file as edge list DataFrame."""
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("%"):
                    continue
                parts = line.strip().split()
                if len(parts) == 3:
                    # 1-based indices
                    src, tgt, val = parts
                    rows.append((int(src)-1, int(tgt)-1, float(val)))
                elif len(parts) == 2:
                    src, tgt = parts
                    rows.append((int(src)-1, int(tgt)-1, 1.0))
        df = pd.DataFrame(rows, columns=["source", "target", "weight"])
        # Synthesize timestamp
        df["timestamp"] = pd.Timestamp.utcnow() + pd.to_timedelta(range(len(df)), unit="s")
        return df

    async def _process_temporal_data_optimized(self, df: pd.DataFrame, filename: str, skip_sampling: bool = False) -> Dict:
        """Optimized temporal data processing for large datasets with flexible column detection.
        
        Processes ALL edges for accurate community detection. No sampling is applied
        during analysis - communities represent the full dataset.
        """
        original_row_count = len(df)
        logger.info(f"Processing {original_row_count:,} edges for full analysis...")
        
        # Initialize flag
        timestamp_inferred = False

        # If the file was read into a single object column (e.g., lines like "1,2,5.0,1234567890"),
        # split on commas to recover original columns.
        if df.shape[1] == 1 and df.iloc[:, 0].dtype == object:
            sample = df.iloc[:5, 0].astype(str).tolist()
            if all(',' in s for s in sample):
                try:
                    new = df.iloc[:, 0].str.split(',', expand=True)
                    df = new
                    logger.info('Split single-column CSV lines into multiple columns')
                except Exception:
                    pass

        # --- NEW: Check timestamp distribution and auto-generate if needed ---
        if 'timestamp' in df.columns:
            try:
                ts_unique = df['timestamp'].nunique()
                ts_total = len(df)
                if ts_unique < max(10, ts_total // 100):
                    # Not enough unique timestamps, generate synthetic evenly spaced timestamps
                    logger.warning(f"Timestamp column not well distributed (unique={ts_unique}, total={ts_total}). Generating synthetic timestamps.")
                    base_time = pd.Timestamp.now(tz="UTC")
                    df['timestamp'] = base_time + pd.to_timedelta(np.linspace(0, ts_total, ts_total), unit='s')
                    timestamp_inferred = True
            except Exception:
                # If timestamp operations fail, we'll regenerate timestamps later
                timestamp_inferred = True
        if df.empty:
            return {}
        
        # Try to detect columns first (pass df for data-based detection on headerless files)
        column_mapping = self._detect_columns_optimized(df.columns.tolist(), df)
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.info(f"Auto-detected column mapping: {column_mapping}")
        
        # Check which columns we have and fill missing with synthetic/default values
        available_cols = set(df.columns)
        required = {'source', 'target', 'timestamp'}
        missing = [col for col in required if col not in available_cols]
        if missing:
            logger.warning(f"Missing columns: {missing}. Proceeding with synthetic/default values.")
        # Always ensure columns exist
        if 'source' not in df.columns:
            if df.shape[1] > 0:
                df['source'] = df.iloc[:, 0].astype(str)
            else:
                df['source'] = [f"node_{i}" for i in range(len(df))]
            logger.warning("Source column not found, using first column or generated IDs")
        if 'target' not in df.columns:
            if df.shape[1] > 1:
                df['target'] = df.iloc[:, 1].astype(str)
            else:
                df['target'] = df['source'].shift(-1).fillna(df['source'].iloc[0])
            logger.warning("Target column not found, using second column or shifted sources")
        if 'timestamp' not in df.columns:
            base_time = pd.Timestamp.now(tz="UTC")
            df['timestamp'] = base_time + pd.to_timedelta(range(len(df)), unit='s')
            logger.warning("Timestamp column not found, generated sequential timestamps")
        
        # Optimize memory usage
        df = self._optimize_dataframe_memory(df)
        
        # Efficient timestamp processing
        if pd.api.types.is_numeric_dtype(df['timestamp']):
            # Already numeric, convert to datetime efficiently
            ts_numeric = pd.to_numeric(df['timestamp'], errors='coerce')
            
            # Detect unit based on range
            if ts_numeric.max() > 1e12:
                df['timestamp'] = pd.to_datetime(ts_numeric, unit='ms', errors='coerce', utc=True)
            else:
                df['timestamp'] = pd.to_datetime(ts_numeric, unit='s', errors='coerce', utc=True)
        else:
            # Try efficient string parsing
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
            except:
                # Fall back to slower parsing
                timestamp_inferred = True
                base_time = pd.Timestamp.now(tz="UTC")
                df['timestamp'] = base_time + pd.to_timedelta(range(len(df)), unit='s')
        
        # Handle missing timestamps
        if df['timestamp'].isnull().any():
            timestamp_inferred = True
            missing_mask = df['timestamp'].isnull()
            base_time = df['timestamp'].min() if df['timestamp'].notna().any() else pd.Timestamp.now(tz="UTC")
            df.loc[missing_mask, 'timestamp'] = base_time + pd.to_timedelta(
                np.arange(missing_mask.sum()), unit='s'
            )
        
        # Add timestamp_ms for efficient sorting
        df['timestamp_ms'] = (df['timestamp'].astype('int64') // 1_000_000).astype('int64')
        
        # Sort efficiently
        df = df.sort_values('timestamp_ms').reset_index(drop=True)
        
        # Add edge IDs efficiently
        df['edge_id'] = df['source'].astype(str) + "_" + df['target'].astype(str) + "_" + (df['timestamp_ms'] // 1000).astype(str)
        
        # Get unique nodes efficiently
        all_nodes = pd.unique(pd.concat([df['source'], df['target']], ignore_index=True))
        
        # Calculate node metrics efficiently
        sources = df['source'].astype(str)
        targets = df['target'].astype(str)
        
        # Degree counts using value_counts (very efficient)
        source_counts = sources.value_counts()
        target_counts = targets.value_counts()
        degree_counts = source_counts.add(target_counts, fill_value=0)
        
        # First and last seen using groupby (optimized)
        node_times = pd.concat([
            pd.DataFrame({'node': sources, 'timestamp': df['timestamp']}),
            pd.DataFrame({'node': targets, 'timestamp': df['timestamp']})
        ], ignore_index=True)
        
        first_seen = node_times.groupby('node')['timestamp'].min()
        last_seen = node_times.groupby('node')['timestamp'].max()
        
        # Calculate weights if present
        if 'weight' in df.columns:
            weights = pd.to_numeric(df['weight'], errors='coerce').fillna(1)
        else:
            weights = pd.Series(1, index=df.index)
        
        # Weighted degree
        source_weights = weights.groupby(sources, sort=False).sum()
        target_weights = weights.groupby(targets, sort=False).sum()
        total_weight = source_weights.add(target_weights, fill_value=0)
        
        # Create nodes list efficiently
        def _iso(ts):
            if pd.isna(ts):
                return None
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.tz_convert('UTC').tz_localize(None)
            return ts.isoformat()
        
        # Use list comprehension for speed
        nodes = [
            {
                "id": str(node),
                "degree": int(degree_counts.get(node, 0)),
                "first_seen": _iso(first_seen.get(node)),
                "last_seen": _iso(last_seen.get(node)),
                "total_weight": float(total_weight.get(node, 0))
            }
            for node in all_nodes
        ]
        
        # Time range
        start_ms = int(df['timestamp_ms'].min())
        end_ms = int(df['timestamp_ms'].max())
        duration_days = max(0, (end_ms - start_ms) // 86_400_000)
        
        start_ts = pd.to_datetime(start_ms, unit='ms', utc=True).tz_localize(None)
        end_ts = pd.to_datetime(end_ms, unit='ms', utc=True).tz_localize(None)
        
        time_range = {
            "start": start_ts.isoformat(),
            "end": end_ts.isoformat(),
            "duration_days": int(duration_days)
        }
        
        # Prepare edges output (sample if too large, unless skip_sampling is True)
        edges_df = df.drop(columns=['timestamp_ms'])
        
        # Convert timestamps to ISO format for JSON
        edges_df['timestamp'] = edges_df['timestamp'].apply(lambda x: _iso(x))
        
        # Sample edges if too many for response (unless analysis mode)
        max_edges_response = 100000
        if len(edges_df) > max_edges_response and not skip_sampling:
            edges_sample = edges_df.sample(n=max_edges_response, random_state=42)
            sampling_rate = max_edges_response / len(edges_df)
            logger.info(f"Sampled edges for response: {max_edges_response}/{len(edges_df)} (rate={sampling_rate:.2%})")
        else:
            edges_sample = edges_df
            sampling_rate = 1
            if skip_sampling and len(edges_df) > max_edges_response:
                logger.info(f"Returning all {len(edges_df)} edges (skip_sampling=True)")
        
        return {
            "nodes": nodes,
            "edges": edges_sample.to_dict('records'),
            "time_range": time_range,
            "total_edges": len(df),
            "unique_nodes": int(len(all_nodes)),
            "sampling_rate": sampling_rate,
            "timestamp_inferred": timestamp_inferred,
            "columns_used": {
                "source": "source" in df.columns,
                "target": "target" in df.columns,
                "timestamp": "timestamp" in df.columns,
                "weight": "weight" in df.columns
            }
        }

    def _optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage by downcasting types"""
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type != 'object':
                c_min = df[col].min()
                c_max = df[col].max()
                
                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                else:
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
            else:
                # Convert object columns to category if beneficial
                if df[col].nunique() / len(df) < 0.5:
                    df[col] = df[col].astype('category')
        
        return df

    def _detect_columns_optimized(self, columns: List[str], df: Optional[pd.DataFrame] = None) -> Dict[str, str]:
        """Maximally aggressive column detection: fallback to first three columns if needed.
        
        For headerless files (numeric column names), uses data-value heuristics.
        """
        mapping = {}
        
        # Check if columns are numeric (headerless file)
        is_headerless = all(str(c).isdigit() for c in columns)
        
        # If we have data and it's headerless, detect based on data values
        if is_headerless and df is not None and len(columns) >= 2:
            logger.info(f"Headerless file detected with {len(columns)} columns. Analyzing data values...")
            timestamp_col = None
            weight_col = None
            
            # Look for Unix timestamp column (large integers around 10^9 - 10^10)
            for col in columns:
                try:
                    col_data = pd.to_numeric(df[col], errors='coerce')
                    if col_data.notna().any():
                        col_min = float(col_data.min())
                        col_max = float(col_data.max())
                        # Unix timestamps (seconds) are around 10^9 to 2*10^9
                        # Unix timestamps (milliseconds) are around 10^12 to 2*10^12
                        if (col_min > 1e8 and col_max < 2e10) or (col_min > 1e11 and col_max < 2e13):
                            timestamp_col = col
                            logger.info(f"Detected column '{col}' as timestamp (min={col_min:.0f}, max={col_max:.0f})")
                            break
                except Exception as e:
                    logger.debug(f"Error checking column {col} for timestamp: {e}")
                    continue
            
            # Look for weight column (small floats, typically ratings 1-5 or similar)
            for col in columns:
                if col == timestamp_col:
                    continue
                try:
                    col_data = pd.to_numeric(df[col], errors='coerce')
                    if col_data.notna().any():
                        col_min = float(col_data.min())
                        col_max = float(col_data.max())
                        # Small range floats (like ratings 1-5, or weights 0-1)
                        if col_min >= 0 and col_max <= 10 and str(col_data.dtype) in ['float64', 'float32']:
                            weight_col = col
                            logger.info(f"Detected column '{col}' as weight (min={col_min}, max={col_max})")
                            break
                except Exception as e:
                    logger.debug(f"Error checking column {col} for weight: {e}")
                    continue
            
            # Assign detected columns
            remaining_cols = [c for c in columns if c not in [timestamp_col, weight_col]]
            
            if len(remaining_cols) >= 2:
                mapping[remaining_cols[0]] = 'source'
                mapping[remaining_cols[1]] = 'target'
            elif len(remaining_cols) == 1:
                mapping[remaining_cols[0]] = 'source'
            
            if timestamp_col:
                mapping[timestamp_col] = 'timestamp'
            if weight_col:
                mapping[weight_col] = 'weight'
            
            if mapping:
                logger.info(f"Data-based column mapping: {mapping}")
                return mapping
        
        # Standard pattern matching for named columns
        source_patterns = {'source', 'from', 'src', 'sender', 'origin', 'user_a', 'node1', 'source_id', 'from_id'}
        target_patterns = {'target', 'to', 'dst', 'receiver', 'destination', 'user_b', 'node2', 'target_id', 'to_id'}
        time_patterns = {'timestamp', 'time', 'date', 'datetime', 'ts', 'created', 'event', 'logged'}
        weight_patterns = {'weight', 'value', 'count', 'amount', 'strength', 'score', 'rating'}
        best_source = None
        best_target = None
        best_time = None
        best_weight = None
        for col in columns:
            col_lower = str(col).lower().strip()
            if not best_source:
                for pattern in source_patterns:
                    if pattern in col_lower or col_lower == pattern:
                        best_source = col
                        break
            if not best_target:
                for pattern in target_patterns:
                    if pattern in col_lower or col_lower == pattern:
                        best_target = col
                        break
            if not best_time:
                for pattern in time_patterns:
                    if pattern in col_lower or col_lower == pattern:
                        best_time = col
                        break
            if not best_weight:
                for pattern in weight_patterns:
                    if pattern in col_lower or col_lower == pattern:
                        best_weight = col
                        break
        # Assign best matches
        if best_source:
            mapping[best_source] = 'source'
        if best_target:
            mapping[best_target] = 'target'
        if best_time:
            mapping[best_time] = 'timestamp'
        if best_weight:
            mapping[best_weight] = 'weight'
        # Fallback: assign first three columns if any required are missing
        required_roles = ['source', 'target', 'timestamp']
        mapped_roles = set(mapping.values())
        missing_roles = [role for role in required_roles if role not in mapped_roles]
        col_idx = 0
        for role in missing_roles:
            # Find next unmapped column
            while col_idx < len(columns) and columns[col_idx] in mapping:
                col_idx += 1
            if col_idx < len(columns):
                mapping[columns[col_idx]] = role
                logger.warning(f"Aggressive fallback: assigning column '{columns[col_idx]}' as '{role}' (auto-mapping)")
                col_idx += 1
        return mapping

    def _summarize_data_optimized(self, df: pd.DataFrame) -> Dict:
        """Optimized data summary without expensive operations"""
        if df.empty:
            return {}
        
        summary = {
            "shape": df.shape,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": {col: int(df[col].isnull().sum()) for col in df.columns[:10]},
        }
        
        # Only compute numeric summary for small datasets or sample
        if len(df) < 100000:
            numeric_cols = df.select_dtypes(include=[np.number]).columns[:5]
            if len(numeric_cols) > 0:
                summary["numeric_summary"] = df[numeric_cols].describe().to_dict()
        
        return summary