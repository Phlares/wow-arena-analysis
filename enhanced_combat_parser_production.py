#!/usr/bin/env python3
# enhanced_combat_parser_production.py - PRODUCTION VERSION with all fixes applied

import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
import re


class ProductionEnhancedCombatParser:
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
        Parse combat logs using enhanced timestamp matching with smart arena boundary detection.
        Production version that processes the full dataset efficiently.
        """
        print("🚀 Starting PRODUCTION Enhanced Combat Log Parsing")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"Output file: {output_csv}")

        # Load enhanced index with precise timestamps
        df = pd.read_csv(enhanced_index_csv)

        # Handle timestamp parsing robustly
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

        # Filter to only matches that have combat logs available (2025 onwards)
        df_with_logs = df[df['precise_start_time'] >= '2025-01-01']
        print(f"🗓️ Found {len(df_with_logs)} matches from 2025 onwards (when combat logs are available)")

        if len(df_with_logs) == 0:
            print("❌ No matches found with available combat logs!")
            return

        # Group matches by reliability for different processing strategies
        high_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'high']
        medium_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'medium']
        low_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'low']

        print(f"   High reliability: {len(high_reliability)} matches")
        print(f"   Medium reliability: {len(medium_reliability)} matches")
        print(f"   Low reliability: {len(low_reliability)} matches")

        # Prepare output CSV
        self.setup_output_csv(output_csv)

        # Get available combat logs
        log_files = list(Path(logs_dir).glob('*.txt'))
        log_files.sort()
        print(f"📁 Found {len(log_files)} combat log files")

        # Process each reliability group with appropriate time windows
        total_processed = 0

        # High reliability: tight time windows with smart arena detection
        if len(high_reliability) > 0:
            print(f"\n🎯 Processing HIGH reliability matches (±30s windows with smart arena detection)...")
            processed = self.process_matches_group(high_reliability, log_files, output_csv, time_window=30)
            total_processed += processed

        # Medium reliability: moderate time windows with smart arena detection
        if len(medium_reliability) > 0:
            print(f"\n⚡ Processing MEDIUM reliability matches (±2min windows with smart arena detection)...")
            processed = self.process_matches_group(medium_reliability, log_files, output_csv, time_window=120)
            total_processed += processed

        # Low reliability: wide time windows with smart arena detection
        if len(low_reliability) > 0:
            print(f"\n⚠️ Processing LOW reliability matches (±5min windows with smart arena detection)...")
            processed = self.process_matches_group(low_reliability, log_files, output_csv, time_window=300)
            total_processed += processed

        print(f"\n🎉 Production parsing complete!")
        print(f"📈 Total matches processed: {total_processed}/{len(df_with_logs)} (from 2025 onwards)")
        print(f"💾 Results saved to: {output_csv}")

        # Save final progress
        self.save_processed_logs()

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

    def process_matches_group(self, matches_df: pd.DataFrame, log_files: list, output_csv: str,
                              time_window: int) -> int:
        """Process a group of matches with the same reliability level."""
        processed_count = 0
        total_matches = len(matches_df)

        for idx, (_, match) in enumerate(matches_df.iterrows(), 1):
            if idx % 100 == 0 or idx == total_matches:
                print(f"   📊 Progress: {idx}/{total_matches} matches ({processed_count} processed)")

            try:
                # Find relevant combat log for this match
                relevant_log = self.find_combat_log_for_match(match, log_files)
                if not relevant_log:
                    continue

                # Skip if already processed this log (efficiency optimization)
                if str(relevant_log) in self.processed_logs:
                    continue

                # Extract combat features for this match with smart arena boundaries
                features = self.extract_combat_features_smart(match, relevant_log, time_window)
                if features:
                    self.write_features_to_csv(features, output_csv)
                    processed_count += 1
                    
                    # Brief progress update for successful matches
                    if processed_count % 50 == 0:
                        print(f"   ✅ Processed {processed_count} matches successfully")

                # Mark log as processed for efficiency
                self.processed_logs.add(str(relevant_log))

            except Exception as e:
                # Don't spam errors in production - log them to a file instead
                error_log = self.base_dir / "parsing_errors.log"
                with open(error_log, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now()}: Error processing {match['filename']}: {e}\n")
                continue

        return processed_count

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

        # Find logs that START before the match (positive time_diff means log is before match)
        valid_logs = []
        for log in candidate_logs:
            time_diff = log['time_diff_seconds']
            
            if time_diff > 0:  # Log starts before match
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
        except:
            pass
        return None

    def extract_combat_features_smart(self, match: pd.Series, log_file: Path, time_window: int) -> Optional[Dict]:
        """
        Extract combat features using smart arena boundary detection.
        This is the production version with all fixes applied.
        """
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)
        match_end = match_start + timedelta(seconds=match_duration)

        # Initial time window for arena searching
        buffer = timedelta(seconds=time_window)
        window_start = match_start - buffer
        window_end = match_end + buffer

        player_name = self.extract_player_name(match['filename'])
        if not player_name:
            return None

        # Initialize counters with enhanced features
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

        try:
            # PHASE 1: Smart arena boundary detection
            arena_start_time, arena_end_time = self.find_matching_arena_boundaries(
                log_file, window_start, window_end, match_start, match['filename'], match_duration
            )
            
            # Use precise arena boundaries if found, otherwise use original window
            if arena_start_time and arena_end_time:
                precise_start = arena_start_time
                precise_end = arena_end_time
            else:
                # Fallback to time window estimate
                precise_start = window_start
                precise_end = window_end
            
            # PHASE 2: Parse events within precise boundaries
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Parse timestamp from log line
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time:
                        continue

                    # Check if within our PRECISE match window
                    if precise_start <= event_time <= precise_end:
                        # Parse the combat event
                        self.process_combat_event_enhanced(line, player_name, pet_name, features)

            return features

        except Exception as e:
            return None

    def find_matching_arena_boundaries(self, log_file: Path, window_start: datetime, 
                                       window_end: datetime, video_start: datetime, 
                                       filename: str, video_duration: float = 300) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Smart arena boundary detection that finds the correct arena match."""
        # Extract expected arena info from filename
        expected_bracket, expected_map = self.extract_arena_info_from_filename(filename)
        
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
                            arena_events.append(('START', event_time, arena_info))
                    elif 'ARENA_MATCH_END' in line:
                        arena_events.append(('END', event_time, None))
        
        # Sort events by time
        arena_events.sort(key=lambda x: x[1])
        
        # Strategy 1: Look backward from video time
        recent_start = None
        for event_type, event_time, info in reversed(arena_events):
            if event_time <= video_start and event_type == 'START':
                if self.arena_info_matches(info, expected_bracket, expected_map):
                    recent_start = (event_time, info)
                    break
        
        # Strategy 2: Look forward if no backward match
        if not recent_start:
            for event_type, event_time, info in arena_events:
                if event_time >= video_start and event_type == 'START':
                    if self.arena_info_matches(info, expected_bracket, expected_map):
                        recent_start = (event_time, info)
                        break
        
        if not recent_start:
            return None, None
        
        # Find corresponding arena end
        start_time, start_info = recent_start
        
        # Special handling for Solo Shuffle (no ARENA_MATCH_END between rounds)
        if expected_bracket == 'Solo Shuffle':
            return self.find_solo_shuffle_boundaries(start_time, start_info, arena_events, video_duration)
        
        # Standard arena: find next ARENA_MATCH_END
        for event_type, event_time, info in arena_events:
            if event_time > start_time and event_type == 'END':
                return start_time, event_time
        
        return start_time, None

    def find_solo_shuffle_boundaries(self, start_time: datetime, start_info: Dict, 
                                     arena_events: list, video_duration: float) -> Tuple[datetime, Optional[datetime]]:
        """Find Solo Shuffle session boundaries by estimating from video duration."""
        # Estimate end time based on video duration
        estimated_end = start_time + timedelta(seconds=video_duration)
        return start_time, estimated_end

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
                    if line_num > 1000:  # Efficiency: don't search the entire log
                        break
                        
                    if 'SPELL_SUMMON' in line:
                        parts = line.strip().split(',')
                        if len(parts) >= 7:
                            src = parts[2].strip('"').split('-', 1)[0]
                            pet_candidate = parts[6].strip('"')
                            if src == player_name:
                                return pet_candidate
        except:
            pass
        return None

    def parse_log_line_timestamp(self, line: str) -> Optional[datetime]:
        """Parse timestamp from a combat log line - FIXED for correct format."""
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
                
        except:
            return None

    def process_combat_event_enhanced(self, line: str, player_name: str, pet_name: Optional[str], features: Dict):
        """Process a single combat log event with enhanced tracking - ALL FIXES APPLIED."""
        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                return

            # Get event type
            first_part = parts[0]
            event_type = first_part.split()[-1] if ' ' in first_part else first_part

            # 1. SPELL_DISPEL events (Pet Purges) - FIXED
            if event_type == 'SPELL_DISPEL' and len(parts) >= 13:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')
                
                if pet_name and src == pet_name and spell_name == "Devour Magic":
                    purged_aura = parts[12].strip('"')
                    features['purges_own'] += 1
                    features['spells_purged'].append(purged_aura)

            # 2. Cast success events - FIXED (only count player casts, not pet)
            elif event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')
                
                if src == player_name:  # Only player casts, not pet
                    features['cast_success_own'] += 1
                    features['spells_cast'].append(spell_name)

            # 3. Interrupt events - FIXED
            elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                dst = parts[6].strip('"').split('-', 1)[0]
                
                # Treat pet as player for interrupts
                actual_src = src
                actual_dst = dst
                if pet_name and src == pet_name:
                    actual_src = player_name
                if pet_name and dst == pet_name:
                    actual_dst = player_name

                if actual_src == player_name:
                    features['interrupt_success_own'] += 1
                elif actual_dst == player_name:
                    features['times_interrupted'] += 1

            # 4. Precognition aura applications
            elif event_type == 'SPELL_AURA_APPLIED' and len(parts) >= 11:
                dst = parts[6].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                if spell_name == 'Precognition':
                    if dst == player_name:
                        features['precog_gained_own'] += 1
                    else:
                        features['precog_gained_enemy'] += 1

            # 5. Death events
            elif event_type == 'UNIT_DIED' and len(parts) >= 7:
                died_unit = parts[6].strip('"').split('-', 1)[0]
                if died_unit == player_name:
                    features['times_died'] += 1

        except:
            # Skip malformed lines silently in production
            pass

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
    """Main function to run production combat parsing."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/match_features_enhanced.csv"

    parser = ProductionEnhancedCombatParser(base_dir)
    parser.parse_enhanced_matches(enhanced_index, logs_dir, output_csv)


if __name__ == '__main__':
    main()
