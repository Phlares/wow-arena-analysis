#!/usr/bin/env python3
# debug_enhanced_parser_with_detailed_logging.py - Debug parser with line-by-line event logging

import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, Set, Optional, Tuple, List
import re


class DebugEnhancedCombatParserWithDetailedLogging:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.processed_logs = set()
        self.processed_file = self.base_dir / "parsed_logs_enhanced.json"

        # Load pet index
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

    def debug_process_single_match(self, match: pd.Series, log_file: Path) -> Optional[Dict]:
        """Debug process a single match with detailed logging of every interrupt and purge."""
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)
        player_name = self.extract_player_name(match['filename'])

        if not player_name:
            print(f"❌ Could not extract player name from {match['filename']}")
            return None

        # Get known pets for this player from index
        known_pets = self.get_player_pets(player_name)

        print(f"\n🎮 DEBUG PROCESSING: {match['filename']}")
        print(f"   Player: {player_name}")
        print(f"   Known pets: {known_pets}")
        print(f"   Match start: {match_start}")
        print(f"   Combat log: {log_file.name}")

        # Initialize features
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

        try:
            # Enhanced arena boundary detection
            buffer = timedelta(seconds=120)
            window_start = match_start - buffer
            window_end = match_start + timedelta(seconds=match_duration) + buffer

            arena_start, arena_end = self.find_arena_boundaries_enhanced(
                log_file, window_start, window_end, match_start, match['filename']
            )

            precise_start = arena_start if arena_start else window_start
            precise_end = arena_end if arena_end else window_end

            print(f"   🎯 Arena boundaries: {precise_start} to {precise_end}")
            if arena_start and arena_end:
                duration = (arena_end - arena_start).total_seconds()
                print(f"   ⏱️ Arena duration: {duration:.0f} seconds")

            # Parse events within boundaries with DETAILED LOGGING
            print(f"\n📋 DETAILED EVENT LOGGING:")
            print(f"=" * 80)

            interrupt_count = 0
            purge_count = 0

            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    event_time = self.parse_log_line_timestamp(line)
                    if not event_time or not (precise_start <= event_time <= precise_end):
                        continue

                    # Process with detailed logging
                    interrupt_found, purge_found = self.process_combat_event_with_detailed_logging(
                        line, line_num, player_name, known_pets, features, event_time
                    )

                    if interrupt_found:
                        interrupt_count += 1
                    if purge_found:
                        purge_count += 1

            print(f"=" * 80)
            print(f"🎯 FINAL EVENT COUNTS:")
            print(f"   Total interrupts found: {interrupt_count}")
            print(f"   Total purges found: {purge_count}")
            print(f"   Final interrupt_success_own: {features['interrupt_success_own']}")
            print(f"   Final purges_own: {features['purges_own']}")
            print(f"   Final times_interrupted: {features['times_interrupted']}")

            return features

        except Exception as e:
            print(f"❌ Error processing match: {e}")
            return None

    def process_combat_event_with_detailed_logging(self, line: str, line_num: int, player_name: str,
                                                   known_pets: List[str], features: Dict, event_time: datetime) -> \
    Tuple[bool, bool]:
        """Process combat event with detailed logging for every interrupt and purge."""
        interrupt_found = False
        purge_found = False

        try:
            parts = line.strip().split(',')
            if len(parts) < 3:
                return False, False

            first_part = parts[0]
            event_type = first_part.split()[-1] if ' ' in first_part else first_part

            # SPELL_DISPEL events (Pet Purges) - WITH DETAILED LOGGING
            if event_type == 'SPELL_DISPEL' and len(parts) >= 13:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')
                purged_aura = parts[12].strip('"')

                # Check if source is any of the player's known pets
                if spell_name == "Devour Magic":
                    is_our_pet = self.is_player_pet(src, player_name)

                    print(f"🔍 PURGE EVENT (Line {line_num}):")
                    print(f"   Time: {event_time}")
                    print(f"   Source: {src}")
                    print(f"   Spell: {spell_name}")
                    print(f"   Purged aura: {purged_aura}")
                    print(f"   Is our pet: {is_our_pet}")
                    print(f"   Known pets: {known_pets}")
                    print(f"   Raw line: {line.strip()}")

                    if is_our_pet:
                        features['purges_own'] += 1
                        features['spells_purged'].append(purged_aura)
                        purge_found = True
                        print(f"   ✅ COUNTED as our purge (total now: {features['purges_own']})")
                    else:
                        print(f"   ❌ NOT COUNTED - not our pet")
                    print()

            # Interrupt events - WITH DETAILED LOGGING
            elif event_type == 'SPELL_INTERRUPT' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                dst = parts[6].strip('"').split('-', 1)[0]
                interrupt_spell = parts[10].strip('"')

                # Check if interrupt source is player OR any of their pets
                interrupt_by_player = (src == player_name)
                interrupt_by_pet = self.is_player_pet(src, player_name)
                interrupted_player = (dst == player_name)
                interrupted_pet = self.is_player_pet(dst, player_name)

                print(f"⚡ INTERRUPT EVENT (Line {line_num}):")
                print(f"   Time: {event_time}")
                print(f"   Source: {src}")
                print(f"   Target: {dst}")
                print(f"   Interrupt spell: {interrupt_spell}")
                print(f"   Source is player: {interrupt_by_player}")
                print(f"   Source is our pet: {interrupt_by_pet}")
                print(f"   Target is player: {interrupted_player}")
                print(f"   Target is our pet: {interrupted_pet}")
                print(f"   Known pets: {known_pets}")
                print(f"   Raw line: {line.strip()}")

                if interrupt_by_player or interrupt_by_pet:
                    features['interrupt_success_own'] += 1
                    interrupt_found = True
                    interrupter = "player" if interrupt_by_player else "pet"
                    print(
                        f"   ✅ COUNTED as our interrupt by {interrupter} (total now: {features['interrupt_success_own']})")
                elif interrupted_player or interrupted_pet:
                    features['times_interrupted'] += 1
                    interrupted_type = "player" if interrupted_player else "pet"
                    print(
                        f"   ⚠️ COUNTED as us being interrupted ({interrupted_type}) (total now: {features['times_interrupted']})")
                else:
                    print(f"   ❌ NOT COUNTED - neither source nor target is ours")
                print()

            # Cast success events - Only count player casts (not pets) - BRIEF LOGGING
            elif event_type == 'SPELL_CAST_SUCCESS' and len(parts) >= 11:
                src = parts[2].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                if src == player_name:
                    features['cast_success_own'] += 1
                    features['spells_cast'].append(spell_name)

            # Precognition aura applications - BRIEF LOGGING
            elif event_type == 'SPELL_AURA_APPLIED' and len(parts) >= 11:
                dst = parts[6].strip('"').split('-', 1)[0]
                spell_name = parts[10].strip('"')

                if spell_name == 'Precognition':
                    if dst == player_name:
                        features['precog_gained_own'] += 1
                    else:
                        features['precog_gained_enemy'] += 1

            # Death events - BRIEF LOGGING
            elif event_type == 'UNIT_DIED' and len(parts) >= 7:
                died_unit = parts[6].strip('"').split('-', 1)[0]
                if died_unit == player_name:
                    features['times_died'] += 1

        except Exception as e:
            print(f"❌ Error processing line {line_num}: {e}")

        return interrupt_found, purge_found

    def find_arena_boundaries_enhanced(self, log_file: Path, window_start: datetime, window_end: datetime,
                                       video_start: datetime, filename: str) -> Tuple[
        Optional[datetime], Optional[datetime]]:
        """Find arena boundaries using enhanced detection with JSON zone data and multiple fallback strategies."""
        expected_bracket, expected_map = self.extract_arena_info_from_filename(filename)

        # Load JSON data for enhanced zone matching
        json_data = self.load_json_data_for_match(filename)
        json_zone_id = None
        json_map_name = None

        if json_data:
            json_zone_id = str(json_data.get('zoneID', ''))
            json_map_name = json_data.get('zoneName', '')
            print(f"   📋 JSON data found - Zone ID: {json_zone_id}, Map: {json_map_name}")

            # Use JSON data if filename has "undefined" or other issues
            if expected_map.lower() in ['undefined', 'unknown']:
                expected_map = json_map_name
                print(f"   🔄 Updated expected map from JSON: {expected_map}")

        # Load death data for verification
        death_data = self.extract_death_info(json_data) if json_data else None

        arena_events = []
        extended_start = window_start - timedelta(minutes=10)
        extended_end = window_end + timedelta(minutes=10)

        print(f"   🔍 Looking for arena events between {extended_start} and {extended_end}")
        print(f"   🎯 Expected: {expected_bracket} on {expected_map}")

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
                        print(
                            f"   📍 Found ARENA_MATCH_START: {event_time} - {arena_info['bracket']} on {arena_info['map']} (Zone: {arena_info['zone_id']})")
                elif 'ARENA_MATCH_END' in line:
                    arena_events.append(('END', event_time, None))
                    print(f"   🏁 Found ARENA_MATCH_END: {event_time}")

        arena_events.sort(key=lambda x: x[1])
        print(f"   📊 Total arena events found: {len(arena_events)}")

        # Find ALL potential arena start candidates with enhanced matching
        matching_starts = []
        for event_type, event_time, info in arena_events:
            if event_type == 'START':
                # Find corresponding end
                arena_end = None
                for end_type, end_time, _ in arena_events:
                    if end_type == 'END' and end_time > event_time:
                        arena_end = end_time
                        break

                if arena_end:
                    duration = (arena_end - event_time).total_seconds()
                    time_diff = abs((event_time - video_start).total_seconds())

                    # Enhanced matching criteria
                    match_score = self.calculate_arena_match_score(
                        info, expected_bracket, expected_map, json_zone_id,
                        event_time, video_start, duration
                    )

                    matching_starts.append({
                        'start': event_time,
                        'end': arena_end,
                        'duration': duration,
                        'time_diff_to_video': time_diff,
                        'match_score': match_score,
                        'arena_info': info
                    })

                    print(f"   📊 Arena candidate: {event_time} to {arena_end}")
                    print(f"      Map: {info['map']}, Zone: {info['zone_id']}, Duration: {duration:.0f}s")
                    print(f"      Time diff: {time_diff:.0f}s, Match score: {match_score:.2f}")

        if not matching_starts:
            print(f"   ❌ No arena candidates found")
            return None, None

        # Sort by match score (highest first)
        matching_starts.sort(key=lambda x: x['match_score'], reverse=True)

        # If we have a high-confidence match, use it
        best_match = matching_starts[0]
        if best_match['match_score'] >= 0.8:
            print(f"   ✅ High-confidence match found (score: {best_match['match_score']:.2f})")
            print(f"      Arena: {best_match['start']} to {best_match['end']}")
            return best_match['start'], best_match['end']

        # Multiple potential matches - use enhanced verification
        print(f"   🔍 Found {len(matching_starts)} candidates - using enhanced verification")

        # Strategy 1: Death correlation verification (most reliable)
        if death_data:
            verified_match = self.verify_match_with_death_correlation(
                matching_starts, death_data, log_file, expected_bracket, expected_map
            )
            if verified_match:
                print(f"   ✅ Death correlation verified match: {verified_match['start']} to {verified_match['end']}")
                return verified_match['start'], verified_match['end']

        # Strategy 2: Use best match score
        best_match = matching_starts[0]
        print(
            f"   ⚠️ Using best scoring match: {best_match['start']} to {best_match['end']} (score: {best_match['match_score']:.2f})")
        return best_match['start'], best_match['end']

    def load_json_data_for_match(self, filename: str) -> Optional[Dict]:
        """Load JSON data for the match to get zone information."""
        try:
            json_name = filename.rsplit('.', 1)[0] + '.json'

            # Try date-organized subdirectory first
            try:
                date_part = filename.split('_', 1)[0]  # YYYY-MM-DD
                year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
                json_path = self.base_dir / year_month / json_name
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except:
                pass

            # Try root directory
            json_path = self.base_dir / json_name
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

        except Exception as e:
            pass
        return None

    def calculate_arena_match_score(self, arena_info: Dict, expected_bracket: str, expected_map: str,
                                    json_zone_id: str, event_time: datetime, video_start: datetime,
                                    duration: float) -> float:
        """Calculate a match score for an arena candidate using multiple criteria."""
        score = 0.0

        # Bracket matching (high weight)
        if self.bracket_matches(arena_info['bracket'], expected_bracket):
            score += 0.4

        # Zone ID matching (highest weight if we have JSON data)
        if json_zone_id and arena_info['zone_id'] == json_zone_id:
            score += 0.5
        # Map name matching (medium weight)
        elif self.map_name_matches(arena_info['map'], expected_map):
            score += 0.3

        # Time proximity (up to 0.3 points)
        time_diff = abs((event_time - video_start).total_seconds())
        if time_diff <= 60:  # Within 1 minute
            score += 0.3
        elif time_diff <= 300:  # Within 5 minutes
            score += 0.2 - (time_diff - 60) / 240 * 0.1
        elif time_diff <= 600:  # Within 10 minutes
            score += 0.1 - (time_diff - 300) / 300 * 0.1

        # Duration reasonableness (small bonus)
        if 30 <= duration <= 900:  # 30 seconds to 15 minutes is reasonable
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def bracket_matches(self, combat_bracket: str, expected_bracket: str) -> bool:
        """Check if bracket matches with special handling for Solo Shuffle."""
        if expected_bracket == 'Solo Shuffle':
            return combat_bracket in ['Solo Shuffle', 'Rated Solo Shuffle']
        elif expected_bracket == 'Skirmish':
            return combat_bracket in ['2v2', '3v3', 'Skirmish']
        else:
            return combat_bracket == expected_bracket

    def map_name_matches(self, combat_map: str, expected_map: str) -> bool:
        """Check if map names match with fuzzy matching."""
        if not expected_map or expected_map.lower() in ['undefined', 'unknown']:
            return False

        combat_lower = combat_map.lower()
        expected_lower = expected_map.lower()

        return (combat_lower == expected_lower or
                expected_lower in combat_lower or
                combat_lower in expected_lower)

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
        """Check if arena info matches expected values."""
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

    def find_combat_log_for_match(self, match: pd.Series, log_files: List[Path]) -> Optional[Path]:
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

        # Filter to reasonable time windows
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


def main():
    """Main function to run detailed debug analysis on a single match."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"

    print("🔍 Debug Enhanced Parser with Detailed Event Logging")
    print(f"📁 Base directory: {base_dir}")

    parser = DebugEnhancedCombatParserWithDetailedLogging(base_dir)

    # Load enhanced index to find target matches
    enhanced_index = Path(base_dir) / "master_index_enhanced.csv"
    df = pd.read_csv(enhanced_index)

    # Handle timestamp parsing
    try:
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
    except ValueError:
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
        except ValueError:
            df['precise_start_time'] = df['precise_start_time'].apply(lambda x: pd.to_datetime(x) if pd.notna(x) else x)

    # Filter to 2025 matches
    matches_2025 = df[df['precise_start_time'] >= '2025-01-01'].copy()
    matches_2025 = matches_2025.sort_values('precise_start_time').reset_index(drop=True)

    # Find target match (corrected to line 1176 equivalent - match 1193)
    total_matches = len(matches_2025)
    # Original was match 1116, need to move to 1193 (shift of +77)
    # Line 1176 in CSV corresponds to match 1193 out of 2480
    estimated_position = int(total_matches * (1193 / 2480))  # Match 1193 of 2480
    target_match = matches_2025.iloc[estimated_position]

    print(f"🎯 Target match (corrected to line 1176 equivalent - match 1193):")
    print(f"   Position: {estimated_position + 1} of {total_matches}")
    print(f"   Match number: ~{int((estimated_position + 1) * (2480 / total_matches))}")
    print(f"   Filename: {target_match['filename']}")

    # Find combat log
    log_files = list(Path(base_dir + "/Logs").glob('*.txt'))
    relevant_log = parser.find_combat_log_for_match(target_match, log_files)

    if not relevant_log:
        print("❌ No combat log found for target match")
        return

    # Debug process the single match with detailed logging
    features = parser.debug_process_single_match(target_match, relevant_log)

    if features:
        print(f"\n🎉 Debug processing complete!")
        print(f"📊 Final results: {features['interrupt_success_own']} interrupts, {features['purges_own']} purges")
    else:
        print(f"\n❌ Debug processing failed")


if __name__ == '__main__':
    main()