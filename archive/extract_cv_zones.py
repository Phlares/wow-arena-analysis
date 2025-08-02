#!/usr/bin/env python3
"""
Computer Vision Zone Extractor for WoW Arena Analysis
Extracts zone definitions from annotated SVG file for OCR implementation
"""

import re
import json
from typing import Dict, List, Tuple

def extract_svg_paths_and_colors(svg_content: str) -> List[Dict]:
    """Extract all colored paths from SVG with their coordinates and colors"""
    zones = []
    
    # Pattern to match path elements with stroke colors
    path_pattern = r'<path style="[^"]*stroke:#([a-fA-F0-9]{6})[^"]*" d="[^"]*" transform="matrix\([^)]+\),([^)]+)\)"/>'
    
    # More comprehensive pattern for paths with colors
    comprehensive_pattern = r'<g clip-rule="nonzero" clip-path="url\(#[^)]+\)"><path style="[^"]*stroke:#([a-fA-F0-9]{6})[^"]*" d="M ([0-9.]+) ([0-9.]+) L ([0-9.]+) ([0-9.]+) L ([0-9.]+) ([0-9.]+) L ([0-9.]+) ([0-9.]+)[^"]*" transform="matrix\(([^)]+)\)"/></g>'
    
    matches = re.findall(comprehensive_pattern, svg_content)
    
    for i, match in enumerate(matches):
        color = match[0]
        # Extract bounding box coordinates
        x1, y1, x2, y2, x3, y3, x4, y4 = map(float, match[1:9])
        transform = match[9]
        
        # Calculate bounding box
        min_x = min(x1, x2, x3, x4)
        min_y = min(y1, y2, y3, y4)
        max_x = max(x1, x2, x3, x4)
        max_y = max(y1, y2, y3, y4)
        
        zone = {
            'zone_id': f'zone_{i+1:03d}',
            'color': f'#{color}',
            'bbox': {
                'x': min_x,
                'y': min_y,
                'width': max_x - min_x,
                'height': max_y - min_y
            },
            'transform': transform,
            'annotation': None  # Will be filled by text extraction
        }
        zones.append(zone)
    
    return zones

def extract_text_annotations(svg_content: str) -> Dict[Tuple[float, float], str]:
    """Extract text annotations with their coordinates"""
    annotations = {}
    
    # Look for text groups that follow the path elements
    # Text usually appears after path elements in similar coordinate ranges
    text_block_pattern = r'<g style="fill:#000000;fill-opacity:1;"><g transform="translate\(([^,]+), ([^)]+)\)">.*?</g></g>'
    
    # This is a simplified approach - in practice, you'd need to decode the path data
    # For now, let's create a mapping based on known zones from the color definitions
    
    # Based on the head output we saw, we know there are annotations like "Player Party 1"
    # Let's create a mapping structure for the 21 zones we need to track
    
    return annotations

def create_zone_mapping() -> Dict:
    """Create the comprehensive zone mapping for WoW Arena UI"""
    
    # Color definitions from our previous analysis
    color_definitions = {
        '#ff3131': 'Healthbars',
        '#1800ad': 'Major Abilities', 
        '#5ce1e6': 'Resource Bars',
        '#ffde59': 'Specialized secondary Resource for Player',
        '#7ed957': 'Names of characters in party, player, player pets, target, or spell',
        '#ff914d': 'Combat log details',
        '#ffffff': 'Enemy Arena Medallion',
        '#171717': 'Enemy dispell',
        '#ff66c4': 'Enemy Arena Combatant Racial Ability',
        '#5a321d': 'Player and enemy cast bars',
        '#5e17eb': 'Player Ability Icons',
        '#8c52ff': 'Player Pet Ability Icons',
        '#e84d20': 'Debuffs - Player & Target',
        '#768047': 'Buffs - Player & Target',
        '#a6a6a6': 'Enemy Crowd Control Diminishing Return Tracker',
        '#ff5757': 'Arena Information',
        '#5170ff': 'Major affect on player',
        '#545454': 'Party Healer is in Crowd Control',
        '#0097b2': 'Location Title',
        '#330a0a': 'Current Time'
    }
    
    # Based on the multi-instance analysis, create expected zone roles
    zone_roles = {
        'healthbars': [
            'Player Health',
            'Party Member 1 Health', 
            'Party Member 2 Health',
            'Target Health',
            'Arena Enemy 1 Health',
            'Arena Enemy 2 Health'
        ],
        'resource_bars': [
            'Player Resource',
            'Party Member 1 Resource',
            'Party Member 2 Resource', 
            'Target Resource',
            'Arena Enemy 1 Resource',
            'Arena Enemy 2 Resource'
        ],
        'major_abilities': [
            'Player Major Abilities',
            'Party Member 1 Major Abilities',
            'Party Member 2 Major Abilities',
            'Arena Enemy 1 Major Abilities',
            'Arena Enemy 2 Major Abilities',
            'Arena Enemy 3 Major Abilities'
        ],
        'character_names': [
            'Player Name',
            'Party Member 1 Name',
            'Party Member 2 Name',
            'Target Name',
            'Arena Enemy 1 Name'
        ],
        'cast_bars': [
            'Player Cast Bar',
            'Arena Enemy 1 Cast Bar',
            'Arena Enemy 2 Cast Bar', 
            'Arena Enemy 3 Cast Bar'
        ],
        'enemy_medallions': [
            'Arena Enemy 1 Medallion',
            'Arena Enemy 2 Medallion',
            'Arena Enemy 3 Medallion'
        ],
        'enemy_dispells': [
            'Arena Enemy 1 Dispell',
            'Arena Enemy 2 Dispell', 
            'Arena Enemy 3 Dispell'
        ],
        'enemy_racials': [
            'Arena Enemy 1 Racial',
            'Arena Enemy 2 Racial',
            'Arena Enemy 3 Racial'
        ],
        'buff_debuff_zones': [
            'Player Buffs',
            'Player Debuffs',
            'Target/Enemy Buffs', 
            'Target/Enemy Debuffs'
        ],
        'single_zones': [
            'Player Specialized Resource',
            'Player Pet Abilities',
            'Player Major Affect',
            'Party Healer CC Status',
            'Arena Information',
            'Location Title',
            'Current Time'
        ]
    }
    
    return {
        'color_definitions': color_definitions,
        'zone_roles': zone_roles,
        'total_zones': sum(len(roles) for roles in zone_roles.values())
    }

def main():
    """Main function to extract and validate zone information"""
    
    svg_file = r'E:\Footage\Footage\WoW - Warcraft Recorder\Wow Arena Matches\COLOURS AND PIXELS_Annotated_Revised.svg'
    
    try:
        with open(svg_file, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        print("TARGET: WoW Arena Computer Vision Zone Extractor")
        print("=" * 50)
        
        # Extract zones and colors
        zones = extract_svg_paths_and_colors(svg_content)
        print(f"ZONES: Extracted {len(zones)} colored zones from SVG")
        
        # Create zone mapping
        mapping = create_zone_mapping()
        print(f"MAPPING: Created mapping for {mapping['total_zones']} expected UI zones")
        
        # Group zones by color
        color_groups = {}
        for zone in zones:
            color = zone['color']
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(zone)
        
        print(f"COLORS: Found {len(color_groups)} unique colors")
        
        # Display color analysis
        print("\nZONE COLOR ANALYSIS:")
        for color, zones_list in color_groups.items():
            color_name = mapping['color_definitions'].get(color, 'Unknown')
            print(f"  {color}: {len(zones_list)} zones - {color_name}")
        
        # Save extracted data
        output_data = {
            'extraction_summary': {
                'total_zones': len(zones),
                'unique_colors': len(color_groups),
                'expected_zones': mapping['total_zones']
            },
            'zones': zones[:10],  # First 10 zones as sample
            'color_groups': {color: len(zones_list) for color, zones_list in color_groups.items()},
            'zone_mapping': mapping
        }
        
        with open('cv_zone_extraction.json', 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nSUCCESS: Zone extraction data saved to 'cv_zone_extraction.json'")
        print(f"READY: For OCR validation testing")
        
        return zones, mapping
        
    except Exception as e:
        print(f"ERROR: extracting zones: {e}")
        return None, None

if __name__ == "__main__":
    zones, mapping = main()