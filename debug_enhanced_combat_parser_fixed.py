#!/usr/bin/env python3
# debug_enhanced_combat_parser_fixed.py - CLEAN VERSION

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
        """DEBUG VERSION: Parse only the first few matches with extensive logging."""
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

        # DEBUG: Find 2025-02-20 matches that actually have combat logs (Solo Shuffle focus)
        print("🔍 Finding 2025-02-20 matches with available combat logs (testing Solo Shuffle support)...")
        df_test = df[df['filename'].str.startswith('2025-02-20')]
        print(f"   Found {len(df_test)} matches from 2025-02-20")

        # Get available combat logs
        log_files = list(Path(logs_dir).glob('*.txt'))
        log_files.sort()
        print(f"📁 Found {len(log_files)} combat log files")

        # Find matches that have corresponding logs
        matches_with_logs = []
        for idx, match in df_test.iterrows():
            relevant_log = self.find_combat_log_for_match(match, log_files)
            if relevant_log:
                matches_with_logs.append((idx, match))
                print(f"   ✅ Match {len(matches_with_logs)}: {match['filename']} -> {relevant_log.name}")
                if len(matches_with_logs) >= 10:
                    break
            else:
                print(f"   ❌ No log for: {match['filename']}")

        if len(matches_with_logs) == 0:
            print("❌ No matches found with corresponding combat logs!")
            return

        debug_matches = pd.DataFrame([match for idx, match in matches_with_logs])
        print(f"🐛 DEBUG MODE: Processing {len(debug_matches)} matches from 2025-02-20 with logs")

        # Prepare output CSV
        self.setup_output_csv(output_csv)

        # Process debug matches
        processed_count = 0
        for idx, (_, match) in enumerate(debug_matches.iterrows(), 1):
            print(f"\n{'='*80}")
            
            # Extract and show bracket type for this match
            expected_bracket, expected_map = self.extract_arena_info_from_filename(match['filename'])
            print(f"🐛 DEBUG MATCH {idx}: {match['filename']}")
            print(f"🎯 Expected: {expected_bracket} on {expected_map}")
            print(f"{'='*80}")
            
            try:
                # Find relevant combat log for this match
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

        # Parse all log files from the same day and nearby days
        candidate_logs = []
        for log_file in log_files:
            log_info = self.parse_log_info_from_filename(log_file.name)
            if log_info:
                log_date, log_time = log_info
                days_diff = abs((match_date - log_date).days)
                
                # Only consider logs from same day or adjacent days
                if days_diff <= 1:
                    # Calculate time difference
                    log_datetime = datetime.combine(log_date, log_time)
                    time_diff_seconds = (match_time - log_datetime).total_seconds()
                    
                    candidate_logs.append({
                        'file': log_file,
                        'log_datetime': log_datetime,
                        'time_diff_seconds': time_diff_seconds,
                        'days_diff': days_diff
                    })

        if not candidate_logs:
            return None

        # Sort by time difference - we want logs that START before the match
        valid_logs = []
        for log in candidate_logs:
            time_diff = log['time_diff_seconds']
            
            # Log should start BEFORE the match (positive time_diff means log is before match)
            if time_diff > 0:
                valid_logs.append(log)
            elif abs(time_diff) <= 600:  # Within 10 minutes after match start
                valid_logs.append(log)

        if not valid_logs:
            return None

        # Sort by time difference (smallest positive difference first)
        valid_logs.sort(key=lambda x: abs(x['time_diff_seconds']))
        
        best_log = valid_logs[0]
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
                log_time = time(hour, minute, second)
                
                return log_date, log_time
        except Exception as e:
            pass
        return None

    def debug_extract_combat_features(self, match: pd.Series, log_file: Path, time_window: int) -> Optional[Dict]:
        """DEBUG VERSION: Extract combat features with extensive logging."""
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)
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
            'purges_own': 0,
            'damage_done': 0,
            'healing_done': 0,
            'deaths_caused': 0,
            'times_died': 0,
            'spells_cast': [],
            'spells_purged': []
        }

        # Discover pet name for this player
        pet_name = self.find_pet_name(log_file, player_name)
        print(f"🐾 Pet name: {pet_name if pet_name else 'None found'}")

        try:
            # PHASE 1: Smart arena boundary detection
            print(f"🎯 Phase 1: Smart arena boundary detection...")
            arena_start_time, arena_end_time = self.find_matching_arena_boundaries(
                log_file, window_start, window_end, match_start, match['filename'], match_duration
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
            events_in_window = 0
            total_lines = 0
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    total_lines += 1
                    
                    # Parse timestamp from log line
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time:
                        continue

                    # Check if within our PRECISE match window
                    if precise_start <= event_time <= precise_end:
                        events_in_window += 1
                        
                        # DEBUG: Print first few events in window
                        if events_in_window <= 10:
                            print(f"   Event {events_in_window}: {event_time} - {line.strip()[:100]}...")
                        
                        # Parse the combat event
                        self.debug_process_combat_event(line, player_name, pet_name, features, event_time)

            print(f"\n📊 Parsing Summary:")
            print(f"   Total lines in log: {total_lines}")
            print(f"   Events in time window: {events_in_window}")
            
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

    def find_matching_arena_boundaries(self, log_file: Path, window_start: datetime, 
                                       window_end: datetime, video_start: datetime, 
                                       filename: str, video_duration: float = 300) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Smart arena boundary detection that finds the correct arena match."""
        print(f"   🔍 Looking for arena match for video: {filename}")
        print(f"   📅 Video timestamp: {video_start}")
        
        # Extract expected arena info from filename
        expected_bracket, expected_map = self.extract_arena_info_from_filename(filename)
        print(f"   🎯 Expected: {expected_bracket} on {expected_map}")
        
        # Collect all arena events in extended time window
        arena_events = []
        extended_start = window_start - timedelta(minutes=10)
        extended_end = window_end + timedelta(minutes=10)
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                event_time = self.parse_log_line_timestamp(line)
                if not event_time:
                    continue
                
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
        
        # Strategy 1: Look backward from video time
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
        
        # Strategy 2: Look forward if no backward match
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
        
        # Handle potential duplicate matches (same bracket + map)
        if recent_start:
            matching_starts = []
            start_time, start_info = recent_start
            
            # Find all matching arena starts within reasonable window
            for event_type, event_time, info, line in arena_events:
                if (event_type == 'START' and 
                    self.arena_info_matches(info, expected_bracket, expected_map) and
                    abs((event_time - video_start).total_seconds()) <= 600):  # Within 10 minutes
                    matching_starts.append((event_time, info))
            
            if len(matching_starts) > 1:
                print(f"   ⚠️ Found {len(matching_starts)} potential matches - using enhanced tiebreaker")
                best_match = self.find_best_match_with_verification(matching_starts, arena_events, video_duration, filename, log_file)
                if best_match:
                    recent_start = best_match
                    print(f"   ✅ Selected verified best match: {recent_start[0]}")
        
        if not recent_start:
            print(f"   ❌ No matching arena start found")
            return None, None
        
        # Find corresponding arena end
        start_time, start_info = recent_start
        
        # Special handling for Solo Shuffle (no ARENA_MATCH_END between rounds)
        if expected_bracket == 'Solo Shuffle':
            return self.find_solo_shuffle_boundaries(start_time, start_info, arena_events, video_duration)
        
        # Standard arena: find next ARENA_MATCH_END
        for event_type, event_time, info, line in arena_events:
            if event_time > start_time and event_type == 'END':
                print(f"      ✅ Found corresponding arena end: {event_time}")
                return start_time, event_time
        
        print(f"   ⚠️ Found arena start but no corresponding end")
        return start_time, None

    def find_solo_shuffle_boundaries(self, start_time: datetime, start_info: Dict, arena_events: list, video_duration: float) -> Tuple[datetime, Optional[datetime]]:
        """Find Solo Shuffle session boundaries by counting rounds."""
        print(f"   🎀 Processing Solo Shuffle session starting at {start_time}")
        
        # Count ARENA_MATCH_START events for this shuffle session
        shuffle_starts = []
        for event_type, event_time, info, line in arena_events:
            if (event_type == 'START' and 
                event_time >= start_time and
                info and info.get('zone_id') == start_info.get('zone_id') and
                'Solo Shuffle' in info.get('bracket', '')):
                shuffle_starts.append(event_time)
        
        rounds_found = len(shuffle_starts)
        print(f"      🔄 Found {rounds_found} shuffle rounds")
        
        # Estimate end time based on video duration or last round + buffer
        if rounds_found >= 1:
            estimated_end = start_time + timedelta(seconds=video_duration)
            print(f"      ⏰ Estimated shuffle end: {estimated_end} (duration: {video_duration}s)")
            return start_time, estimated_end
        else:
            print(f"      ⚠️ Could not determine shuffle boundaries")
            return start_time, None

    def find_best_duration_match(self, matching_starts, arena_events, video_duration):
        """Find the best arena match based on duration comparison."""
        best_match = None
        best_duration_diff = float('inf')
        
        for start_time, start_info in matching_starts:
            # Find corresponding end for this start
            arena_duration = None
            for event_type, event_time, info, line in arena_events:
                if event_time > start_time and event_type == 'END':
                    arena_duration = (event_time - start_time).total_seconds()
                    break
            
            if arena_duration:
                duration_diff = abs(arena_duration - video_duration)
                print(f"      Arena {start_time}: duration {arena_duration:.0f}s vs video {video_duration:.0f}s (diff: {duration_diff:.0f}s)")
                
                if duration_diff < best_duration_diff:
                    best_duration_diff = duration_diff
                    best_match = (start_time, start_info)
        
        return best_match

    def find_best_match_with_verification(self, matching_starts, arena_events, video_duration, filename, log_file):
        """Find best arena match using duration AND confirmed death matches."""
        best_match = None
        best_score = -1
        
        # Load death data from JSON
        json_data = self.load_death_data_from_json(filename)
        player_name = self.extract_player_name(filename)
        
        # Handle both regular deaths list and Solo Shuffle format
        json_deaths = None
        shuffle_timeline = None
        if isinstance(json_data, dict) and 'deaths' in json_data:
            # Solo Shuffle format
            json_deaths = json_data['deaths']
            shuffle_timeline = json_data.get('timeline')
        elif isinstance(json_data, list):
            # Regular arena format
            json_deaths = json_data
        
        # Collect death match counts for all candidates
        candidate_results = []
        
        for start_time, start_info in matching_starts:
            # Find corresponding end for this start
            arena_duration = None
            arena_end = None
            for event_type, event_time, info, line in arena_events:
                if event_time > start_time and event_type == 'END':
                    arena_end = event_time
                    arena_duration = (event_time - start_time).total_seconds()
                    break
            
            if not arena_duration or not arena_end:
                continue
                
            # Calculate duration score (closer = better)
            duration_diff = abs(arena_duration - video_duration)
            duration_score = max(0, 1 - (duration_diff / 300))  # Normalize to 0-1 range
            
            # Calculate confirmed death matches
            confirmed_deaths = 0
            if json_deaths and player_name:
                combat_deaths = self.find_death_events_in_arena(log_file, start_time, arena_end, player_name)
                confirmed_deaths = self.verify_death_correlation(json_deaths, combat_deaths, start_time)
            
            candidate_results.append({
                'start_time': start_time,
                'start_info': start_info,
                'duration_score': duration_score,
                'confirmed_deaths': confirmed_deaths,
                'arena_duration': arena_duration
            })
        
        # Calculate death correlation scores based on confirmed death distribution
        total_confirmed_deaths = sum(c['confirmed_deaths'] for c in candidate_results)
        
        for candidate in candidate_results:
            confirmed_deaths = candidate['confirmed_deaths']
            
            if total_confirmed_deaths == 0:
                # No confirmed deaths for any candidate - use neutral score
                death_score = 0.5
            elif confirmed_deaths == 0:
                # This candidate has no confirmed deaths while others do
                death_score = 0.0
            else:
                # Distribute score based on confirmed death proportion
                death_score = confirmed_deaths / total_confirmed_deaths
            
            # Combined score (duration weighted 70%, death correlation 30%)
            combined_score = (candidate['duration_score'] * 0.7) + (death_score * 0.3)
            
            print(f"      Arena {candidate['start_time']}: duration {candidate['arena_duration']:.0f}s vs video {video_duration:.0f}s")
            print(f"         Duration score: {candidate['duration_score']:.2f}, Confirmed deaths: {confirmed_deaths}, Death score: {death_score:.2f}, Combined: {combined_score:.2f}")
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = (candidate['start_time'], candidate['start_info'])
        
        return best_match

    def load_death_data_from_json(self, filename: str) -> Optional[list]:
        """Load death timestamps from the corresponding JSON file."""
        try:
            json_name = filename.rsplit('.', 1)[0] + '.json'
            
            # Try to find JSON file (similar to timestamp matcher logic)
            json_path = None
            try:
                date_part = filename.split('_', 1)[0]  # YYYY-MM-DD
                year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
                json_path = self.base_dir / year_month / json_name
                if not json_path.exists():
                    json_path = self.base_dir / json_name
            except:
                json_path = self.base_dir / json_name
            
            if not json_path or not json_path.exists():
                return None
                
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract death events from the "deaths" array
            deaths = []
            if 'deaths' in data:
                for death in data['deaths']:
                    if 'name' in death and 'timestamp' in death:
                        deaths.append({
                            'name': death['name'],
                            'timestamp': death['timestamp']  # Seconds from match start
                        })
            
            # For Solo Shuffle, also extract round timeline for verification
            shuffle_timeline = None
            if 'soloShuffleTimeline' in data:
                shuffle_timeline = data['soloShuffleTimeline']
                print(f"      🎀 Solo Shuffle: {len(shuffle_timeline)} rounds")
                        
            print(f"      📊 Loaded {len(deaths)} deaths from JSON")
            
            # Return both deaths and timeline if it's a shuffle
            if shuffle_timeline:
                return {'deaths': deaths, 'timeline': shuffle_timeline}
            else:
                return deaths if deaths else None
            
        except Exception as e:
            print(f"      ⚠️ Could not load death data from JSON: {e}")
            return None

    def find_death_events_in_arena(self, log_file: Path, arena_start: datetime, arena_end: datetime, player_name: str) -> list:
        """Find all death events within arena boundaries."""
        deaths = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time or not (arena_start <= event_time <= arena_end):
                        continue
                    
                    if 'UNIT_DIED' in line:
                        parts = line.strip().split(',')
                        if len(parts) >= 7:
                            # Extract full name: "Shíízz-Tichondrius-US"
                            died_unit_full = parts[6].strip('"')
                            died_unit_name = died_unit_full.split('-', 1)[0]  # Just first name part
                            
                            deaths.append({
                                'timestamp': event_time,
                                'name': died_unit_full,  # Full name for matching
                                'unit': died_unit_name,  # Short name for player comparison
                                'is_player': died_unit_name == player_name
                            })
                            
            print(f"      ⚖️ Found {len(deaths)} deaths in combat log")
        except Exception as e:
            print(f"      ⚠️ Error finding death events: {e}")
        
        return deaths

    def verify_death_correlation(self, json_deaths: list, combat_deaths: list, arena_start: datetime) -> int:
        """Calculate number of confirmed death matches between JSON and combat log."""
        if not json_deaths or not combat_deaths:
            return 0  # No matches possible
        
        print(f"      🔍 Verifying {len(json_deaths)} JSON deaths vs {len(combat_deaths)} combat deaths")
        
        # Find confirmed death matches by name and time
        confirmed_matches = 0
        tolerance = timedelta(seconds=10)  # Tolerance for timezone/precision differences
        
        for json_death in json_deaths:
            json_name = json_death['name']
            # Convert JSON timestamp (seconds from arena start) to absolute time
            json_time = arena_start + timedelta(seconds=json_death['timestamp'])
            
            for combat_death in combat_deaths:
                combat_name = combat_death['name']
                combat_time = combat_death['timestamp']
                
                # Check if names match and times are close
                name_match = json_name == combat_name
                time_diff = abs(json_time - combat_time)
                time_match = time_diff <= tolerance
                
                if name_match and time_match:
                    confirmed_matches += 1
                    print(f"         ✅ Match: {json_name} at {json_time} vs {combat_time} (diff: {time_diff.total_seconds():.1f}s)")
                    break
                elif name_match:
                    print(f"         ⚠️ Name match but time off: {json_name} - {time_diff.total_seconds():.1f}s difference")
        
        print(f"      🎯 Confirmed death matches: {confirmed_matches}")
        return confirmed_matches

    def extract_arena_info_from_filename(self, filename: str) -> Tuple[str, str]:
        """Extract bracket type and map name from video filename."""
        try:
            parts = filename.split('_-_')
            if len(parts) >= 3:
                bracket_map_result = parts[2]
                
                # Extract bracket
                if bracket_map_result.startswith('3v3'):
                    bracket = '3v3'
                    map_part = bracket_map_result[4:]
                elif bracket_map_result.startswith('2v2'):
                    bracket = '2v2'
                    map_part = bracket_map_result[4:]
                elif 'Skirmish' in bracket_map_result:
                    bracket = 'Skirmish'
                    map_part = bracket_map_result.replace('Skirmish_', '')
                elif 'Solo_Shuffle' in bracket_map_result:
                    bracket = 'Solo Shuffle'
                    map_part = bracket_map_result.replace('Solo_Shuffle_', '')
                else:
                    bracket = 'Unknown'
                    map_part = bracket_map_result
                
                # Extract map name
                arena_map = map_part.split('_(')[0].replace('_', ' ')
                arena_map = arena_map.replace("Tol viron", "Tol'viron")
                
                return bracket, arena_map
        except:
            pass
        
        return 'Unknown', 'Unknown'

    def parse_arena_start_line(self, line: str, event_time: datetime) -> Optional[Dict]:
        """Parse ARENA_MATCH_START line to extract arena info."""
        try:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                zone_id = parts[1].strip()
                bracket = parts[3].strip()
                
                zone_map = {
                    '980': "Tol'viron",
                    '1552': "Ashamane's Fall", 
                    '2759': "Cage of Carnage",
                    '1504': "Black Rook",
                    '2167': "Robodrome",
                    '2563': "Nokhudon", 
                    '1911': "Mugambala",
                    '2373': "Empyrean Domain",
                    '1134': "Tiger's Peak",
                    '1505': "Nagrand",
                    '1825': "Hook Point",
                    '2509': "Maldraxxus",
                    '572': "Ruins of Lordaeron",
                    '617': "Dalaran Sewers",
                    '2547': "Enigma Crucible"
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
        
        # Bracket matching with Solo Shuffle special handling
        combat_bracket = arena_info['bracket']
        bracket_match = False
        
        if expected_bracket == 'Solo Shuffle':
            # Solo Shuffle can appear as "Rated Solo Shuffle" in combat logs
            bracket_match = combat_bracket in ['Solo Shuffle', 'Rated Solo Shuffle']
        elif expected_bracket == 'Skirmish':
            bracket_match = combat_bracket in ['2v2', '3v3', 'Skirmish']
        else:
            bracket_match = combat_bracket == expected_bracket
        
        # Map matching (case insensitive)
        map_match = (arena_info['map'].lower() == expected_map.lower() or
                    expected_map.lower() in arena_info['map'].lower() or
                    arena_info['map'].lower() in expected_map.lower())
        
        return bracket_match and map_match

    def extract_player_name(self, filename: str) -> Optional[str]:
        """Extract player name from video filename."""
        try:
            parts = filename.split('_-_')
            if len(parts) >= 2:
                return parts[1]
        except:
            pass
        return None

    def find_pet_name(self, log_file: Path, player_name: str) -> Optional[str]:
        """Find the pet name for this player in the combat log."""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 1000:
                        break
                        
                    if 'SPELL_SUMMON' in line:
                        parts = line.strip().split(',')
                        if len(parts) >= 7:
                            src = parts[2].strip('"').split('-', 1)[0]
                            pet_candidate = parts[6].strip('"')
                            if src == player_name:
                                return pet_candidate
        except Exception as e:
            pass
        return None

    def parse_log_line_timestamp(self, line: str) -> Optional[datetime]:
        """Parse timestamp from a combat log line."""
        try:
            parts = line.strip().split(None, 2)
            if len(parts) < 2:
                return None

            # Get full timestamp "1/2/2025 18:04:33.345-5"
            full_timestamp = f"{parts[0]} {parts[1]}"
            
            # Remove timezone offset
            timestamp_clean = full_timestamp.split('-')[0].strip()
            
            # Parse the timestamp
            try:
                result = datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S.%f")
                return result
            except ValueError:
                result = datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S")
                return result
                
        except Exception as e:
            return None

    def debug_process_combat_event(self, line: str, player_name: str, pet_name: Optional[str], 
                                   features: Dict, event_time: datetime) -> str:
        """Process a single combat log event and update feature counters."""
        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                return "invalid_format"

            # Get event type
            first_part = parts[0]
            event_type = first_part.split()[-1] if ' ' in first_part else first_part

            # Control debug output
            debug_count = (features['cast_success_own'] + features['interrupt_success_own'] + 
                          features['purges_own'] + features['times_interrupted'])
            show_debug = debug_count < 10

            # 1. SPELL_DISPEL events (Pet Purges)
            if event_type == 'SPELL_DISPEL' and len(parts) >= 13:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')
                
                if pet_name and src == pet_name and spell_name == "Devour Magic":
                    purged_aura = parts[12].strip('"')
                    features['purges_own'] += 1
                    features['spells_purged'].append(purged_aura)
                    
                    if show_debug:
                        print(f"      🔥 PET PURGE at {event_time}: {src} dispelled '{purged_aura}' with {spell_name}")
                    return "purge"

            # 2. Cast success events
            elif event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')
                
                if src == player_name:
                    features['cast_success_own'] += 1
                    features['spells_cast'].append(spell_name)
                    
                    if show_debug:
                        print(f"      ✅ PLAYER CAST at {event_time}: {src} cast '{spell_name}'")
                    return "cast_success"
                elif pet_name and src == pet_name:
                    if show_debug:
                        print(f"      ⚪ Pet cast ignored at {event_time}: {src} cast '{spell_name}'")
                    return "pet_cast_ignored"

            # 3. Interrupt events
            elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                dst = parts[6].strip('"').split('-', 1)[0]
                interrupt_spell = parts[10].strip('"')
                
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
                        print(f"      ✅ INTERRUPT SUCCESS at {event_time}: {actual_src} interrupted {actual_dst} with '{interrupt_spell}'")
                    return "interrupt_success"
                elif actual_dst == player_name:
                    features['times_interrupted'] += 1
                    if show_debug:
                        print(f"      ❌ GOT INTERRUPTED at {event_time}: {actual_dst} interrupted by {actual_src} using '{interrupt_spell}'")
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
            return "error"

    def setup_output_csv(self, output_csv: str):
        """Set up the output CSV file with headers."""
        if not os.path.exists(output_csv):
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'filename', 'match_start_time', 'cast_success_own', 'interrupt_success_own',
                    'times_interrupted', 'precog_gained_own', 'precog_gained_enemy', 'purges_own',
                    'damage_done', 'healing_done', 'deaths_caused', 'times_died',
                    'spells_cast', 'spells_purged'
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
