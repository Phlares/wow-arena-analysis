#!/usr/bin/env python3
# improved_timestamp_matcher.py

import os
import json
import re
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Tuple, Dict, List
from pathlib import Path


class TimestampMatcher:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.cache = {}  # Cache parsed JSON timestamps

    def get_precise_match_time(self, video_filename: str, combat_log_path: Optional[str] = None) -> Tuple[
        datetime, Dict]:
        """
        Get precise match start time using the most reliable method available.

        Returns:
            Tuple[datetime, Dict]: (match_start_time, metadata)
        """
        json_path = self._find_json_file(video_filename)
        if not json_path:
            raise FileNotFoundError(f"No JSON file found for {video_filename}")

        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Method 1: Use 'start' timestamp (new format, most reliable)
        if 'start' in json_data:
            start_ms = json_data['start']
            start_time = datetime.fromtimestamp(start_ms / 1000.0)
            return start_time, {
                'method': 'json_start_field',
                'reliability': 'high',
                'source': 'JSON start timestamp',
                'json_path': str(json_path)
            }

        # Method 2: Parse combat log for match start (old format)
        if combat_log_path:
            try:
                start_time, validation = self._parse_combat_log_for_match(json_data, combat_log_path)
                return start_time, {
                    'method': 'combat_log_parsing',
                    'reliability': 'medium',
                    'source': 'Combat log ARENA_MATCH_START',
                    'validation': validation,
                    'json_path': str(json_path)
                }
            except Exception as e:
                print(f"Combat log parsing failed: {e}")

        # Method 3: Estimate from filename (least reliable)
        estimated_time = self._estimate_from_filename(video_filename)
        return estimated_time, {
            'method': 'filename_estimation',
            'reliability': 'low',
            'source': 'Filename timestamp estimation',
            'warning': 'This method can be off by 5-10 minutes',
            'json_path': str(json_path)
        }

    def _find_json_file(self, video_filename: str) -> Optional[Path]:
        """Find the corresponding JSON file for a video file."""
        json_name = video_filename.rsplit('.', 1)[0] + '.json'

        # Method 1: Try in date-organized subdirectory
        try:
            date_part = video_filename.split('_', 1)[0]  # YYYY-MM-DD
            year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
            json_path = self.base_dir / year_month / json_name
            if json_path.exists():
                return json_path
        except (IndexError, ValueError):
            pass

        # Method 2: Try in root directory
        json_path = self.base_dir / json_name
        if json_path.exists():
            return json_path

        # Method 3: Search recursively (slower but thorough)
        for json_file in self.base_dir.rglob(json_name):
            return json_file

        return None

    def _parse_combat_log_for_match(self, json_data: dict, combat_log_path: str) -> Tuple[datetime, Dict]:
        """
        Parse combat log to find match start time by looking for ARENA_MATCH_START events.
        """
        target_zone_id = str(json_data['zoneID'])
        target_player = json_data['player']['_name']

        # Extract log date from filename (WoWCombatLog-MMDDYY_HHMMSS.txt)
        log_filename = os.path.basename(combat_log_path)
        date_match = re.search(r'(\d{6})_\d{6}', log_filename)
        if not date_match:
            raise ValueError(f"Cannot parse date from log filename: {log_filename}")

        date_str = date_match.group(1)  # MMDDYY
        month = int(date_str[:2])
        day = int(date_str[2:4])
        year = 2000 + int(date_str[4:6])
        log_date = datetime(year, month, day)

        # Look for relevant events in the combat log
        arena_events = []
        player_found = False

        with open(combat_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Quick validation: check if our player appears in the first 100 lines
                if line_num <= 100 and not player_found:
                    if target_player in line:
                        player_found = True

                # Look for ARENA_MATCH_START events
                if 'ARENA_MATCH_START' in line:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        time_part = parts[1].strip()
                        zone_id = parts[2].strip().strip('"')

                        if zone_id == target_zone_id:
                            # Parse timestamp: "4/18 21:17:28.000"
                            try:
                                time_clean = time_part.split('-', 1)[0]  # Remove any suffixes
                                # Combine log date with time
                                match_datetime = datetime.strptime(f"{year} {time_clean}", "%Y %m/%d %H:%M:%S.%f")
                                arena_events.append({
                                    'time': match_datetime,
                                    'zone_id': zone_id,
                                    'line_num': line_num
                                })
                            except ValueError as e:
                                continue

                # Stop searching after reasonable number of lines (performance)
                if line_num > 10000:
                    break

        if not player_found:
            raise ValueError(f"Player {target_player} not found in combat log")

        if not arena_events:
            raise ValueError(f"No ARENA_MATCH_START events found for zone {target_zone_id}")

        # Return the first matching event (there should typically be only one)
        best_match = arena_events[0]
        validation = {
            'player_validated': player_found,
            'zone_id_match': best_match['zone_id'] == target_zone_id,
            'events_found': len(arena_events),
            'line_number': best_match['line_num']
        }

        return best_match['time'], validation

    def _estimate_from_filename(self, video_filename: str) -> datetime:
        """
        Extract timestamp from filename as fallback method.
        Format: YYYY-MM-DD_HH-MM-SS_...
        """
        try:
            # Parse the first part: YYYY-MM-DD_HH-MM-SS
            parts = video_filename.split('_')
            date_part = parts[0]  # YYYY-MM-DD
            time_part = parts[1]  # HH-MM-SS

            # Convert to datetime
            year, month, day = map(int, date_part.split('-'))
            hour, minute, second = map(int, time_part.split('-'))

            return datetime(year, month, day, hour, minute, second)
        except (IndexError, ValueError) as e:
            raise ValueError(f"Cannot parse timestamp from filename {video_filename}: {e}")


def match_videos_to_logs(master_index_csv: str, logs_dir: str, base_dir: str) -> pd.DataFrame:
    """
    Enhanced matching function that uses the new TimestampMatcher.
    """
    matcher = TimestampMatcher(base_dir)

    # Load the master index
    df = pd.read_csv(master_index_csv)

    # Add new columns for enhanced matching
    df['precise_start_time'] = None
    df['matching_method'] = None
    df['matching_reliability'] = None
    df['matching_metadata'] = None

    # Get available combat logs
    log_files = list(Path(logs_dir).glob('*.txt'))
    log_files.sort()

    success_count = 0
    for idx, row in df.iterrows():
        video_filename = row['filename']
        print(f"Processing {idx + 1}/{len(df)}: {video_filename}")

        try:
            # Find the most appropriate combat log file
            combat_log = find_relevant_combat_log(video_filename, log_files)

            # Get precise match time
            start_time, metadata = matcher.get_precise_match_time(video_filename, combat_log)

            # Update the dataframe
            df.at[idx, 'precise_start_time'] = start_time
            df.at[idx, 'matching_method'] = metadata['method']
            df.at[idx, 'matching_reliability'] = metadata['reliability']
            df.at[idx, 'matching_metadata'] = json.dumps(metadata)

            success_count += 1
            print(f"  ✅ Matched using {metadata['method']} (reliability: {metadata['reliability']})")

        except Exception as e:
            print(f"  ❌ Failed to match: {e}")
            df.at[idx, 'matching_metadata'] = json.dumps({'error': str(e)})

    print(f"\nMatching complete: {success_count}/{len(df)} videos successfully matched")

    # Save results
    output_path = Path(master_index_csv).parent / 'master_index_enhanced.csv'
    df.to_csv(output_path, index=False)
    print(f"Enhanced index saved to: {output_path}")

    return df


def find_relevant_combat_log(video_filename: str, log_files: List[Path]) -> Optional[str]:
    """
    Find the combat log file that's most likely to contain the match data.
    """
    try:
        # Extract date from video filename
        date_part = video_filename.split('_')[0]  # YYYY-MM-DD
        video_date = datetime.strptime(date_part, '%Y-%m-%d').date()

        # Find log files from the same day or nearby
        relevant_logs = []
        for log_file in log_files:
            # Parse log filename: WoWCombatLog-MMDDYY_HHMMSS.txt
            match = re.search(r'(\d{6})_\d{6}', log_file.name)
            if match:
                date_str = match.group(1)  # MMDDYY
                month = int(date_str[:2])
                day = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                log_date = datetime(year, month, day).date()

                # Check if log is from same day or within 1 day
                if abs((video_date - log_date).days) <= 1:
                    relevant_logs.append((log_file, abs((video_date - log_date).days)))

        if relevant_logs:
            # Return the closest log file
            relevant_logs.sort(key=lambda x: x[1])
            return str(relevant_logs[0][0])

    except Exception as e:
        print(f"Error finding relevant combat log for {video_filename}: {e}")

    return None


if __name__ == '__main__':
    # Example usage
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    logs_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches/Logs"
    master_index = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches/master_index.csv"

    # Test the matcher
    try:
        enhanced_df = match_videos_to_logs(master_index, logs_dir, base_dir)
        print("Enhanced matching completed successfully!")
    except Exception as e:
        print(f"Error: {e}")