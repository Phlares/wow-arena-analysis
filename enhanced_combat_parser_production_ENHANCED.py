#!/usr/bin/env python3
# enhanced_combat_parser_production_ENHANCED.py - PRODUCTION VERSION with death correlation

import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, Set, Optional, Tuple, List
import re


class EnhancedProductionCombatParser:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.processed_logs = set()
        self.processed_file = self.base_dir / "parsed_logs_enhanced.json"
        
        # Load pet index for comprehensive pet detection
        self.pet_index = self.load_pet_index()
        self.load_processed_logs()

    def load_pet_index(self) -> Dict:
        """Load the comprehensive pet index."""
        index_file = self.base_dir / "player_pet_index.json"

        if not index_file.exists():
            print("❌ Pet index not found! Run pet_index_builder.py first.")
            return {'player_pets': {}, 'pet_lookup': {}}

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                pet_index = json.load(f)
                print(f"✅ Loaded pet index with {len(pet_index['player_pets'])} players")
                return pet_index
        except Exception as e:
            print(f"❌ Error loading pet index: {e}")
            return {'player_pets': {}, 'pet_lookup': {}}

    def get_player_pets(self, player_name: str) -> List[str]:
        """Get all known pets for a specific player from the index."""
        return self.pet_index.get('player_pets', {}).get(player_name, {}).get('pet_names', [])

    def is_player_pet(self, potential_pet_name: str, player_name: str) -> bool:
        """Check if a potential pet name belongs to the specified player."""
        player_pets = self.get_player_pets(player_name)

        # Direct match
        if potential_pet_name in player_pets:
            return True

        # Partial match (pet names can have suffixes like "Felhunter-1234")
        base_pet_name = potential_pet_name.split('-')[0] if '-' in potential_pet_name else potential_pet_name
        for known_pet in player_pets:
            known_base = known_pet.split('-')[0] if '-' in known_pet else known_pet
            if base_pet_name == known_base:
                return True

        return False

    def load_processed_logs(self):
        """Load list of already processed combat logs."""
        if self.processed_file.exists():
            with open(self.processed_file, 'r', encoding='utf-8') as f:
                self.processed_logs = set(json.load(f))

    def save_processed_logs(self):
        """Save list of processed combat logs."""
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.processed_logs), f)

    def parse_enhanced_matches_selective(self, enhanced_index_csv: str, logs_dir: str, output_csv: str):
        """Selectively re-process matches with zero interrupts and continue with unparsed matches."""
        print("🚀 Starting SELECTIVE Re-processing and Continuation")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"Output file: {output_csv}")
        print(f"Pet index players: {len(self.pet_index.get('player_pets', {}))}")

        # Load enhanced index
        index_df = pd.read_csv(enhanced_index_csv)
        index_df = self._clean_timestamps_in_df(index_df)
        
        # Filter to 2025+ matches
        index_df = index_df[index_df['precise_start_time'] >= '2025-01-01'].copy()
        index_df = index_df.sort_values('precise_start_time').reset_index(drop=True)
        print(f"📊 Total matches available for processing: {len(index_df)}")

        # Get combat logs
        log_files = list(Path(logs_dir).glob('*.txt'))
        print(f"📁 Found {len(log_files)} combat log files")

        # PHASE 1: Load existing results and re-process zero interrupt matches
        updated_count = 0
        if os.path.exists(output_csv):
            existing_df = pd.read_csv(output_csv)
            print(f"\n📊 PHASE 1: Re-processing existing matches with zero interrupts")
            print(f"   Loaded {len(existing_df)} existing match results")

            # Find matches with zero interrupts
            zero_interrupt_matches = existing_df[existing_df['interrupt_success_own'] == 0]
            print(f"   🎯 Found {len(zero_interrupt_matches)} matches with zero interrupts to re-process")

            if len(zero_interrupt_matches) > 0:
                for idx, (original_idx, match_result) in enumerate(zero_interrupt_matches.iterrows(), 1):
                    filename = match_result['filename']
                    
                    if idx % 10 == 0:
                        print(f"      📊 Progress: {idx}/{len(zero_interrupt_matches)} ({updated_count} updated)")

                    # Find corresponding match in index
                    index_match = index_df[index_df['filename'] == filename]
                    if index_match.empty:
                        continue

                    match_data = index_match.iloc[0]
                    
                    # Re-process with enhanced pet logic
                    relevant_log = self.find_combat_log_for_match(match_data, log_files)
                    if not relevant_log:
                        continue

                    # Determine time window based on reliability
                    reliability = match_data.get('matching_reliability', 'medium')
                    time_window = {'high': 30, 'medium': 120, 'low': 300}.get(reliability, 120)

                    # Extract features with enhanced pet detection
                    new_features = self.extract_combat_features_enhanced(match_data, relevant_log, time_window)
                    if not new_features:
                        continue

                    # Check if we found interrupts OR purges now
                    new_interrupts = new_features.get('interrupt_success_own', 0)
                    new_purges = new_features.get('purges_own', 0)
                    old_interrupts = match_result['interrupt_success_own']
                    old_purges = match_result['purges_own']

                    if new_interrupts > old_interrupts or new_purges > old_purges:
                        print(f"      ✅ UPDATED: {filename}")
                        print(f"         Interrupts: {old_interrupts} → {new_interrupts}")
                        print(f"         Purges: {old_purges} → {new_purges}")
                        
                        # Update the row in existing_df using .loc with the original index
                        for key, value in new_features.items():
                            if key in existing_df.columns:
                                if key in ['spells_cast', 'spells_purged']:
                                    existing_df.at[original_idx, key] = '; '.join(value) if value else ''
                                else:
                                    existing_df.at[original_idx, key] = value
                        
                        updated_count += 1

                # Save updated results after Phase 1
                if updated_count > 0:
                    existing_df.to_csv(output_csv, index=False)
                    print(f"   ✅ Phase 1 complete: Updated {updated_count} matches")
            else:
                print("   ✅ No zero-interrupt matches found to re-process")

        else:
            print(f"\n📊 PHASE 1: No existing CSV found - will create new one")
            existing_df = pd.DataFrame()

        # PHASE 2: Continue processing unparsed matches
        print(f"\n📊 PHASE 2: Processing remaining unparsed matches")
        
        # Find which matches are already processed
        if not existing_df.empty:
            processed_filenames = set(existing_df['filename'].tolist())
            remaining_matches = index_df[~index_df['filename'].isin(processed_filenames)]
        else:
            remaining_matches = index_df
            # Setup CSV if it doesn't exist
            self.setup_output_csv(output_csv)

        print(f"   📊 Found {len(remaining_matches)} matches to process")

        if len(remaining_matches) > 0:
            # Group by reliability for processing
            high_reliability = remaining_matches[remaining_matches['matching_reliability'] == 'high']
            medium_reliability = remaining_matches[remaining_matches['matching_reliability'] == 'medium']
            low_reliability = remaining_matches[remaining_matches['matching_reliability'] == 'low']

            print(f"      High reliability: {len(high_reliability)} matches")
            print(f"      Medium reliability: {len(medium_reliability)} matches")
            print(f"      Low reliability: {len(low_reliability)} matches")

            new_processed = 0
            if len(high_reliability) > 0:
                print(f"\n   🎯 Processing HIGH reliability matches...")
                processed = self.process_matches_group(high_reliability, log_files, output_csv, time_window=30)
                new_processed += processed

            if len(medium_reliability) > 0:
                print(f"\n   ⚡ Processing MEDIUM reliability matches...")
                processed = self.process_matches_group(medium_reliability, log_files, output_csv, time_window=120)
                new_processed += processed

            if len(low_reliability) > 0:
                print(f"\n   ⚠️ Processing LOW reliability matches...")
                processed = self.process_matches_group(low_reliability, log_files, output_csv, time_window=300)
                new_processed += processed

            print(f"   ✅ Phase 2 complete: Processed {new_processed} new matches")
        else:
            print("   ✅ All matches already processed")

        print(f"\n🎉 Selective processing complete!")
        print(f"📈 Re-processed matches: {updated_count}")
        if len(remaining_matches) > 0:
            print(f"📈 New matches processed: {new_processed if 'new_processed' in locals() else 0}")
        print(f"💾 Results saved to: {output_csv}")

    def _clean_timestamps_in_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean timestamps in dataframe."""
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
        except ValueError:
            try:
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
            except ValueError:
                df['precise_start_time'] = df['precise_start_time'].apply(self._clean_timestamp)
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])
        return df

    def parse_enhanced_matches(self, enhanced_index_csv: str, logs_dir: str, output_csv: str,
                               force_rebuild: bool = True):
        """Parse combat logs using enhanced timestamp matching with smart arena boundary detection."""
        print("🚀 Starting ENHANCED Production Combat Log Parsing")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"Output file: {output_csv}")

        # FORCE REBUILD: Delete existing files to start fresh
        if force_rebuild:
            print("🔄 Force rebuild enabled - clearing existing data")
            if os.path.exists(output_csv):
                os.remove(output_csv)
                print(f"   Deleted existing CSV: {output_csv}")
            if self.processed_file.exists():
                self.processed_file.unlink()
                print(f"   Deleted existing processed log: {self.processed_file}")
            self.processed_logs = set()

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

        # Group matches by reliability
        high_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'high']
        medium_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'medium']
        low_reliability = df_with_logs[df_with_logs['matching_reliability'] == 'low']

        print(f"   High reliability: {len(high_reliability)} matches")
        print(f"   Medium reliability: {len(medium_reliability)} matches")
        print(f"   Low reliability: {len(low_reliability)} matches")

        # Prepare output CSV with COMPLETE schema
        self.setup_output_csv(output_csv)

        # Get available combat logs
        log_files = list(Path(logs_dir).glob('*.txt'))
        log_files.sort()
        print(f"📁 Found {len(log_files)} combat log files")

        # Process each reliability group
        total_processed = 0

        if len(high_reliability) > 0:
            print(f"\n🎯 Processing HIGH reliability matches...")
            processed = self.process_matches_group(high_reliability, log_files, output_csv, time_window=30)
            total_processed += processed

        if len(medium_reliability) > 0:
            print(f"\n⚡ Processing MEDIUM reliability matches...")
            processed = self.process_matches_group(medium_reliability, log_files, output_csv, time_window=120)
            total_processed += processed

        if len(low_reliability) > 0:
            print(f"\n⚠️ Processing LOW reliability matches...")
            processed = self.process_matches_group(low_reliability, log_files, output_csv, time_window=300)
            total_processed += processed

        print(f"\n🎉 Enhanced production parsing complete!")
        print(f"📈 Total matches processed: {total_processed}/{len(df_with_logs)}")
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
            if idx % 50 == 0 or idx == total_matches:
                print(f"   📊 Progress: {idx}/{total_matches} matches ({processed_count} processed)")

            try:
                relevant_log = self.find_combat_log_for_match(match, log_files)
                if not relevant_log:
                    continue

                match_id = f"{relevant_log}_{match['filename']}"
                if match_id in self.processed_logs:
                    continue

                features = self.extract_combat_features_enhanced(match, relevant_log, time_window)
                if features:
                    self.write_features_to_csv(features, output_csv)
                    processed_count += 1

                self.processed_logs.add(match_id)

            except Exception as e:
                error_log = self.base_dir / "parsing_errors.log"
                with open(error_log, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now()}: Error processing {match['filename']}: {e}\n")
                continue

        return processed_count

    def find_combat_log_for_match(self, match: pd.Series, log_files: list) -> Optional[Path]:
        """Find the combat log file that contains this match."""
        match_time = match['precise_start_time']
        match_date = match_time.date()

        candidate_logs = []
        for log_file in log_files:
            log_info = self.parse_log_info_from_filename(log_file.name)
            if log_info:
                log_date, log_time = log_info
                days_diff = abs((match_date - log_date).days)

                if days_diff <= 1:
                    log_datetime = datetime.combine(log_date, log_time)
                    time_diff_seconds = (match_time - log_datetime).total_seconds()
                    candidate_logs.append({'file': log_file, 'time_diff_seconds': time_diff_seconds})

        if not candidate_logs:
            return None

        valid_logs = [log for log in candidate_logs
                      if log['time_diff_seconds'] > 0 or abs(log['time_diff_seconds']) <= 600]

        if not valid_logs:
            return None

        valid_logs.sort(key=lambda x: abs(x['time_diff_seconds']))
        return valid_logs[0]['file']

    def parse_log_info_from_filename(self, log_filename: str) -> Optional[Tuple[datetime.date, datetime.time]]:
        """Extract date and time from combat log filename."""
        try:
            match = re.search(r'(\d{6})_(\d{6})', log_filename)
            if match:
                date_str, time_str = match.groups()
                month = int(date_str[:2])
                day = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                log_date = datetime(year, month, day).date()

                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                log_time = time(hour, minute, second)

                return log_date, log_time
        except:
            pass
        return None

    def extract_combat_features_enhanced(self, match: pd.Series, log_file: Path, time_window: int) -> Optional[Dict]:
        """Extract combat features using enhanced arena boundary detection with death correlation."""
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)
        player_name = self.extract_player_name(match['filename'])

        if not player_name:
            return None

        # Initialize features with COMPLETE schema
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

        pet_name = self.find_pet_name(log_file, player_name)

        try:
            # Enhanced arena boundary detection with verification
            buffer = timedelta(seconds=time_window)
            window_start = match_start - buffer
            window_end = match_start + timedelta(seconds=match_duration) + buffer

            arena_start, arena_end = self.find_verified_arena_boundaries(
                log_file, window_start, window_end, match_start, match['filename'], match_duration
            )

            precise_start = arena_start if arena_start else window_start
            precise_end = arena_end if arena_end else window_end

            # Parse events within precise boundaries
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time:
                        continue

                    if precise_start <= event_time <= precise_end:
                        self.process_combat_event_enhanced(line, player_name, pet_name, features)

            return features

        except Exception as e:
            return None

    def find_verified_arena_boundaries(self, log_file: Path, window_start: datetime, window_end: datetime,
                                       video_start: datetime, filename: str, video_duration: float) -> Tuple[
        Optional[datetime], Optional[datetime]]:
        """Find arena match boundaries using enhanced detection WITH death correlation verification."""
        expected_bracket, expected_map = self.extract_arena_info_from_filename(filename)

        # Load JSON death data for verification
        death_data = self.load_death_data_from_json(filename)

        arena_events = []
        extended_start = window_start - timedelta(minutes=10)
        extended_end = window_end + timedelta(minutes=10)

        # Collect all arena events in extended window
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                event_time = self.parse_log_line_timestamp(line)
                if not event_time or not (extended_start <= event_time <= extended_end):
                    continue

                if 'ARENA_MATCH_START' in line:
                    arena_info = self.parse_arena_start_line(line, event_time)
                    if arena_info:
                        arena_events.append(('START', event_time, arena_info))
                elif 'ARENA_MATCH_END' in line:
                    arena_events.append(('END', event_time, None))

        arena_events.sort(key=lambda x: x[1])

        # Find ALL matching arena start candidates
        matching_starts = []
        for event_type, event_time, info in arena_events:
            if event_type == 'START' and self.arena_info_matches(info, expected_bracket, expected_map):
                # Find corresponding end
                arena_end = None
                for end_type, end_time, _ in arena_events:
                    if end_type == 'END' and end_time > event_time:
                        arena_end = end_time
                        break

                if arena_end:
                    duration = (arena_end - event_time).total_seconds()
                    matching_starts.append({
                        'start': event_time,
                        'end': arena_end,
                        'duration': duration,
                        'time_diff_to_video': abs((event_time - video_start).total_seconds())
                    })

        if not matching_starts:
            return None, None

        # If only one match, use it
        if len(matching_starts) == 1:
            best_match = matching_starts[0]
            return best_match['start'], best_match['end']

        # Multiple matches - use enhanced verification
        print(f"   🔍 Found {len(matching_starts)} potential arena matches for {filename}")

        # Strategy 1: Death correlation verification (most reliable)
        if death_data:
            verified_match = self.verify_match_with_death_correlation(
                matching_starts, death_data, log_file, expected_bracket, expected_map
            )
            if verified_match:
                print(f"   ✅ Death correlation verified match")
                return verified_match['start'], verified_match['end']

        # Strategy 2: Duration-based verification
        expected_duration = video_duration
        duration_verified = self.verify_match_with_duration(matching_starts, expected_duration)
        if duration_verified:
            print(f"   ✅ Duration verified match")
            return duration_verified['start'], duration_verified['end']

        # Strategy 3: Time proximity (fallback)
        closest_match = min(matching_starts, key=lambda x: x['time_diff_to_video'])
        print(f"   ⚠️ Using closest match by time (±{closest_match['time_diff_to_video']:.0f}s)")
        return closest_match['start'], closest_match['end']

    def load_death_data_from_json(self, filename: str) -> Optional[Dict]:
        """Load death data from corresponding JSON file for verification."""
        try:
            json_name = filename.rsplit('.', 1)[0] + '.json'

            # Try date-organized subdirectory first
            try:
                date_part = filename.split('_', 1)[0]  # YYYY-MM-DD
                year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
                json_path = self.base_dir / year_month / json_name
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return self.extract_death_info(data)
            except:
                pass

            # Try root directory
            json_path = self.base_dir / json_name
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return self.extract_death_info(data)

        except Exception as e:
            pass
        return None

    def extract_death_info(self, json_data: dict) -> Dict:
        """Extract death information from JSON data."""
        death_info = {
            'player_deaths': 0,
            'enemy_deaths': 0,
            'total_deaths': 0
        }

        try:
            # Extract from combatants if available
            if 'combatants' in json_data:
                for combatant in json_data['combatants']:
                    if 'deathCount' in combatant:
                        deaths = combatant.get('deathCount', 0)
                        death_info['total_deaths'] += deaths

                        # Try to identify if player or enemy
                        player_name = json_data.get('player', {}).get('_name', '')
                        if combatant.get('_name', '') == player_name:
                            death_info['player_deaths'] = deaths
                        else:
                            death_info['enemy_deaths'] += deaths

        except Exception as e:
            pass

        return death_info

    def verify_match_with_death_correlation(self, matching_starts: List[Dict], death_data: Dict,
                                            log_file: Path, expected_bracket: str, expected_map: str) -> Optional[Dict]:
        """Verify arena match using death correlation between JSON and combat log."""
        if not death_data or death_data['total_deaths'] == 0:
            return None

        player_name = self.extract_player_name_from_combat_log(log_file)
        if not player_name:
            return None

        best_match = None
        best_correlation = -1

        for match_candidate in matching_starts:
            try:
                # Count deaths in this arena match window
                combat_deaths = self.count_deaths_in_arena_window(
                    log_file, match_candidate['start'], match_candidate['end'], player_name
                )

                # Calculate correlation score
                json_total = death_data['total_deaths']
                combat_total = combat_deaths['total_deaths']

                if json_total > 0 and combat_total > 0:
                    # Simple correlation: how close are the death counts?
                    correlation = 1.0 - abs(json_total - combat_total) / max(json_total, combat_total)

                    if correlation > best_correlation and correlation > 0.5:  # At least 50% correlation
                        best_correlation = correlation
                        best_match = match_candidate

            except Exception as e:
                continue

        return best_match

    def count_deaths_in_arena_window(self, log_file: Path, start_time: datetime, end_time: datetime,
                                     player_name: str) -> Dict:
        """Count deaths within a specific arena time window."""
        death_counts = {
            'player_deaths': 0,
            'enemy_deaths': 0,
            'total_deaths': 0
        }

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time or not (start_time <= event_time <= end_time):
                        continue

                    if 'UNIT_DIED' in line:
                        parts = line.strip().split(',')
                        if len(parts) >= 7:
                            died_unit = parts[6].strip('"').split('-', 1)[0]
                            death_counts['total_deaths'] += 1

                            if died_unit == player_name:
                                death_counts['player_deaths'] += 1
                            else:
                                death_counts['enemy_deaths'] += 1

        except Exception as e:
            pass

        return death_counts

    def extract_player_name_from_combat_log(self, log_file: Path) -> Optional[str]:
        """Extract player name from combat log (first player that appears)."""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 100:  # Check first 100 lines
                        break
                    if any(event in line for event in ['SPELL_CAST_SUCCESS', 'SPELL_AURA_APPLIED']):
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            src = parts[2].strip('"').split('-', 1)[0]
                            if src and len(src) > 2:  # Basic name validation
                                return src
        except:
            pass
        return None

    def verify_match_with_duration(self, matching_starts: List[Dict], expected_duration: float) -> Optional[Dict]:
        """Verify arena match using duration comparison."""
        best_match = None
        smallest_duration_diff = float('inf')

        for match_candidate in matching_starts:
            duration_diff = abs(match_candidate['duration'] - expected_duration)

            # Allow up to 60 seconds difference (arena matches can vary)
            if duration_diff <= 60 and duration_diff < smallest_duration_diff:
                smallest_duration_diff = duration_diff
                best_match = match_candidate

        return best_match

    def extract_arena_info_from_filename(self, filename: str) -> Tuple[str, str]:
        """Extract bracket type and map name from video filename."""
        try:
            parts = filename.split('_-_')
            if len(parts) >= 3:
                bracket_map_result = parts[2]

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
                    '980': "Tol'viron", '1552': "Ashamane's Fall", '2759': "Cage of Carnage",
                    '1504': "Black Rook", '2167': "Robodrome", '2563': "Nokhudon",
                    '1911': "Mugambala", '2373': "Empyrean Domain", '1134': "Tiger's Peak",
                    '1505': "Nagrand", '1825': "Hook Point", '2509': "Maldraxxus",
                    '572': "Ruins of Lordaeron", '617': "Dalaran Sewers", '2547': "Enigma Crucible"
                }

                arena_map = zone_map.get(zone_id, f'Zone_{zone_id}')
                return {'zone_id': zone_id, 'bracket': bracket, 'map': arena_map, 'time': event_time}
        except:
            pass
        return None

    def arena_info_matches(self, arena_info: Dict, expected_bracket: str, expected_map: str) -> bool:
        """Check if arena info matches expected values from filename."""
        if not arena_info:
            return False

        combat_bracket = arena_info['bracket']
        bracket_match = False

        if expected_bracket == 'Solo Shuffle':
            bracket_match = combat_bracket in ['Solo Shuffle', 'Rated Solo Shuffle']
        elif expected_bracket == 'Skirmish':
            bracket_match = combat_bracket in ['2v2', '3v3', 'Skirmish']
        else:
            bracket_match = combat_bracket == expected_bracket

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
        except:
            pass
        return None

    def parse_log_line_timestamp(self, line: str) -> Optional[datetime]:
        """Parse timestamp from a combat log line."""
        try:
            parts = line.strip().split(None, 2)
            if len(parts) < 2:
                return None

            full_timestamp = f"{parts[0]} {parts[1]}"
            timestamp_clean = full_timestamp.split('-')[0].strip()

            try:
                return datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S.%f")
            except ValueError:
                return datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S")
        except:
            return None

    def process_combat_event_enhanced(self, line: str, player_name: str, pet_name: Optional[str], features: Dict):
        """Process a single combat log event with enhanced pet index tracking."""
        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                return

            first_part = parts[0]
            event_type = first_part.split()[-1] if ' ' in first_part else first_part

            # SPELL_DISPEL events (Pet Purges) - USE PET INDEX
            if event_type == 'SPELL_DISPEL' and len(parts) >= 13:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                # Check if source is any of the player's known pets using pet index
                if spell_name == "Devour Magic" and self.is_player_pet(src, player_name):
                    purged_aura = parts[12].strip('"')
                    features['purges_own'] += 1
                    features['spells_purged'].append(purged_aura)

            # Cast success events - Only count player casts (not pets)
            elif event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                if src == player_name:
                    features['cast_success_own'] += 1
                    features['spells_cast'].append(spell_name)

            # Interrupt events - CHECK FOR BOTH PLAYER AND PET INTERRUPTS
            elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                dst = parts[6].strip('"').split('-', 1)[0]

                # Check if interrupt source is player OR any of their pets
                interrupt_by_player = (src == player_name)
                interrupt_by_pet = self.is_player_pet(src, player_name)
                interrupted_player = (dst == player_name)
                interrupted_pet = self.is_player_pet(dst, player_name)

                if interrupt_by_player or interrupt_by_pet:
                    features['interrupt_success_own'] += 1
                elif interrupted_player or interrupted_pet:
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

        except:
            pass

    def setup_output_csv(self, output_csv: str):
        """Set up the output CSV file with complete headers including purges_own."""
        if os.path.exists(output_csv):
            os.remove(output_csv)
            print(f"   🗑️ Deleted existing CSV file for clean rebuild")

        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'match_start_time', 'cast_success_own', 'interrupt_success_own',
                'times_interrupted', 'precog_gained_own', 'precog_gained_enemy', 'purges_own',
                'damage_done', 'healing_done', 'deaths_caused', 'times_died',
                'spells_cast', 'spells_purged'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            print(f"   ✅ Created new CSV with complete schema: {len(fieldnames)} columns")

    def write_features_to_csv(self, features: Dict, output_csv: str):
        """Write extracted features to the output CSV."""
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            features_for_csv = features.copy()
            features_for_csv['spells_cast'] = '; '.join(features['spells_cast']) if features['spells_cast'] else ''
            features_for_csv['spells_purged'] = '; '.join(features['spells_purged']) if features[
                'spells_purged'] else ''

            fieldnames = [
                'filename', 'match_start_time', 'cast_success_own', 'interrupt_success_own',
                'times_interrupted', 'precog_gained_own', 'precog_gained_enemy', 'purges_own',
                'damage_done', 'healing_done', 'deaths_caused', 'times_died',
                'spells_cast', 'spells_purged'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(features_for_csv)


def main():
    """Main function to run enhanced production combat parsing."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/match_features_enhanced_VERIFIED.csv"

    parser = EnhancedProductionCombatParser(base_dir)
    # CRITICAL: Force rebuild with enhanced verification
    parser.parse_enhanced_matches(enhanced_index, logs_dir, output_csv, force_rebuild=True)