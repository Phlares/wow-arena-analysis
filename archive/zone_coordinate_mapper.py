#!/usr/bin/env python3
"""
Zone Coordinate Mapper for WoW Arena Analysis
Maps precise pixel coordinates to specific UI element roles
"""

import json
from typing import Dict, List, Tuple, Optional

class ZoneCoordinateMapper:
    """Maps zones to specific UI element roles based on position and color"""
    
    def __init__(self, zone_data_file: str = 'cv_zone_extraction.json'):
        """Initialize mapper with zone data"""
        self.zone_data = self._load_zone_data(zone_data_file)
        self.coordinate_mapping = {}
        
    def _load_zone_data(self, file_path: str) -> Dict:
        """Load extracted zone data"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Zone data file {file_path} not found")
            return {}
    
    def create_coordinate_mapping(self) -> Dict:
        """Create comprehensive coordinate to UI role mapping"""
        
        mapping = {
            'healthbars': {},
            'resource_bars': {},
            'character_names': {},
            'major_abilities': {},
            'cast_bars': {},
            'specialized_resources': {},
            'enemy_abilities': {},
            'combat_log': {},
            'ui_elements': {},
            'metadata': {
                'total_mapped_zones': 0,
                'resolution': '3440x1440',
                'coordinate_system': 'top_left_origin'
            }
        }
        
        if 'zones' not in self.zone_data:
            print("ERROR: No zones found in data")
            return mapping
        
        # Process each zone and assign to appropriate category
        for zone in self.zone_data['zones']:
            zone_id = zone['zone_id']
            color = zone['color']
            bbox = zone['bbox']
            
            # Create coordinate entry
            coord_entry = {
                'zone_id': zone_id,
                'bbox': bbox,
                'center_point': {
                    'x': bbox['x'] + bbox['width'] / 2,
                    'y': bbox['y'] + bbox['height'] / 2
                },
                'color': color,
                'area': bbox['width'] * bbox['height']
            }
            
            # Assign to category based on color and position
            role = self._determine_ui_role(color, bbox, zone_id)
            category = self._get_category_for_role(role)
            
            if category in mapping:
                mapping[category][role] = coord_entry
                mapping['metadata']['total_mapped_zones'] += 1
        
        self.coordinate_mapping = mapping
        return mapping
    
    def _determine_ui_role(self, color: str, bbox: Dict, zone_id: str) -> str:
        """Determine specific UI role based on color, position, and context"""
        
        x, y = bbox['x'], bbox['y']
        width, height = bbox['width'], bbox['height']
        
        # Health bars (#ff3131) - distinguish by position
        if color == '#ff3131':
            if x < 600:  # Left side of screen
                if y < 500:
                    return 'player_health'
                elif y < 600:
                    return 'party_member_1_health'
                else:
                    return 'party_member_2_health'
            elif x > 1500:  # Right side of screen 
                if y < 500:
                    return 'arena_enemy_1_health'
                elif y < 600:
                    return 'arena_enemy_2_health'
                else:
                    return 'arena_enemy_3_health'
            else:  # Center area
                return 'target_health'
        
        # Resource bars (#5ce1e6) - follow similar pattern to health
        elif color == '#5ce1e6':
            if x < 600:
                if y < 500:
                    return 'player_resource'
                else:
                    return 'party_member_resource'
            elif x > 1500:
                return 'arena_enemy_resource'
            else:
                return 'target_resource'
        
        # Major Abilities (#1800ad) - distinguish by screen position
        elif color == '#1800ad':
            if x < 800:
                return 'player_major_abilities'
            elif x > 1800:
                if y < 400:
                    return 'arena_enemy_1_abilities'
                elif y < 600:
                    return 'arena_enemy_2_abilities'
                else:
                    return 'arena_enemy_3_abilities'
            else:
                return 'party_member_abilities'
        
        # Specialized Resources (#ffde59) - usually near player area
        elif color == '#ffde59':
            if y > 600:
                return 'player_specialized_resource_1'
            elif y > 500:
                return 'player_specialized_resource_2'
            else:
                return 'player_specialized_resource_3'
        
        # Character Names (#7ed957)
        elif color == '#7ed957':
            if x < 600:
                return 'player_name'
            elif x > 1500:
                return 'arena_enemy_name'
            else:
                return 'target_name'
        
        # Cast Bars (#5a321d)
        elif color == '#5a321d':
            if x < 800:
                return 'player_cast_bar'
            elif x > 1800:
                if y < 400:
                    return 'arena_enemy_1_cast_bar'
                elif y < 600:
                    return 'arena_enemy_2_cast_bar'
                else:
                    return 'arena_enemy_3_cast_bar'
            else:
                return 'target_cast_bar'
        
        # Enemy Racial Abilities (#ff66c4)
        elif color == '#ff66c4':
            if y < 400:
                return 'arena_enemy_1_racial'
            elif y < 600:
                return 'arena_enemy_2_racial'
            else:
                return 'arena_enemy_3_racial'
        
        # Buffs (#768047)
        elif color == '#768047':
            if x < 800:
                return 'player_buffs'
            else:
                return 'target_buffs'
        
        # Combat Log (#ff914d)
        elif color == '#ff914d':
            return 'combat_log_details'
        
        # Major Effect on Player (#5170ff)
        elif color == '#5170ff':
            return 'player_major_effect'
        
        # Location Title (#0097b2)
        elif color == '#0097b2':
            return 'location_title'
        
        # Current Time (#330a0a)
        elif color == '#330a0a':
            return 'current_time'
        
        else:
            return f'unknown_role_{zone_id}'
    
    def _get_category_for_role(self, role: str) -> str:
        """Get category for a specific role"""
        category_map = {
            'health': 'healthbars',
            'resource': 'resource_bars', 
            'name': 'character_names',
            'abilities': 'major_abilities',
            'cast': 'cast_bars',
            'specialized': 'specialized_resources',
            'racial': 'enemy_abilities',
            'buffs': 'ui_elements',
            'effect': 'ui_elements',
            'combat': 'combat_log',
            'location': 'ui_elements',
            'time': 'ui_elements'
        }
        
        for key, category in category_map.items():
            if key in role.lower():
                return category
        
        return 'ui_elements'  # Default category
    
    def get_ocr_targets_by_category(self, category: str) -> List[Dict]:
        """Get all OCR targets for a specific category"""
        if category not in self.coordinate_mapping:
            return []
        
        targets = []
        for role, coord_data in self.coordinate_mapping[category].items():
            target = {
                'role': role,
                'category': category,
                'ocr_region': {
                    'x': int(coord_data['bbox']['x']),
                    'y': int(coord_data['bbox']['y']),
                    'width': int(coord_data['bbox']['width']),
                    'height': int(coord_data['bbox']['height'])
                },
                'center_point': coord_data['center_point'],
                'color': coord_data['color'],
                'priority': self._get_ocr_priority(role)
            }
            targets.append(target)
        
        # Sort by priority (higher priority first)
        targets.sort(key=lambda x: x['priority'], reverse=True)
        return targets
    
    def _get_ocr_priority(self, role: str) -> int:
        """Get OCR priority for role (1-10, higher is more important)"""
        priority_map = {
            'player_health': 10,
            'target_health': 9,
            'arena_enemy_1_health': 8,
            'arena_enemy_2_health': 8,
            'player_resource': 8,
            'target_resource': 7,
            'player_cast_bar': 9,
            'target_cast_bar': 8,
            'arena_enemy_1_cast_bar': 7,
            'current_time': 6,
            'location_title': 5,
            'combat_log_details': 4,
            'player_name': 6,
            'target_name': 6,
            'player_major_abilities': 7,
            'player_specialized_resource': 6
        }
        
        return priority_map.get(role, 3)  # Default priority
    
    def generate_mapping_summary(self) -> str:
        """Generate summary of coordinate mapping"""
        if not self.coordinate_mapping:
            self.create_coordinate_mapping()
        
        summary = []
        summary.append("=" * 60)
        summary.append("WoW Arena UI Coordinate Mapping Summary")
        summary.append("=" * 60)
        
        # Metadata
        meta = self.coordinate_mapping['metadata']
        summary.append(f"\nMETADATA:")
        summary.append(f"  Total Mapped Zones: {meta['total_mapped_zones']}")
        summary.append(f"  Resolution: {meta['resolution']}")
        summary.append(f"  Coordinate System: {meta['coordinate_system']}")
        
        # Category breakdown
        for category, zones in self.coordinate_mapping.items():
            if category == 'metadata':
                continue
                
            if zones:
                summary.append(f"\n{category.upper()}: ({len(zones)} zones)")
                for role, data in zones.items():
                    bbox = data['bbox']
                    center = data['center_point']
                    summary.append(f"  {role}:")
                    summary.append(f"    Position: ({int(bbox['x'])}, {int(bbox['y'])})")
                    summary.append(f"    Size: {int(bbox['width'])}x{int(bbox['height'])}")
                    summary.append(f"    Center: ({int(center['x'])}, {int(center['y'])})")
                    summary.append(f"    Color: {data['color']}")
        
        # OCR Priority listing
        summary.append(f"\nOCR PRIORITY TARGETS:")
        all_targets = []
        for category in self.coordinate_mapping:
            if category != 'metadata':
                all_targets.extend(self.get_ocr_targets_by_category(category))
        
        for target in all_targets[:10]:  # Top 10 priority targets
            summary.append(f"  Priority {target['priority']}: {target['role']} @ ({target['ocr_region']['x']}, {target['ocr_region']['y']})")
        
        summary.append("=" * 60)
        return "\n".join(summary)
    
    def save_mapping_data(self, output_file: str = 'zone_coordinate_mapping.json'):
        """Save coordinate mapping to JSON file"""
        if not self.coordinate_mapping:
            self.create_coordinate_mapping()
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.coordinate_mapping, f, indent=2)
            print(f"MAPPING: Saved coordinate mapping to {output_file}")
            return True
        except Exception as e:
            print(f"ERROR: Saving mapping data: {e}")
            return False

def main():
    """Main coordinate mapping function"""
    print("MAPPER: Zone Coordinate Mapping Starting...")
    
    # Initialize mapper
    mapper = ZoneCoordinateMapper()
    
    # Create coordinate mapping
    mapping = mapper.create_coordinate_mapping()
    
    # Generate and display summary
    summary = mapper.generate_mapping_summary()
    print(summary)
    
    # Save mapping data
    mapper.save_mapping_data()
    
    # Save summary report
    with open('coordinate_mapping_summary.txt', 'w') as f:
        f.write(summary)
    
    print("\nMAPPING: Complete - Check 'zone_coordinate_mapping.json' and 'coordinate_mapping_summary.txt'")

if __name__ == "__main__":
    main()