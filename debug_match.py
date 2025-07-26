import os
import pandas as pd
from datetime import datetime, timedelta
from parse_logs_fast import parse_log_datetime

LOG_FILE = 'Logs/WoWCombatLog-010125_201010.txt'

# 1. Extract date & time from the filename
fname      = os.path.basename(LOG_FILE)
parts      = fname.split('-', 1)[1]          # "010125_201010.txt"
date_tok, time_tok_ext = parts.split('_')    # ["010125","201010.txt"]
time_tok   = time_tok_ext.split('.')[0]      # "201010"
date_part  = date_tok                        

# 2. Build the log’s start datetime
if ':' in time_tok:
    # already in HH:MM:SS.mmm
    log_start = parse_log_datetime(LOG_FILE, time_tok)
else:
    # convert "HHMMSS" → HH:MM:SS.000
    hh = int(time_tok[0:2])
    mm = int(time_tok[2:4])
    ss = int(time_tok[4:6])
    # date_part is "MMDDYY"
    month = int(date_part[0:2])
    day   = int(date_part[2:4])
    year  = 2000 + int(date_part[4:6])
    log_start = datetime(year, month, day, hh, mm, ss)

print("Log starts at:", log_start)

# 3. Load the master index and compute end times
df = pd.read_csv('master_index.csv', parse_dates=['date_time'])
df['end_time'] = df['date_time'] + pd.to_timedelta(df['duration_s'], unit='s')

# 4. Find which session covers log_start
matches = df[(df['date_time'] <= log_start) & (log_start <= df['end_time'])]
print("\nSessions covering that timestamp:")
print(matches[['filename','date_time','end_time']])