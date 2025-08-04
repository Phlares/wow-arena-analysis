#!/usr/bin/env python3
"""
Development: Coordinate System Analyzer

Based on the ListOfAdvancedParameters image and warcraft.wiki.gg documentation,
this analyzer properly identifies position coordinates at advanced parameter 
indices 13 and 14, validating each event type individually.

Key insights from documentation:
- Position coordinates are at advanced parameter indices 13 and 14
- Format: floating-point numbers with 2 decimal places (####.##, ##.##)
- Not all events have position data - need per-event-type validation
- Coordinates represent world space positioning
- Advanced parameters start after: 9 base + 0-3 prefix parameters
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json

class CoordinateSystemAnalyzer:
    """Analyzes combat log coordinate systems with proper parameter validation."""
    
    def __init__(self):
        # Track which event types have been validated for coordinates
        self.event_coordinate_validation = {}
        self.coordinate_examples = defaultdict(list)
        
    def analyze_event_coordinates(self, log_file: Path, max_lines: int = 100000) -> Dict:
        """Analyze coordinates by event type with proper validation."""
        print("COORDINATE SYSTEM ANALYZER")
        print("=" * 80)
        print(f"Analyzing: {log_file.name}")
        print(f"Max lines: {max_lines:,}")
        print("Based on ListOfAdvancedParameters documentation:")
        print("- Position coordinates at advanced parameter indices 13 and 14")
        print("- Format: ####.## (floating-point with 2 decimal places)")
        print()
        
        event_stats = defaultdict(lambda: {
            'total_count': 0,
            'coordinate_count': 0,
            'parameter_counts': defaultdict(int),
            'coordinate_examples': [],
            'has_coordinates': None
        })
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line_num > max_lines:
                    break
                
                if line_num % 25000 == 0:
                    print(f"  Processed {line_num:,} lines...")
                
                # Parse the combat log line
                parsed = self._parse_combat_line(line)
                if not parsed:
                    continue
                
                event_type = parsed['event_type']
                param_count = parsed['parameter_count']
                
                # Update statistics
                event_stats[event_type]['total_count'] += 1
                event_stats[event_type]['parameter_counts'][param_count] += 1
                
                # Check for coordinates if we have enough parameters
                if param_count >= 25:  # Need sufficient parameters for advanced logging
                    coordinate_data = self._extract_coordinates(parsed['parameters'], event_type)
                    
                    if coordinate_data:
                        event_stats[event_type]['coordinate_count'] += 1
                        
                        # Store examples (up to 3 per event type)
                        if len(event_stats[event_type]['coordinate_examples']) < 3:
                            event_stats[event_type]['coordinate_examples'].append({
                                'line_number': line_num,
                                'timestamp': parsed['timestamp'],
                                'source_name': parsed['source_name'],
                                'coordinates': coordinate_data,
                                'parameter_count': param_count,
                                'raw_line': line.strip()[:200] + "..." if len(line.strip()) > 200 else line.strip()
                            })
        
        # Determine which event types have coordinates
        for event_type, stats in event_stats.items():
            if stats['coordinate_count'] > 0:
                stats['has_coordinates'] = True
                coordinate_rate = stats['coordinate_count'] / stats['total_count'] * 100
                stats['coordinate_rate'] = coordinate_rate
            else:
                stats['has_coordinates'] = False
                stats['coordinate_rate'] = 0.0
        
        # Display results
        self._display_analysis_results(event_stats)
        
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
    
    def _extract_coordinates(self, params: List[str], event_type: str) -> Optional[Dict]:
        """Extract coordinates using the correct advanced parameter positioning."""
        # Based on the ListOfAdvancedParameters image:
        # Advanced parameters start after base (9) + prefix (0-3) parameters
        # Position coordinates are at advanced parameter indices 13 and 14
        
        # Determine where advanced parameters start based on event type
        advanced_starts = self._determine_advanced_start_positions(params, event_type)
        
        for advanced_start in advanced_starts:
            # Position coordinates are at advanced indices 13 and 14
            pos_x_idx = advanced_start + 12  # Advanced parameter 13 (0-based = 12)
            pos_y_idx = advanced_start + 13  # Advanced parameter 14 (0-based = 13)
            
            if pos_x_idx < len(params) and pos_y_idx < len(params):
                try:
                    x_str = params[pos_x_idx].strip()
                    y_str = params[pos_y_idx].strip()
                    
                    # Check if these match coordinate format (####.##)
                    if self._is_coordinate_format(x_str) and self._is_coordinate_format(y_str):
                        x = float(x_str)
                        y = float(y_str)
                        
                        # Validate coordinate ranges (reasonable world coordinates)
                        if abs(x) < 50000 and abs(y) < 50000 and (abs(x) > 0.01 or abs(y) > 0.01):
                            return {
                                'position_x': x,
                                'position_y': y,
                                'x_parameter_index': pos_x_idx,
                                'y_parameter_index': pos_y_idx,
                                'advanced_start_index': advanced_start,
                                'coordinate_format': f"{x_str}, {y_str}",
                                'coordinate_system': self._classify_coordinate_system(x, y)
                            }
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _determine_advanced_start_positions(self, params: List[str], event_type: str) -> List[int]:
        """Determine possible starting positions for advanced parameters."""
        # Based on combat log structure from documentation:
        # 9 base + 0-3 prefix + 17 advanced + 0-10 suffix
        
        possible_starts = []
        
        if event_type.startswith('SPELL_'):
            # SPELL events typically have 3 prefix parameters (spell info)
            possible_starts.append(12)  # 9 base + 3 spell prefix
            
            # Some spell events have additional damage/heal parameters
            if 'DAMAGE' in event_type or 'HEAL' in event_type:
                possible_starts.append(22)  # 9 base + 3 spell + 10 damage/heal
            elif 'ENERGIZE' in event_type:
                possible_starts.append(15)  # 9 base + 3 spell + 3 energize
                
        elif event_type.startswith('SWING_'):
            # SWING events have no spell prefix, but may have damage parameters
            possible_starts.append(9)   # 9 base only
            possible_starts.append(19)  # 9 base + 10 damage
            
        elif event_type.startswith('RANGE_'):
            # RANGE events may have weapon info + damage parameters
            possible_starts.append(12)  # 9 base + 3 weapon
            possible_starts.append(22)  # 9 base + 3 weapon + 10 damage
            
        else:
            # For unknown event types, try common positions
            possible_starts.extend([9, 12, 15, 19, 22])
        
        return possible_starts
    
    def _is_coordinate_format(self, value: str) -> bool:
        """Check if a value matches coordinate format (####.##)."""
        # Look for floating point numbers with exactly 2 decimal places
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
    
    def _display_analysis_results(self, event_stats: Dict):
        """Display the analysis results."""
        print(f"\n{'='*80}")
        print("COORDINATE ANALYSIS RESULTS")
        print("=" * 80)
        
        # Sort event types by coordinate count
        events_with_coords = []
        events_without_coords = []
        
        for event_type, stats in event_stats.items():
            if stats['has_coordinates']:
                events_with_coords.append((event_type, stats))
            else:
                events_without_coords.append((event_type, stats))
        
        # Display events WITH coordinates
        print(f"\nEVENT TYPES WITH COORDINATES ({len(events_with_coords)}):")
        print("-" * 60)
        
        events_with_coords.sort(key=lambda x: x[1]['coordinate_count'], reverse=True)
        
        for event_type, stats in events_with_coords:
            print(f"\n{event_type}:")
            print(f"  Total events: {stats['total_count']:,}")
            print(f"  With coordinates: {stats['coordinate_count']:,} ({stats['coordinate_rate']:.1f}%)")
            print(f"  Parameter counts: {dict(stats['parameter_counts'])}")
            
            # Show coordinate examples
            for i, example in enumerate(stats['coordinate_examples']):
                coord_data = example['coordinates']
                print(f"  Example {i+1} (Line {example['line_number']:,}):")
                print(f"    Source: {example['source_name']}")
                print(f"    Coordinates: ({coord_data['position_x']:.2f}, {coord_data['position_y']:.2f})")
                print(f"    System: {coord_data['coordinate_system']}")
                print(f"    Parameter indices: {coord_data['x_parameter_index']}-{coord_data['y_parameter_index']}")
                print(f"    Advanced start: {coord_data['advanced_start_index']}")
                print(f"    Format: {coord_data['coordinate_format']}")
        
        # Display events WITHOUT coordinates (top 10)
        print(f"\n\nEVENT TYPES WITHOUT COORDINATES (Top 10 by frequency):")
        print("-" * 60)
        
        events_without_coords.sort(key=lambda x: x[1]['total_count'], reverse=True)
        
        for event_type, stats in events_without_coords[:10]:
            print(f"{event_type}: {stats['total_count']:,} events")
            if stats['parameter_counts']:
                common_param_count = max(stats['parameter_counts'].keys(), 
                                       key=lambda x: stats['parameter_counts'][x])
                print(f"  Most common parameter count: {common_param_count}")
        
        # Summary
        total_events_with_coords = sum(s['coordinate_count'] for s in event_stats.values())
        total_events = sum(s['total_count'] for s in event_stats.values())
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print("=" * 80)
        print(f"Total event types analyzed: {len(event_stats)}")
        print(f"Event types with coordinates: {len(events_with_coords)}")
        print(f"Event types without coordinates: {len(events_without_coords)}")
        print(f"Total events with coordinates: {total_events_with_coords:,}")
        print(f"Total events processed: {total_events:,}")
        if total_events > 0:
            print(f"Overall coordinate rate: {total_events_with_coords/total_events*100:.2f}%")
        
        # Coordinate system distribution
        if events_with_coords:
            print(f"\nCOORDINATE SYSTEM DISTRIBUTION:")
            print("-" * 40)
            system_counts = defaultdict(int)
            for event_type, stats in events_with_coords:
                for example in stats['coordinate_examples']:
                    system_counts[example['coordinates']['coordinate_system']] += 1
            
            for system, count in sorted(system_counts.items()):
                print(f"  {system}: {count} examples")

def test_coordinate_analyzer():
    """Test the coordinate system analyzer."""
    analyzer = CoordinateSystemAnalyzer()
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        available_logs = list(Path("./Logs").glob("*.txt"))
        if available_logs:
            print("Available log files:")
            for log in available_logs[:5]:
                print(f"  {log.name}")
        return
    
    # Analyze coordinates
    results = analyzer.analyze_event_coordinates(log_file, max_lines=100000)
    
    # Save results
    output_file = "coordinate_system_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    test_coordinate_analyzer()