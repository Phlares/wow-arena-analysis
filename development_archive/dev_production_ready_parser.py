#!/usr/bin/env python3
"""
Development: Production-Ready Advanced Combat Log Parser

Based on analysis of actual combat log format, this parser correctly extracts
position data from real WoW combat logs with advanced logging enabled.

Key findings from format analysis:
- SPELL_CAST_SUCCESS: 31 parameters, position at index 26-27
- SPELL_HEAL: 36 parameters, position at index 26-27  
- SPELL_DAMAGE: 42 parameters, position at index varies

Position coordinates are consistently at parameters 26-27 for most events.
"""

import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ProductionCombatEvent:
    """Production-ready combat event with validated position data."""
    timestamp: datetime
    event_type: str
    source_guid: str
    source_name: str
    dest_guid: str = ""
    dest_name: str = ""
    spell_id: Optional[int] = None
    spell_name: Optional[str] = None
    
    # Advanced parameters
    current_hp: int = 0
    max_hp: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    facing: float = 0.0
    level: int = 0
    
    # Metadata
    has_position_data: bool = False
    coordinate_system: str = "unknown"
    parameter_count: int = 0
    raw_line: str = ""

class ProductionAdvancedParser:
    """Production-ready parser based on actual log format analysis."""
    
    POSITION_EVENTS = {
        'SPELL_CAST_SUCCESS', 'SPELL_CAST_START', 'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE',
        'SPELL_HEAL', 'SPELL_PERIODIC_HEAL', 'SPELL_ENERGIZE', 'SPELL_PERIODIC_ENERGIZE',
        'SWING_DAMAGE', 'SWING_DAMAGE_LANDED', 'RANGE_DAMAGE'
    }
    
    def parse_combat_event(self, line: str) -> Optional[ProductionCombatEvent]:
        """Parse combat event from actual combat log format."""
        if not line.strip():
            return None
        
        # Split timestamp from event data
        parts = line.strip().split('  ', 1)
        if len(parts) != 2:
            return None
        
        timestamp_str, event_data = parts
        
        # Parse timestamp
        timestamp = self._parse_timestamp(timestamp_str)
        if not timestamp:
            return None
        
        # Split parameters by comma
        params = [p.strip() for p in event_data.split(',')]
        if len(params) < 9:
            return None
        
        # Extract base information
        event_type = params[0]
        if event_type not in self.POSITION_EVENTS:
            return None
        
        # Create event object
        event = ProductionCombatEvent(
            timestamp=timestamp,
            event_type=event_type,
            source_guid=params[1],
            source_name=self._extract_quoted_name(params[2]),
            dest_guid=params[5] if len(params) > 5 else "",
            dest_name=self._extract_quoted_name(params[6]) if len(params) > 6 else "",
            parameter_count=len(params),
            raw_line=line.strip()
        )
        
        # Extract spell information for spell events
        if event_type.startswith('SPELL_') and len(params) > 11:
            try:
                event.spell_id = int(params[9])
                event.spell_name = self._extract_quoted_name(params[10])
            except (ValueError, IndexError):
                pass
        
        # Parse position data based on parameter count patterns
        self._parse_position_data(event, params)
        
        return event
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp with timezone handling."""
        try:
            # Remove timezone offset: "5/6/2025 19:04:25.703-4"
            clean_timestamp = re.sub(r'[+-]\d+$', '', timestamp_str)
            return datetime.strptime(clean_timestamp, "%m/%d/%Y %H:%M:%S.%f")
        except ValueError:
            return None
    
    def _extract_quoted_name(self, param: str) -> str:
        """Extract name from quoted parameter."""
        if param.startswith('"') and param.endswith('"'):
            return param[1:-1]
        return param
    
    def _parse_position_data(self, event: ProductionCombatEvent, params: List[str]):
        """Parse position data based on actual log format patterns."""
        param_count = len(params)
        
        # Based on format analysis, position data locations:
        position_indices = []
        
        if param_count == 31:  # SPELL_CAST_SUCCESS format
            position_indices = [26, 27]  # Position X, Y
            health_indices = [14, 15]    # Current HP, Max HP
            level_index = 30             # Level/ItemLevel
            facing_index = 29            # Facing
            
        elif param_count == 36:  # SPELL_HEAL format
            position_indices = [26, 27]  # Position X, Y
            health_indices = [14, 15]    # Current HP, Max HP
            level_index = 30             # Level/ItemLevel
            facing_index = 29            # Facing
            
        elif param_count == 42:  # SPELL_DAMAGE format (needs investigation)
            # For 42-parameter format, position might be in different location
            # We'll search for it in the likely range
            self._search_for_position(event, params)
            return
            
        else:
            # For other formats, search for position data
            self._search_for_position(event, params)
            return
        
        # Extract position data using known indices
        try:
            if len(position_indices) == 2 and all(idx < len(params) for idx in position_indices):
                x = float(params[position_indices[0]])
                y = float(params[position_indices[1]])
                
                # Validate coordinates
                if abs(x) < 10000 and abs(y) < 10000 and (abs(x) > 0.1 or abs(y) > 0.1):
                    event.position_x = x
                    event.position_y = y
                    event.has_position_data = True
                    event.coordinate_system = self._classify_coordinate_system(x, y)
                    
                    # Extract additional data
                    if health_indices and all(idx < len(params) for idx in health_indices):
                        event.current_hp = int(params[health_indices[0]])
                        event.max_hp = int(params[health_indices[1]])
                    
                    if facing_index and facing_index < len(params):
                        event.facing = float(params[facing_index])
                    
                    if level_index and level_index < len(params):
                        event.level = int(params[level_index])
                        
        except (ValueError, IndexError):
            # Failed to extract position data
            pass
    
    def _search_for_position(self, event: ProductionCombatEvent, params: List[str]):
        """Search for position data in parameter list (fallback method)."""
        # Look for position coordinates in the last ~15 parameters
        for i in range(max(0, len(params) - 15), len(params) - 1):
            try:
                x = float(params[i])
                y = float(params[i + 1])
                
                # Validate coordinates - look for reasonable position data
                if abs(x) < 10000 and abs(y) < 10000:
                    if abs(x) > 10 or abs(y) > 10:  # Non-trivial coordinates
                        event.position_x = x
                        event.position_y = y
                        event.has_position_data = True
                        event.coordinate_system = self._classify_coordinate_system(x, y)
                        
                        # Try to find facing data nearby
                        for offset in [2, 3, 4]:
                            if i + offset < len(params):
                                try:
                                    facing = float(params[i + offset])
                                    if 0 <= facing <= 6.5:  # Reasonable facing range
                                        event.facing = facing
                                        break
                                except ValueError:
                                    pass
                        
                        # Try to find level data nearby  
                        for offset in [3, 4, 5]:
                            if i + offset < len(params):
                                try:
                                    level = int(params[i + offset])
                                    if 1 <= level <= 1000:  # Reasonable level range
                                        event.level = level
                                        break
                                except ValueError:
                                    pass
                        
                        return
                        
            except (ValueError, IndexError):
                continue
    
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

def test_production_parser():
    """Test production parser with real arena log data."""
    parser = ProductionAdvancedParser()
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print("PRODUCTION PARSER TEST")
    print("=" * 60)
    print(f"Testing with: {log_file.name}")
    print()
    
    # Test with arena time examples we found
    arena_pattern = r"5/6/2025 19:04:[23456][0-9]"
    successful_extractions = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines_processed = 0
        events_parsed = 0
        position_events = 0
        
        for line in f:
            lines_processed += 1
            
            # Focus on arena time for testing
            if re.search(arena_pattern, line):
                # Only test position events
                if any(event_type in line for event_type in parser.POSITION_EVENTS):
                    event = parser.parse_combat_event(line)
                    
                    if event:
                        events_parsed += 1
                        
                        if event.has_position_data:
                            position_events += 1
                            
                            # Store successful extractions
                            if len(successful_extractions) < 10:
                                successful_extractions.append({
                                    'timestamp': event.timestamp.strftime("%H:%M:%S.%f")[:-3],
                                    'event_type': event.event_type,
                                    'source_name': event.source_name,
                                    'position': (event.position_x, event.position_y),
                                    'coordinate_system': event.coordinate_system,
                                    'facing': event.facing,
                                    'health': f"{event.current_hp}/{event.max_hp}",
                                    'level': event.level,
                                    'parameter_count': event.parameter_count
                                })
            
            if lines_processed >= 10000:  # Limit processing
                break
    
    print(f"Processing Results:")
    print(f"  Lines processed: {lines_processed}")
    print(f"  Events parsed: {events_parsed}")
    print(f"  Position events: {position_events}")
    if events_parsed > 0:
        print(f"  Position extraction rate: {position_events/events_parsed*100:.1f}%")
    
    print(f"\nSuccessful Position Extractions ({len(successful_extractions)}):")
    print("-" * 60)
    
    for i, extraction in enumerate(successful_extractions):
        print(f"{i+1}. {extraction['timestamp']} - {extraction['event_type']}")
        print(f"   {extraction['source_name']}")
        print(f"   Position: ({extraction['position'][0]:.2f}, {extraction['position'][1]:.2f}) [{extraction['coordinate_system']}]")
        print(f"   Facing: {extraction['facing']:.4f}, Health: {extraction['health']}, Level: {extraction['level']}")
        print(f"   Parameters: {extraction['parameter_count']}")
        print()

def analyze_coordinate_systems():
    """Analyze coordinate systems found in the combat log."""
    parser = ProductionAdvancedParser()
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        return
    
    print(f"{'='*60}")
    print("COORDINATE SYSTEM ANALYSIS")
    print("=" * 60)
    
    coordinate_systems = defaultdict(list)
    arena_pattern = r"5/6/2025 19:04:[23456][0-9]"
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if re.search(arena_pattern, line):
                if any(event_type in line for event_type in parser.POSITION_EVENTS):
                    event = parser.parse_combat_event(line)
                    
                    if event and event.has_position_data:
                        coordinate_systems[event.coordinate_system].append({
                            'position': (event.position_x, event.position_y),
                            'source': event.source_name,
                            'event': event.event_type
                        })
    
    print(f"Coordinate Systems Found:")
    for system, positions in coordinate_systems.items():
        print(f"\n{system.upper()}: {len(positions)} positions")
        
        # Show coordinate ranges
        x_coords = [pos['position'][0] for pos in positions]
        y_coords = [pos['position'][1] for pos in positions]
        
        print(f"  X range: {min(x_coords):.2f} to {max(x_coords):.2f}")
        print(f"  Y range: {min(y_coords):.2f} to {max(y_coords):.2f}")
        
        # Show first few examples
        for i, pos in enumerate(positions[:3]):
            print(f"  Example {i+1}: {pos['source']} at ({pos['position'][0]:.2f}, {pos['position'][1]:.2f}) - {pos['event']}")

if __name__ == "__main__":
    test_production_parser()
    analyze_coordinate_systems()