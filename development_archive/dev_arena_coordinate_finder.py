#!/usr/bin/env python3
"""
Arena Coordinate Finder

Focuses specifically on arena match times to find coordinate data,
since advanced logging may only be enabled during PvP matches.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import json

class ArenaCoordinateFinder:
    """Finds coordinates specifically during arena match times."""
    
    def __init__(self):
        self.coordinate_examples = defaultdict(list)
        
    def find_arena_coordinates(self, log_file: Path) -> Dict:
        """Find coordinates during known arena match times."""
        print("ARENA COORDINATE FINDER")
        print("=" * 80)
        print(f"Analyzing: {log_file.name}")
        print("Focusing on arena match times (19:04-19:08 range)")
        print()
        
        # Focus on known arena times from our previous analysis
        arena_pattern = r"5/6/2025 19:0[4-8]:[0-5][0-9]"
        
        event_stats = defaultdict(lambda: {
            'total_count': 0,
            'coordinate_count': 0,
            'coordinate_examples': []
        })
        
        lines_in_arena_time = 0
        total_coordinates_found = 0
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Only process lines during arena time
                if not re.search(arena_pattern, line):
                    continue
                
                lines_in_arena_time += 1
                
                if lines_in_arena_time % 1000 == 0:
                    print(f"  Processed {lines_in_arena_time:,} arena-time lines...")
                
                # Parse the combat log line
                parsed = self._parse_combat_line(line)
                if not parsed:
                    continue
                
                event_type = parsed['event_type']
                param_count = parsed['parameter_count']
                
                # Update statistics
                event_stats[event_type]['total_count'] += 1
                
                # Check for coordinates with sufficient parameters
                if param_count >= 25:
                    coordinate_data = self._extract_coordinates_comprehensive(parsed['parameters'], event_type)
                    
                    if coordinate_data:
                        event_stats[event_type]['coordinate_count'] += 1
                        total_coordinates_found += 1
                        
                        # Store examples (up to 5 per event type)
                        if len(event_stats[event_type]['coordinate_examples']) < 5:
                            event_stats[event_type]['coordinate_examples'].append({
                                'line_number': line_num,
                                'timestamp': parsed['timestamp'],
                                'source_name': parsed['source_name'],
                                'coordinates': coordinate_data,
                                'parameter_count': param_count,
                                'raw_line': line.strip()
                            })
        
        print(f"Arena-time lines processed: {lines_in_arena_time:,}")
        print(f"Total coordinates found: {total_coordinates_found}")
        
        # Calculate coordinate rates
        for event_type, stats in event_stats.items():
            if stats['coordinate_count'] > 0:
                stats['coordinate_rate'] = stats['coordinate_count'] / stats['total_count'] * 100
            else:
                stats['coordinate_rate'] = 0.0
        
        # Display results
        self._display_arena_results(event_stats)
        
        return dict(event_stats)
    
    def _parse_combat_line(self, line: str) -> Optional[Dict]:
        """Parse a combat log line into components."""
        if not line.strip():
            return None
        
        # Split timestamp from event data
        parts = line.strip().split('  ', 1)
        if len(parts) != 2:
            return None
        
        timestamp_str, event_data = parts
        
        # Parse timestamp
        try:
            clean_timestamp = re.sub(r'[+-]\d+$', '', timestamp_str)
            timestamp = datetime.strptime(clean_timestamp, "%m/%d/%Y %H:%M:%S.%f")
        except ValueError:
            return None
        
        # Split parameters
        params = [p.strip() for p in event_data.split(',')]
        if len(params) < 3:
            return None
        
        # Extract basic info
        event_type = params[0]
        source_name = self._extract_quoted_name(params[2]) if len(params) > 2 else ""
        
        return {
            'timestamp': timestamp,
            'event_type': event_type,
            'source_name': source_name,
            'parameter_count': len(params),
            'parameters': params
        }
    
    def _extract_quoted_name(self, param: str) -> str:
        """Extract name from quoted parameter."""
        if param.startswith('"') and param.endswith('"'):
            return param[1:-1]
        return param
    
    def _extract_coordinates_comprehensive(self, params: List[str], event_type: str) -> Optional[Dict]:
        """Comprehensive coordinate extraction trying multiple positions."""
        
        # Try all possible advanced start positions for this event type
        possible_starts = self._get_all_possible_advanced_starts(event_type, len(params))
        
        for advanced_start in possible_starts:
            # Try coordinates at advanced indices 13 and 14
            pos_x_idx = advanced_start + 12  # Advanced parameter 13
            pos_y_idx = advanced_start + 13  # Advanced parameter 14
            
            if pos_x_idx < len(params) and pos_y_idx < len(params):
                coordinate_data = self._try_extract_at_position(params, pos_x_idx, pos_y_idx, advanced_start)
                if coordinate_data:
                    return coordinate_data
        
        # If standard positions didn't work, scan for coordinate patterns
        return self._scan_for_coordinate_pattern(params)
    
    def _get_all_possible_advanced_starts(self, event_type: str, param_count: int) -> List[int]:
        """Get all possible advanced start positions for an event type."""
        possible_starts = []
        
        # Based on event type patterns
        if event_type.startswith('SPELL_'):
            if 'CAST_SUCCESS' in event_type:
                possible_starts.append(12)  # 9 base + 3 spell
            elif 'DAMAGE' in event_type or 'HEAL' in event_type:
                possible_starts.extend([12, 22])  # With/without damage params
            elif 'ENERGIZE' in event_type:
                possible_starts.extend([12, 15])  # With/without energize params
            else:
                possible_starts.extend([12, 15, 19, 22])
        elif event_type.startswith('SWING_'):
            possible_starts.extend([9, 19])  # With/without damage
        elif event_type.startswith('RANGE_'):
            possible_starts.extend([12, 22])  # With/without damage
        else:
            # Try common positions
            possible_starts.extend([9, 12, 15, 19, 22])
        
        # Also try positions based on parameter count patterns we observed
        if param_count == 31:
            possible_starts.append(12)  # SPELL_CAST_SUCCESS pattern
        elif param_count == 36:
            possible_starts.append(12)  # SPELL_HEAL pattern  
        elif param_count == 42:
            possible_starts.append(22)  # SPELL_DAMAGE pattern
        
        # Remove duplicates and sort
        return sorted(list(set(possible_starts)))
    
    def _try_extract_at_position(self, params: List[str], x_idx: int, y_idx: int, advanced_start: int) -> Optional[Dict]:
        """Try to extract coordinates at specific parameter positions."""
        try:
            x_str = params[x_idx].strip()
            y_str = params[y_idx].strip()
            
            # Check coordinate format (####.##)
            if self._is_coordinate_format(x_str) and self._is_coordinate_format(y_str):
                x = float(x_str)
                y = float(y_str)
                
                # Validate coordinate ranges
                if abs(x) < 50000 and abs(y) < 50000 and (abs(x) > 0.01 or abs(y) > 0.01):
                    return {
                        'position_x': x,
                        'position_y': y,
                        'x_parameter_index': x_idx,
                        'y_parameter_index': y_idx,
                        'advanced_start_index': advanced_start,
                        'coordinate_format': f"{x_str}, {y_str}",
                        'coordinate_system': self._classify_coordinate_system(x, y),
                        'extraction_method': 'standard_position'
                    }
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _scan_for_coordinate_pattern(self, params: List[str]) -> Optional[Dict]:
        """Scan entire parameter list for coordinate patterns."""
        # Look for consecutive parameters matching coordinate format
        for i in range(len(params) - 1):
            try:
                x_str = params[i].strip()
                y_str = params[i + 1].strip()
                
                if self._is_coordinate_format(x_str) and self._is_coordinate_format(y_str):
                    x = float(x_str)
                    y = float(y_str)
                    
                    # Validate coordinate ranges
                    if abs(x) < 50000 and abs(y) < 50000 and (abs(x) > 0.01 or abs(y) > 0.01):
                        return {
                            'position_x': x,
                            'position_y': y,
                            'x_parameter_index': i,
                            'y_parameter_index': i + 1,
                            'advanced_start_index': None,
                            'coordinate_format': f"{x_str}, {y_str}",
                            'coordinate_system': self._classify_coordinate_system(x, y),
                            'extraction_method': 'pattern_scan'
                        }
            except (ValueError, IndexError):
                continue
        
        return None
    
    def _is_coordinate_format(self, value: str) -> bool:
        """Check if a value matches coordinate format (####.##)."""
        pattern = r'^-?\d+\.\d{2}$'
        return bool(re.match(pattern, value))
    
    def _classify_coordinate_system(self, x: float, y: float) -> str:
        """Classify coordinate system based on coordinate ranges."""
        if abs(x) < 100 and abs(y) < 100:
            return "local_small"
        elif abs(x) < 1000 and abs(y) < 1000:
            return "local_medium"
        elif x < -1000:
            return "world_negative"
        elif x > 1000:
            return "world_positive"
        else:
            return "mixed"
    
    def _display_arena_results(self, event_stats: Dict):
        """Display arena coordinate analysis results."""
        print(f"\n{'='*80}")
        print("ARENA COORDINATE ANALYSIS RESULTS")
        print("=" * 80)
        
        # Events with coordinates
        events_with_coords = [(et, stats) for et, stats in event_stats.items() 
                             if stats['coordinate_count'] > 0]
        events_with_coords.sort(key=lambda x: x[1]['coordinate_count'], reverse=True)
        
        if events_with_coords:
            print(f"\nEVENT TYPES WITH COORDINATES ({len(events_with_coords)}):")
            print("-" * 60)
            
            for event_type, stats in events_with_coords:
                print(f"\n{event_type}:")
                print(f"  Total events: {stats['total_count']:,}")
                print(f"  With coordinates: {stats['coordinate_count']:,} ({stats['coordinate_rate']:.1f}%)")
                
                # Show coordinate examples
                for i, example in enumerate(stats['coordinate_examples']):
                    coord_data = example['coordinates']
                    print(f"\n  Example {i+1} (Line {example['line_number']:,}):")
                    print(f"    Time: {example['timestamp'].strftime('%H:%M:%S.%f')[:-3]}")
                    print(f"    Source: {example['source_name']}")
                    print(f"    Coordinates: ({coord_data['position_x']:.2f}, {coord_data['position_y']:.2f})")
                    print(f"    System: {coord_data['coordinate_system']}")
                    print(f"    Method: {coord_data['extraction_method']}")
                    print(f"    Parameter indices: {coord_data['x_parameter_index']}-{coord_data['y_parameter_index']}")
                    if coord_data['advanced_start_index'] is not None:
                        print(f"    Advanced start: {coord_data['advanced_start_index']}")
                    print(f"    Parameters: {example['parameter_count']}")
        else:
            print("\nNo coordinates found during arena time.")
        
        # Summary
        total_coords = sum(stats['coordinate_count'] for stats in event_stats.values())
        total_events = sum(stats['total_count'] for stats in event_stats.values())
        
        print(f"\n{'='*80}")
        print("ARENA SUMMARY")
        print("=" * 80)
        print(f"Event types analyzed: {len(event_stats)}")
        print(f"Event types with coordinates: {len(events_with_coords)}")
        print(f"Total coordinates found: {total_coords:,}")
        print(f"Total arena events: {total_events:,}")
        if total_events > 0:
            print(f"Arena coordinate rate: {total_coords/total_events*100:.2f}%")

def test_arena_finder():
    """Test the arena coordinate finder."""
    finder = ArenaCoordinateFinder()
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    # Find arena coordinates
    results = finder.find_arena_coordinates(log_file)
    
    # Save results
    output_file = "arena_coordinate_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    test_arena_finder()