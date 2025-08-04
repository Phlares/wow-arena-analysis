#!/usr/bin/env python3
"""
Development: Robust Advanced Combat Log Parser

Handles the exact format we see in our combat logs, with debugging output
to understand the parameter positioning.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ParsedCombatEvent:
    """Simplified combat event for debugging."""
    timestamp: datetime
    event_type: str
    source_guid: str
    source_name: str
    spell_id: Optional[int]
    spell_name: Optional[str]
    position_x: float
    position_y: float
    facing: float
    current_hp: int
    max_hp: int
    power_type: int
    current_power: int
    max_power: int
    coordinate_system: str
    parameter_count: int
    advanced_start_index: int
    raw_line: str

class RobustAdvancedParser:
    """Robust parser with debugging capabilities."""
    
    def parse_line_with_debug(self, line: str) -> Dict:
        """Parse line and return detailed debugging information."""
        result = {
            'success': False,
            'error': None,
            'timestamp': None,
            'event_type': None,
            'parameter_count': 0,
            'parameters': [],
            'advanced_data': {},
            'position_found': False,
            'raw_line': line.strip()
        }
        
        try:
            # Split timestamp and event data
            parts = line.strip().split('  ', 1)
            if len(parts) != 2:
                result['error'] = "Could not split timestamp from event data"
                return result
            
            timestamp_str, event_data = parts
            
            # Parse timestamp
            try:
                # Handle timezone: "5/6/2025 19:04:25.703-4"
                clean_timestamp = re.sub(r'[+-]\d+$', '', timestamp_str)
                result['timestamp'] = datetime.strptime(clean_timestamp, "%m/%d/%Y %H:%M:%S.%f")
            except ValueError as e:
                result['error'] = f"Timestamp parsing failed: {e}"
                return result
            
            # Split parameters by comma (simple split for now)
            params = [p.strip() for p in event_data.split(',')]
            result['parameter_count'] = len(params)
            result['parameters'] = params[:20]  # Store first 20 for debugging
            
            if len(params) < 9:
                result['error'] = "Not enough base parameters"
                return result
            
            # Extract basic info
            result['event_type'] = params[0]
            source_guid = params[1]
            source_name = self._extract_name(params[2]) if len(params) > 2 else ""
            
            # Look for position data in the last ~20 parameters
            position_data = self._find_position_data(params)
            if position_data:
                result['position_found'] = True
                result['advanced_data'] = position_data
                
                # Create parsed event
                event = ParsedCombatEvent(
                    timestamp=result['timestamp'],
                    event_type=result['event_type'],
                    source_guid=source_guid,
                    source_name=source_name,
                    spell_id=self._extract_spell_id(params),
                    spell_name=self._extract_spell_name(params),
                    position_x=position_data['position_x'],
                    position_y=position_data['position_y'],
                    facing=position_data.get('facing', 0.0),
                    current_hp=position_data.get('current_hp', 0),
                    max_hp=position_data.get('max_hp', 0),
                    power_type=position_data.get('power_type', 0),
                    current_power=position_data.get('current_power', 0),
                    max_power=position_data.get('max_power', 0),
                    coordinate_system=self._classify_coordinates(
                        position_data['position_x'], position_data['position_y']
                    ),
                    parameter_count=len(params),
                    advanced_start_index=position_data['found_at_index'],
                    raw_line=line.strip()
                )
                result['parsed_event'] = event
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = f"Parsing exception: {e}"
        
        return result
    
    def _extract_name(self, param: str) -> str:
        """Extract name from quoted parameter."""
        if param.startswith('"') and param.endswith('"'):
            return param[1:-1]
        return param
    
    def _extract_spell_id(self, params: List[str]) -> Optional[int]:
        """Try to find spell ID in common positions."""
        for i in [9, 10, 11]:  # Common spell ID positions
            if i < len(params):
                try:
                    return int(params[i])
                except ValueError:
                    continue
        return None
    
    def _extract_spell_name(self, params: List[str]) -> Optional[str]:
        """Try to find spell name in common positions."""
        for i in [10, 11, 12]:  # Common spell name positions
            if i < len(params):
                name = self._extract_name(params[i])
                if name and not name.isdigit():
                    return name
        return None
    
    def _find_position_data(self, params: List[str]) -> Optional[Dict]:
        """Find position data by scanning the parameter list."""
        # Look for position coordinates in the last ~20 parameters
        for i in range(max(0, len(params) - 20), len(params) - 1):
            try:
                x = float(params[i])
                y = float(params[i + 1])
                
                # Basic coordinate validation
                if abs(x) < 10000 and abs(y) < 10000:
                    if abs(x) > 0.1 or abs(y) > 0.1:  # Not just zeros
                        # Found potential position data
                        position_data = {
                            'position_x': x,
                            'position_y': y,
                            'found_at_index': i
                        }
                        
                        # Try to extract additional data around this position
                        self._extract_surrounding_data(params, i, position_data)
                        
                        return position_data
                        
            except (ValueError, IndexError):
                continue
        
        return None
    
    def _extract_surrounding_data(self, params: List[str], pos_index: int, data: Dict):
        """Extract health, power, and facing data around position coordinates."""
        try:
            # Look backwards for health data (typically large integers)
            for offset in range(1, 10):
                idx = pos_index - offset
                if idx >= 0:
                    try:
                        val = int(params[idx])
                        if 1000 <= val <= 50000000:  # Reasonable HP range
                            if 'max_hp' not in data:
                                data['max_hp'] = val
                            elif 'current_hp' not in data and val <= data['max_hp']:
                                data['current_hp'] = val
                    except ValueError:
                        pass
            
            # Look forwards for facing and other data
            for offset in [2, 3, 4]:
                idx = pos_index + offset
                if idx < len(params):
                    try:
                        val = float(params[idx])
                        if 0 <= val <= 6.5:  # Reasonable facing range (0-2π)
                            data['facing'] = val
                            break
                    except ValueError:
                        pass
            
            # Look for power data (smaller integers around position)
            for offset in range(-5, 5):
                idx = pos_index + offset
                if idx >= 0 and idx < len(params):
                    try:
                        val = int(params[idx])
                        if 0 <= val <= 10:  # Power type range
                            data['power_type'] = val
                        elif 0 <= val <= 5000:  # Current/max power range
                            if 'current_power' not in data:
                                data['current_power'] = val
                            elif 'max_power' not in data and val >= data.get('current_power', 0):
                                data['max_power'] = val
                    except ValueError:
                        pass
                        
        except Exception:
            pass
    
    def _classify_coordinates(self, x: float, y: float) -> str:
        """Classify coordinate system."""
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

def test_with_real_data():
    """Test parser with actual combat log data."""
    parser = RobustAdvancedParser()
    
    # Test with the example line you provided and our known formats
    test_lines = [
        # Your example
        '5/6/2025 19:04:25.703-4  SPELL_CAST_SUCCESS,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x511,0x0,0000000000000000,nil,0x80000000,0x0,115191,"Stealth",0x1,Player-11-0E366FE1,0000000000000000,46877,46877,0,0,0,0,3,300,300,0,-1938.60,1368.80,0,3.9970,673',
        
        # Try to load from actual log file
    ]
    
    print("ROBUST ADVANCED PARSER DEBUGGING")
    print("=" * 60)
    
    # Test with sample lines first
    for i, line in enumerate(test_lines):
        print(f"\nTest Line {i+1}:")
        print(f"Line: {line[:100]}...")
        
        result = parser.parse_line_with_debug(line)
        
        print(f"Success: {result['success']}")
        if result['error']:
            print(f"Error: {result['error']}")
        
        print(f"Event Type: {result['event_type']}")
        print(f"Parameter Count: {result['parameter_count']}")
        print(f"Position Found: {result['position_found']}")
        
        if result['position_found']:
            pos_data = result['advanced_data']
            print(f"Position: ({pos_data['position_x']:.2f}, {pos_data['position_y']:.2f})")
            print(f"Found at parameter index: {pos_data['found_at_index']}")
            if 'facing' in pos_data:
                print(f"Facing: {pos_data['facing']:.4f}")
            if 'current_hp' in pos_data:
                print(f"Health: {pos_data.get('current_hp', 0)}/{pos_data.get('max_hp', 0)}")
    
    # Try reading from actual log file
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    if log_file.exists():
        print(f"\n{'='*60}")
        print(f"TESTING WITH ACTUAL LOG FILE: {log_file.name}")
        print(f"{'='*60}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines_tested = 0
            successful_parses = 0
            position_found_count = 0
            
            for line in f:
                if lines_tested >= 1000:  # Test first 1000 lines
                    break
                
                # Only test lines that might have position data
                if any(event in line for event in ['SPELL_CAST_SUCCESS', 'SPELL_DAMAGE', 'SPELL_HEAL']):
                    result = parser.parse_line_with_debug(line)
                    lines_tested += 1
                    
                    if result['success']:
                        successful_parses += 1
                        
                        if result['position_found']:
                            position_found_count += 1
                            
                            # Show first few successful position extractions
                            if position_found_count <= 3:
                                print(f"\nSuccessful Position Extract {position_found_count}:")
                                pos_data = result['advanced_data']
                                print(f"  Event: {result['event_type']}")
                                print(f"  Position: ({pos_data['position_x']:.2f}, {pos_data['position_y']:.2f})")
                                print(f"  Parameter {pos_data['found_at_index']}-{pos_data['found_at_index']+1}")
                                print(f"  Total params: {result['parameter_count']}")
            
            print(f"\nLog File Test Results:")
            print(f"  Lines tested: {lines_tested}")
            print(f"  Successful parses: {successful_parses}")
            print(f"  Position data found: {position_found_count}")
            print(f"  Success rate: {successful_parses/lines_tested*100:.1f}%")
            print(f"  Position rate: {position_found_count/lines_tested*100:.1f}%")
    else:
        print(f"\nLog file not found: {log_file}")

if __name__ == "__main__":
    test_with_real_data()