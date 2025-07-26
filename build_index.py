#!/usr/bin/env python3
# build_index.py
#
# Reads all WoW Arena session JSONs, builds master_index.csv and arena.db,
# and gracefully handles missing fields.

import os
import glob
import json
import sqlite3
import csv
import logging
from datetime import datetime

# ——— Configuration ———
logging.basicConfig(
    filename='build_index_errors.log',
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(message)s'
)

DATA_DIR     = os.path.abspath(os.path.dirname(__file__))
JSON_PATTERN = os.path.join(DATA_DIR, '**', '*.json')
CSV_PATH     = os.path.join(DATA_DIR, 'master_index.csv')
DB_PATH      = os.path.join(DATA_DIR, 'arena.db')

# ——— 1. Collect rows ———
rows = []

for jf in glob.glob(JSON_PATTERN, recursive=True):
    try:
        with open(jf, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
    except Exception as e:
        logging.warning(f"Failed to parse JSON {jf}: {e}")
        continue

    # Parse timestamp from filename: YYYY-MM-DD_HH-MM-SS
    base = os.path.basename(jf).replace('.json', '.mp4')
    try:
        date_part, time_part, _ = base.split('_', 2)
        iso_ts = f"{date_part}T{time_part.replace('-', ':')}"
        dt = datetime.fromisoformat(iso_ts)
    except Exception:
        logging.warning(f"Invalid filename timestamp in {base}")
        continue

    # Safe field extraction with defaults
    player = data.get('player', {})
    player_name = player.get('_name')
    if not player_name:
        logging.warning(f"Missing player._name in {jf}, skipping file")
        continue

    bracket = data.get('category', 'Unknown')
    zone    = data.get('zoneName',
               f"UnknownZoneID_{data.get('zoneID','')}")
    result  = data.get('result', False)
    duration = data.get('duration', 0)
    deaths   = data.get('deaths', [])
    overrun  = data.get('overrun', 0)
    unique_hash = data.get('uniqueHash', '')

    # Compute death counts
    friendly_deaths = sum(d.get('friendly', False) for d in deaths)
    enemy_deaths    = sum(not d.get('friendly', False) for d in deaths)

    # Gather opponent specs
    team_id = player.get('_teamID')
    combatants = data.get('combatants', [])
    opponents = [
        str(c.get('_specID', ''))
        for c in combatants
        if c.get('_teamID') != team_id
    ]

    rows.append({
        'filename'        : base,
        'date_time'       : dt.isoformat(),
        'player_name'     : player_name,
        'bracket'         : bracket,
        'map'             : zone,
        'outcome'         : 'Win' if result else 'Loss',
        'duration_s'      : duration,
        'death_events'    : len(deaths),
        'friendly_deaths' : friendly_deaths,
        'enemy_deaths'    : enemy_deaths,
        'overrun'         : overrun,
        'uniqueHash'      : unique_hash,
        'spec_player'     : player.get('_specID', -1),
        'spec_opponents'  : ','.join(opponents)
    })

if not rows:
    print("⚠️  No valid rows were collected. Exiting.")
    exit(1)

# ——— 2. Write CSV ———
with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"✅ CSV saved to {CSV_PATH}")

# ——— 3. Build SQLite ———
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("DROP TABLE IF EXISTS sessions;")

# Dynamically define column types
fields = []
for col in rows[0].keys():
    if col in ('filename','player_name','bracket','map','outcome','uniqueHash','spec_opponents'):
        col_type = 'TEXT'
    elif col in ('date_time',):
        col_type = 'TEXT'
    else:
        col_type = 'INTEGER'
    fields.append(f"{col} {col_type}")

cols_def = ', '.join(fields)
cur.execute(f"CREATE TABLE sessions ({cols_def});")

# Import from CSV
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    dr = csv.DictReader(f)
    to_db = [tuple(d.values()) for d in dr]

placeholders = ', '.join('?' for _ in rows[0].keys())
cur.executemany(f"INSERT INTO sessions VALUES ({placeholders});", to_db)

conn.commit()
conn.close()
print(f"✅ SQLite DB created at {DB_PATH}")