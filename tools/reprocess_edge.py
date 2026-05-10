import asyncio
import json
from pathlib import Path
from app.services.data_loader import DataLoader

UPLOADS = Path('data/uploads')
SOURCE_META = UPLOADS / '15f0d51c93872b9a_metadata.json'

async def main():
    if not SOURCE_META.exists():
        print('metadata not found:', SOURCE_META)
        return
    with open(SOURCE_META,'r',encoding='utf-8') as f:
        meta = json.load(f)
    file_path = Path(meta.get('file_path'))
    if not file_path.exists():
        print('data file not found:', file_path)
        return
    dl = DataLoader(upload_dir=str(UPLOADS))
    print('Reprocessing', file_path)
    # Force filename to .edge so loader uses edge-list parser
    res = await dl.load_from_path(file_path, filename=file_path.stem + '.edge')
    file_id = meta.get('file_id') or res.get('file_id')
    new_meta = {
        'file_id': file_id,
        'filename': file_path.name,
        'file_path': str(file_path),
        'size': res.get('size', file_path.stat().st_size),
        'rows': res.get('rows', 0),
        'columns': res.get('columns', []),
        'data_summary': res.get('data_summary', {}),
        'processed_data': res.get('processed_data', {}),
        'raw_data_sample': res.get('raw_data', [])[:100] if res.get('raw_data') else [],
        'parsing_error': res.get('parsing_error')
    }
    meta_path = UPLOADS / f"{file_id}_metadata.json"
    with open(meta_path,'w',encoding='utf-8') as f:
        json.dump(new_meta, f, default=str)
    print('Wrote updated metadata to', meta_path)
    print('processed keys:', list(new_meta.get('processed_data', {}).keys()))
    print('time_range:', new_meta.get('processed_data', {}).get('time_range'))
    print('columns_used:', new_meta.get('processed_data', {}).get('columns_used'))

if __name__ == '__main__':
    asyncio.run(main())
