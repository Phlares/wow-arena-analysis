#!/usr/bin/env python3
"""
OCR Zone Validation Script for WoW Arena Analysis
Tests and validates computer vision zone extraction for accuracy
"""

import json
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
from pathlib import Path

class OCRZoneValidator:
    """Validates OCR zones against extracted frame data"""
    
    def __init__(self, zone_data_file: str = 'cv_zone_extraction.json'):
        """Initialize validator with zone data"""
        self.zone_data = self._load_zone_data(zone_data_file)
        self.frame_width = 3440  # Ultrawide resolution
        self.frame_height = 1440
        
    def _load_zone_data(self, file_path: str) -> Dict:
        """Load extracted zone data from JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Zone data file {file_path} not found")
            return {}
        except json.JSONDecurityError as e:
            print(f"ERROR: Invalid JSON in {file_path}: {e}")
            return {}
    
    def create_zone_overlay(self, output_path: str = 'zone_overlay.png') -> bool:
        """Create visual overlay of all detected zones"""
        try:
            # Create blank canvas
            overlay = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
            
            # Color mapping for visualization
            color_map = {
                '#ff3131': (49, 49, 255),    # Red -> BGR
                '#1800ad': (173, 0, 24),     # Dark Blue -> BGR  
                '#5ce1e6': (230, 225, 92),   # Cyan -> BGR
                '#ffde59': (89, 222, 255),   # Yellow -> BGR
                '#7ed957': (87, 217, 126),   # Light Green -> BGR
                '#ff914d': (77, 145, 255),   # Orange -> BGR
                '#ffffff': (255, 255, 255),  # White -> BGR
                '#171717': (23, 23, 23),     # Dark Gray -> BGR
                '#ff66c4': (196, 102, 255),  # Pink -> BGR
                '#5a321d': (29, 50, 90),     # Brown -> BGR
                '#5e17eb': (235, 23, 94),    # Purple -> BGR
                '#8c52ff': (255, 82, 140),   # Light Purple -> BGR
                '#e84d20': (32, 77, 232),    # Red-Orange -> BGR
                '#768047': (71, 128, 118),   # Olive Green -> BGR
                '#a6a6a6': (166, 166, 166),  # Light Gray -> BGR
                '#ff5757': (87, 87, 255),    # Light Red -> BGR
                '#5170ff': (255, 112, 81),   # Blue -> BGR
                '#545454': (84, 84, 84),     # Medium Gray -> BGR
                '#0097b2': (178, 151, 0),    # Teal -> BGR
                '#330a0a': (10, 10, 51),     # Dark Brown -> BGR
            }
            
            zones_drawn = 0
            if 'zones' in self.zone_data:
                for zone in self.zone_data['zones']:
                    color_hex = zone['color']
                    bbox = zone['bbox']
                    
                    # Convert to integer coordinates
                    x = int(bbox['x'])
                    y = int(bbox['y']) 
                    w = int(bbox['width'])
                    h = int(bbox['height'])
                    
                    # Get color for this zone
                    bgr_color = color_map.get(color_hex, (128, 128, 128))  # Default gray
                    
                    # Draw rectangle
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), bgr_color, 2)
                    
                    # Add zone ID text
                    zone_id = zone.get('zone_id', 'unknown')
                    cv2.putText(overlay, zone_id, (x + 5, y + 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, bgr_color, 1)
                    
                    zones_drawn += 1
            
            # Save overlay image
            cv2.imwrite(output_path, overlay)
            print(f"OVERLAY: Created zone overlay with {zones_drawn} zones -> {output_path}")
            return True
            
        except Exception as e:
            print(f"ERROR: Creating zone overlay: {e}")
            return False
    
    def validate_zone_categories(self) -> Dict:
        """Validate that we have zones for all expected categories"""
        validation_results = {
            'total_zones_found': 0,
            'total_zones_expected': 0,
            'color_coverage': {},
            'missing_categories': [],
            'zone_distribution': {},
            'validation_passed': False
        }
        
        try:
            # Get extraction summary
            if 'extraction_summary' in self.zone_data:
                summary = self.zone_data['extraction_summary']
                validation_results['total_zones_found'] = summary.get('total_zones', 0)
                validation_results['total_zones_expected'] = summary.get('expected_zones', 0)
            
            # Analyze color groups
            if 'color_groups' in self.zone_data:
                color_groups = self.zone_data['color_groups']
                validation_results['zone_distribution'] = color_groups
                
                # Check coverage against expected colors
                if 'zone_mapping' in self.zone_data:
                    expected_colors = self.zone_data['zone_mapping']['color_definitions']
                    
                    for color, description in expected_colors.items():
                        found_count = color_groups.get(color, 0)
                        validation_results['color_coverage'][color] = {
                            'description': description,
                            'zones_found': found_count,
                            'has_zones': found_count > 0
                        }
                        
                        if found_count == 0:
                            validation_results['missing_categories'].append(description)
            
            # Determine if validation passed
            missing_count = len(validation_results['missing_categories'])
            found_colors = len([c for c in validation_results['color_coverage'].values() if c['has_zones']])
            total_colors = len(validation_results['color_coverage'])
            
            validation_results['validation_passed'] = (
                missing_count <= 3 and  # Allow up to 3 missing categories
                found_colors >= (total_colors * 0.6)  # At least 60% color coverage
            )
            
            return validation_results
            
        except Exception as e:
            print(f"ERROR: Validating zone categories: {e}")
            validation_results['error'] = str(e)
            return validation_results
    
    def create_test_frame_targets(self, test_frame_path: Optional[str] = None) -> List[Dict]:
        """Create OCR target regions for testing on actual frame"""
        targets = []
        
        if not test_frame_path or not os.path.exists(test_frame_path):
            print("INFO: No test frame provided, creating theoretical targets")
            
        try:
            # Create OCR targets for each zone
            if 'zones' in self.zone_data:
                for zone in self.zone_data['zones']:
                    bbox = zone['bbox']
                    color = zone['color']
                    
                    # Get zone type from color
                    zone_type = "Unknown"
                    if 'zone_mapping' in self.zone_data:
                        zone_type = self.zone_data['zone_mapping']['color_definitions'].get(color, "Unknown")
                    
                    target = {
                        'zone_id': zone['zone_id'],
                        'zone_type': zone_type,
                        'color': color,
                        'ocr_region': {
                            'x': int(bbox['x']),
                            'y': int(bbox['y']),
                            'width': int(bbox['width']),
                            'height': int(bbox['height'])
                        },
                        'expected_content_type': self._get_content_type(zone_type),
                        'ocr_confidence_threshold': self._get_confidence_threshold(zone_type)
                    }
                    targets.append(target)
            
            print(f"TARGETS: Created {len(targets)} OCR target regions")
            return targets
            
        except Exception as e:
            print(f"ERROR: Creating test frame targets: {e}")
            return []
    
    def _get_content_type(self, zone_type: str) -> str:
        """Determine expected content type for OCR"""
        content_map = {
            'Healthbars': 'numeric_percentage',
            'Resource Bars': 'numeric_values', 
            'Names of characters': 'text_names',
            'Major Abilities': 'ability_names',
            'Arena Information': 'mixed_text_numeric',
            'Current Time': 'time_format',
            'Location Title': 'location_name',
            'Cast bars': 'spell_names',
            'Combat log details': 'mixed_combat_text'
        }
        
        for key, content_type in content_map.items():
            if key.lower() in zone_type.lower():
                return content_type
        
        return 'general_text'
    
    def _get_confidence_threshold(self, zone_type: str) -> float:
        """Get OCR confidence threshold based on zone type"""
        # Different zones may require different confidence levels
        threshold_map = {
            'healthbars': 0.8,      # High confidence for health percentages
            'resource': 0.8,        # High confidence for resource values  
            'names': 0.7,           # Medium confidence for character names
            'time': 0.9,            # Very high confidence for time
            'location': 0.7,        # Medium confidence for location names
            'abilities': 0.6,       # Lower confidence for ability names (varied fonts)
            'combat': 0.5           # Lower confidence for combat text (lots of variation)
        }
        
        for key, threshold in threshold_map.items():
            if key in zone_type.lower():
                return threshold
        
        return 0.6  # Default threshold
    
    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report"""
        try:
            validation = self.validate_zone_categories()
            
            report = []
            report.append("=" * 60)
            report.append("WoW Arena OCR Zone Validation Report")
            report.append("=" * 60)
            
            # Summary
            report.append(f"\nSUMMARY:")
            report.append(f"  Zones Found: {validation['total_zones_found']}")
            report.append(f"  Zones Expected: {validation['total_zones_expected']}")
            report.append(f"  Validation Status: {'PASSED' if validation['validation_passed'] else 'FAILED'}")
            
            # Color coverage
            report.append(f"\nCOLOR COVERAGE:")
            for color, info in validation['color_coverage'].items():
                status = "OK" if info['has_zones'] else "MISSING"
                report.append(f"  {color}: {info['zones_found']} zones - {info['description']} [{status}]")
            
            # Missing categories
            if validation['missing_categories']:
                report.append(f"\nMISSING CATEGORIES:")
                for category in validation['missing_categories']:
                    report.append(f"  - {category}")
            
            # Zone distribution
            report.append(f"\nZONE DISTRIBUTION:")
            for color, count in validation['zone_distribution'].items():
                report.append(f"  {color}: {count} zones")
            
            # OCR targets
            targets = self.create_test_frame_targets()
            report.append(f"\nOCR TARGET REGIONS: {len(targets)} created")
            
            # Recommendations
            report.append(f"\nRECOMMENDATIONS:")
            if validation['validation_passed']:
                report.append("  - Zone extraction successful, ready for OCR implementation")
                report.append("  - Test on actual frame data for validation")
                report.append("  - Fine-tune OCR confidence thresholds per zone type")
            else:
                report.append("  - Review SVG annotation completeness")
                report.append("  - Check extraction patterns for missing zones")
                report.append("  - Verify color definitions match actual UI elements")
            
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            return f"ERROR: Generating validation report: {e}"

def main():
    """Main validation function"""
    print("VALIDATOR: OCR Zone Validation Starting...")
    
    # Initialize validator
    validator = OCRZoneValidator()
    
    # Create zone overlay visualization
    validator.create_zone_overlay()
    
    # Generate and display validation report
    report = validator.generate_validation_report()
    print(report)
    
    # Save validation report
    with open('ocr_validation_report.txt', 'w') as f:
        f.write(report)
    
    print("\nVALIDATION: Complete - Check 'zone_overlay.png' and 'ocr_validation_report.txt'")

if __name__ == "__main__":
    main()