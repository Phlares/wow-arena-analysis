#!/usr/bin/env python3
"""
Corrected Zone Extractor for WoW Arena Analysis
Properly extracts zones from annotated SVG to match actual PNG layout
"""

import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional

class CorrectedZoneExtractor:
    """Extracts zones correctly from annotated SVG"""
    
    def __init__(self, svg_file: str):
        self.svg_file = svg_file
        self.zones = []
        self.text_annotations = {}
        
    def extract_svg_zones(self) -> List[Dict]:
        """Extract all zones with proper coordinate handling"""
        try:
            with open(self.svg_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Extract path elements with their colors and transforms
            path_pattern = r'<g clip-rule="nonzero" clip-path="url\(#[^)]+\)"><path style="[^"]*stroke:#([a-fA-F0-9]{6})[^"]*" d="M ([0-9.-]+) ([0-9.-]+) L ([0-9.-]+) ([0-9.-]+) L ([0-9.-]+) ([0-9.-]+) L ([0-9.-]+) ([0-9.-]+)[^"]*" transform="matrix\(([^)]+)\)"/></g>'
            
            matches = re.findall(path_pattern, svg_content)
            
            zones = []
            for i, match in enumerate(matches):
                color = f"#{match[0]}"
                
                # Extract path coordinates  
                path_coords = [float(x) for x in match[1:9]]
                x1, y1, x2, y2, x3, y3, x4, y4 = path_coords
                
                # Parse transform matrix
                transform_values = [float(x) for x in match[9].split(',')]
                if len(transform_values) >= 6:
                    # Apply transform matrix to get actual screen coordinates
                    # matrix(sx, 0, 0, sy, tx, ty) format
                    sx, sy, tx, ty = transform_values[0], transform_values[3], transform_values[4], transform_values[5]
                    
                    # Transform the bounding box
                    min_x = min(x1, x2, x3, x4) * sx + tx
                    max_x = max(x1, x2, x3, x4) * sx + tx  
                    min_y = min(y1, y2, y3, y4) * sy + ty
                    max_y = max(y1, y2, y3, y4) * sy + ty
                    
                    zone = {
                        'zone_id': f'zone_{i+1:03d}',
                        'color': color,
                        'bbox': {
                            'x': round(min_x, 2),
                            'y': round(min_y, 2), 
                            'width': round(max_x - min_x, 2),
                            'height': round(max_y - min_y, 2)
                        },
                        'center': {
                            'x': round((min_x + max_x) / 2, 2),
                            'y': round((min_y + max_y) / 2, 2)
                        },
                        'area': round((max_x - min_x) * (max_y - min_y), 2),
                        'annotation': None  # Will be filled by matching nearby text
                    }
                    zones.append(zone)
            
            print(f"EXTRACT: Found {len(zones)} zones with proper coordinates")
            return zones
            
        except Exception as e:
            print(f"ERROR: Extracting zones: {e}")
            return []
    
    def extract_text_annotations(self, svg_content: str) -> Dict:
        """Extract text annotations and their positions"""
        annotations = {}
        
        # Look for text content in the SVG
        # Text is encoded as path data, but we can find transform positions
        text_group_pattern = r'<g style="fill:#000000;fill-opacity:1;"><g transform="translate\(([0-9.-]+), ([0-9.-]+)\)">'
        
        matches = re.findall(text_group_pattern, svg_content)
        
        for match in matches:
            x, y = float(match[0]), float(match[1])
            # This gives us text positions - we'd need to decode the path data for actual text
            # For now, we'll use position-based inference
            annotations[(x, y)] = self._infer_annotation_from_position(x, y)
        
        return annotations
    
    def _infer_annotation_from_position(self, x: float, y: float) -> str:
        """Infer annotation text based on position in the layout"""
        # Based on the PNG image, map positions to likely annotations
        
        # Left side annotations (combat logs)
        if x < 150:
            if y < 150:
                return "Variable Combat log 4"
            elif y < 250:
                return "Variable Combat log 3"
            elif y < 350:
                return "Variable Combat log 2"
            elif y < 450:
                return "Variable Combat log 1"
        
        # Top section
        elif y < 100:
            if 200 < x < 400:
                return "Variable Combat log 5"
            elif 400 < x < 600:
                return "Variable Combat log 6" 
            elif 600 < x < 800:
                return "Variable Combat log 7"
            elif 800 < x < 1000:
                return "Arena details"
        
        # Player area (left-center)
        elif 200 < x < 500:
            if 200 < y < 300:
                return "Player or party 1 (name as adjacent)"
            elif 300 < y < 400:
                return "Player health/resource"
            elif 400 < y < 500:
                return "Debuffs on Player"
            elif y > 500:
                return "Player Pet Abilities"
        
        # Center area
        elif 500 < x < 900:
            if 200 < y < 300:
                return "Healer CC"
            elif 300 < y < 400:
                return "Buffs on player"
            elif 400 < y < 500:
                return "Affect on player"
            elif y > 500:
                return "Player Abilities"
        
        # Target area (center-right)
        elif 900 < x < 1200:
            if 200 < y < 300:
                return "Target health/resource"
            elif 300 < y < 400:
                return "Target abilities"
            elif 400 < y < 500:
                return "Debuffs on Target"
                
        # Right side (arena enemies)
        elif x > 1200:
            if y < 200:
                return "Arena Enemy 1"
            elif y < 400:
                return "Arena Enemy 2" 
            elif y < 600:
                return "Arena Enemy 3"
        
        # Bottom right (more combat logs)
        elif x > 1000 and y > 500:
            return "Variable Combat log 8/9"
        
        return f"Unknown position ({x}, {y})"
    
    def match_zones_to_annotations(self, zones: List[Dict]) -> List[Dict]:
        """Match extracted zones to their likely annotations based on position"""
        
        for zone in zones:
            center_x = zone['center']['x']
            center_y = zone['center']['y']
            
            # Infer annotation based on position and color
            annotation = self._infer_zone_annotation(center_x, center_y, zone['color'])
            zone['annotation'] = annotation
            zone['inferred_role'] = self._get_role_from_annotation(annotation)
        
        return zones
    
    def _infer_zone_annotation(self, x: float, y: float, color: str) -> str:
        """Infer zone annotation from position and color"""
        
        # Use color and position to determine annotation
        color_roles = {
            '#ff3131': 'Health',
            '#1800ad': 'Major Abilities',
            '#5ce1e6': 'Resource', 
            '#ffde59': 'Specialized Resource',
            '#7ed957': 'Character Name',
            '#ff914d': 'Combat Log',
            '#ffffff': 'Enemy Medallion',
            '#171717': 'Enemy Dispell',
            '#ff66c4': 'Enemy Racial',
            '#5a321d': 'Cast Bar',
            '#5e17eb': 'Player Abilities',
            '#8c52ff': 'Pet Abilities',
            '#e84d20': 'Debuffs',
            '#768047': 'Buffs',
            '#a6a6a6': 'Enemy CC Tracker',
            '#ff5757': 'Arena Information',
            '#5170ff': 'Major Effect',
            '#545454': 'Healer CC',
            '#0097b2': 'Location',
            '#330a0a': 'Current Time'
        }
        
        base_role = color_roles.get(color, 'Unknown')
        
        # Add position context
        if x < 600:  # Left side
            if base_role == 'Health':
                return 'Player Health'
            elif base_role == 'Resource':
                return 'Player Resource'
            elif base_role == 'Major Abilities':
                return 'Player Major Abilities'
            elif base_role == 'Character Name':
                return 'Player Name'
            elif base_role == 'Combat Log':
                return f'Combat Log (Left Side)'
        elif x > 1200:  # Right side  
            if base_role == 'Health':
                if y < 300:
                    return 'Arena Enemy 1 Health'
                elif y < 500:
                    return 'Arena Enemy 2 Health'
                else:
                    return 'Arena Enemy 3 Health'
            elif base_role == 'Major Abilities':
                return 'Arena Enemy Abilities'
        else:  # Center area
            if base_role == 'Health':
                return 'Target Health'
            elif base_role == 'Resource':
                return 'Target Resource'
        
        return f'{base_role} ({int(x)}, {int(y)})'
    
    def _get_role_from_annotation(self, annotation: str) -> str:
        """Get OCR role from annotation"""
        role_map = {
            'player health': 'player_health',
            'target health': 'target_health', 
            'arena enemy 1 health': 'arena_enemy_1_health',
            'arena enemy 2 health': 'arena_enemy_2_health',
            'arena enemy 3 health': 'arena_enemy_3_health',
            'player resource': 'player_resource',
            'target resource': 'target_resource',
            'player abilities': 'player_abilities',
            'player name': 'player_name',
            'combat log': 'combat_log'
        }
        
        annotation_lower = annotation.lower()
        for key, role in role_map.items():
            if key in annotation_lower:
                return role
        
        return 'unknown_role'
    
    def generate_corrected_mapping(self) -> Dict:
        """Generate corrected zone mapping"""
        
        zones = self.extract_svg_zones()
        if not zones:
            return {}
        
        # Match zones to annotations
        annotated_zones = self.match_zones_to_annotations(zones)
        
        # Group by color
        color_groups = {}
        for zone in annotated_zones:
            color = zone['color']
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(zone)
        
        # Create final mapping
        mapping = {
            'metadata': {
                'total_zones': len(annotated_zones),
                'extraction_method': 'corrected_svg_parsing',
                'coordinate_system': 'svg_transformed',
                'resolution': '3440x1440'
            },
            'zones': annotated_zones,
            'color_groups': color_groups,
            'zone_summary': {}
        }
        
        # Create zone summary
        for color, zones_list in color_groups.items():
            mapping['zone_summary'][color] = {
                'count': len(zones_list),
                'annotations': [zone['annotation'] for zone in zones_list]
            }
        
        return mapping

def main():
    """Main function to extract corrected zone data"""
    
    svg_file = r'E:\Footage\Footage\WoW - Warcraft Recorder\Wow Arena Matches\COLOURS AND PIXELS_Annotated_Revised.svg'
    
    print("CORRECTED EXTRACTOR: Starting zone extraction...")
    
    extractor = CorrectedZoneExtractor(svg_file)
    mapping = extractor.generate_corrected_mapping()
    
    if mapping:
        print(f"SUCCESS: Extracted {mapping['metadata']['total_zones']} zones")
        
        # Display color summary
        print("\nCORRECTED COLOR ANALYSIS:")
        for color, info in mapping['zone_summary'].items():
            print(f"  {color}: {info['count']} zones")
            for annotation in info['annotations'][:3]:  # Show first 3 annotations
                print(f"    - {annotation}")
            if len(info['annotations']) > 3:
                print(f"    ... and {len(info['annotations'])-3} more")
        
        # Save corrected mapping
        with open('corrected_zone_mapping.json', 'w') as f:
            json.dump(mapping, f, indent=2)
        
        print(f"\nCORRECTED: Zone mapping saved to 'corrected_zone_mapping.json'")
        print("READY: For accurate OCR implementation")
    
    else:
        print("ERROR: Failed to extract zones")

if __name__ == "__main__":
    main()