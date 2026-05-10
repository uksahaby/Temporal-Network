import sys
from pathlib import Path

p = Path('data/analysis_cache/855c82689571bc2e_1776474805.json')
if not p.exists():
    print('file not found')
    sys.exit(1)

with open(p, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Find the summary key
idx = text.find('"summary"')
if idx == -1:
    print('summary not found')
    sys.exit(0)
# Find the ':' after summary
colon = text.find(':', idx)
start = text.find('{', colon)
if start == -1:
    print('summary object start not found')
    sys.exit(0)

# Extract balanced braces
i = start
depth = 0
end = None
while i < len(text):
    if text[i] == '{':
        depth += 1
    elif text[i] == '}':
        depth -= 1
        if depth == 0:
            end = i
            break
    i += 1

if end is None:
    print('could not find end of summary object')
    sys.exit(0)

summary_text = text[start:end+1]
print('summary snippet:')
print(summary_text)

# Also attempt to find 'time_windows' count
tw_idx = text.find('"time_windows"')
if tw_idx != -1:
    # find '[' after it
    br = text.find('[', tw_idx)
    if br != -1:
        # count occurrences of 'window_key' as proxy for windows
        sub = text[br:br+200000]
        count = sub.count('"window_key"')
        print('\napprox time_windows count (by window_key in first chunk):', count)
