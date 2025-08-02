#!/usr/bin/env python3
"""
Corrected Zone Validator for WoW Arena Analysis
Validates the corrected zone extraction against the actual PNG layout
"""

import json
import cv2
import numpy as np
from typing import Dict, List

class CorrectedZoneValidator:
    """Validates corrected zone extraction"""
    
    def __init__(self, zone_data_file: str = 'corrected_zone_mapping.json'):
        self.zone_data = self._load_zone_data(zone_data_file)
        self.frame_width = 3440
        self.frame_height = 1440
        
    def _load_zone_data(self, file_path: str) -> Dict:
        """Load corrected zone data"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Zone data file {file_path} not found")
            return {}
    
    def create_corrected_overlay(self, output_path: str = 'corrected_zone_overlay.png') -> bool:
        """Create visual overlay of corrected zones"""
        try:
            # Create blank canvas
            overlay = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
            
            # Enhanced color mapping for better visibility
            color_map = {
                '#ff3131': (31, 49, 255),    # Red (Health)
                '#1800ad': (173, 0, 24),     # Dark Blue (Major Abilities)
                '#5ce1e6': (230, 225, 92),   # Cyan (Resources)
                '#ffde59': (89, 222, 255),   # Yellow (Specialized)
                '#7ed957': (87, 217, 126),   # Light Green (Names)
                '#ff914d': (77, 145, 255),   # Orange (Combat Log)
                '#ffffff': (255, 255, 255),  # White (Enemy Medallion)
                '#171717': (23, 23, 23),     # Dark Gray (Enemy Dispell)
                '#ff66c4': (196, 102, 255),  # Pink (Enemy Racial)
                '#5a321d': (29, 50, 90),     # Brown (Cast Bars)
                '#5e17eb': (235, 23, 94),    # Purple (Player Abilities)
                '#8c52ff': (255, 82, 140),   # Light Purple (Pet Abilities)
                '#e84d20': (32, 77, 232),    # Red-Orange (Debuffs)
                '#768047': (71, 128, 118),   # Olive Green (Buffs)
                '#a6a6a6': (166, 166, 166),  # Light Gray (Enemy CC)
                '#ff5757': (87, 87, 255),    # Light Red (Arena Info)
                '#5170ff': (255, 112, 81),   # Blue (Major Effect)
                '#545454': (84, 84, 84),     # Medium Gray (Healer CC)
                '#0097b2': (178, 151, 0),    # Teal (Location)
                '#330a0a': (10, 10, 51),     # Dark Brown (Time)
            }
            
            zones_drawn = 0
            if 'zones' in self.zone_data:
                for zone in self.zone_data['zones']:
                    color_hex = zone['color']
                    bbox = zone['bbox']
                    annotation = zone.get('annotation', 'Unknown')
                    
                    # Convert to integer coordinates
                    x = max(0, min(int(bbox['x']), self.frame_width-1))
                    y = max(0, min(int(bbox['y']), self.frame_height-1))
                    w = max(1, min(int(bbox['width']), self.frame_width-x))
                    h = max(1, min(int(bbox['height']), self.frame_height-y))
                    
                    # Skip invalid zones
                    if w <= 0 or h <= 0:
                        continue
                    
                    # Get color for this zone
                    bgr_color = color_map.get(color_hex, (128, 128, 128))
                    
                    # Draw rectangle
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), bgr_color, 2)
                    
                    # Add zone annotation (truncated)
                    annotation_short = annotation[:15] + "..." if len(annotation) > 15 else annotation
                    cv2.putText(overlay, annotation_short, (x + 2, y + 12), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, bgr_color, 1)
                    
                    zones_drawn += 1
            
            # Save overlay
            cv2.imwrite(output_path, overlay)
            print(f"OVERLAY: Created corrected zone overlay with {zones_drawn} zones -> {output_path}")
            return True
            
        except Exception as e:
            print(f"ERROR: Creating corrected overlay: {e}")
            return False
    
    def validate_corrected_zones(self) -> Dict:
        """Validate corrected zone extraction"""
        validation = {
            'total_zones': 0,
            'zones_by_category': {},
            'key_zones_found': {},
            'missing_critical_zones': [],
            'coordinate_analysis': {},
            'validation_score': 0
        }
        
        try:
            if 'zones' not in self.zone_data:
                return validation
            
            zones = self.zone_data['zones']
            validation['total_zones'] = len(zones)
            
            # Critical zones we need for OCR
            critical_zones = {
                'player_health': False,
                'target_health': False,
                'arena_enemy_health': False,
                'player_resource': False,
                'player_abilities': False,
                'cast_bars': False,
                'combat_log': False,
                'arena_information': False
            }
            
            # Analyze each zone
            for zone in zones:
                annotation = zone.get('annotation', '').lower()
                color = zone['color']
                bbox = zone['bbox']
                
                # Check for critical zones
                if 'player health' in annotation:
                    critical_zones['player_health'] = True
                elif 'target health' in annotation:
                    critical_zones['target_health'] = True
                elif 'arena enemy' in annotation and 'health' in annotation:
                    critical_zones['arena_enemy_health'] = True
                elif 'player resource' in annotation:
                    critical_zones['player_resource'] = True
                elif 'player abilities' in annotation:
                    critical_zones['player_abilities'] = True
                elif 'cast bar' in annotation:
                    critical_zones['cast_bars'] = True
                elif 'combat log' in annotation:
                    critical_zones['combat_log'] = True
                elif 'arena information' in annotation:
                    critical_zones['arena_information'] = True
                
                # Group by category
                category = self._get_zone_category(annotation)
                if category not in validation['zones_by_category']:
                    validation['zones_by_category'][category] = 0
                validation['zones_by_category'][category] += 1
                
                # Coordinate analysis
                x_region = 'left' if bbox['x'] < 1000 else 'center' if bbox['x'] < 2000 else 'right'
                y_region = 'top' if bbox['y'] < 400 else 'middle' if bbox['y'] < 800 else 'bottom'
                region_key = f"{x_region}_{y_region}"
                
                if region_key not in validation['coordinate_analysis']:
                    validation['coordinate_analysis'][region_key] = 0
                validation['coordinate_analysis'][region_key] += 1
            
            # Set key zones found
            validation['key_zones_found'] = critical_zones
            
            # Find missing critical zones
            for zone_name, found in critical_zones.items():
                if not found:
                    validation['missing_critical_zones'].append(zone_name)
            
            # Calculate validation score (0-100)
            found_critical = sum(1 for found in critical_zones.values() if found)
            total_critical = len(critical_zones)
            validation['validation_score'] = int((found_critical / total_critical) * 100)
            
            return validation
            
        except Exception as e:
            print(f"ERROR: Validating zones: {e}")
            validation['error'] = str(e)
            return validation
    
    def _get_zone_category(self, annotation: str) -> str:
        """Get category from annotation"""
        annotation_lower = annotation.lower()
        
        if 'health' in annotation_lower:
            return 'health_bars'
        elif 'resource' in annotation_lower:
            return 'resource_bars'
        elif 'abilities' in annotation_lower or 'ability' in annotation_lower:
            return 'abilities'
        elif 'name' in annotation_lower:
            return 'character_names'
        elif 'cast' in annotation_lower:
            return 'cast_bars'
        elif 'combat log' in annotation_lower:
            return 'combat_logs'
        elif 'buff' in annotation_lower:
            return 'buffs'
        elif 'debuff' in annotation_lower:
            return 'debuffs'
        elif 'enemy' in annotation_lower:
            return 'enemy_elements'
        else:
            return 'other'
    
    def create_priority_ocr_targets(self) -> List[Dict]:
        """Create prioritized OCR targets from corrected zones"""
        targets = []
        
        if 'zones' not in self.zone_data:
            return targets
        
        for zone in self.zone_data['zones']:
            annotation = zone.get('annotation', '')
            bbox = zone['bbox']
            color = zone['color']
            
            # Determine OCR priority
            priority = self._get_ocr_priority(annotation)
            
            if priority > 0:  # Only include zones that need OCR
                target = {
                    'zone_id': zone['zone_id'],
                    'annotation': annotation,
                    'priority': priority,
                    'color': color,
                    'ocr_region': {
                        'x': int(bbox['x']),
                        'y': int(bbox['y']),
                        'width': int(bbox['width']),
                        'height': int(bbox['height'])
                    },
                    'expected_content': self._get_expected_content(annotation),
                    'confidence_threshold': self._get_confidence_threshold(annotation)
                }
                targets.append(target)
        
        # Sort by priority (highest first)
        targets.sort(key=lambda x: x['priority'], reverse=True)
        return targets
    
    def _get_ocr_priority(self, annotation: str) -> int:
        """Get OCR priority (1-10, 0 for no OCR needed)"""
        annotation_lower = annotation.lower()
        
        priority_map = {
            'player health': 10,
            'target health': 9,
            'arena enemy 1 health': 8,
            'arena enemy 2 health': 8,
            'arena enemy 3 health': 8,
            'player resource': 8,
            'target resource': 7,
            'cast bar': 9,
            'player name': 6,
            'target name': 6,
            'arena information': 7,
            'current time': 5,
            'location': 4,
            'combat log': 3
        }
        
        for key, priority in priority_map.items():
            if key in annotation_lower:
                return priority
        
        # Default priorities by type
        if 'health' in annotation_lower:
            return 7
        elif 'resource' in annotation_lower:
            return 6
        elif 'abilities' in annotation_lower:
            return 5
        elif 'name' in annotation_lower:
            return 4
        
        return 0  # No OCR needed
    
    def _get_expected_content(self, annotation: str) -> str:
        """Get expected content type for OCR"""
        annotation_lower = annotation.lower()
        
        if 'health' in annotation_lower:
            return 'percentage_or_numbers'
        elif 'resource' in annotation_lower:
            return 'numbers'
        elif 'name' in annotation_lower:
            return 'character_name'
        elif 'time' in annotation_lower:
            return 'time_format'
        elif 'cast' in annotation_lower:
            return 'spell_name'
        elif 'location' in annotation_lower:
            return 'zone_name'
        else:
            return 'text'
    
    def _get_confidence_threshold(self, annotation: str) -> float:
        """Get OCR confidence threshold"""
        annotation_lower = annotation.lower()
        
        if 'health' in annotation_lower or 'resource' in annotation_lower:
            return 0.8  # High confidence for numbers
        elif 'time' in annotation_lower:
            return 0.9  # Very high for time
        elif 'name' in annotation_lower:
            return 0.7  # Medium for names
        else:
            return 0.6  # Default
    
    def generate_corrected_report(self) -> str:
        """Generate comprehensive corrected validation report"""
        validation = self.validate_corrected_zones()
        targets = self.create_priority_ocr_targets()
        
        report = []
        report.append("=" * 70)
        report.append("WoW Arena CORRECTED Zone Validation Report")
        report.append("=" * 70)
        
        # Summary
        report.append(f"\nSUMMARY:")
        report.append(f"  Total Zones Extracted: {validation['total_zones']}")
        report.append(f"  Validation Score: {validation['validation_score']}/100")
        report.append(f"  OCR Targets Created: {len(targets)}")
        
        # Critical zones status
        report.append(f"\nCRITICAL ZONES STATUS:")
        for zone_name, found in validation['key_zones_found'].items():
            status = "FOUND" if found else "MISSING"
            report.append(f"  {zone_name}: {status}")
        
        # Missing zones
        if validation['missing_critical_zones']:
            report.append(f"\nMISSING CRITICAL ZONES:")
            for zone in validation['missing_critical_zones']:
                report.append(f"  - {zone}")
        
        # Zone distribution by category
        report.append(f"\nZONE DISTRIBUTION:")  
        for category, count in validation['zones_by_category'].items():
            report.append(f"  {category}: {count} zones")
        
        # Coordinate distribution
        report.append(f"\nCOORDINATE DISTRIBUTION:")
        for region, count in validation['coordinate_analysis'].items():
            report.append(f"  {region}: {count} zones")
        
        # Top priority OCR targets
        report.append(f"\nTOP PRIORITY OCR TARGETS:")
        for target in targets[:10]:  # Top 10
            x, y = target['ocr_region']['x'], target['ocr_region']['y']
            report.append(f"  Priority {target['priority']}: {target['annotation']} @ ({x}, {y})")
        
        # Recommendations
        report.append(f"\nRECOMMENDATIONS:")
        if validation['validation_score'] >= 80:
            report.append("  - EXCELLENT: Zone extraction is highly accurate")
            report.append("  - Ready for production OCR implementation")
            report.append("  - Test with actual game frames for final validation")
        elif validation['validation_score'] >= 60:
            report.append("  - GOOD: Zone extraction is mostly accurate")
            report.append("  - Address missing critical zones if needed")
            report.append("  - Proceed with cautious OCR testing")
        else:
            report.append("  - NEEDS IMPROVEMENT: Review zone extraction")
            report.append("  - Several critical zones are missing")
            report.append("  - Re-examine SVG annotation accuracy")
        
        report.append("=" * 70)
        return "\n".join(report)

def main():
    """Main corrected validation function"""
    print("CORRECTED VALIDATOR: Starting corrected zone validation...")
    
    validator = CorrectedZoneValidator()
    
    # Create corrected overlay
    validator.create_corrected_overlay()
    
    # Generate and display report
    report = validator.generate_corrected_report()
    print(report)
    
    # Save files
    with open('corrected_validation_report.txt', 'w') as f:
        f.write(report)
    
    # Save OCR targets
    targets = validator.create_priority_ocr_targets()
    with open('corrected_ocr_targets.json', 'w') as f:
        json.dump(targets, f, indent=2)
    
    print(f"\nCORRECTED VALIDATION: Complete")
    print(f"  - Check 'corrected_zone_overlay.png' for visual verification")
    print(f"  - Review 'corrected_validation_report.txt' for analysis")
    print(f"  - Use 'corrected_ocr_targets.json' for OCR implementation")

if __name__ == "__main__":
    main()