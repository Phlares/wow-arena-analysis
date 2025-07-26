#!/usr/bin/env python3
# enhanced_combat_parser.py - FIXED VERSION

import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
import re


class EnhancedCombatParser:
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
        Parse combat logs using the enhanced timestamp matching.

        Args:
            enhanced_index_csv: Path to master_index_enhanced.csv
            logs_dir: Directory containing WoW combat logs
            output_csv: Output file for match features
        """
        print("🚀 Starting Enhanced Combat Log Parsing")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"Output file: {output_csv}")

        # Load enhanced index with precise timestamps
        df = pd.read_csv(enhanced_index_csv)

        # FIX: Handle timestamp parsing more robustly
        print("🔧 Parsing timestamps...")
        try:
            # Try ISO8601 format first (handles microseconds automatically)
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
        except ValueError:
            try:
                # Fallback: let pandas infer the format
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
            except ValueError:
                # Last resort: manual cleaning
                print("⚠️ Using manual timestamp cleaning...")
                df['precise_start_time'] = df['precise_start_time'].apply(self._clean_timestamp)
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

        print(f"📊 Loaded {len(df)} matches from enhanced index")

        # Group matches by reliability for different processing strategies
        high_reliability = df[df['matching_reliability'] == 'high']
        medium_reliability = df[df['matching_reliability'] == 'medium']
        low_reliability = df[df['matching_reliability'] == 'low']

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

        # High reliability: tight time windows (±30 seconds)
        if len(high_reliability) > 0:
            print(f"\n🎯 Processing HIGH reliability matches...")
            processed = self.process_matches_group(high_reliability, log_files, output_csv, time_window=30)
            total_processed += processed

        # Medium reliability: moderate time windows (±2 minutes)
        if len(medium_reliability) > 0:
            print(f"\n⚡ Processing MEDIUM reliability matches...")
            processed = self.process_matches_group(medium_reliability, log_files, output_csv, time_window=120)
            total_processed += processed

        # Low reliability: wide time windows (±5 minutes)
        if len(low_reliability) > 0:
            print(f"\n⚠️ Processing LOW reliability matches...")
            processed = self.process_matches_group(low_reliability, log_files, output_csv, time_window=300)
            total_processed += processed

        print(f"\n🎉 Enhanced parsing complete!")
        print(f"📈 Total matches processed: {total_processed}/{len(df)}")
        print(f"💾 Results saved to: {output_csv}")

    def _clean_timestamp(self, timestamp_str):
        """Clean timestamp string for parsing."""
        if pd.isna(timestamp_str):
            return timestamp_str

        # Convert to string if it isn't already
        ts = str(timestamp_str)

        # Handle common timestamp format issues
        # Remove any trailing/leading whitespace
        ts = ts.strip()

        # If it looks like it has microseconds, ensure proper format
        if '.' in ts and len(ts.split('.')[-1]) > 3:
            # Truncate microseconds to 6 digits max
            parts = ts.split('.')
            if len(parts) == 2:
                base, microsec = parts
                microsec = microsec[:6].ljust(6, '0')  # Pad or truncate to 6 digits
                ts = f"{base}.{microsec}"

        return ts

    def process_matches_group(self, matches_df: pd.DataFrame, log_files: list, output_csv: str,
                              time_window: int) -> int:
        """Process a group of matches with the same reliability level."""
        processed_count = 0

        for idx, match in matches_df.iterrows():
            try:
                # Find relevant combat log for this match
                relevant_log = self.find_combat_log_for_match(match, log_files)
                if not relevant_log:
                    print(f"   ⚠️ No combat log found for {match['filename']}")
                    continue

                # Skip if already processed this log
                if str(relevant_log) in self.processed_logs:
                    continue

                # Extract combat features for this match
                features = self.extract_combat_features(match, relevant_log, time_window)
                if features:
                    self.write_features_to_csv(features, output_csv)
                    processed_count += 1
                    print(
                        f"   ✅ {match['filename']} - Found {features['cast_success_own']} casts, {features['interrupt_success_own']} interrupts")

                # Mark log as processed
                self.processed_logs.add(str(relevant_log))

            except Exception as e:
                print(f"   ❌ Error processing {match['filename']}: {e}")
                continue

        # Save progress
        self.save_processed_logs()
        return processed_count

    def find_combat_log_for_match(self, match: pd.Series, log_files: list) -> Optional[Path]:
        """Find the combat log file that contains this match."""
        match_time = match['precise_start_time']
        match_date = match_time.date()

        # Find logs from the same day (or adjacent days for edge cases)
        relevant_logs = []
        for log_file in log_files:
            log_date = self.parse_log_date_from_filename(log_file.name)
            if log_date and abs((match_date - log_date).days) <= 1:
                relevant_logs.append(log_file)

        if not relevant_logs:
            return None

        # If multiple logs, pick the one most likely to contain the match
        # (for now, just return the first one - could be enhanced later)
        return relevant_logs[0]

    def parse_log_date_from_filename(self, log_filename: str) -> Optional:
        """Extract date from combat log filename: WoWCombatLog-MMDDYY_HHMMSS.txt"""
        try:
            match = re.search(r'(\d{6})_\d{6}', log_filename)
            if match:
                date_str = match.group(1)  # MMDDYY
                month = int(date_str[:2])
                day = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                return datetime(year, month, day).date()
        except:
            pass
        return None

    def extract_combat_features(self, match: pd.Series, log_file: Path, time_window: int) -> Optional[Dict]:
        """
        Extract combat features from the log file for a specific match.
        Uses precise timing to only look at events during the actual match.
        """
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)  # Default 5 min if unknown
        match_end = match_start + timedelta(seconds=match_duration)

        # Allow some buffer based on reliability
        buffer = timedelta(seconds=time_window)
        window_start = match_start - buffer
        window_end = match_end + buffer

        player_name = self.extract_player_name(match['filename'])
        if not player_name:
            return None

        # Initialize counters
        features = {
            'filename': match['filename'],
            'match_start_time': match_start.isoformat(),
            'cast_success_own': 0,
            'interrupt_success_own': 0,
            'times_interrupted': 0,
            'precog_gained_own': 0,
            'precog_gained_enemy': 0,
            'damage_done': 0,
            'healing_done': 0,
            'deaths_caused': 0,
            'times_died': 0
        }

        # Discover pet name for this player
        pet_name = self.find_pet_name(log_file, player_name)

        # Parse combat log events within the time window
        log_date = self.parse_log_date_from_filename(log_file.name)
        if not log_date:
            return None

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Parse timestamp from log line
                    event_time = self.parse_log_line_timestamp(line, log_date)
                    if not event_time:
                        continue

                    # Only process events within our match window
                    if not (window_start <= event_time <= window_end):
                        continue

                    # Parse the combat event
                    self.process_combat_event(line, player_name, pet_name, features)

            return features

        except Exception as e:
            print(f"Error parsing log file {log_file}: {e}")
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
                for line in f:
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

    def parse_log_line_timestamp(self, line: str, log_date: datetime.date) -> Optional[datetime]:
        """Parse timestamp from a combat log line."""
        try:
            parts = line.strip().split(None, 2)
            if len(parts) < 2:
                return None

            time_token = parts[1]
            time_clean = time_token.split('-', 1)[0]  # Remove any suffixes

            # Parse time: "4/18 21:17:28.000"
            time_obj = datetime.strptime(time_clean, "%m/%d %H:%M:%S.%f").time()
            return datetime.combine(log_date, time_obj)
        except:
            return None

    def process_combat_event(self, line: str, player_name: str, pet_name: Optional[str], features: Dict):
        """Process a single combat log event and update feature counters."""
        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                return

            event_type = parts[0].split()[-1]  # Last part after timestamp

            # Cast success events
            if event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 3:
                src = parts[2].strip('"').split('-', 1)[0]
                if src == player_name or src == pet_name:
                    features['cast_success_own'] += 1

            # Interrupt events
            elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 7:
                src = parts[2].strip('"').split('-', 1)[0]
                dst = parts[6].strip('"').split('-', 1)[0]

                # Treat pet as player for both source and destination
                if src == pet_name:
                    src = player_name
                if dst == pet_name:
                    dst = player_name

                if src == player_name:
                    features['interrupt_success_own'] += 1
                elif dst == player_name:
                    features['times_interrupted'] += 1

            # Precognition aura applications
            elif event_type == 'SPELL_AURA_APPLIED' and len(parts) >= 11:
                dst = parts[6].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                if spell_name == 'Precognition':
                    if dst == player_name:
                        features['precog_gained_own'] += 1
                    else:
                        features['precog_gained_enemy'] += 1

            # Death events
            elif event_type == 'UNIT_DIED' and len(parts) >= 7:
                died_unit = parts[6].strip('"').split('-', 1)[0]
                if died_unit == player_name:
                    features['times_died'] += 1
                else:
                    # Could be enhanced to track if we caused the death
                    features['deaths_caused'] += 1

        except Exception as e:
            # Skip malformed lines
            pass

    def setup_output_csv(self, output_csv: str):
        """Set up the output CSV file with headers."""
        if not os.path.exists(output_csv):
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'filename', 'match_start_time', 'cast_success_own', 'interrupt_success_own',
                    'times_interrupted', 'precog_gained_own', 'precog_gained_enemy',
                    'damage_done', 'healing_done', 'deaths_caused', 'times_died'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

    def write_features_to_csv(self, features: Dict, output_csv: str):
        """Write extracted features to the output CSV."""
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            fieldnames = list(features.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(features)


def main():
    """Main function to run enhanced combat parsing."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/match_features_enhanced.csv"

    parser = EnhancedCombatParser(base_dir)
    parser.parse_enhanced_matches(enhanced_index, logs_dir, output_csv)


if __name__ == '__main__':
    main()