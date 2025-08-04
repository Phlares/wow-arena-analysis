#!/usr/bin/env python3
"""
Parameter Structure Analyzer

Analyzes the exact parameter structure to understand where position data is located.
"""

import re
from datetime import datetime

def analyze_parameter_structure():
    """Analyze the parameter structure of the example line."""
    
    # Your example line with known position data
    test_line = '5/6/2025 19:04:25.703-4  SPELL_CAST_SUCCESS,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x511,0x0,0000000000000000,nil,0x80000000,0x0,115191,"Stealth",0x1,Player-11-0E366FE1,0000000000000000,46877,46877,0,0,0,0,3,300,300,0,-1938.60,1368.80,0,3.9970,673'
    
    print("PARAMETER STRUCTURE ANALYSIS")
    print("=" * 80)
    print(f"Test Line: {test_line}")
    print()
    
    # Split timestamp and event data
    parts = test_line.strip().split('  ', 1)
    timestamp_str, event_data = parts
    
    print(f"Timestamp: {timestamp_str}")
    print(f"Event Data: {event_data}")
    print()
    
    # Split parameters
    params = [p.strip() for p in event_data.split(',')]
    
    print(f"Total Parameters: {len(params)}")
    print()
    
    print("PARAMETER BREAKDOWN:")
    print("-" * 50)
    
    for i, param in enumerate(params):
        # Highlight position coordinates
        highlight = ""
        if param == "-1938.60":
            highlight = "  <-- POSITION X"
        elif param == "1368.80":
            highlight = "  <-- POSITION Y"
        elif param == "3.9970":
            highlight = "  <-- FACING"
        elif param in ["46877"]:
            if params[i-1] == "46877":
                highlight = "  <-- MAX HP"
            else:
                highlight = "  <-- CURRENT HP"
        elif param in ["300"] and i > 15:
            if i == 21:
                highlight = "  <-- CURRENT POWER"
            elif i == 22:
                highlight = "  <-- MAX POWER"
        elif param == "3" and i > 15:
            highlight = "  <-- POWER TYPE (Energy)"
        elif param == "673":
            highlight = "  <-- LEVEL/ITEM LEVEL"
        
        print(f"{i:2d}: {param:20s}{highlight}")
    
    print()
    print("COORDINATE ANALYSIS:")
    print("-" * 50)
    
    # Find the actual position coordinates
    for i, param in enumerate(params):
        try:
            x = float(param)
            if i + 1 < len(params):
                try:
                    y = float(params[i + 1])
                    # Check if this looks like reasonable coordinates
                    if abs(x) > 100 or abs(y) > 100:  # Larger coordinates
                        print(f"Coordinate pair at index {i}-{i+1}: ({x:.2f}, {y:.2f})")
                        
                        # Show surrounding parameters
                        print(f"  Context: ", end="")
                        for j in range(max(0, i-2), min(len(params), i+4)):
                            marker = " [X]" if j == i else " [Y]" if j == i+1 else ""
                            print(f"{params[j]}{marker}, ", end="")
                        print()
                except ValueError:
                    pass
        except ValueError:
            pass
    
    print()
    print("ADVANCED PARAMETER SECTION ANALYSIS:")
    print("-" * 50)
    
    # According to WoWPedia, for SPELL_CAST_SUCCESS:
    # 9 base + 3 spell = 12 parameters before advanced section
    # Advanced section starts at index 12
    
    print("Based on WoWPedia specification:")
    print("SPELL_CAST_SUCCESS = 9 base + 3 spell = 12 params before advanced")
    print("Advanced section should start at parameter index 12")
    print()
    
    if len(params) > 12:
        print("Expected Advanced Parameters:")
        advanced_labels = [
            "infoGUID", "ownerGUID", "currentHP", "maxHP", "attackPower", 
            "spellPower", "armor", "absorb", "powerType", "currentPower", 
            "maxPower", "powerCost", "positionX", "positionY", "uiMapID", "facing", "level"
        ]
        
        for i, label in enumerate(advanced_labels):
            param_index = 12 + i
            if param_index < len(params):
                value = params[param_index]
                print(f"{param_index:2d}: {label:15s} = {value}")
    
    print()
    print("CORRECTED POSITION EXTRACTION:")
    print("-" * 50)
    
    # According to the spec, position should be at index 12 + 12 = 24 and 12 + 13 = 25
    pos_x_index = 24
    pos_y_index = 25
    
    if len(params) > pos_y_index:
        pos_x = params[pos_x_index]
        pos_y = params[pos_y_index]
        print(f"Position X at index {pos_x_index}: {pos_x}")
        print(f"Position Y at index {pos_y_index}: {pos_y}")
        
        try:
            x_val = float(pos_x)
            y_val = float(pos_y)
            print(f"Parsed position: ({x_val:.2f}, {y_val:.2f})")
        except ValueError:
            print("Failed to parse as floats")
    
    # Also check the actual -1938.60, 1368.80 coordinates we see
    for i, param in enumerate(params):
        if param == "-1938.60":
            print(f"Found expected X coordinate -1938.60 at index {i}")
            if i + 1 < len(params):
                print(f"Y coordinate at index {i+1}: {params[i+1]}")

if __name__ == "__main__":
    analyze_parameter_structure()