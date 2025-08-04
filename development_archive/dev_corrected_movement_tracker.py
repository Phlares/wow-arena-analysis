#!/usr/bin/env python3
"""
Development: Corrected Movement Tracker

Fixes the critical issue identified where position data was being mixed up between
source and target entities, and players weren't being tracked per-unit correctly.

Key fixes:
1. Track position data per specific unit GUID, not just player name
2. Properly associate position data with the SOURCE entity of each action
3. Separate movement tracking per individual unit
4. Avoid mixing source/target positions or different players with same name
"""

import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import json
from dataclasses import dataclass
from collections import defaultdict

from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser

@dataclass
class UnitPosition:
    """Position data for a specific unit."""
    timestamp: datetime
    x: float
    y: float
    facing: float
    event_type: str
    unit_guid: str
    unit_name: str
    hp_current: int
    hp_max: int
    raw_line: str

@dataclass
class MovementSegment:
    """Movement segment between two positions for a specific unit."""
    unit_guid: str
    unit_name: str
    start_pos: UnitPosition
    end_pos: UnitPosition
    distance: float
    time_diff: float
    speed: float
    dx: float
    dy: float

class CorrectedAdvancedCombatAction:
    """
    Corrected advanced combat action that properly tracks which entity the position data belongs to.
    """
    
    SUPPORTED_EVENTS = {
        'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE', 'SPELL_HEAL', 'SPELL_PERIODIC_HEAL',
        'SPELL_ENERGIZE', 'SPELL_PERIODIC_ENERGIZE', 'RANGE_DAMAGE', 'SWING_DAMAGE',
        'SWING_DAMAGE_LANDED', 'SPELL_CAST_SUCCESS', 'SPELL_CAST_START'
    }
    
    def __init__(self, raw_line: str):
        """Initialize from raw combat log line."""
        self.raw_line = raw_line.strip()
        self.timestamp = None
        self.event = None
        self.source_guid = None
        self.source_name = None
        self.has_advanced_data = False
        
        # Position data (belongs to SOURCE entity)
        self.position_x = 0.0
        self.position_y = 0.0
        self.facing = 0.0
        self.hp_current = 0
        self.hp_max = 0
        
        self._parse_line()
    
    def _parse_line(self):
        """Parse the combat log line and extract data."""
        # Split timestamp from rest of line
        parts = self.raw_line.split('  ', 1)
        if len(parts) != 2:
            return
        
        timestamp_str, event_data = parts
        
        # Parse timestamp
        try:
            # Handle timezone offset: "8/3/2025 09:31:20.347-4"
            if '+' in timestamp_str or timestamp_str.endswith(('-4', '-5', '-6', '-7', '-8')):
                timestamp_str = timestamp_str.split('+')[0].split('-')[0]
            self.timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S.%f")
        except ValueError:
            return
        
        # Split event data by commas
        params = [p.strip() for p in event_data.split(',')]
        if len(params) < 3:
            return
        
        # Extract event type
        self.event = params[0]
        if self.event not in self.SUPPORTED_EVENTS:
            return
        
        # Extract source information (first entity in the line)
        self.source_guid = params[1] if len(params) > 1 else ""
        
        # Extract source name from quotes
        if len(params) > 2:
            name_match = re.search(r'"([^"]+)"', params[2])
            self.source_name = name_match.group(1) if name_match else ""
        
        # Parse advanced logging data (at the end of the line)
        self._parse_advanced_data(params)
    
    def _parse_advanced_data(self, params: List[str]):
        """Parse advanced logging data from the end of the parameter list."""
        # Advanced logging data is typically at the end of long combat log lines
        # Look for numeric position data in the last ~10 parameters
        
        if len(params) < 20:  # Not enough parameters for advanced logging
            return
        
        try:
            # Look for position coordinates in the last several parameters
            # Position data is typically: ...,posX,posY,posZ,facing,itemLevel
            
            # Check last 10 parameters for position-like data
            for i in range(max(0, len(params) - 10), len(params) - 1):
                try:
                    x = float(params[i])
                    y = float(params[i + 1])
                    
                    # Basic sanity check: WoW coordinates are typically in reasonable ranges
                    if abs(x) < 10000 and abs(y) < 10000 and (abs(x) > 10 or abs(y) > 10):
                        self.position_x = x
                        self.position_y = y
                        
                        # Try to get facing if available
                        if i + 3 < len(params):
                            try:
                                self.facing = float(params[i + 3])
                            except:
                                self.facing = 0.0
                        
                        # Try to get health data from earlier in the line
                        self._extract_health_data(params)
                        
                        self.has_advanced_data = True
                        break
                except (ValueError, IndexError):
                    continue
                    
        except Exception:
            pass
    
    def _extract_health_data(self, params: List[str]):
        """Extract health data from combat log parameters."""
        # Health data is typically found in the middle section of the line
        # Look for two consecutive large integers that could be current/max HP
        
        for i in range(10, min(len(params) - 1, 25)):  # Check middle section
            try:
                current = int(params[i])
                maximum = int(params[i + 1])
                
                # Basic validation: reasonable HP values
                if 1000 <= current <= 50000000 and current <= maximum <= 50000000:
                    self.hp_current = current
                    self.hp_max = maximum
                    break
            except (ValueError, IndexError):
                continue
    
    def is_valid_position(self) -> bool:
        """Check if position data is valid."""
        return (self.has_advanced_data and 
                self.position_x != 0.0 and 
                self.position_y != 0.0 and
                abs(self.position_x) < 10000 and 
                abs(self.position_y) < 10000)
    
    def get_unit_key(self) -> str:
        """Get unique key for this unit (GUID + name for safety)."""
        return f"{self.source_guid}:{self.source_name}"

class CorrectedMovementTracker:
    """
    Corrected movement tracker that properly handles per-unit position tracking.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.production_parser = EnhancedProductionCombatParser(base_dir)
        
        # Per-unit position tracking
        self.unit_positions: Dict[str, List[UnitPosition]] = defaultdict(list)
        self.unit_movements: Dict[str, List[MovementSegment]] = defaultdict(list)
        
        # Movement analysis thresholds
        self.LARGE_MOVEMENT_THRESHOLD = 50.0
        self.VERY_LARGE_MOVEMENT_THRESHOLD = 100.0  
        self.TELEPORT_THRESHOLD = 200.0
    
    def analyze_corrected_movement(self, log_file: Path, match_info: Dict) -> Dict:
        """
        Analyze movement with corrected per-unit tracking.
        """
        print(f"\n{'='*80}")
        print(f"CORRECTED MOVEMENT ANALYSIS")
        print(f"Match: {match_info['filename']}")
        print(f"Log: {log_file.name}")
        print(f"{'='*80}")
        
        # Get match details
        player_name = self.production_parser.extract_player_name(match_info['filename'])
        expected_bracket, expected_map = self.production_parser.extract_arena_info_from_filename(match_info['filename'])
        
        print(f"Target Player: {player_name}")
        print(f"Expected: {expected_bracket} on {expected_map}")
        
        # Get arena boundaries using production parser
        match_start_time = match_info['precise_start_time']
        if hasattr(match_start_time, 'to_pydatetime'):
            match_start = match_start_time.to_pydatetime()
        elif isinstance(match_start_time, str):
            match_start = datetime.fromisoformat(match_start_time.replace('Z', '+00:00'))
        else:
            match_start = match_start_time
        
        match_duration = match_info.get('duration_s', 300)
        
        arena_start, arena_end = self.production_parser.find_verified_arena_boundaries(
            log_file,
            match_start - timedelta(seconds=60),
            match_start + timedelta(seconds=match_duration + 60),
            match_start,
            match_info['filename'],
            match_duration
        )
        
        if not arena_start:
            return {'error': 'No verified arena boundaries found'}
        
        print(f"Arena boundaries: {arena_start} to {arena_end}")
        
        # Parse combat log with corrected tracking
        unit_positions = self._parse_corrected_positions(log_file, arena_start, arena_end)
        
        print(f"\n--- UNIT POSITION ANALYSIS ---")
        print(f"Total units with position data: {len(unit_positions)}")
        
        # Find units that match our target player
        target_units = []
        for unit_key, positions in unit_positions.items():
            unit_name = unit_key.split(':', 1)[1] if ':' in unit_key else unit_key
            if player_name in unit_name or unit_name in player_name:
                target_units.append((unit_key, unit_name, positions))
        
        print(f"Target player units found: {len(target_units)}")
        for unit_key, unit_name, positions in target_units:
            print(f"  {unit_name}: {len(positions)} positions")
        
        if not target_units:
            print(f"Available units: {list(unit_positions.keys())}")
            return {'error': f'No units found matching {player_name}'}
        
        # Analyze movement for the main target unit (most positions)
        main_unit = max(target_units, key=lambda x: len(x[2]))
        unit_key, unit_name, positions = main_unit
        
        print(f"\nAnalyzing movement for: {unit_name}")
        print(f"Position count: {len(positions)}")
        
        # Calculate movement segments
        movements = self._calculate_movements(unit_key, positions)
        
        print(f"Movement segments: {len(movements)}")
        
        # Analyze movement quality
        analysis = self._analyze_movement_quality(unit_name, movements, positions)
        
        # Flag large movements
        large_movements = [m for m in movements if m.speed > self.LARGE_MOVEMENT_THRESHOLD]
        print(f"Large movements flagged: {len(large_movements)}")
        
        for i, movement in enumerate(large_movements[:10]):  # Show first 10
            print(f"  Large Movement {i+1}: {movement.distance:.1f} units in {movement.time_diff:.3f}s = {movement.speed:.1f} u/s")
            print(f"    From: ({movement.start_pos.x:.1f}, {movement.start_pos.y:.1f}) at {movement.start_pos.timestamp}")
            print(f"    To: ({movement.end_pos.x:.1f}, {movement.end_pos.y:.1f}) at {movement.end_pos.timestamp}")
            print(f"    Events: {movement.start_pos.event_type} -> {movement.end_pos.event_type}")
        
        analysis.update({
            'filename': match_info['filename'],
            'target_player': player_name,
            'unit_analyzed': unit_name,
            'unit_key': unit_key,
            'arena_start': arena_start.isoformat(),
            'arena_end': arena_end.isoformat() if arena_end else None,
            'large_movements': len(large_movements),
            'large_movement_details': [
                {
                    'distance': m.distance,
                    'time_diff': m.time_diff,
                    'speed': m.speed,
                    'start_time': m.start_pos.timestamp.isoformat(),
                    'end_time': m.end_pos.timestamp.isoformat(),
                    'start_event': m.start_pos.event_type,
                    'end_event': m.end_pos.event_type
                }
                for m in large_movements[:20]  # First 20 large movements
            ]
        })
        
        return analysis
    
    def _parse_corrected_positions(self, log_file: Path, start_time: datetime, end_time: datetime) -> Dict[str, List[UnitPosition]]:
        """Parse position data with corrected per-unit tracking."""
        unit_positions = defaultdict(list)
        
        print(f"Parsing combat log from {start_time} to {end_time}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            line_count = 0
            parsed_actions = 0
            
            for line in f:
                line_count += 1
                
                action = CorrectedAdvancedCombatAction(line)
                
                if (action.timestamp and 
                    start_time <= action.timestamp <= end_time and
                    action.is_valid_position()):
                    
                    unit_key = action.get_unit_key()
                    
                    position = UnitPosition(
                        timestamp=action.timestamp,
                        x=action.position_x,
                        y=action.position_y,
                        facing=action.facing,
                        event_type=action.event,
                        unit_guid=action.source_guid,
                        unit_name=action.source_name,
                        hp_current=action.hp_current,
                        hp_max=action.hp_max,
                        raw_line=action.raw_line
                    )
                    
                    unit_positions[unit_key].append(position)
                    parsed_actions += 1
        
        print(f"Processed {line_count} lines, extracted {parsed_actions} position actions")
        
        # Sort positions by timestamp for each unit
        for unit_key in unit_positions:
            unit_positions[unit_key].sort(key=lambda p: p.timestamp)
        
        return dict(unit_positions)
    
    def _calculate_movements(self, unit_key: str, positions: List[UnitPosition]) -> List[MovementSegment]:
        """Calculate movement segments for a specific unit."""
        movements = []
        
        for i in range(1, len(positions)):
            start_pos = positions[i-1]
            end_pos = positions[i]
            
            # Calculate distance and movement metrics
            dx = end_pos.x - start_pos.x
            dy = end_pos.y - start_pos.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            time_diff = (end_pos.timestamp - start_pos.timestamp).total_seconds()
            speed = distance / time_diff if time_diff > 0 else float('inf')
            
            movement = MovementSegment(
                unit_guid=unit_key.split(':', 1)[0],
                unit_name=unit_key.split(':', 1)[1] if ':' in unit_key else unit_key,
                start_pos=start_pos,
                end_pos=end_pos,
                distance=distance,
                time_diff=time_diff,
                speed=speed,
                dx=dx,
                dy=dy
            )
            
            movements.append(movement)
        
        return movements
    
    def _analyze_movement_quality(self, unit_name: str, movements: List[MovementSegment], positions: List[UnitPosition]) -> Dict:
        """Analyze movement quality for a unit."""
        if not movements:
            return {'error': 'No movements to analyze'}
        
        # Calculate totals
        total_distance = sum(m.distance for m in movements)
        total_time = (positions[-1].timestamp - positions[0].timestamp).total_seconds()
        avg_speed = total_distance / total_time if total_time > 0 else 0
        
        # Calculate arena coverage
        x_coords = [p.x for p in positions]
        y_coords = [p.y for p in positions]
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        coverage_area = x_range * y_range
        
        # Movement quality flags
        large_movements = [m for m in movements if m.speed > self.LARGE_MOVEMENT_THRESHOLD]
        very_large_movements = [m for m in movements if m.speed > self.VERY_LARGE_MOVEMENT_THRESHOLD]
        teleport_movements = [m for m in movements if m.speed > self.TELEPORT_THRESHOLD]
        
        # Check for repetitive patterns (same coordinates)
        position_counts = defaultdict(int)
        for pos in positions:
            coord_key = f"{pos.x:.1f},{pos.y:.1f}"
            position_counts[coord_key] += 1
        
        max_position_repeats = max(position_counts.values()) if position_counts else 0
        repeated_positions = sum(1 for count in position_counts.values() if count > 5)
        
        return {
            'unit_name': unit_name,
            'total_distance': total_distance,
            'total_time': total_time,
            'average_speed': avg_speed,
            'position_count': len(positions),
            'movement_count': len(movements),
            'x_range': x_range,
            'y_range': y_range,
            'coverage_area': coverage_area,
            
            # Movement quality indicators
            'large_movements_count': len(large_movements),
            'very_large_movements_count': len(very_large_movements),
            'teleport_movements_count': len(teleport_movements),
            'max_speed': max(m.speed for m in movements),
            'max_distance_segment': max(m.distance for m in movements),
            
            # Pattern analysis
            'unique_positions': len(position_counts),
            'max_position_repeats': max_position_repeats,
            'repeated_positions': repeated_positions,
            
            # Quality flags
            'has_anomalous_patterns': repeated_positions > 10 or max_position_repeats > 20,
            'has_teleport_behavior': len(teleport_movements) > 5,
            'position_variety_ratio': len(position_counts) / len(positions) if positions else 0
        }

def main():
    """Test corrected movement tracking."""
    tracker = CorrectedMovementTracker(".")
    
    # Test with a known match
    test_match = {
        'filename': '2025-05-06_19-03-32_-_Phlurbotomy_-_3v3_Mugambala_(Win).mp4',
        'precise_start_time': '2025-05-06 19:04:28',
        'duration_s': 200
    }
    
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if log_file.exists():
        result = tracker.analyze_corrected_movement(log_file, test_match)
        
        # Save results
        output_file = "corrected_movement_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
    else:
        print(f"Log file not found: {log_file}")

if __name__ == "__main__":
    main()