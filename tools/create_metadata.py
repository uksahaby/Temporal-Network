import asyncio
import shutil
import json
from pathlib import Path
import hashlib

from app.services.data_loader import DataLoader

SOURCE = Path(r"C:\Users\helpdesk\Downloads\tempD\rec-amazon-ratings.edges")
UPLOADS = Path("data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)

async def main():
    dl = DataLoader(upload_dir=str(UPLOADS))
    print(f"Processing {SOURCE}")
    res = await dl.load_from_path(SOURCE, SOURCE.name)
    file_id = res.get('file_id')
    if not file_id:
        file_id = hashlib.md5(str(SOURCE).encode()).hexdigest()[:16]
    dest = UPLOADS / f"{file_id}_{SOURCE.name}"
    print(f"Copying file to {dest}")
    shutil.copy(SOURCE, dest)
    metadata = {
        "file_id": file_id,
        "filename": SOURCE.name,
        "file_path": str(dest),
        "size": res.get('size', dest.stat().st_size),
        "rows": res.get('rows', 0),
        "columns": res.get('columns', []),
        "data_summary": res.get('data_summary', {}),
        "processed_data": res.get('processed_data', {}),
        "raw_data_sample": res.get('raw_data', [])[:100] if res.get('raw_data') else [],
        "parsing_error": res.get('parsing_error')
    }
    meta_path = UPLOADS / f"{file_id}_metadata.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, default=str)
    print(f"Wrote metadata to {meta_path}")
    print(json.dumps({"file_id": file_id, "metadata_path": str(meta_path)}))

if __name__ == '__main__':
    asyncio.run(main())
