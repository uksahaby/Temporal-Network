import asyncio
import time
import json
from pathlib import Path

from app.api.endpoints import AnalyzeRequest, analyze_network, get_analysis_results, analysis_cache

FILE_ID = '855c82689571bc2e'

async def main():
    payload = AnalyzeRequest(
        file_id=FILE_ID,
        time_resolution='1d',
        compute_communities=False,
    )
    resp = await analyze_network(payload)
    task_id = resp.task_id
    print('Started analysis, task_id=', task_id)

    # Poll analysis_cache for progress
    for _ in range(60):
        entry = analysis_cache.get(task_id)
        if entry:
            print('status:', entry.get('status'), 'progress:', entry.get('progress'))
            if entry.get('status') == 'completed':
                print('Completed. Summary:', entry.get('summary'))
                # Save to disk location
                data_file = Path('data/analysis_cache') / f"{task_id}.json"
                if data_file.exists():
                    with open(data_file,'r',encoding='utf-8') as f:
                        d = json.load(f)
                    print('Saved analysis file size:', data_file.stat().st_size)
                    # Print number of windows if available
                    summary = d.get('summary')
                    print('Persisted summary:', summary)
                break
        else:
            print('No cache entry yet')
        await asyncio.sleep(2)

    # Try to fetch using get_analysis_results
    try:
        res = await get_analysis_results(task_id)
        print('get_analysis_results:', res)
    except Exception as e:
        print('get_analysis_results error:', e)

if __name__ == '__main__':
    asyncio.run(main())
