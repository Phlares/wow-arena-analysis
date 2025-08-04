#!/usr/bin/env python3
"""
Development: Final Corrected Advanced Combat Log Parser

Uses the verified WoWPedia specification with correct parameter positioning
based on our parameter structure analysis.

Key findings:
- Advanced parameters start at index 12 for SPELL_CAST_SUCCESS
- Position X is at advanced parameter index 12 (overall index 24)
- Position Y is at advanced parameter index 13 (overall index 25)
- Facing is at advanced parameter index 15 (overall index 27)
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
class CorrectedCombatEvent:
    """Correctly parsed combat event with validated position data."""
    timestamp: datetime
    event_type: str
    source_guid: str
    source_name: str
    spell_id: Optional[int] = None
    spell_name: Optional[str] = None
    
    # Advanced parameters (correctly positioned)
    info_guid: str = ""
    owner_guid: str = ""
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
    
    # Analysis metadata
    has_position_data: bool = False
    coordinate_system: str = "unknown"
    raw_line: str = ""

class FinalCorrectedParser:
    """Final corrected parser using verified parameter positions."""
    
    POSITION_EVENTS = {
        'SPELL_CAST_SUCCESS', 'SPELL_CAST_START', 'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE',
        'SPELL_HEAL', 'SPELL_PERIODIC_HEAL', 'SPELL_ENERGIZE', 'SPELL_PERIODIC_ENERGIZE',
        'SWING_DAMAGE', 'SWING_DAMAGE_LANDED', 'RANGE_DAMAGE'
    }
    
    # Advanced parameter start positions for different event types
    ADVANCED_START_POSITIONS = {
        'SPELL_CAST_SUCCESS': 12,    # 9 base + 3 spell
        'SPELL_CAST_START': 12,      # 9 base + 3 spell
        'SPELL_DAMAGE': 22,          # 9 base + 3 spell + 10 damage
        'SPELL_PERIODIC_DAMAGE': 22, # 9 base + 3 spell + 10 damage
        'SPELL_HEAL': 22,            # 9 base + 3 spell + 10 heal
        'SPELL_PERIODIC_HEAL': 22,   # 9 base + 3 spell + 10 heal
        'SPELL_ENERGIZE': 15,        # 9 base + 3 spell + 3 energize
        'SPELL_PERIODIC_ENERGIZE': 15, # 9 base + 3 spell + 3 energize
        'SWING_DAMAGE': 19,          # 9 base + 10 damage
        'SWING_DAMAGE_LANDED': 19,   # 9 base + 10 damage
        'RANGE_DAMAGE': 22,          # 9 base + 3 weapon + 10 damage
    }
    
    def parse_combat_event(self, line: str) -> Optional[CorrectedCombatEvent]:
        """Parse combat event with correct parameter positioning."""
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
        
        # Split parameters by comma (simple split, handle quotes later)
        params = [p.strip() for p in event_data.split(',')]
        if len(params) < 9:
            return None
        
        # Extract base information
        event_type = params[0]
        if event_type not in self.POSITION_EVENTS:
            return None
        
        source_guid = params[1]
        source_name = self._extract_quoted_name(params[2])
        
        # Create event object
        event = CorrectedCombatEvent(
            timestamp=timestamp,
            event_type=event_type,
            source_guid=source_guid,
            source_name=source_name,
            raw_line=line.strip()
        )
        
        # Extract spell information for spell events
        if event_type.startswith('SPELL_') and len(params) > 11:
            try:
                event.spell_id = int(params[9])
                event.spell_name = self._extract_quoted_name(params[10])
            except (ValueError, IndexError):
                pass
        
        # Parse advanced parameters
        self._parse_advanced_parameters(event, params)
        
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
    
    def _parse_advanced_parameters(self, event: CorrectedCombatEvent, params: List[str]):
        """Parse advanced parameters using correct positioning."""
        # Get the starting position for advanced parameters
        advanced_start = self.ADVANCED_START_POSITIONS.get(event.event_type)
        if not advanced_start or len(params) < advanced_start + 17:
            return  # Not enough parameters for advanced logging
        
        try:
            # Extract advanced parameters according to WoWPedia specification
            idx = advanced_start
            
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
            
            # CORRECT POSITION EXTRACTION - These are the key parameters!
            event.position_x = float(params[idx + 12]) if idx + 12 < len(params) else 0.0
            event.position_y = float(params[idx + 13]) if idx + 13 < len(params) else 0.0
            event.ui_map_id = int(params[idx + 14]) if idx + 14 < len(params) else 0
            event.facing = float(params[idx + 15]) if idx + 15 < len(params) else 0.0
            event.level = int(params[idx + 16]) if idx + 16 < len(params) else 0
            
            # Validate position data
            if abs(event.position_x) < 10000 and abs(event.position_y) < 10000:
                if event.position_x != 0.0 or event.position_y != 0.0:
                    event.has_position_data = True
                    event.coordinate_system = self._classify_coordinate_system(
                        event.position_x, event.position_y
                    )
                    
        except (ValueError, IndexError):
            # Failed to parse advanced parameters
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

def test_final_parser():
    """Test the final corrected parser."""
    parser = FinalCorrectedParser()
    
    # Test with the verified example
    test_line = '5/6/2025 19:04:25.703-4  SPELL_CAST_SUCCESS,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x511,0x0,0000000000000000,nil,0x80000000,0x0,115191,"Stealth",0x1,Player-11-0E366FE1,0000000000000000,46877,46877,0,0,0,0,3,300,300,0,-1938.60,1368.80,0,3.9970,673'
    
    print("FINAL CORRECTED PARSER TEST")
    print("=" * 60)
    print(f"Test Line: {test_line[:80]}...")
    print()
    
    event = parser.parse_combat_event(test_line)
    
    if event:
        print("PARSING SUCCESSFUL")
        print(f"Event Type: {event.event_type}")
        print(f"Source: {event.source_name} ({event.source_guid})")
        print(f"Timestamp: {event.timestamp}")
        
        if event.spell_id:
            print(f"Spell: {event.spell_name} ({event.spell_id})")
        
        print(f"Has Position Data: {event.has_position_data}")
        
        if event.has_position_data:
            print(f"Position: ({event.position_x:.2f}, {event.position_y:.2f})")
            print(f"Coordinate System: {event.coordinate_system}")
            print(f"Facing: {event.facing:.4f} radians")
            
            print(f"Health: {event.current_hp}/{event.max_hp}")
            print(f"Power: {event.current_power}/{event.max_power} (Type: {event.power_type})")
            print(f"Level/ItemLevel: {event.level}")
            
            # Verify against expected values
            expected_x = -1938.60
            expected_y = 1368.80
            expected_facing = 3.9970
            
            print(f"\nVERIFICATION:")
            print(f"Expected Position: ({expected_x}, {expected_y})")
            print(f"Parsed Position: ({event.position_x}, {event.position_y})")
            print(f"Position Correct: {abs(event.position_x - expected_x) < 0.01 and abs(event.position_y - expected_y) < 0.01}")
            
            print(f"Expected Facing: {expected_facing}")
            print(f"Parsed Facing: {event.facing}")
            print(f"Facing Correct: {abs(event.facing - expected_facing) < 0.01}")
            
        else:
            print("NO POSITION DATA EXTRACTED")
    else:
        print("PARSING FAILED")

def test_with_real_log():
    """Test with real combat log data."""
    parser = FinalCorrectedParser()
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print(f"\n{'='*60}")
    print(f"TESTING WITH REAL LOG: {log_file.name}")
    print(f"{'='*60}")
    
    successful_extractions = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines_processed = 0
        events_parsed = 0
        position_events = 0
        
        for line in f:
            if lines_processed >= 2000:  # Test first 2000 lines
                break
            
            lines_processed += 1
            
            # Only test relevant event types
            if any(event_type in line for event_type in parser.POSITION_EVENTS):
                event = parser.parse_combat_event(line)
                
                if event:
                    events_parsed += 1
                    
                    if event.has_position_data:
                        position_events += 1
                        
                        # Store first few successful extractions
                        if len(successful_extractions) < 5:
                            successful_extractions.append({
                                'event_type': event.event_type,
                                'source_name': event.source_name,
                                'position': (event.position_x, event.position_y),
                                'coordinate_system': event.coordinate_system,
                                'timestamp': event.timestamp.strftime("%H:%M:%S.%f")[:-3]
                            })
    
    print(f"Lines processed: {lines_processed}")
    print(f"Events parsed: {events_parsed}")
    print(f"Position events: {position_events}")
    print(f"Position extraction rate: {position_events/events_parsed*100:.1f}%")
    
    print(f"\nFirst {len(successful_extractions)} Position Extractions:")
    for i, extraction in enumerate(successful_extractions):
        print(f"{i+1}. {extraction['timestamp']} - {extraction['event_type']}")
        print(f"   {extraction['source_name']}: ({extraction['position'][0]:.2f}, {extraction['position'][1]:.2f}) [{extraction['coordinate_system']}]")

if __name__ == "__main__":
    test_final_parser()
    test_with_real_log()