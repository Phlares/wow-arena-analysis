#!/usr/bin/env python3
# debug_enhanced_combat_parser.py - DEBUG VERSION

import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
import re


class DebugEnhancedCombatParser:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.processed_logs = set()
        self.processed_file = self.base_dir / "parsed_logs_enhanced.json"
        self.load_processed_logs()

    def load_processed_logs(self):
        """Load list of already processed combat logs."""
        if self.processed_file.exists():
            with open(self.processed_file, 'r', encoding='utf-8') as f:
                self.processed_logs = set(json.load(f))

    def save_processed_logs(self):
        """Save list of processed combat logs."""
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.processed_logs), f)

    def parse_enhanced_matches(self, enhanced_index_csv: str, logs_dir: str, output_csv: str):
        """
        DEBUG VERSION: Parse only the first few matches with extensive logging.
        """
        print("🚀 Starting DEBUG Enhanced Combat Log Parsing")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"Output file: {output_csv}")

        # Load enhanced index with precise timestamps
        df = pd.read_csv(enhanced_index_csv)

        # Handle timestamp parsing
        print("🔧 Parsing timestamps...")
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
        except ValueError:
            try:
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
            except ValueError:
                print("⚠️ Using manual timestamp cleaning...")
                df['precise_start_time'] = df['precise_start_time'].apply(self._clean_timestamp)
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

        print(f"📊 Loaded {len(df)} matches from enhanced index")

        # DEBUG: Find 2025-01-01 matches that actually have combat logs
        print("🔍 Finding 2025-01-01 matches with available combat logs...")
        df_jan1 = df[df['filename'].str.startswith('2025-01-01')]
        print(f"   Found {len(df_jan1)} matches from 2025-01-01")

        # Get available combat logs
        log_files = list(Path(logs_dir).glob('*.txt'))
        log_files.sort()
        print(f"📁 Found {len(log_files)} combat log files")

        # Find matches that have corresponding logs
        matches_with_logs = []
        for idx, match in df_jan1.iterrows():
            relevant_log = self.find_combat_log_for_match(match, log_files)
            if relevant_log:
                matches_with_logs.append((idx, match))
                print(f"   ✅ Match {len(matches_with_logs)}: {match['filename']} -> {relevant_log.name}")
                if len(matches_with_logs) >= 3:
                    break
            else:
                print(f"   ❌ No log for: {match['filename']}")

        if len(matches_with_logs) == 0:
            print("❌ No matches found with corresponding combat logs!")
            return

        debug_matches = pd.DataFrame([match for idx, match in matches_with_logs])
        print(f"🐛 DEBUG MODE: Processing {len(debug_matches)} matches from 2025-01-01 with logs")

        # Prepare output CSV
        self.setup_output_csv(output_csv)

        # Process debug matches (we already found the logs above)
        processed_count = 0
        for idx, (_, match) in enumerate(debug_matches.iterrows(), 1):
            print(f"\n{'=' * 80}")
            print(f"🐛 DEBUG MATCH {idx}: {match['filename']}")
            print(f"{'=' * 80}")

            try:
                # Find relevant combat log for this match (we know it exists)
                relevant_log = self.find_combat_log_for_match(match, log_files)
                if not relevant_log:
                    print(f"   ⚠️ No combat log found for {match['filename']}")
                    continue

                print(f"📄 Using combat log: {relevant_log.name}")

                # Extract combat features for this match with DEBUG
                features = self.debug_extract_combat_features(match, relevant_log, time_window=120)
                if features:
                    self.write_features_to_csv(features, output_csv)
                    processed_count += 1
                    print(f"✅ Successfully processed {match['filename']}")
                else:
                    print(f"❌ Failed to extract features for {match['filename']}")

            except Exception as e:
                print(f"   ❌ Error processing {match['filename']}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n🎉 DEBUG parsing complete! Processed {processed_count} matches.")

    def _clean_timestamp(self, timestamp_str):
        """Clean timestamp string for parsing."""
        if pd.isna(timestamp_str):
            return timestamp_str

        ts = str(timestamp_str).strip()

        if '.' in ts and len(ts.split('.')[-1]) > 3:
            parts = ts.split('.')
            if len(parts) == 2:
                base, microsec = parts
                microsec = microsec[:6].ljust(6, '0')
                ts = f"{base}.{microsec}"

        return ts

    def find_combat_log_for_match(self, match: pd.Series, log_files: list) -> Optional[Path]:
        """Find the combat log file that contains this match using smart time-based matching."""
        match_time = match['precise_start_time']
        match_date = match_time.date()

        print(f"🔍 Smart log matching for match at {match_time}")
        print(f"   Match date: {match_date}")
        print(f"   Match time: {match_time.time()}")

        # Parse all log files from the same day and nearby days
        candidate_logs = []
        for log_file in log_files:
            log_info = self.parse_log_info_from_filename(log_file.name)
            if log_info:
                log_date, log_time = log_info
                days_diff = abs((match_date - log_date).days)
                print(f"   Log {log_file.name}: {log_date} {log_time} (diff: {days_diff} days)")

                # Only consider logs from same day or adjacent days
                if days_diff <= 1:
                    # Calculate time difference (handle day boundaries)
                    log_datetime = datetime.combine(log_date, log_time)
                    time_diff_seconds = (match_time - log_datetime).total_seconds()

                    candidate_logs.append({
                        'file': log_file,
                        'log_datetime': log_datetime,
                        'time_diff_seconds': time_diff_seconds,
                        'days_diff': days_diff
                    })

        if not candidate_logs:
            print(f"   ❌ No candidate logs found for {match_date}")
            return None

        print(f"   Found {len(candidate_logs)} candidate logs")

        # Sort by time difference - we want logs that START before the match
        # but are closest to the match time
        valid_logs = []
        for log in candidate_logs:
            time_diff = log['time_diff_seconds']
            print(f"   Log {log['file'].name}: {log['log_datetime']} (diff: {time_diff:.0f}s)")

            # Log should start BEFORE the match (positive time_diff means log is before match)
            if time_diff > 0:
                # Log starts before match - this is good
                valid_logs.append(log)
            elif abs(time_diff) <= 600:  # Within 10 minutes after match start
                # Log starts slightly after match (within 10 min) - might be clock skew
                print(f"      ⚠️ Log starts after match but within 10min - including due to potential clock skew")
                valid_logs.append(log)

        if not valid_logs:
            print(f"   ❌ No valid logs found (logs must start before or within 10min of match)")
            return None

        # Sort by time difference (smallest positive difference first)
        valid_logs.sort(key=lambda x: abs(x['time_diff_seconds']))

        best_log = valid_logs[0]
        print(f"   ✅ Selected log: {best_log['file'].name}")
        print(f"      Log starts: {best_log['log_datetime']}")
        print(f"      Match time: {match_time}")
        print(f"      Time diff: {best_log['time_diff_seconds']:.0f} seconds")

        return best_log['file']

    def parse_log_info_from_filename(self, log_filename: str) -> Optional[Tuple[datetime.date, datetime.time]]:
        """Extract date and time from combat log filename: WoWCombatLog-MMDDYY_HHMMSS.txt"""
        try:
            match = re.search(r'(\d{6})_(\d{6})', log_filename)
            if match:
                date_str, time_str = match.groups()

                # Parse date: MMDDYY
                month = int(date_str[:2])
                day = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                log_date = datetime(year, month, day).date()

                # Parse time: HHMMSS
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                log_time = time(hour, minute, second)  # Fix: use time() not datetime.time()

                return log_date, log_time
        except Exception as e:
            print(f"   ⚠️ Error parsing log filename {log_filename}: {e}")
        return None

    def debug_extract_combat_features(self, match: pd.Series, log_file: Path, time_window: int) -> Optional[Dict]:
        """
        DEBUG VERSION: Extract combat features with extensive logging.
        """
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)  # Default 5 min if unknown
        match_end = match_start + timedelta(seconds=match_duration)

        # Allow some buffer based on reliability
        buffer = timedelta(seconds=time_window)
        window_start = match_start - buffer
        window_end = match_end + buffer

        print(f"⏰ Time window:")
        print(f"   Match start: {match_start}")
        print(f"   Match end: {match_end}")
        print(f"   Window start: {window_start} (buffer: -{time_window}s)")
        print(f"   Window end: {window_end} (buffer: +{time_window}s)")

        player_name = self.extract_player_name(match['filename'])
        if not player_name:
            print(f"❌ Could not extract player name from {match['filename']}")
            return None

        print(f"👤 Player name: {player_name}")

        # Initialize counters
        features = {
            'filename': match['filename'],
            'match_start_time': match_start.isoformat(),
            'cast_success_own': 0,
            'interrupt_success_own': 0,
            'times_interrupted': 0,
            'precog_gained_own': 0,
            'precog_gained_enemy': 0,
            'purges_own': 0,  # NEW: Track pet Devour Magic dispels
            'damage_done': 0,
            'healing_done': 0,
            'deaths_caused': 0,
            'times_died': 0,
            'spells_cast': [],  # NEW: Track which spells were cast
            'spells_purged': []  # NEW: Track which auras were purged
        }

        # Discover pet name for this player
        pet_name = self.find_pet_name(log_file, player_name)
        print(f"🐾 Pet name: {pet_name if pet_name else 'None found'}")

        # Parse combat log events within the time window
        # NOTE: We don't need log_date anymore since we parse full timestamps from each line
        print(f"📅 Parsing events from combat log...")

        # DEBUG: Track what we find
        events_in_window = 0
        cast_events = 0
        interrupt_events = 0
        precog_events = 0
        death_events = 0
        purge_events = 0
        total_lines = 0

        # NEW: Track precise arena match boundaries
        arena_start_time = None
        arena_end_time = None

        try:
            # PHASE 1: Smart arena boundary detection
            print(f"🎯 Phase 1: Smart arena boundary detection...")
            arena_start_time, arena_end_time = self.find_matching_arena_boundaries(
                log_file, window_start, window_end, match_start, match['filename']
            )

            # Use precise arena boundaries if found, otherwise use original window
            if arena_start_time and arena_end_time:
                print(f"   ✅ Found matching arena boundaries")
                print(f"   🚀 Arena start: {arena_start_time}")
                print(f"   🏁 Arena end: {arena_end_time}")
                precise_start = arena_start_time
                precise_end = arena_end_time
            else:
                print(f"   ⚠️ No matching arena found, using time window estimate")
                precise_start = window_start
                precise_end = window_end

            print(f"   📍 Precise match window: {precise_start} to {precise_end}")

            # PHASE 2: Parse events within precise boundaries
            print(f"🎯 Phase 2: Parsing events within precise boundaries...")
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    total_lines += 1

                    # Parse timestamp from log line
                    event_time = self.parse_log_line_timestamp(line, None)
                    if not event_time:
                        continue

                    # Check if within our PRECISE match window
                    if precise_start <= event_time <= precise_end:
                        events_in_window += 1

                        # DEBUG: Print first few events in window with timestamps
                        if events_in_window <= 10:
                            print(f"   Event {events_in_window}: {event_time} - {line.strip()[:100]}...")

                        # Parse the combat event with DEBUG
                        event_type = self.debug_process_combat_event(line, player_name, pet_name, features, event_time)

                        # Count event types for summary
                        if 'SPELL_CAST_SUCCESS' in line:
                            cast_events += 1
                        elif 'SPELL_INTERRUPT' in line:
                            interrupt_events += 1
                        elif 'SPELL_DISPEL' in line and 'Devour Magic' in line:
                            purge_events += 1
                        elif 'SPELL_AURA_APPLIED' in line and 'Precognition' in line:
                            precog_events += 1
                        elif 'UNIT_DIED' in line:
                            death_events += 1

            print(f"\n📊 Parsing Summary:")
            print(f"   Total lines in log: {total_lines}")
            print(f"   Events in time window: {events_in_window}")
            print(f"   Cast events in window: {cast_events}")
            print(f"   Interrupt events in window: {interrupt_events}")
            print(f"   Precognition events in window: {precog_events}")
            print(f"   Death events in window: {death_events}")
            print(f"   Purge events in window: {purge_events}")

            print(f"\n🎯 Final Feature Counts:")
            print(f"   cast_success_own: {features['cast_success_own']}")
            print(f"   interrupt_success_own: {features['interrupt_success_own']}")
            print(f"   times_interrupted: {features['times_interrupted']}")
            print(f"   precog_gained_own: {features['precog_gained_own']}")
            print(f"   precog_gained_enemy: {features['precog_gained_enemy']}")
            print(f"   purges_own: {features['purges_own']}")

            print(f"\n📜 Spells Cast: {features['spells_cast']}")
            print(f"🔥 Spells Purged: {features['spells_purged']}")

            return features

        except Exception as e:
            print(f"❌ Error parsing log file {log_file}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_player_name(self, filename: str) -> Optional[str]:
        """Extract player name from video filename."""
        try:
            # Format: YYYY-MM-DD_HH-MM-SS_-_PLAYERNAME_-_...
            parts = filename.split('_-_')
            if len(parts) >= 2:
                return parts[1]  # PLAYERNAME
        except:
            pass
        return None

    def find_pet_name(self, log_file: Path, player_name: str) -> Optional[str]:
        """Find the pet name for this player in the combat log."""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 1000:  # Don't search entire file
                        break

                    if 'SPELL_SUMMON' in line:
                        parts = line.strip().split(',')
                        if len(parts) >= 7:
                            src = parts[2].strip('"').split('-', 1)[0]
                            pet_candidate = parts[6].strip('"')
                            if src == player_name:
                                print(f"🐾 Found pet: {pet_candidate} for player {player_name}")
                                return pet_candidate
        except Exception as e:
            print(f"⚠️ Error finding pet name: {e}")
        return None

    def parse_log_line_timestamp(self, line: str, log_date: datetime.date) -> Optional[datetime]:
        """Parse timestamp from a combat log line - DEBUG VERSION."""
        try:
            # Combat log format: "1/2/2025 18:04:33.345-5  SPELL_CAST_SUCCESS,..."
            # We need to extract the full timestamp including date
            parts = line.strip().split(None, 2)
            if len(parts) < 2:
                return None

            # Get the full timestamp "1/2/2025 18:04:33.345-5"
            full_timestamp = f"{parts[0]} {parts[1]}"

            # Remove timezone offset (the "-5" part)
            timestamp_clean = full_timestamp.split('-')[0].strip()

            # Parse the full timestamp: "1/2/2025 18:04:33.345"
            try:
                # Try format with 3-digit milliseconds
                result = datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S.%f")

    def find_matching_arena_boundaries(self, log_file: Path, window_start: datetime,
                                       window_end: datetime, video_start: datetime,
                                       filename: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Smart arena boundary detection that finds the correct arena match.
        Uses backward/forward search from video timestamp to find matching arena.
        """
        print(f"   🔍 Looking for arena match for video: {filename}")
        print(f"   📅 Video timestamp: {video_start}")

        # Extract expected arena info from filename
        expected_bracket, expected_map = self.extract_arena_info_from_filename(filename)
        print(f"   🎯 Expected: {expected_bracket} on {expected_map}")

        # Collect all arena events in the time window
        arena_events = []

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                event_time = self.parse_log_line_timestamp(line, None)
                if not event_time:
                    continue

                # Look in a wider window to catch nearby matches
                extended_start = window_start - timedelta(minutes=10)
                extended_end = window_end + timedelta(minutes=10)

                if extended_start <= event_time <= extended_end:
                    if 'ARENA_MATCH_START' in line:
                        arena_info = self.parse_arena_start_line(line, event_time)
                        if arena_info:
                            arena_events.append(('START', event_time, arena_info, line.strip()))
                    elif 'ARENA_MATCH_END' in line:
                        arena_events.append(('END', event_time, None, line.strip()))

        # Sort events by time
        arena_events.sort(key=lambda x: x[1])

        print(f"   📋 Found {len(arena_events)} arena events in extended window:")
        for event_type, event_time, info, line in arena_events:
            if event_type == 'START':
                print(f"      🚀 {event_time}: START - {info['bracket']} on {info['map']} (Zone: {info['zone_id']})")
            else:
                print(f"      🏁 {event_time}: END")

        # Strategy 1: Look backward from video time to find most recent arena start
        print(f"   🔄 Strategy 1: Looking backward from video time...")
        recent_start = None
        for event_type, event_time, info, line in reversed(arena_events):
            if event_time <= video_start and event_type == 'START':
                if self.arena_info_matches(info, expected_bracket, expected_map):
                    recent_start = (event_time, info)
                    print(f"      ✅ Found matching arena start: {event_time}")
                    break
                else:
                    print(f"      ❌ Arena doesn't match: {info['bracket']} on {info['map']}")

        # Strategy 2: If no backward match, look forward from video time
        if not recent_start:
            print(f"   🔄 Strategy 2: Looking forward from video time...")
            for event_type, event_time, info, line in arena_events:
                if event_time >= video_start and event_type == 'START':
                    if self.arena_info_matches(info, expected_bracket, expected_map):
                        recent_start = (event_time, info)
                        print(f"      ✅ Found matching arena start: {event_time}")
                        break
                    else:
                        print(f"      ❌ Arena doesn't match: {info['bracket']} on {info['map']}")

        if not recent_start:
            print(f"   ❌ No matching arena start found")
            return None, None

        # Find the corresponding arena end
        start_time, start_info = recent_start
        for event_type, event_time, info, line in arena_events:
            if event_time > start_time and event_type == 'END':
                print(f"      ✅ Found corresponding arena end: {event_time}")
                return start_time, event_time

        print(f"   ⚠️ Found arena start but no corresponding end")
        return start_time, None

    def extract_arena_info_from_filename(self, filename: str) -> Tuple[str, str]:
        """Extract bracket type and map name from video filename."""
        try:
            # Format: YYYY-MM-DD_HH-MM-SS_-_PLAYER_-_BRACKET_MAP_(RESULT).mp4
            parts = filename.split('_-_')
            if len(parts) >= 3:
                bracket_map_result = parts[2]  # "3v3_Ruins_of_Lordaeron_(Win)"

                # Extract bracket (3v3, 2v2, etc.)
                if bracket_map_result.startswith('3v3'):
                    bracket = '3v3'
                    map_part = bracket_map_result[4:]  # Remove "3v3_"
                elif bracket_map_result.startswith('2v2'):
                    bracket = '2v2'
                    map_part = bracket_map_result[4:]  # Remove "2v2_"
                elif 'Skirmish' in bracket_map_result:
                    bracket = 'Skirmish'
                    map_part = bracket_map_result.replace('Skirmish_', '')
                elif 'Solo_Shuffle' in bracket_map_result:
                    bracket = 'Solo Shuffle'
                    map_part = bracket_map_result.replace('Solo_Shuffle_', '')
                else:
                    bracket = 'Unknown'
                    map_part = bracket_map_result

                # Extract map name (remove result suffix)
                arena_map = map_part.split('_(')[0].replace('_', ' ')
                # Handle special cases like "Tol'viron"
                arena_map = arena_map.replace("Tol viron", "Tol'viron")

                return bracket, arena_map
        except:
            pass

        return 'Unknown', 'Unknown'

    def parse_arena_start_line(self, line: str, event_time: datetime) -> Optional[Dict]:
        """Parse ARENA_MATCH_START line to extract arena info."""
        try:
            # Format: 1/1/2025 20:22:03.932-5  ARENA_MATCH_START,572,38,3v3,1
            parts = line.strip().split(',')
            if len(parts) >= 5:
                zone_id = parts[1].strip()
                bracket = parts[3].strip()

                # Map zone ID to arena name (common ones)
                zone_map = {
                    '572': 'Ruins of Lordaeron',
                    '617': "Dalaran Sewers",
                    '618': "The Ring of Valor",
                    '1825': 'Hook Point',
                    '1911': "Tol'viron Arena",
                    '2547': 'Empyrean Domain',
                    # Add more zone mappings as needed
                }

                arena_map = zone_map.get(zone_id, f'Zone_{zone_id}')

                return {
                    'zone_id': zone_id,
                    'bracket': bracket,
                    'map': arena_map,
                    'time': event_time
                }
        except:
            pass

        return None

    def arena_info_matches(self, arena_info: Dict, expected_bracket: str, expected_map: str) -> bool:
        """Check if arena info matches expected values from filename."""
        if not arena_info:
            return False

        # Bracket matching
        bracket_match = (arena_info['bracket'] == expected_bracket or
                         (expected_bracket == 'Skirmish' and arena_info['bracket'] in ['2v2', '3v3']))

        # Map matching (case insensitive, handle common variations)
        map_match = (arena_info['map'].lower() == expected_map.lower() or
                     expected_map.lower() in arena_info['map'].lower() or
                     arena_info['map'].lower() in expected_map.lower())

        return bracket_match and map_match
        except ValueError:
        # Try format without microseconds
        result = datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S")
        return result

except Exception as e:
# DEBUG: Print parsing failures occasionally
if "SPELL_CAST_SUCCESS" in line or "SPELL_INTERRUPT" in line:
    print(f"⚠️ Failed to parse timestamp from: {line.strip()[:70]}... Error: {e}")
    print(f"   Trying to parse: '{timestamp_clean}'" if 'timestamp_clean' in locals() else "   No timestamp_clean")
return None


def debug_process_combat_event(self, line: str, player_name: str, pet_name: Optional[str], features: Dict,
                               event_time: datetime) -> str:
    """Process a single combat log event and update feature counters - DEBUG VERSION."""
    try:
        parts = line.strip().split(',')
        if len(parts) < 3:
            return "invalid_format"

        # Get event type from the timestamp line
        first_part = parts[0]
        event_type = first_part.split()[-1] if ' ' in first_part else first_part

        # DEBUG: Control debug output based on total events found
        debug_count = (features['cast_success_own'] + features['interrupt_success_own'] +
                       features['purges_own'] + features['times_interrupted'])
        show_debug = debug_count < 10

        # 1. SPELL_DISPEL events (Pet Purges)
        if event_type == 'SPELL_DISPEL' and len(parts) >= 13:
            src = parts[2].strip('"').split('-', 1)[0]
            spell_name = parts[10].strip('"')  # The dispel spell (should be "Devour Magic")

            if pet_name and src == pet_name and spell_name == "Devour Magic":
                # The purged aura is in parts[12]
                purged_aura = parts[12].strip('"')
                features['purges_own'] += 1
                features['spells_purged'].append(purged_aura)

                if show_debug:
                    print(f"      🔥 PET PURGE at {event_time}: {src} dispelled '{purged_aura}' with {spell_name}")
                return "purge"

        # 2. Cast success events - EXCLUDE PET CASTS (except purges handled above)
        elif event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 11:
            src = parts[2].strip('"').split('-', 1)[0]
            spell_name = parts[10].strip('"')

            # Only count player casts, NOT pet casts
            if src == player_name:
                features['cast_success_own'] += 1
                features['spells_cast'].append(spell_name)

                if show_debug:
                    print(f"      ✅ PLAYER CAST at {event_time}: {src} cast '{spell_name}'")
                return "cast_success"
            elif pet_name and src == pet_name:
                # Pet casts - ignore (purges handled separately above)
                if show_debug:
                    print(f"      ⚪ Pet cast ignored at {event_time}: {src} cast '{spell_name}'")
                return "pet_cast_ignored"

        # 3. Interrupt events
        elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 11:
            src = parts[2].strip('"').split('-', 1)[0]
            dst = parts[6].strip('"').split('-', 1)[0]
            interrupt_spell = parts[10].strip('"')  # The spell used to interrupt

            # Treat pet as player for interrupts
            actual_src = src
            actual_dst = dst
            if pet_name and src == pet_name:
                actual_src = player_name
            if pet_name and dst == pet_name:
                actual_dst = player_name

            if actual_src == player_name:
                features['interrupt_success_own'] += 1
                if show_debug:
                    print(
                        f"      ✅ INTERRUPT SUCCESS at {event_time}: {actual_src} interrupted {actual_dst} with '{interrupt_spell}'")
                return "interrupt_success"
            elif actual_dst == player_name:
                features['times_interrupted'] += 1
                if show_debug:
                    print(
                        f"      ❌ GOT INTERRUPTED at {event_time}: {actual_dst} interrupted by {actual_src} using '{interrupt_spell}'")
                return "got_interrupted"

        # 4. Precognition aura applications
        elif event_type == 'SPELL_AURA_APPLIED' and len(parts) >= 11:
            dst = parts[6].strip('"').split('-', 1)[0]
            spell_name = parts[10].strip('"')

            if spell_name == 'Precognition':
                if dst == player_name:
                    features['precog_gained_own'] += 1
                    if show_debug:
                        print(f"      ✅ PRECOGNITION gained at {event_time}: {dst}")
                    return "precog_own"
                else:
                    features['precog_gained_enemy'] += 1
                    if show_debug:
                        print(f"      ⚠️ PRECOGNITION gained by enemy at {event_time}: {dst}")
                    return "precog_enemy"

        # 5. Death events
        elif event_type == 'UNIT_DIED' and len(parts) >= 7:
            died_unit = parts[6].strip('"').split('-', 1)[0]
            if died_unit == player_name:
                features['times_died'] += 1
                if show_debug:
                    print(f"      💀 DEATH at {event_time}: {died_unit}")
                return "player_died"

        return event_type

    except Exception as e:
        print(f"      ❌ Error processing event at {event_time}: {e}")
        print(f"         Line: {line.strip()[:150]}...")
        return "error"


def setup_output_csv(self, output_csv: str):
    """Set up the output CSV file with headers."""
    if not os.path.exists(output_csv):
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'match_start_time', 'cast_success_own', 'interrupt_success_own',
                'times_interrupted', 'precog_gained_own', 'precog_gained_enemy', 'purges_own',
                'damage_done', 'healing_done', 'deaths_caused', 'times_died',
                'spells_cast', 'spells_purged'  # NEW: Add spell tracking columns
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def write_features_to_csv(self, features: Dict, output_csv: str):
    """Write extracted features to the output CSV."""
    with open(output_csv, 'a', newline='', encoding='utf-8') as f:
        # Convert lists to strings for CSV storage
        features_for_csv = features.copy()
        features_for_csv['spells_cast'] = '; '.join(features['spells_cast']) if features['spells_cast'] else ''
        features_for_csv['spells_purged'] = '; '.join(features['spells_purged']) if features['spells_purged'] else ''

        fieldnames = list(features_for_csv.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(features_for_csv)


def main():
    """Main function to run debug combat parsing."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/debug_match_features.csv"

    parser = DebugEnhancedCombatParser(base_dir)
    parser.parse_enhanced_matches(enhanced_index, logs_dir, output_csv)


if __name__ == '__main__':
    main()