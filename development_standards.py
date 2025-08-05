"""
Development Standards Implementation

Reusable functions for Unicode handling, codec safety, and arena boundary detection.
Import these functions to ensure consistent behavior across all arena analysis components.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import traceback


class SafeLogger:
    """Safe logging for arena analysis system - no Unicode characters"""
    
    @staticmethod
    def success(message: str):
        print(f"SUCCESS: {message}")
    
    @staticmethod 
    def error(message: str):
        print(f"ERROR: {message}")
        
    @staticmethod
    def warning(message: str):
        print(f"WARNING: {message}")
        
    @staticmethod
    def info(message: str):
        print(f"INFO: {message}")
        
    @staticmethod
    def debug(message: str, verbose: bool = False):
        if verbose:
            print(f"DEBUG: {message}")


def parse_combat_log_timestamp(line: str) -> Optional[datetime]:
    """
    Standard method for parsing WoW combat log timestamps
    Handles formats: "5/6/2025 22:14:29.304-4" and variations
    """
    try:
        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            return None

        # Extract timestamp portion (before first comma or space)
        full_timestamp = f"{parts[0]} {parts[1]}"
        timestamp_clean = full_timestamp.split('-')[0].strip()  # Remove timezone

        # Try microseconds first, then seconds only
        try:
            return datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S.%f")
        except ValueError:
            try:
                return datetime.strptime(timestamp_clean, "%m/%d/%Y %H:%M:%S")
            except ValueError:
                return None
    except Exception:
        return None


def read_combat_log_safely(file_path: Path) -> str:
    """Standard method for reading combat log files"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 for problematic files
        try:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                return f.read()
        except Exception as e:
            SafeLogger.error(f"Could not read {file_path}: {str(e)}")
            return ""
    except Exception as e:
        SafeLogger.error(f"Could not read {file_path}: {str(e)}")
        return ""


def export_json_safely(data: dict, file_path: Path):
    """Standard method for JSON export"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        SafeLogger.success(f"Exported JSON to: {file_path}")
    except UnicodeEncodeError:
        # Fallback: ASCII-only export
        try:
            with open(file_path, 'w', encoding='ascii', errors='ignore') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=True)
            SafeLogger.warning(f"Exported JSON with ASCII fallback to: {file_path}")
        except Exception as e:
            SafeLogger.error(f"Could not export JSON to {file_path}: {str(e)}")
    except Exception as e:
        SafeLogger.error(f"Could not export JSON to {file_path}: {str(e)}")


def select_combat_log_file(match_timestamp: datetime, logs_directory: Path) -> Optional[Path]:
    """
    Standard method for selecting the correct combat log file
    """
    available_logs = list(logs_directory.glob("WoWCombatLog-*.txt"))
    
    if not available_logs:
        SafeLogger.error(f"No combat log files found in {logs_directory}")
        return None
    
    # Parse log file timestamps from filenames
    log_times = []
    for log_file in available_logs:
        try:
            # Extract timestamp from filename: WoWCombatLog-050625_182406.txt
            date_part = log_file.stem.split('-')[1]  # 050625_182406
            date_str, time_str = date_part.split('_')
            
            # Parse: 050625 = May 6, 2025; 182406 = 18:24:06
            month = int(date_str[:2])
            day = int(date_str[2:4]) 
            year = 2000 + int(date_str[4:6])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            log_start_time = datetime(year, month, day, hour, minute, second)
            log_times.append((log_file, log_start_time))
            
        except Exception as e:
            SafeLogger.debug(f"Could not parse timestamp from {log_file.name}: {e}")
            continue
    
    if not log_times:
        SafeLogger.warning("No parseable log file timestamps, using first available")
        return available_logs[0]
    
    # Find log file that starts before match time and is closest
    suitable_logs = [(log, start) for log, start in log_times if start <= match_timestamp]
    
    if suitable_logs:
        # Choose the log that starts closest to (but before) the match
        chosen_log = max(suitable_logs, key=lambda x: x[1])[0]
        SafeLogger.info(f"Selected log file: {chosen_log.name} (starts before match)")
        return chosen_log
    else:
        # No log starts before match - use earliest log
        chosen_log = min(log_times, key=lambda x: x[1])[0]
        SafeLogger.warning(f"No log starts before match, using earliest: {chosen_log.name}")
        return chosen_log


def find_arena_boundaries_robust(log_content: str, 
                                match_timestamp: datetime,
                                match_duration: int,
                                search_window_minutes: int = 10) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Standard method for finding arena match boundaries with fallback
    Note: For production systems, use find_verified_arena_boundaries() for enhanced multi-stage matching
    """
    window_start = match_timestamp - timedelta(minutes=search_window_minutes)
    window_end = match_timestamp + timedelta(seconds=match_duration + search_window_minutes * 60)
    
    arena_starts = []
    arena_ends = []
    lines_processed = 0
    
    for line in log_content.split('\n'):
        lines_processed += 1
        if lines_processed > 50000:  # Reasonable limit
            break
            
        if not line.strip():
            continue
            
        timestamp = parse_combat_log_timestamp(line)
        if not timestamp or not (window_start <= timestamp <= window_end):
            continue
            
        # Look for arena boundary events
        if 'ARENA_MATCH_START' in line:
            arena_starts.append(timestamp)
        elif 'ARENA_MATCH_END' in line:
            arena_ends.append(timestamp)
    
    # Find best match based on proximity to expected match time
    best_start = None
    best_end = None
    
    if arena_starts:
        best_start = min(arena_starts, key=lambda t: abs((t - match_timestamp).total_seconds()))
        SafeLogger.success(f"Found ARENA_MATCH_START at {best_start}")
        
        # Find corresponding end
        if arena_ends:
            potential_ends = [t for t in arena_ends if t > best_start]
            if potential_ends:
                best_end = min(potential_ends, key=lambda t: abs((t - (match_timestamp + timedelta(seconds=match_duration))).total_seconds()))
                SafeLogger.success(f"Found ARENA_MATCH_END at {best_end}")
    
    # Fallback to time window if no boundaries found
    if not best_start:
        SafeLogger.warning(f"No ARENA_MATCH_START found, using fallback window")
        best_start = window_start
        
    if not best_end:
        SafeLogger.warning(f"No ARENA_MATCH_END found, using fallback window")
        best_end = window_end
        
    return best_start, best_end


def extract_events_in_time_window(log_content: str,
                                 start_time: datetime,
                                 end_time: datetime,
                                 max_lines: int = 100000) -> List[str]:
    """
    Standard method for extracting combat log events in time window
    """
    events_in_window = []
    lines_processed = 0
    valid_timestamps = 0
    
    for line in log_content.split('\n'):
        lines_processed += 1
        if lines_processed > max_lines:
            SafeLogger.warning(f"Reached max lines limit ({max_lines}), stopping processing")
            break
            
        if not line.strip():
            continue
            
        timestamp = parse_combat_log_timestamp(line)
        if timestamp:
            valid_timestamps += 1
            if start_time <= timestamp <= end_time:
                events_in_window.append(line)
    
    SafeLogger.info(f"Processed {lines_processed:,} lines, {valid_timestamps:,} valid timestamps, {len(events_in_window):,} events in window")
    
    return events_in_window


def normalize_player_name(full_name: str) -> str:
    """Extract base player name without server suffix"""
    if '-' in full_name:
        return full_name.split('-')[0]
    return full_name


def player_name_matches(combat_log_name: str, target_player_name: str) -> bool:
    """Check if player names match, handling server suffixes"""
    log_base = normalize_player_name(combat_log_name)
    target_base = normalize_player_name(target_player_name)
    return log_base.lower() == target_base.lower()


def process_match_safely(match_filename: str, match_timestamp: datetime, 
                        player_name: str, logs_dir: Path, match_duration: int = 300) -> Dict:
    """Complete example of safe match processing"""
    
    SafeLogger.info(f"Processing match: {match_filename}")
    
    try:
        # 1. Safe log file selection
        log_file = select_combat_log_file(match_timestamp, logs_dir)
        if not log_file:
            return {'status': 'no_log_file', 'error': 'No suitable log file found'}
        
        # 2. Safe file reading
        log_content = read_combat_log_safely(log_file)
        if not log_content:
            return {'status': 'read_failed', 'error': f'Could not read {log_file}'}
        
        # 3. Robust boundary detection
        start_time, end_time = find_arena_boundaries_robust(
            log_content, match_timestamp, match_duration
        )
        
        # 4. Safe event extraction
        events = extract_events_in_time_window(log_content, start_time, end_time)
        
        # 5. Process events with safe player matching
        player_events = []
        for event in events:
            event_parts = event.split(',')
            if len(event_parts) >= 3:
                # Check source and destination names
                for i in [2, 6]:  # Typical positions for player names
                    if i < len(event_parts):
                        name_part = event_parts[i].strip().strip('"')
                        if player_name_matches(name_part, player_name):
                            player_events.append(event)
                            break
        
        SafeLogger.success(f"Processed {match_filename}: {len(events)} total events, {len(player_events)} player events")
        
        return {
            'status': 'success',
            'log_file': log_file.name,
            'events_found': len(events),
            'player_events': len(player_events),
            'boundary_detection': 'arena_events' if 'ARENA_MATCH' in log_content else 'fallback_window',
            'time_window': f"{start_time} to {end_time}"
        }
        
    except Exception as e:
        SafeLogger.error(f"Exception processing {match_filename}: {str(e)}")
        return {
            'status': 'error', 
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def safe_print_results(results: Dict, title: str = "Results"):
    """Safe printing of results without Unicode issues"""
    print(f"\n{title}")
    print("=" * len(title))
    
    for key, value in results.items():
        if isinstance(value, (int, float)):
            print(f"{key}: {value}")
        elif isinstance(value, str):
            # Ensure safe string output
            safe_value = value.encode('ascii', errors='ignore').decode('ascii')
            print(f"{key}: {safe_value}")
        elif isinstance(value, (list, dict)):
            print(f"{key}: {type(value).__name__} with {len(value)} items")
        else:
            print(f"{key}: {str(type(value))}")


# =============================================================================
# PRODUCTION-LEVEL ARENA MATCHING SYSTEM
# Multi-stage verification with death correlation, duration matching, Solo Shuffle support
# =============================================================================

def find_verified_arena_boundaries(log_file: Path, window_start: datetime, window_end: datetime,
                                   video_start: datetime, filename: str, video_duration: float, 
                                   base_dir: Path) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Production-level arena boundary detection with multi-stage verification.
    
    Uses sophisticated matching strategies:
    1. Death correlation verification (most reliable)
    2. Duration-based verification
    3. Time proximity matching (fallback)
    
    Handles Solo Shuffle bracket equivalence and JSON metadata integration.
    """
    expected_bracket, expected_map = extract_arena_info_from_filename(filename)
    
    # Load JSON death data for verification
    death_data = load_death_data_from_json(filename, base_dir)
    
    arena_events = []
    extended_start = window_start - timedelta(minutes=10)
    extended_end = window_end + timedelta(minutes=10)
    
    # Collect all arena events in extended window
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            event_time = parse_combat_log_timestamp(line)
            if not event_time or not (extended_start <= event_time <= extended_end):
                continue
                
            if 'ARENA_MATCH_START' in line:
                arena_info = parse_arena_start_line(line, event_time)
                if arena_info:
                    arena_events.append(('START', event_time, arena_info))
            elif 'ARENA_MATCH_END' in line:
                arena_events.append(('END', event_time, None))
    
    arena_events.sort(key=lambda x: x[1])
    
    # Find ALL matching arena start candidates
    matching_starts = []
    for event_type, event_time, info in arena_events:
        if event_type == 'START' and arena_info_matches(info, expected_bracket, expected_map):
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
        SafeLogger.warning("No matching arena boundaries found")
        return None, None
        
    # If only one match, use it
    if len(matching_starts) == 1:
        best_match = matching_starts[0]
        SafeLogger.success("Single arena match found")
        return best_match['start'], best_match['end']
    
    # Multiple matches - use enhanced verification
    SafeLogger.info(f"Found {len(matching_starts)} potential arena matches, using verification")
    
    # Strategy 1: Death correlation verification (most reliable)
    if death_data:
        verified_match = verify_match_with_death_correlation(
            matching_starts, death_data, log_file
        )
        if verified_match:
            SafeLogger.success("Death correlation verified match")
            return verified_match['start'], verified_match['end']
    
    # Strategy 2: Duration-based verification
    duration_verified = verify_match_with_duration(matching_starts, video_duration)
    if duration_verified:
        SafeLogger.success("Duration verified match")
        return duration_verified['start'], duration_verified['end']
    
    # Strategy 3: Time proximity (fallback)
    closest_match = min(matching_starts, key=lambda x: x['time_diff_to_video'])
    SafeLogger.warning(f"Using closest match by time (±{closest_match['time_diff_to_video']:.0f}s)")
    return closest_match['start'], closest_match['end']


def load_death_data_from_json(filename: str, base_dir: Path) -> Optional[Dict]:
    """Load death data from corresponding JSON file for verification."""
    try:
        json_name = filename.rsplit('.', 1)[0] + '.json'
        
        # Try date-organized subdirectory first
        try:
            date_part = filename.split('_', 1)[0]  # YYYY-MM-DD
            year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
            json_path = base_dir / year_month / json_name
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return extract_death_info(data)
        except:
            pass
            
        # Try root directory
        json_path = base_dir / json_name
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return extract_death_info(data)
                
    except Exception as e:
        SafeLogger.debug(f"Could not load death data: {e}")
    return None


def extract_death_info(json_data: dict) -> Dict:
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
        SafeLogger.debug(f"Error extracting death info: {e}")
        
    return death_info


def verify_match_with_death_correlation(matching_starts: List[Dict], death_data: Dict, 
                                       log_file: Path) -> Optional[Dict]:
    """Verify arena match using death correlation between JSON and combat log."""
    if not death_data or death_data['total_deaths'] == 0:
        return None
        
    player_name = extract_player_name_from_combat_log(log_file)
    if not player_name:
        return None
        
    best_match = None
    best_correlation = -1
    
    for match_candidate in matching_starts:
        try:
            # Count deaths in this arena match window
            combat_deaths = count_deaths_in_arena_window(
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
            SafeLogger.debug(f"Error in death correlation: {e}")
            continue
            
    return best_match


def count_deaths_in_arena_window(log_file: Path, start_time: datetime, end_time: datetime,
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
                event_time = parse_combat_log_timestamp(line)
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
        SafeLogger.debug(f"Error counting deaths: {e}")
        
    return death_counts


def extract_player_name_from_combat_log(log_file: Path) -> Optional[str]:
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


def verify_match_with_duration(matching_starts: List[Dict], expected_duration: float) -> Optional[Dict]:
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


def extract_arena_info_from_filename(filename: str) -> Tuple[str, str]:
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


def parse_arena_start_line(line: str, event_time: datetime) -> Optional[Dict]:
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


def arena_info_matches(arena_info: Dict, expected_bracket: str, expected_map: str) -> bool:
    """Check if arena info matches expected values from filename."""
    if not arena_info:
        return False
        
    combat_bracket = arena_info['bracket']
    bracket_match = False
    
    # Handle Solo Shuffle bracket equivalence
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


# Test function
def test_development_standards():
    """Test the development standards implementation"""
    
    SafeLogger.info("Testing development standards implementation")
    
    # Test timestamp parsing
    test_line = "5/6/2025 22:14:29.304-4  SPELL_DAMAGE,Player-123-456"
    timestamp = parse_combat_log_timestamp(test_line)
    
    if timestamp:
        SafeLogger.success(f"Timestamp parsing works: {timestamp}")
    else:
        SafeLogger.error("Timestamp parsing failed")
    
    # Test player name matching
    if player_name_matches("Phlargus-Eredar-US", "Phlargus"):
        SafeLogger.success("Player name matching works")
    else:
        SafeLogger.error("Player name matching failed")
    
    # Test Solo Shuffle bracket equivalence
    test_arena_info = {'bracket': 'Rated Solo Shuffle', 'map': 'Nagrand'}
    if arena_info_matches(test_arena_info, 'Solo Shuffle', 'Nagrand'):
        SafeLogger.success("Solo Shuffle bracket equivalence works")
    else:
        SafeLogger.error("Solo Shuffle bracket equivalence failed")
    
    # Test arena info extraction from filename
    test_filename = "2025-05-06_-_Phlargus_-_Solo_Shuffle_Nagrand_(Win).mp4"
    bracket, arena_map = extract_arena_info_from_filename(test_filename)
    if bracket == 'Solo Shuffle' and arena_map == 'Nagrand':
        SafeLogger.success("Arena info extraction works")
    else:
        SafeLogger.error(f"Arena info extraction failed: {bracket}, {arena_map}")
    
    SafeLogger.info("Development standards test complete")
    SafeLogger.info("Production-level arena matching system integrated")
    SafeLogger.info("Key features: Multi-stage verification, death correlation, Solo Shuffle support")
    

if __name__ == "__main__":
    test_development_standards()