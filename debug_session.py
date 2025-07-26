import pandas as pd
from datetime import datetime, timedelta
from parse_logs_fast import parse_log_datetime

# 1. Load the index
df = pd.read_csv('master_index.csv', parse_dates=['date_time'])

# 2. Pick the session that matches this log file name/time
LOG_FILE   = 'Logs/WoWCombatLog-010125_201010.txt'
SESS_PREFIX = '2025-01-01_20-10-10'   # must match the filename timestamp in your CSV

sess = df[df['filename'].str.contains(SESS_PREFIX)]
if sess.empty:
    print("No matching session found for", SESS_PREFIX)
    exit(1)

sess = sess.iloc[0]
start = sess['date_time']
end   = start + timedelta(seconds=sess['duration_s'])
print(f"Session window: {start} → {end} ({sess['duration_s']}s)")

# 3. Read first few lines of the log
print("\nFirst 5 lines of the log + parsed timestamp:")
with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    count = 0
    for line in f:
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        date_tok, time_tok, rest = parts
        ts = parse_log_datetime(LOG_FILE, time_tok)
        print(f"  {line.strip()}")
        print(f"    → parsed ts = {ts}  {'(in window)' if start <= ts <= end else '(out of window)'}")
        count += 1
        if count >= 5:
            break