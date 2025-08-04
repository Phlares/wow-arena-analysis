#!/usr/bin/env python3
"""
Development: Corrected Advanced Combat Log Parser

Uses the definitive WoWPedia Advanced Combat Log syntax specification to 
properly parse position data and combat events.

Key improvements:
1. Follows exact WoWPedia parameter positioning
2. Properly handles different event types with varying prefix parameters
3. Correctly extracts position data from advanced parameters
4. Handles multiple coordinate systems without suppression
"""

import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import json
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class AdvancedCombatEvent:
    """Represents a parsed advanced combat log event."""
    timestamp: datetime
    event_type: str
    source_guid: str
    source_name: str
    source_flags: str
    dest_guid: str
    dest_name: str
    dest_flags: str
    
    # Spell information (if applicable)
    spell_id: Optional[int] = None
    spell_name: Optional[str] = None
    spell_school: Optional[str] = None
    
    # Damage/Heal information (if applicable)
    amount: Optional[int] = None
    overkill_overheal: Optional[int] = None
    
    # Advanced parameters (from source entity)
    info_guid: Optional[str] = None
    owner_guid: Optional[str] = None
    current_hp: int = 0
    max_hp: int = 0
    attack_power: int = 0
    spell_power: int = 0
    armor: int = 0
    absorb: int = 0
    power_type: int = 0
    current_power: int = 0
    max_power: int = 0
    power_cost: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    ui_map_id: int = 0
    facing: float = 0.0
    level: int = 0
    
    # Parsing metadata
    has_advanced_data: bool = False
    coordinate_system: str = "unknown"
    raw_line: str = ""

class CorrectedAdvancedCombatParser:
    """
    Advanced combat log parser following WoWPedia specification.
    """
    
    # Events that provide position data
    POSITION_EVENTS = {
        'SPELL_CAST_SUCCESS', 'SPELL_CAST_START', 'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE',
        'SPELL_HEAL', 'SPELL_PERIODIC_HEAL', 'SPELL_ENERGIZE', 'SPELL_PERIODIC_ENERGIZE',
        'SWING_DAMAGE', 'SWING_DAMAGE_LANDED', 'RANGE_DAMAGE'
    }
    
    # Event type parameter counts (base + prefix parameters before advanced section)
    EVENT_PARAM_COUNTS = {
        'SPELL_CAST_SUCCESS': 12,    # 9 base + 3 spell params
        'SPELL_CAST_START': 12,      # 9 base + 3 spell params
        'SPELL_DAMAGE': 22,          # 9 base + 3 spell + 10 damage params
        'SPELL_PERIODIC_DAMAGE': 22, # 9 base + 3 spell + 10 damage params
        'SPELL_HEAL': 22,            # 9 base + 3 spell + 10 heal params
        'SPELL_PERIODIC_HEAL': 22,   # 9 base + 3 spell + 10 heal params
        'SPELL_ENERGIZE': 15,        # 9 base + 3 spell + 3 energize params
        'SPELL_PERIODIC_ENERGIZE': 15, # 9 base + 3 spell + 3 energize params
        'SWING_DAMAGE': 19,          # 9 base + 10 damage params
        'SWING_DAMAGE_LANDED': 19,   # 9 base + 10 damage params
        'RANGE_DAMAGE': 22,          # 9 base + 3 weapon + 10 damage params
    }
    
    def parse_combat_line(self, line: str) -> Optional[AdvancedCombatEvent]:
        """Parse a single combat log line following WoWPedia specification."""
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
        params = self._split_parameters(event_data)
        if len(params) < 9:  # Need at least base parameters
            return None
        
        # Extract base parameters
        event = AdvancedCombatEvent(
            timestamp=timestamp,
            event_type=params[0],
            source_guid=params[1],
            source_name=self._extract_quoted_string(params[2]),
            source_flags=params[3],
            dest_guid=params[5] if len(params) > 5 else "",
            dest_name=self._extract_quoted_string(params[6]) if len(params) > 6 else "",
            dest_flags=params[7] if len(params) > 7 else "",
            raw_line=line.strip()
        )
        
        # Only process events we care about for position tracking
        if event.event_type not in self.POSITION_EVENTS:
            return None
        
        # Extract spell information if present
        if event.event_type.startswith('SPELL_'):
            if len(params) > 11:
                try:
                    event.spell_id = int(params[9])
                    event.spell_name = self._extract_quoted_string(params[10])
                    event.spell_school = params[11]
                except (ValueError, IndexError):
                    pass
        
        # Extract damage/heal amount if present
        if 'DAMAGE' in event.event_type or 'HEAL' in event.event_type:
            amount_index = self._get_amount_parameter_index(event.event_type)
            if amount_index and len(params) > amount_index:
                try:
                    event.amount = int(params[amount_index])
                except (ValueError, IndexError):
                    pass
        
        # Parse advanced parameters
        self._parse_advanced_parameters(event, params)
        
        return event
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        try:
            # Handle timezone offset: "5/6/2025 19:04:25.703-4"
            if '+' in timestamp_str or timestamp_str.count('-') > 2:
                # Remove timezone offset
                timestamp_str = re.sub(r'[+-]\d+$', '', timestamp_str)
            
            return datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S.%f")
        except ValueError:
            return None
    
    def _split_parameters(self, event_data: str) -> List[str]:
        """Split event data into parameters, handling quoted strings."""
        params = []
        current_param = ""
        in_quotes = False
        
        for char in event_data:
            if char == '"':
                in_quotes = not in_quotes
                current_param += char
            elif char == ',' and not in_quotes:
                params.append(current_param.strip())
                current_param = ""
            else:
                current_param += char
        
        # Add final parameter
        if current_param:
            params.append(current_param.strip())
        
        return params
    
    def _extract_quoted_string(self, param: str) -> str:
        """Extract string from quoted parameter."""
        if param.startswith('"') and param.endswith('"'):
            return param[1:-1]
        return param
    
    def _get_amount_parameter_index(self, event_type: str) -> Optional[int]:
        """Get the parameter index for damage/heal amount."""
        if event_type.startswith('SPELL_'):
            return 12  # After 9 base + 3 spell params
        elif event_type.startswith('SWING_'):
            return 9   # After 9 base params
        elif event_type.startswith('RANGE_'):
            return 12  # After 9 base + 3 weapon params
        return None
    
    def _parse_advanced_parameters(self, event: AdvancedCombatEvent, params: List[str]):
        """Parse advanced logging parameters from the combat log line."""
        # Determine where advanced parameters start based on event type
        advanced_start_index = self.EVENT_PARAM_COUNTS.get(event.event_type)
        
        if not advanced_start_index or len(params) < advanced_start_index + 17:
            return  # Not enough parameters for advanced logging
        
        try:
            # Extract advanced parameters according to WoWPedia specification
            idx = advanced_start_index
            
            event.info_guid = params[idx] if idx < len(params) else ""
            event.owner_guid = params[idx + 1] if idx + 1 < len(params) else ""
            event.current_hp = int(params[idx + 2]) if idx + 2 < len(params) else 0
            event.max_hp = int(params[idx + 3]) if idx + 3 < len(params) else 0
            event.attack_power = int(params[idx + 4]) if idx + 4 < len(params) else 0
            event.spell_power = int(params[idx + 5]) if idx + 5 < len(params) else 0
            event.armor = int(params[idx + 6]) if idx + 6 < len(params) else 0
            event.absorb = int(params[idx + 7]) if idx + 7 < len(params) else 0
            event.power_type = int(params[idx + 8]) if idx + 8 < len(params) else 0
            event.current_power = int(params[idx + 9]) if idx + 9 < len(params) else 0
            event.max_power = int(params[idx + 10]) if idx + 10 < len(params) else 0
            event.power_cost = int(params[idx + 11]) if idx + 11 < len(params) else 0
            
            # Position data - the key parameters we need!
            event.position_x = float(params[idx + 12]) if idx + 12 < len(params) else 0.0
            event.position_y = float(params[idx + 13]) if idx + 13 < len(params) else 0.0
            event.ui_map_id = int(params[idx + 14]) if idx + 14 < len(params) else 0
            event.facing = float(params[idx + 15]) if idx + 15 < len(params) else 0.0
            event.level = int(params[idx + 16]) if idx + 16 < len(params) else 0
            
            # Validate position data
            if abs(event.position_x) < 10000 and abs(event.position_y) < 10000:
                if event.position_x != 0.0 or event.position_y != 0.0:
                    event.has_advanced_data = True
                    event.coordinate_system = self._classify_coordinate_system(
                        event.position_x, event.position_y
                    )
        
        except (ValueError, IndexError) as e:
            # Advanced parameter parsing failed
            pass
    
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

def test_corrected_parser():
    """Test the corrected parser with real combat log data."""
    parser = CorrectedAdvancedCombatParser()
    
    # Test with actual combat log lines
    test_lines = [
        # Example from the reference
        '5/6/2025 19:04:25.703-4  SPELL_CAST_SUCCESS,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x511,0x0,0000000000000000,nil,0x80000000,0x0,115191,"Stealth",0x1,Player-11-0E366FE1,0000000000000000,46877,46877,0,0,0,0,3,300,300,0,-1938.60,1368.80,0,3.9970,673'
    ]
    
    print("TESTING CORRECTED ADVANCED COMBAT LOG PARSER")
    print("=" * 60)
    
    for i, line in enumerate(test_lines):
        print(f"\nTest Line {i+1}:")
        event = parser.parse_combat_line(line)
        
        if event:
            print(f"  Event Type: {event.event_type}")
            print(f"  Source: {event.source_name} ({event.source_guid})")
            print(f"  Timestamp: {event.timestamp}")
            
            if event.spell_id:
                print(f"  Spell: {event.spell_name} ({event.spell_id})")
            
            if event.has_advanced_data:
                print(f"  Health: {event.current_hp}/{event.max_hp}")
                print(f"  Power: {event.current_power}/{event.max_power} (Type: {event.power_type})")
                print(f"  Position: ({event.position_x:.2f}, {event.position_y:.2f})")
                print(f"  Coordinate System: {event.coordinate_system}")
                print(f"  Facing: {event.facing:.4f} radians")
                print(f"  Level/ItemLevel: {event.level}")
            else:
                print("  No advanced data found")
        else:
            print("  Failed to parse line")

if __name__ == "__main__":
    test_corrected_parser()