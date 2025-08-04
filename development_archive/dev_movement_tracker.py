#!/usr/bin/env python3
"""
Development Script: Enhanced Movement Tracker
Arena-boundary-aware coordinate extraction with detailed debugging.

DEVELOPMENT ONLY - NOT FOR PRODUCTION USE
"""

import os
import re
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ArenaMovementTracker:
    """Development movement tracker with arena boundary integration."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.debug_mode = True
        
    def find_arena_match_boundaries(self, video_filename: str, logs_dir: str) -> Optional[Dict]:
        """
        Find arena match boundaries using existing enhanced parser logic.
        Start from timestamp-matched video metadata.
        """
        # Extract match info from video filename
        match_info = self.parse_video_filename(video_filename)
        if not match_info:
            return None
            
        # Find corresponding combat log
        log_file = self.find_combat_log_for_match(match_info, logs_dir)
        if not log_file:
            return None
            
        # Extract arena boundaries from combat log
        boundaries = self.extract_arena_boundaries(log_file, match_info)
        
        return boundaries
    
    def parse_video_filename(self, filename: str) -> Optional[Dict]:
        """Parse video filename to extract match metadata."""
        try:
            # Example: 2025-05-06_22-31-04_-_Phlargus_-_3v3_Nagrand_(Loss).mp4
            parts = filename.replace('.mp4', '').split('_-_')
            
            if len(parts) < 3:
                return None
                
            date_time = parts[0]
            player = parts[1]
            bracket_arena_result = parts[2]  # "3v3_Nagrand_(Loss)"
            
            # Parse date/time
            dt = datetime.strptime(date_time, '%Y-%m-%d_%H-%M-%S')
            
            # Parse bracket_arena_result: "3v3_Nagrand_(Loss)"
            if '_(Win)' in bracket_arena_result:
                won = True
                bracket_arena = bracket_arena_result.replace('_(Win)', '')
            elif '_(Loss)' in bracket_arena_result:
                won = False
                bracket_arena = bracket_arena_result.replace('_(Loss)', '')
            else:
                won = False
                bracket_arena = bracket_arena_result
            
            # Parse bracket and arena
            if bracket_arena.startswith('3v3_'):
                bracket = '3v3'
                arena = bracket_arena[4:]
            elif bracket_arena.startswith('2v2_'):
                bracket = '2v2'
                arena = bracket_arena[4:]
            else:
                bracket = 'unknown'
                arena = bracket_arena
                
            return {
                'filename': filename,
                'datetime': dt,
                'player': player,
                'bracket': bracket,
                'arena': arena,
                'result': 'Win' if won else 'Loss',
                'won': won
            }
            
        except Exception as e:
            print(f"DEBUG: Error parsing filename {filename}: {e}")
            return None
    
    def find_combat_log_for_match(self, match_info: Dict, logs_dir: str) -> Optional[Path]:
        """Find combat log file containing this match."""
        match_date = match_info['datetime'].date()
        log_dir = Path(logs_dir)
        
        # Look for logs from the same day
        date_pattern = match_date.strftime('%m%d%y')
        log_candidates = list(log_dir.glob(f'WoWCombatLog-{date_pattern}_*.txt'))
        
        if not log_candidates:
            return None
            
        # For now, return the first candidate
        # TODO: Could be refined with time-based matching
        return log_candidates[0]
    
    def extract_arena_boundaries(self, log_file: Path, match_info: Dict) -> Optional[Dict]:
        """Extract arena match boundaries from combat log."""
        if self.debug_mode:
            print(f"DEBUG: Extracting boundaries from {log_file.name}")
            print(f"DEBUG: Looking for {match_info['bracket']} {match_info['arena']} match")
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Find arena match start/end
            match_start = None
            match_end = None
            zone_info = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Look for zone change to arena
                if 'ZONE_CHANGE' in line and 'Arena' in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        zone_id = parts[1].strip()
                        zone_name = parts[2].strip().strip('"')
                        zone_info = {'id': zone_id, 'name': zone_name, 'line': i}
                        if self.debug_mode:
                            print(f"DEBUG: Found arena zone {zone_id}: {zone_name} at line {i}")
                
                # Look for arena match start
                if 'ARENA_MATCH_START' in line:
                    match_start = {'line': i, 'timestamp': line.split()[0] + ' ' + line.split()[1]}
                    if self.debug_mode:
                        print(f"DEBUG: Arena match start at line {i}: {match_start['timestamp']}")
                
                # Look for arena match end
                if 'ARENA_MATCH_END' in line:
                    match_end = {'line': i, 'timestamp': line.split()[0] + ' ' + line.split()[1]}
                    if self.debug_mode:
                        print(f"DEBUG: Arena match end at line {i}: {match_end['timestamp']}")
                    break
                    
            return {
                'log_file': log_file,
                'zone_info': zone_info,
                'match_start': match_start,
                'match_end': match_end,
                'total_lines': len(lines)
            }
            
        except Exception as e:
            print(f"DEBUG: Error extracting boundaries: {e}")
            return None
    
    def extract_coordinates_within_boundaries(self, boundaries: Dict) -> List[Dict]:
        """Extract coordinates only within arena match boundaries."""
        if not boundaries or not boundaries['log_file']:
            return []
            
        coordinates = []
        log_file = boundaries['log_file']
        start_line = boundaries['match_start']['line'] if boundaries['match_start'] else 0
        end_line = boundaries['match_end']['line'] if boundaries['match_end'] else None
        
        if self.debug_mode:
            print(f"DEBUG: Scanning lines {start_line} to {end_line or 'EOF'}")
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            scan_lines = lines[start_line:end_line] if end_line else lines[start_line:]
            
            for line_num, line in enumerate(scan_lines, start=start_line):
                line = line.strip()
                
                # Check for coordinate-bearing events
                if any(event in line for event in ['SPELL_HEAL', 'SPELL_DAMAGE', 'SPELL_CAST_SUCCESS', 
                                                 'SPELL_ENERGIZE', 'RANGE_DAMAGE', 'SWING_DAMAGE']):
                    
                    coordinate_match = re.search(r',(-?\d+\.\d+),(-?\d+\.\d+),0,(\d+\.\d+),\d+', line)
                    if coordinate_match:
                        # Extract player info
                        player_match = re.search(r'Player-[^,]+,"([^"]+)"', line)
                        player_name = player_match.group(1) if player_match else "Unknown"
                        
                        # Extract timestamp
                        timestamp_match = re.search(r'^([^,]+)', line)
                        timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"
                        
                        # Extract event type
                        event_match = re.search(r'  ([A-Z_]+),', line)
                        event_type = event_match.group(1) if event_match else "Unknown"
                        
                        coord_data = {
                            'line_number': line_num,
                            'timestamp': timestamp,
                            'event_type': event_type,
                            'player_name': player_name,
                            'x': float(coordinate_match.group(1)),
                            'y': float(coordinate_match.group(2)),
                            'facing': float(coordinate_match.group(3)),
                            'raw_line': line[:100] + '...' if len(line) > 100 else line
                        }
                        
                        coordinates.append(coord_data)
                        
                        if self.debug_mode and len(coordinates) <= 10:
                            print(f"DEBUG: Line {line_num}: {player_name} at ({coord_data['x']:.2f}, {coord_data['y']:.2f}) during {event_type}")
                            
        except Exception as e:
            print(f"DEBUG: Error extracting coordinates: {e}")
            
        return coordinates
    
    def analyze_arena_movement(self, video_filename: str, logs_dir: str) -> Dict:
        """Complete arena movement analysis for a single match."""
        print(f"\\n=== ARENA MOVEMENT ANALYSIS ===")
        print(f"Video: {video_filename}")
        print(f"Logs Directory: {logs_dir}")
        
        # Step 1: Parse video metadata
        match_info = self.parse_video_filename(video_filename)
        if not match_info:
            return {'error': 'Could not parse video filename'}
            
        print(f"Match: {match_info['bracket']} {match_info['arena']} - {match_info['datetime']}")
        print(f"Player: {match_info['player']} ({'Win' if match_info['won'] else 'Loss'})")
        
        # Step 2: Find arena boundaries
        boundaries = self.find_arena_match_boundaries(video_filename, logs_dir)
        if not boundaries:
            return {'error': 'Could not find arena boundaries'}
            
        # Step 3: Extract coordinates within boundaries
        coordinates = self.extract_coordinates_within_boundaries(boundaries)
        
        # Step 4: Analyze results
        analysis = {
            'match_info': match_info,
            'boundaries': boundaries,
            'coordinates': coordinates,
            'summary': {
                'total_coordinates': len(coordinates),
                'unique_players': len(set(c['player_name'] for c in coordinates)),
                'event_types': list(set(c['event_type'] for c in coordinates)),
                'time_span': None,
                'coordinate_ranges': None
            }
        }
        
        if coordinates:
            # Calculate coordinate ranges
            x_coords = [c['x'] for c in coordinates]
            y_coords = [c['y'] for c in coordinates]
            analysis['summary']['coordinate_ranges'] = {
                'x_min': min(x_coords), 'x_max': max(x_coords),
                'y_min': min(y_coords), 'y_max': max(y_coords)
            }
            
            # Get time span
            timestamps = [c['timestamp'] for c in coordinates]
            if len(timestamps) > 1:
                analysis['summary']['time_span'] = f"{timestamps[0]} to {timestamps[-1]}"
        
        return analysis

def test_arena_movement_tracker():
    """Test the arena movement tracker on specific matches."""
    tracker = ArenaMovementTracker(".")
    
    # Test cases - known 3v3 matches from May 2025
    test_cases = [
        "2025-05-06_22-31-04_-_Phlargus_-_3v3_Nagrand_(Loss).mp4",
        "2025-05-08_18-44-24_-_Phlurbotomy_-_3v3_Black_Rook_(Win).mp4",
        "2025-05-10_21-11-20_-_Phlurbotomy_-_3v3_Tiger's_Peak_(Win).mp4"
    ]
    
    results = []
    for test_video in test_cases:
        if Path(f"./2025-05/{test_video}").exists():
            analysis = tracker.analyze_arena_movement(test_video, "./Logs")
            results.append(analysis)
        else:
            print(f"SKIP: {test_video} not found")
    
    # Summary
    print(f"\\n=== SUMMARY ===")
    print(f"Analyzed {len(results)} matches")
    for i, result in enumerate(results, 1):
        if 'error' not in result:
            summary = result['summary']
            match = result['match_info']
            print(f"{i}. {match['arena']}: {summary['total_coordinates']} coords, {summary['unique_players']} players")
        else:
            print(f"{i}. ERROR: {result['error']}")
    
    return results

if __name__ == "__main__":
    print("Arena Movement Tracker - Development Version")
    print("Testing arena-boundary-aware coordinate extraction")
    
    results = test_arena_movement_tracker()