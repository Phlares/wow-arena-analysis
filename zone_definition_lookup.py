#!/usr/bin/env python3
"""
Zone Definition Lookup Tool
Quick lookup for zone definitions by number or annotation
"""

import json

def load_zone_definitions():
    """Load zone definitions from scaled mapping"""
    with open('scaled_zone_mapping.json', 'r') as f:
        return json.load(f)

def show_zone_definitions():
    """Display all zone definitions with numbers"""
    data = load_zone_definitions()
    
    print("WoW Arena Zone Definitions (73 Total)")
    print("=" * 80)
    print(f"{'#':<3} {'Zone ID':<12} {'Color':<8} {'Annotation':<30} {'Position':<15}")
    print("-" * 80)
    
    for i, zone in enumerate(data['zones'], 1):
        zone_id = zone['zone_id']
        color = zone['color']
        annotation = zone['annotation'][:28] + ".." if len(zone['annotation']) > 30 else zone['annotation']
        bbox = zone['bbox']
        position = f"({int(bbox['x'])}, {int(bbox['y'])})"
        
        print(f"{i:<3} {zone_id:<12} {color:<8} {annotation:<30} {position:<15}")

def lookup_zone(zone_number):
    """Look up specific zone by number"""
    data = load_zone_definitions()
    
    if 1 <= zone_number <= len(data['zones']):
        zone = data['zones'][zone_number - 1]
        print(f"\nZONE #{zone_number} DETAILS:")
        print(f"  Zone ID: {zone['zone_id']}")
        print(f"  Color: {zone['color']}")
        print(f"  Annotation: {zone['annotation']}")
        print(f"  Position: ({int(zone['bbox']['x'])}, {int(zone['bbox']['y'])})")
        print(f"  Size: {int(zone['bbox']['width'])}x{int(zone['bbox']['height'])}")
        print(f"  Debug Image: debug_ocr_output/zone_{zone_number-1:03d}_original.png")
        return zone
    else:
        print(f"ERROR: Zone {zone_number} not found (valid range: 1-{len(data['zones'])})")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            zone_num = int(sys.argv[1])
            lookup_zone(zone_num)
        except ValueError:
            print("Usage: python zone_definition_lookup.py [zone_number]")
    else:
        show_zone_definitions()