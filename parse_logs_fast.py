#!/usr/bin/env python3
# parse_logs_fast.py

import os
import glob
import csv
import json
import argparse
from datetime import datetime, timedelta
import pandas as pd
from intervaltree import IntervalTree
from typing import Optional, Tuple, Dict
import re

# ——— Helpers ———
def parse_fname_timestamp(log_fname):
    """
    From WoWCombatLog-MMDDYY_HHMMSS.txt → datetime(year,mo,day,HH,MM,SS)
    """
    base = os.path.basename(log_fname)
    # "WoWCombatLog-031125_175236.txt"
    part = base.split('-', 1)[1].split('.')[0]  # "031125_175236"
    date_s, time_s = part.split('_')
    mo, da, yr = int(date_s[:2]), int(date_s[2:4]), 2000 + int(date_s[4:6])
    hh, mm, ss = int(time_s[0:2]), int(time_s[2:4]), int(time_s[4:6])
    return datetime(yr, mo, da, hh, mm, ss)
    
def parse_log_datetime(log_fname, hhmmss_str):
    """
    Combines the date from the log filename (WoWCombatLog-MMDDYY_HHMMSS.txt)
    with the in-line time HH:MM:SS.mmm
    """
    # Add debug logging
    print(f"Parsing timestamp from file: {log_fname}")
    print(f"Time string: {hhmmss_str}")
    
    base      = os.path.basename(log_fname)
    # Extract "MMDDYY" from "WoWCombatLog-032825_133938.txt"
    date_part = base.split('-', 1)[1].split('_', 1)[0]
    month     = int(date_part[0:2])
    day       = int(date_part[2:4])
    year      = 2000 + int(date_part[4:6])
    dt_time   = datetime.strptime(hhmmss_str, "%H:%M:%S.%f").time()

    result = datetime(year, month, day,
                     dt_time.hour, dt_time.minute,
                     dt_time.second, dt_time.microsecond)
    print(f"Parsed datetime: {result}")
    return result

def build_session_tree(index_df):
    """
    Builds an IntervalTree mapping [start_ts, end_ts) → session index,
    forcing a minimum duration of 1 second (or a default fallback).
    """
    tree = IntervalTree()
    for idx, row in index_df.iterrows():
        start = row['date_time']
        dur   = row.get('duration_s', 0)
        # if your JSON uses a different key, adjust above accordingly
        if dur < 1:
            dur = 300     # fallback to 5 min window
        end = start + timedelta(seconds=dur)
        tree[start.timestamp(): end.timestamp()] = idx
    return tree

# ——— Get Player Name ———

def get_player_name_from_filename(fpath):
    # fpath: "2025-..._-_Phlurbotomy_-_3v3_....mp4"
    base = os.path.basename(fpath)
    # remove ".mp4"
    core = base.rsplit('.', 1)[0]
    # split on "_-_" and take the middle chunk
    parts = core.split('_-_')
    return parts[1] if len(parts) > 1 else ""  # "Phlurbotomy"
    
# ——— Main Parsing Logic ———

def find_json_file(base_dir, video_filename):
    """
    Find JSON file in YYYY-MM subdirectories matching the video filename
    """
    json_name = video_filename.rsplit('.', 1)[0] + '.json'
    print(f"Looking for JSON file: {json_name}")
    
    # Extract date from filename format: YYYY-MM-DD_HH-MM-SS_...
    try:
        date_part = video_filename.split('_', 1)[0]  # YYYY-MM-DD
        year_month = date_part.rsplit('-', 1)[0]     # YYYY-MM
        
        # Look in the YYYY-MM subdirectory
        json_path = os.path.join(base_dir, year_month, json_name)
        print(f"Trying path: {json_path}")
        if os.path.exists(json_path):
            print(f"Found JSON at: {json_path}")
            return json_path
    except IndexError as e:
        print(f"Error parsing filename {video_filename}: {str(e)}")
    
    # Fallback: try direct path
    json_path = os.path.join(base_dir, json_name)
    print(f"Trying fallback path: {json_path}")
    if os.path.exists(json_path):
        print(f"Found JSON at fallback path: {json_path}")
        return json_path
    
    return None

def load_json_timestamps(index_csv):
    """
    Load Unix timestamps from associated JSON files for each video session
    """
    print(f"\nLoading JSON timestamps from index: {index_csv}")
    df = pd.read_csv(index_csv)
    print(f"Loaded {len(df)} entries from CSV")
    timestamps = {}
    durations = {}
    
    # Get the directory where the index file is located
    base_dir = os.path.dirname(os.path.abspath(index_csv))
    print(f"Base directory: {base_dir}")
    
    total_files = len(df)
    for idx, row in df.iterrows():
        video_file = row['filename']
        print(f"\nProcessing {idx + 1}/{total_files}: {video_file}")
        
        json_path = find_json_file(base_dir, video_file)
        
        if json_path is None:
            print(f"Warning: Could not find JSON file for {video_file}")
            continue
            
        try:
            print(f"Reading JSON file: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # Debug print the entire JSON structure
                    print(f"JSON content keys: {list(data.keys())}")
                    
                    # More robust start field extraction
                    if 'start' not in data:
                        print(f"Warning: JSON structure for {json_path}:")
                        print(json.dumps(data, indent=2))
                        print("No 'start' field found in JSON structure")
                        continue
                    
                    unix_ms = data['start']  # Direct access instead of get()
                    if not isinstance(unix_ms, (int, float)):
                        print(f"Warning: 'start' field is not a number: {unix_ms}")
                        continue
                        
                    # Convert milliseconds to seconds and create datetime
                    unix_s = float(unix_ms) / 1000.0
                    timestamps[video_file] = datetime.fromtimestamp(unix_s)
                    
                    # Store duration from JSON if available
                    if 'duration' in data:
                        duration_val = data['duration']
                        if isinstance(duration_val, (int, float)):
                            durations[video_file] = float(duration_val)
                        else:
                            print(f"Warning: Invalid duration format: {duration_val}")
                    
                    print(f"Successfully processed {json_path}")
                    print(f"Start timestamp: {unix_ms}")
                    print(f"Converted datetime: {timestamps[video_file]}")
                    
                except json.JSONDecodeError as je:
                    print(f"JSON parsing error in {json_path}: {str(je)}")
                    # Try to read the raw content to see what's wrong
                    f.seek(0)
                    raw_content = f.read()
                    print(f"Raw JSON content (first 500 chars): {raw_content[:500]}")
                    continue
                    
        except FileNotFoundError:
            print(f"Warning: File not found: {json_path}")
            continue
        except Exception as e:
            print(f"Unexpected error processing {json_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\nFound {len(timestamps)} JSON files with timestamps")
    return timestamps, durations

def parse_logs_fast(log_dir, index_csv, out_csv, processed_file):
    # 1. Load master index and JSON timestamps
    df_index = pd.read_csv(index_csv, parse_dates=['date_time'])
    json_timestamps, json_durations = load_json_timestamps(index_csv)
    
    # Update the date_time column with precise timestamps from JSON files
    for video_file, timestamp in json_timestamps.items():
        mask = df_index['filename'] == video_file
        if any(mask):
            df_index.loc[mask, 'date_time'] = timestamp
            # Update duration if available from JSON
            if video_file in json_durations:
                df_index.loc[mask, 'duration_s'] = json_durations[video_file]
    
    df_index['player_name'] = df_index['filename']\
        .apply(lambda fn: get_player_name_from_filename(fn))
    print("Loaded sessions:", len(df_index))
    print("Sessions with JSON timestamps:", len(json_timestamps))

    # Build the interval tree for fast timestamp→session lookups
    tree = build_session_tree(df_index)

    # 2. Load list of already-parsed logs
    processed = set()
    if os.path.exists(processed_file):
        processed = set(json.load(open(processed_file, 'r', encoding='utf-8')))

    # 3. Prepare output CSV writer (append mode)
    is_new = not os.path.exists(out_csv)
    cols = [
      'filename',
      'cast_success_own',
      'interrupt_success_own',
      'times_interrupted',
      'precog_gained_own',
      'precog_gained_enemy'
    ]
    writer = csv.DictWriter(
        open(out_csv, 'a', newline='', encoding='utf-8'),
        fieldnames=cols
    )
    if is_new:
        writer.writeheader()

    # 4. Scan each combat log once
    for log_file in glob.glob(os.path.join(log_dir, '*.txt')):
        if log_file in processed:
            continue
    
        print(f"⏳ Processing {os.path.basename(log_file)}…")
    
        # ——— 4a) Map this log to exactly one session by first‐event timestamp ———
        
        # 1) Read the very first valid timestamp in the log
        log_dt = None
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split(None, 2)
                if len(parts) < 3:
                    continue
                time_tok   = parts[1]
                time_clean = time_tok.split('-', 1)[0]
                try:
                    log_dt = parse_log_datetime(log_file, time_clean)
                except ValueError:
                    continue
                break
        
        if log_dt is None:
            print(f"   ⚠️ Couldn't parse any timestamp in {log_file}, skipping.")
            continue
        
        # 2) Precompute end times (once, outside the loop would be better)
        df_index['end_time'] = df_index['date_time'] + pd.to_timedelta(df_index['duration_s'], unit='s')
        
        # 3) Find session where log_dt ∈ [start, end]
        matches = df_index[
            (df_index['date_time'] <= log_dt) &
            (log_dt <= df_index['end_time'])
        ]
        
        # 4) Fallback to nearest‐start within ±5 min if no exact containment
        if matches.empty:
            df_index['diff'] = (df_index['date_time'] - log_dt).abs()
            close = df_index[df_index['diff'] <= pd.Timedelta(minutes=5)]
            if close.empty:
                print(f"   ⚠️ No session window for {os.path.basename(log_file)} at {log_dt}, skipping.")
                continue
            matches = close.nsmallest(1, 'diff')
        
        # 5) We expect exactly one session now
        session_idx = matches.index[0]
        me          = df_index.at[session_idx, 'player_name']
        start_ts    = matches.at[session_idx, 'date_time'].timestamp()
        end_ts      = matches.at[session_idx, 'end_time'].timestamp()
        
        # pull out the one-and-only session index
        session_idx = matches.index[0]
        me          = df_index.at[session_idx, 'player_name']
        
        # compute our window once
        start_ts = df_index.at[session_idx, 'date_time'].timestamp()
        end_ts   = (df_index.at[session_idx, 'date_time']
                    + timedelta(seconds=df_index.at[session_idx, 'duration_s'])
                   ).timestamp()
    
        # 4b) Discover pet name for this player in this log
        pet_name = None
        with open(log_file,'r',encoding='utf-8',errors='ignore') as pf:
            for l in pf:
                if 'SPELL_SUMMON' not in l:
                    continue
                pparts = l.strip().split(',', 7)
                if len(pparts) < 7:
                    continue
                src       = pparts[2].strip('"').split('-',1)[0]
                candidate = pparts[6].strip('"')
                if src == me:
                    pet_name = candidate
                    break
    
        # Initialize your per‐session counters
        session_casts        = {i:0 for i in df_index.index}
        session_interrupts   = {i:0 for i in df_index.index}
        session_interrupted  = {i:0 for i in df_index.index}
        session_precog_gain  = {i:0 for i in df_index.index}
        session_precog_enemy = {i:0 for i in df_index.index}
    
        # 4c) Now your normal event‐parsing loop
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split(None, 2)
                if len(parts) < 3:
                    continue
                _, time_tok, rest = parts
                time_clean = time_tok.split('-', 1)[0]
                try:
                    ts = parse_log_datetime(log_file, time_clean).timestamp()
                except ValueError:
                    continue
       
                # only keep events inside this match’s exact [start_ts, end_ts]
                if ts < start_ts or ts > end_ts:
                    continue
                
                # we’ve already mapped this log to one session
                idx = session_idx
                
                fields = rest.split(',')
                event  = fields[0]

                # 1) Your casts
                if event == 'SPELL_CAST_SUCCESS' and len(fields) >= 3:
                    src = fields[2].strip('"').split('-',1)[0]
                    if src == me:
                        session_casts[idx] += 1

                # 2) Interrupts
                elif event == 'SPELL_INTERRUPT' and len(fields) >= 7:
                    # unpack bare names
                    src = fields[2].strip('"').split('-',1)[0]
                    dst = fields[6].strip('"').split('-',1)[0]
                
                    # treat your pet as you for both src and dst
                    if src == pet_name:
                        src = me
                    if dst == pet_name:
                        dst = me
                
                    # now count
                    if src == me:
                        session_interrupts[idx] += 1
                    elif dst == me:
                        session_interrupted[idx] += 1

                # 3) Precognition
                elif event == 'SPELL_AURA_APPLIED' and len(fields) >= 11:
                    dst  = fields[6].strip('"').split('-',1)[0]
                    spell = fields[10].strip('"')
                    if spell == 'Precognition':
                        if dst == me:
                            session_precog_gain[idx] += 1
                        else:
                            session_precog_enemy[idx] += 1
    
        # 5) Write & sanity‐print
        for idx in df_index.index:
            # wrap your five counters in a list so any() sees a single iterable
            if any([
                session_casts[idx],
                session_interrupts[idx],
                session_interrupted[idx],
                session_precog_gain[idx],
                session_precog_enemy[idx]
            ]):
        
                writer.writerow({
                    'filename'              : df_index.at[idx,'filename'],
                    'cast_success_own'      : session_casts[idx],
                    'interrupt_success_own' : session_interrupts[idx],
                    'times_interrupted'     : session_interrupted[idx],
                    'precog_gained_own'     : session_precog_gain[idx],
                    'precog_gained_enemy'   : session_precog_enemy[idx],
                })
        
                print(
                    f"   ▶ {df_index.at[idx,'filename']}\n"
                    f"      casts:         {session_casts[idx]}\n"
                    f"      int_success:   {session_interrupts[idx]}\n"
                    f"      int_received:  {session_interrupted[idx]}\n"
                    f"      precog_own:    {session_precog_gain[idx]}\n"
                    f"      precog_enemy:  {session_precog_enemy[idx]}"
                )
    
        # 6) Mark done
        processed.add(log_file)
        with open(processed_file, 'w', encoding='utf-8') as pf:
            json.dump(list(processed), pf)
    
        print(f"✅ Done {os.path.basename(log_file)}")

    print("🎉 All logs parsed.")

# ——— CLI Entry Point ———

if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description="Fast parser for WoW combat logs → per-match features"
    )
    p.add_argument('--logs',      default='Logs',              help='Path to Logs folder')
    p.add_argument('--index',     default='master_index.csv',  help='Master index CSV')
    p.add_argument('--out',       default='match_log_features.csv', help='Output CSV')
    p.add_argument('--processed', default='parsed_logs.json',  help='Track processed logs')
    args = p.parse_args()

    parse_logs_fast(args.logs, args.index, args.out, args.processed)
from typing import Optional, Tuple, Dict
from datetime import datetime
import json
import os
from pathlib import Path

def validate_match_data(json_path: str, combat_log_path: Optional[str] = None) -> Dict[str, any]:
    """
    Validate match data by performing comprehensive checks on both JSON and combat log data.
    
    Args:
        json_path (str): Path to the JSON file
        combat_log_path (str, optional): Path to the combat log file
        
    Returns:
        Dict[str, any]: Validation results containing all checks and their status
    """
    validation_results = {
        'timestamp_method': None,
        'json_validation': {},
        'combat_log_validation': {},
        'cross_validation': {},
        'errors': [],
        'warnings': [],
        'is_valid': False
    }

    try:
        # 1. Load and validate JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Basic JSON structure validation
        required_fields = ['category', 'zoneID', 'zoneName', 'player', 'combatants']
        for field in required_fields:
            validation_results['json_validation'][f'has_{field}'] = field in json_data
        
        # Extract filename components
        json_filename = Path(json_path).name
        filename_parts = json_filename.split('_')
        if len(filename_parts) >= 4:
            filename_date = filename_parts[0]
            filename_player = filename_parts[2]
            
            # Validate filename matches JSON player data
            player_match = (filename_player == json_data['player']['_name'])
            validation_results['json_validation']['filename_player_match'] = player_match
            
            # Parse filename date
            try:
                file_date = datetime.strptime(filename_date, '%Y-%m-%d')
                validation_results['json_validation']['valid_filename_date'] = True
            except ValueError:
                validation_results['json_validation']['valid_filename_date'] = False
                validation_results['warnings'].append("Invalid date format in filename")
        
        # 2. Determine and validate timestamp method
        method = determine_timestamp_method(json_data)
        validation_results['timestamp_method'] = method
        
        if method == 'new':
            # Validate start field
            if 'start' in json_data:
                try:
                    start_time = datetime.fromtimestamp(json_data['start'] / 1000.0)
                    validation_results['json_validation']['valid_start_timestamp'] = True
                    
                    # Check if start timestamp is within reasonable range
                    if start_time.year < 2023 or start_time > datetime.now():
                        validation_results['warnings'].append("Start timestamp outside expected range")
                except ValueError:
                    validation_results['json_validation']['valid_start_timestamp'] = False
                    validation_results['errors'].append("Invalid start timestamp format")
        
        # 3. Combat log validation (if provided and needed)
        if combat_log_path and (method == 'old' or validation_results.get('json_validation', {}).get('valid_start_timestamp') == False):
            if not os.path.exists(combat_log_path):
                validation_results['errors'].append("Combat log file not found")
                return validation_results
            
            try:
                match_time, combat_log_info = parse_combat_log_for_match_start(json_data, combat_log_path)
                validation_results['combat_log_validation'] = combat_log_info
                
                # Cross-validate combat log findings with JSON data
                validation_results['cross_validation'].update({
                    'zone_id_match': str(json_data['zoneID']) == combat_log_info.get('zone_id'),
                    'arena_name_match': json_data['zoneName'] == combat_log_info.get('arena_name'),
                    'player_found': combat_log_info.get('player_validated') == 'True'
                })
                
            except ValueError as e:
                validation_results['errors'].append(f"Combat log parsing error: {str(e)}")
        
        # 4. Final validation status
        validation_results['is_valid'] = (
            all(validation_results['json_validation'].values()) and
            (method == 'new' or 
             (method == 'old' and all(validation_results.get('cross_validation', {}).values())))
        )
        
    except Exception as e:
        validation_results['errors'].append(f"Unexpected error: {str(e)}")
        validation_results['is_valid'] = False
    
    return validation_results

def determine_timestamp_method(json_data: dict) -> str:
    """
    Determine which timestamp method to use based on JSON data structure.
    
    Args:
        json_data (dict): The parsed JSON data from the arena match file
        
    Returns:
        str: Either 'new' if the file has a 'start' field, or 'old' if we need to use combat log parsing
    """
    if 'start' in json_data:
        return 'new'
    return 'old'

def get_match_start_time(json_data: dict, combat_log_path: Optional[str] = None) -> Tuple[datetime, dict]:
    """
    Get the match start time using either the new or old method.
    
    Args:
        json_data (dict): The parsed JSON data from the arena match file
        combat_log_path (str, optional): Path to the combat log file (required for old method)
        
    Returns:
        Tuple[datetime, dict]: (start_time, method_info)
        method_info contains details about which method was used and validation info
        
    Raises:
        ValueError: If combat_log_path is not provided for old method or if validation fails
    """
    method = determine_timestamp_method(json_data)
    
    if method == 'new':
        start_timestamp = json_data['start']
        start_time = datetime.fromtimestamp(start_timestamp / 1000.0)
        return start_time, {'method': 'new', 'validation': 'Used start field from JSON'}
    
    # Old method
    if not combat_log_path:
        raise ValueError("Combat log path is required for pre-June 2024 matches")
    
    start_time, validation_info = parse_combat_log_for_match_start(json_data, combat_log_path)
    validation_info['method'] = 'old'
    
    return start_time, validation_info
def parse_combat_log_for_match_start(json_data: dict, combat_log_path: str) -> Tuple[datetime, Dict[str, str]]:
    """
    Parse combat log to find the match start time by correlating ZONE_CHANGE and ARENA_MATCH_START events
    
    Args:
        combat_log_path (str): Path to the combat log file
        json_data (dict): The parsed JSON data containing arena and player information
        
    Returns:
        Tuple[datetime, Dict[str, str]]: (match_start_time, validation_info)
        validation_info contains matched arena name, zone ID, and player name for verification
        
    Raises:
        ValueError: If unable to find matching events or validation fails
    """
    target_zone_name = json_data['zoneName']
    target_zone_id = str(json_data['zoneID'])
    target_player = f"{json_data['player']['_name']}-{json_data['player']['_realm']}"
    
    # Store relevant events we find
    found_events = {
        'zone_change': None,
        'arena_match_start': None,
        'player_found': False
    }
    
    # Regular expressions for parsing combat log lines
    zone_change_pattern = r'^(\d+/\d+\s+\d+:\d+:\d+\.\d+).*ZONE_CHANGE,([^,]+),([^,]+)'
    arena_start_pattern = r'^(\d+/\d+\s+\d+:\d+:\d+\.\d+).*ARENA_MATCH_START,([^,]+)'
    player_pattern = re.escape(target_player)
    
    line_count = 0
    with open(combat_log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
            
            # Check for player name in first 50 lines for validation
            if line_count <= 50 and not found_events['player_found']:
                if re.search(player_pattern, line, re.IGNORECASE):
                    found_events['player_found'] = True
            
            # Look for ZONE_CHANGE event matching our arena
            if not found_events['zone_change']:
                zone_match = re.match(zone_change_pattern, line)
                if zone_match:
                    timestamp, zone_id, zone_name = zone_match.groups()
                    if (zone_name.strip() == target_zone_name or 
                        zone_id.strip() == target_zone_id):
                        found_events['zone_change'] = {
                            'timestamp': timestamp,
                            'zone_id': zone_id.strip(),
                            'zone_name': zone_name.strip()
                        }
            
            # Look for ARENA_MATCH_START event
            if not found_events['arena_match_start']:
                arena_match = re.match(arena_start_pattern, line)
                if arena_match:
                    timestamp, match_zone_id = arena_match.groups()
                    found_events['arena_match_start'] = {
                        'timestamp': timestamp,
                        'zone_id': match_zone_id.strip()
                    }
            
            # If we found both events and validated player, we can stop
            if (found_events['zone_change'] and 
                found_events['arena_match_start'] and 
                found_events['player_found']):
                break
    
    # Validate findings
    if not found_events['player_found']:
        raise ValueError(f"Could not find player {target_player} in first 50 lines")
    
    if not found_events['zone_change']:
        raise ValueError(f"Could not find ZONE_CHANGE event for arena {target_zone_name}")
    
    if not found_events['arena_match_start']:
        raise ValueError("Could not find ARENA_MATCH_START event")
    
    # Verify zone IDs match between events
    if found_events['zone_change']['zone_id'] != found_events['arena_match_start']['zone_id']:
        raise ValueError("Zone ID mismatch between ZONE_CHANGE and ARENA_MATCH_START events")
    
    # Parse the timestamp from the ARENA_MATCH_START event
    # Assuming timestamp format is "MM/DD HH:mm:ss.mmm"
    timestamp = found_events['arena_match_start']['timestamp']
    current_year = datetime.now().year
    match_time = datetime.strptime(f"{current_year} {timestamp}", "%Y %m/%d %H:%M:%S.%f")
    
    validation_info = {
        'arena_name': found_events['zone_change']['zone_name'],
        'zone_id': found_events['zone_change']['zone_id'],
        'player_validated': str(found_events['player_found'])
    }
    
    return match_time, validation_info

def test_match_data_validation():
    """
    Test the validation system with both new and old format files.
    """
    test_cases = [
        {
            "name": "New format test (post June 2024)",
            "json_path": "2024-07-13_23-06-06_-_Sluglishphsh_-_3v3_Nokhudon_(Win).json",
            "combat_log_path": "WoWCombatLog.txt",
            "expected_method": "new"
        },
        {
            "name": "Old format test (pre June 2024)",
            "json_path": "2024-05-01_23-45-50_-_Phlargus_-_2v2_Dalaran_Sewers_(Win).json",
            "combat_log_path": "WoWCombatLog.txt",
            "expected_method": "old"
        },
        {
            "name": "File with apostrophe (Tol'viron)",
            "json_path": "2025-01-01_20-06-29_-_Phlurbotomy_-_3v3_Tol'viron_(Loss).json",
            "combat_log_path": "WoWCombatLog.txt",
            "expected_method": "new"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nRunning test: {test_case['name']}")
        print("-" * 50)
        
        try:
            results = validate_match_data(test_case["json_path"], test_case["combat_log_path"])
            
            print(f"Timestamp method: {results['timestamp_method']}")
            print(f"Expected method: {test_case['expected_method']}")
            print(f"Is valid: {results['is_valid']}")
            
            if results["warnings"]:
                print("\nWarnings:")
                for warning in results["warnings"]:
                    print(f"- {warning}")
            
            if results["errors"]:
                print("\nErrors:")
                for error in results["errors"]:
                    print(f"- {error}")
            
            print("\nValidation details:")
            for category, checks in results.items():
                if isinstance(checks, dict) and category not in ["warnings", "errors"]:
                    print(f"\n{category}:")
                    for check, status in checks.items():
                        print(f"- {check}: {status}")

            # Assert expected method matches actual method
            assert results["timestamp_method"] == test_case["expected_method"], \
                f"Expected {test_case['expected_method']} method but got {results['timestamp_method']}"

        except Exception as e:
            print(f"Test failed: {str(e)}")
            raise

if __name__ == "__main__":
    test_match_data_validation()
