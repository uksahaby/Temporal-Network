import requests
import time
import sys

s = requests.Session()

# Login
r = s.post('http://localhost:8000/api/auth/login', json={'email':'demo@test.com','password':'demo1234'})
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    sys.exit(1)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Check existing task first
task_id = '15f0d51c93872b9a_1776632552'
r = s.get(f'http://localhost:8000/api/analysis/{task_id}', headers=h)
d = r.json()
print(f"Existing task {task_id}: status={d.get('status')}, progress={d.get('progress')}, error={d.get('error')}")

if d.get('status') in ('completed', 'processing'):
    # Monitor it
    for i in range(60):
        time.sleep(10)
        r = s.get(f'http://localhost:8000/api/analysis/{task_id}', headers=h)
        d = r.json()
        status = d.get('status')
        progress = d.get('progress')
        error = d.get('error')
        print(f"[{i*10}s] status={status}, progress={progress}")
        if status in ('completed', 'failed'):
            if error:
                print(f"ERROR: {error}")
            if status == 'completed':
                summary = d.get('summary', {})
                print(f"COMPLETED! Summary: {summary}")
            break
elif d.get('status') == 'failed':
    # Submit a new one
    print("Previous task failed, submitting new analysis...")
    r = s.post('http://localhost:8000/api/analyze', json={
        'file_id': '15f0d51c93872b9a',
        'time_resolution': 'day',
        'column_mapping': {'source':'source','target':'target','weight':'weight','timestamp':'timestamp'}
    }, headers=h)
    print(f"Submit: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        task_id = d.get('task_id')
        print(f"New task: {task_id}")
        for i in range(60):
            time.sleep(10)
            r = s.get(f'http://localhost:8000/api/analysis/{task_id}', headers=h)
            d = r.json()
            status = d.get('status')
            progress = d.get('progress')
            error = d.get('error')
            print(f"[{i*10}s] status={status}, progress={progress}")
            if status in ('completed', 'failed'):
                if error:
                    print(f"ERROR: {error}")
                if status == 'completed':
                    summary = d.get('summary', {})
                    print(f"COMPLETED! Summary: {summary}")
                break
