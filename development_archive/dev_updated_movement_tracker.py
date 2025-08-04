#!/usr/bin/env python3
"""
Development: Updated Movement Tracker

Final production-ready movement tracker that:
1. Uses corrected WoWPedia-based position parsing
2. Properly handles multiple coordinate systems  
3. Integrates with production parser arena boundary detection
4. Provides comprehensive movement analysis with proper validation
"""

import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass
from collections import defaultdict

from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
from dev_production_ready_parser import ProductionAdvancedParser, ProductionCombatEvent

@dataclass
class MovementData:
    """Movement data for a specific unit."""
    unit_guid: str
    unit_name: str
    positions: List[ProductionCombatEvent]
    total_distance: float = 0.0
    movement_count: int = 0
    coordinate_systems_used: set = None
    large_movements: List[Dict] = None
    
    def __post_init__(self):
        if self.coordinate_systems_used is None:
            self.coordinate_systems_used = set()
        if self.large_movements is None:
            self.large_movements = []

class UpdatedMovementTracker:
    """Updated movement tracker with corrected position parsing."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.production_parser = EnhancedProductionCombatParser(base_dir)
        self.position_parser = ProductionAdvancedParser()
        
        # Movement analysis thresholds
        self.LARGE_MOVEMENT_THRESHOLD = 50.0
        self.VERY_LARGE_MOVEMENT_THRESHOLD = 100.0
        self.TELEPORT_THRESHOLD = 200.0
        
        # Coordinate system boundaries for movement validation
        self.COORDINATE_SYSTEM_BOUNDARIES = {
            'world_negative': ((-2000, -1900), (1200, 1400)),
            'world_positive': ((1200, 1400), (-10, 10)),
            'local_medium': ((-10, 10), (50, 350)),
            'local_small': ((-10, 10), (50, 150)),
            'mixed': ((-10, 10), (-2000, -1900))
        }
    
    def analyze_match_movement(self, log_file: Path, match_info: Dict) -> Dict:
        """Analyze movement for a specific match with corrected parsing."""
        print(f"\n{'='*80}")
        print(f"UPDATED MOVEMENT ANALYSIS")
        print(f"Match: {match_info['filename']}")
        print(f"Log: {log_file.name}")
        print(f"{'='*80}")
        
        # Get match details from production parser
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
        
        # Extract position data using corrected parser
        unit_movements = self._extract_movement_data(log_file, arena_start, arena_end, player_name)
        
        if not unit_movements:
            return {'error': 'No movement data found'}
        
        # Analyze movement for target player
        target_movement = self._find_target_player_movement(unit_movements, player_name)
        
        if not target_movement:
            return {'error': f'No movement data found for {player_name}'}
        
        # Perform movement analysis
        analysis_results = self._analyze_movement_patterns(target_movement)
        
        # Add match metadata
        analysis_results.update({
            'filename': match_info['filename'],
            'target_player': player_name,
            'arena_start': arena_start.isoformat(),
            'arena_end': arena_end.isoformat() if arena_end else None,
            'expected_bracket': expected_bracket,
            'expected_map': expected_map,
            'match_duration': match_duration
        })
        
        return analysis_results
    
    def _extract_movement_data(self, log_file: Path, start_time: datetime, end_time: datetime, target_player: str) -> Dict[str, MovementData]:
        """Extract movement data using corrected position parsing."""
        print(f"\nExtracting movement data from {start_time} to {end_time}")
        
        unit_movements = defaultdict(lambda: MovementData("", "", []))
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines_processed = 0
            events_with_position = 0
            
            for line in f:
                lines_processed += 1
                
                # Parse combat event
                event = self.position_parser.parse_combat_event(line)
                
                if (event and event.has_position_data and
                    start_time <= event.timestamp <= end_time):
                    
                    # Create unit key
                    unit_key = f"{event.source_guid}:{event.source_name}"
                    
                    # Initialize movement data if needed
                    if unit_key not in unit_movements:
                        unit_movements[unit_key] = MovementData(
                            event.source_guid, event.source_name, []
                        )
                    
                    # Add position event
                    unit_movements[unit_key].positions.append(event)
                    unit_movements[unit_key].coordinate_systems_used.add(event.coordinate_system)
                    events_with_position += 1
                
                if lines_processed % 10000 == 0:
                    print(f"  Processed {lines_processed:,} lines, found {events_with_position} position events...")
        
        print(f"Final results: {lines_processed:,} lines processed, {events_with_position} position events")
        print(f"Units with movement data: {len(unit_movements)}")
        
        # Sort positions by timestamp for each unit
        for unit_key, movement_data in unit_movements.items():
            movement_data.positions.sort(key=lambda x: x.timestamp)
            print(f"  {movement_data.unit_name}: {len(movement_data.positions)} positions, systems: {movement_data.coordinate_systems_used}")
        
        return dict(unit_movements)
    
    def _find_target_player_movement(self, unit_movements: Dict[str, MovementData], target_player: str) -> Optional[MovementData]:
        """Find movement data for the target player."""
        # Look for units matching the target player name
        matching_units = []
        
        for unit_key, movement_data in unit_movements.items():
            if (target_player in movement_data.unit_name or 
                movement_data.unit_name in target_player):
                matching_units.append((unit_key, movement_data))
        
        if not matching_units:
            print(f"No units found matching '{target_player}'")
            print(f"Available units: {[md.unit_name for md in unit_movements.values()]}")
            return None
        
        # Return the unit with the most position data
        best_match = max(matching_units, key=lambda x: len(x[1].positions))
        print(f"Selected unit: {best_match[1].unit_name} with {len(best_match[1].positions)} positions")
        
        return best_match[1]
    
    def _analyze_movement_patterns(self, movement_data: MovementData) -> Dict:
        """Analyze movement patterns with proper coordinate system handling."""
        positions = movement_data.positions
        
        if len(positions) < 2:
            return {'error': 'Insufficient position data for movement analysis'}
        
        print(f"\nAnalyzing movement for {movement_data.unit_name}")
        print(f"Position count: {len(positions)}")
        print(f"Time span: {positions[0].timestamp} to {positions[-1].timestamp}")
        print(f"Coordinate systems: {movement_data.coordinate_systems_used}")
        
        # Calculate movements between consecutive positions
        movements = []
        total_distance = 0.0
        coordinate_system_transitions = 0
        large_movements = []
        
        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]
            
            # Calculate distance
            dx = curr_pos.position_x - prev_pos.position_x
            dy = curr_pos.position_y - prev_pos.position_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Calculate time difference
            time_diff = (curr_pos.timestamp - prev_pos.timestamp).total_seconds()
            speed = distance / time_diff if time_diff > 0 else float('inf')
            
            # Check for coordinate system transitions
            if prev_pos.coordinate_system != curr_pos.coordinate_system:
                coordinate_system_transitions += 1
            
            movement = {
                'distance': distance,
                'time_diff': time_diff,
                'speed': speed,
                'dx': dx,
                'dy': dy,
                'start_system': prev_pos.coordinate_system,
                'end_system': curr_pos.coordinate_system,
                'system_transition': prev_pos.coordinate_system != curr_pos.coordinate_system,
                'start_time': prev_pos.timestamp,
                'end_time': curr_pos.timestamp,
                'start_pos': (prev_pos.position_x, prev_pos.position_y),
                'end_pos': (curr_pos.position_x, curr_pos.position_y)
            }
            
            movements.append(movement)
            total_distance += distance
            
            # Flag large movements
            if speed > self.LARGE_MOVEMENT_THRESHOLD:
                large_movements.append(movement)
        
        # Calculate movement statistics
        if movements:
            total_time = (positions[-1].timestamp - positions[0].timestamp).total_seconds()
            avg_speed = total_distance / total_time if total_time > 0 else 0
            max_speed = max(m['speed'] for m in movements if m['speed'] != float('inf'))
            max_distance = max(m['distance'] for m in movements)
        else:
            total_time = avg_speed = max_speed = max_distance = 0
        
        # Analyze coordinate coverage
        x_coords = [pos.position_x for pos in positions]
        y_coords = [pos.position_y for pos in positions]
        x_range = max(x_coords) - min(x_coords) if x_coords else 0
        y_range = max(y_coords) - min(y_coords) if y_coords else 0
        
        # Classify large movements
        large_movement_details = []
        teleport_movements = []
        system_transition_movements = []
        
        for movement in large_movements:
            movement_detail = {
                'distance': movement['distance'],
                'speed': movement['speed'],
                'time_diff': movement['time_diff'],
                'system_transition': movement['system_transition'],
                'start_system': movement['start_system'],
                'end_system': movement['end_system'],
                'start_time': movement['start_time'].isoformat(),
                'classification': self._classify_movement(movement)
            }
            
            large_movement_details.append(movement_detail)
            
            if movement['speed'] > self.TELEPORT_THRESHOLD:
                teleport_movements.append(movement_detail)
            
            if movement['system_transition']:
                system_transition_movements.append(movement_detail)
        
        # Print movement analysis
        print(f"Movement Analysis Results:")
        print(f"  Total distance: {total_distance:.2f} units")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Average speed: {avg_speed:.2f} u/s")
        print(f"  Max speed: {max_speed:.2f} u/s")
        print(f"  Movement segments: {len(movements)}")
        print(f"  Large movements (>{self.LARGE_MOVEMENT_THRESHOLD} u/s): {len(large_movements)}")
        print(f"  Teleport movements (>{self.TELEPORT_THRESHOLD} u/s): {len(teleport_movements)}")
        print(f"  Coordinate system transitions: {coordinate_system_transitions}")
        
        # Show coordinate system usage
        system_usage = defaultdict(int)
        for pos in positions:
            system_usage[pos.coordinate_system] += 1
        
        print(f"  Coordinate system usage:")
        for system, count in system_usage.items():
            percentage = count / len(positions) * 100
            print(f"    {system}: {count} positions ({percentage:.1f}%)")
        
        return {
            'unit_name': movement_data.unit_name,
            'unit_guid': movement_data.unit_guid,
            'position_count': len(positions),
            'movement_count': len(movements),
            'total_distance': total_distance,
            'total_time': total_time,
            'average_speed': avg_speed,
            'max_speed': max_speed,
            'max_distance': max_distance,
            'x_range': x_range,
            'y_range': y_range,
            'coordinate_systems_used': list(movement_data.coordinate_systems_used),
            'coordinate_system_transitions': coordinate_system_transitions,
            'system_usage': dict(system_usage),
            'large_movements_count': len(large_movements),
            'teleport_movements_count': len(teleport_movements),
            'system_transition_movements_count': len(system_transition_movements),
            'large_movement_details': large_movement_details[:20],  # First 20
            'movement_quality_flags': {
                'has_multiple_coordinate_systems': len(movement_data.coordinate_systems_used) > 1,
                'has_teleport_behavior': len(teleport_movements) > 0,
                'has_system_transitions': coordinate_system_transitions > 0,
                'movement_variety_good': len(movements) > 10,
                'coordinate_coverage_good': x_range > 20 and y_range > 20
            }
        }
    
    def _classify_movement(self, movement: Dict) -> str:
        """Classify a movement based on its characteristics."""
        if movement['system_transition']:
            return "coordinate_system_transition"
        elif movement['speed'] > self.TELEPORT_THRESHOLD:
            return "teleportation"
        elif movement['speed'] > self.VERY_LARGE_MOVEMENT_THRESHOLD:
            return "very_large_movement"
        elif movement['speed'] > self.LARGE_MOVEMENT_THRESHOLD:
            return "large_movement"
        else:
            return "normal_movement"

def test_updated_tracker():
    """Test the updated movement tracker."""
    tracker = UpdatedMovementTracker(".")
    
    # Test with known match
    test_match = {
        'filename': '2025-05-06_19-03-32_-_Phlurbotomy_-_3v3_Mugambala_(Win).mp4',
        'precise_start_time': '2025-05-06 19:04:28',
        'duration_s': 200
    }
    
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if log_file.exists():
        print("TESTING UPDATED MOVEMENT TRACKER")
        print("=" * 80)
        
        result = tracker.analyze_match_movement(log_file, test_match)
        
        # Save results
        output_file = "updated_movement_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
        if 'error' not in result:
            print(f"\nSUMMARY:")
            print(f"  Player: {result['unit_name']}")
            print(f"  Total Distance: {result['total_distance']:.2f} units")
            print(f"  Average Speed: {result['average_speed']:.2f} u/s")
            print(f"  Large Movements: {result['large_movements_count']}")
            print(f"  Coordinate Systems: {len(result['coordinate_systems_used'])}")
            print(f"  System Transitions: {result['coordinate_system_transitions']}")
        
    else:
        print(f"Log file not found: {log_file}")

if __name__ == "__main__":
    test_updated_tracker()