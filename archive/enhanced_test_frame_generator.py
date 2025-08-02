#!/usr/bin/env python3
"""
Enhanced Test Frame Generator for WoW Arena Analysis
Creates test frames with full resolution coverage and zone tracking overlays
"""

import json
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional

class EnhancedTestFrameGenerator:
    """Generate test frames with enhanced zone overlays and coverage analysis"""
    
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
    
    def create_full_resolution_test_frame(self) -> np.ndarray:
        """Create test frame showing full 3440x1440 resolution with coverage analysis"""
        
        # Create frame with dark gray background
        frame = np.full((self.frame_height, self.frame_width, 3), (30, 30, 30), dtype=np.uint8)
        
        # Draw resolution grid
        self._draw_resolution_grid(frame)
        
        # Draw zones with enhanced visibility
        self._draw_enhanced_zones(frame)
        
        # Draw coverage analysis
        self._draw_coverage_analysis(frame)
        
        # Add resolution indicators
        self._add_resolution_indicators(frame)
        
        return frame
    
    def _draw_resolution_grid(self, frame: np.ndarray):
        """Draw resolution grid for reference"""
        
        # Vertical grid lines every 500px
        for x in range(0, self.frame_width, 500):
            cv2.line(frame, (x, 0), (x, self.frame_height), (60, 60, 60), 1)
            cv2.putText(frame, f'{x}', (x + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        # Horizontal grid lines every 200px
        for y in range(0, self.frame_height, 200):
            cv2.line(frame, (0, y), (self.frame_width, y), (60, 60, 60), 1)
            cv2.putText(frame, f'{y}', (5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        # Draw screen boundaries
        cv2.rectangle(frame, (0, 0), (self.frame_width-1, self.frame_height-1), (200, 200, 200), 2)
    
    def _draw_enhanced_zones(self, frame: np.ndarray):
        """Draw zones with enhanced visibility and labels"""
        
        if 'zones' not in self.zone_data:
            return
        
        # Enhanced color mapping for better visibility
        color_map = {
            '#ff3131': (31, 49, 255),    # Red (Health) - Bright Red
            '#1800ad': (173, 0, 24),     # Dark Blue (Major Abilities) - Blue
            '#5ce1e6': (230, 225, 92),   # Cyan (Resources) - Cyan
            '#ffde59': (89, 222, 255),   # Yellow (Specialized) - Yellow
            '#7ed957': (87, 217, 126),   # Light Green (Names) - Green
            '#ff914d': (77, 145, 255),   # Orange (Combat Log) - Orange
            '#ffffff': (255, 255, 255),  # White (Enemy Medallion) - White
            '#171717': (100, 100, 100),  # Dark Gray (Enemy Dispell) - Gray
            '#ff66c4': (196, 102, 255),  # Pink (Enemy Racial) - Pink
            '#5a321d': (60, 80, 140),    # Brown (Cast Bars) - Brown
            '#5e17eb': (235, 23, 94),    # Purple (Player Abilities) - Purple
            '#8c52ff': (255, 82, 140),   # Light Purple (Pet Abilities) - Light Purple
            '#e84d20': (32, 77, 232),    # Red-Orange (Debuffs) - Red-Orange
            '#768047': (71, 128, 118),   # Olive Green (Buffs) - Olive
            '#a6a6a6': (166, 166, 166),  # Light Gray (Enemy CC) - Light Gray
            '#ff5757': (87, 87, 255),    # Light Red (Arena Info) - Light Red
            '#5170ff': (255, 112, 81),   # Blue (Major Effect) - Blue
            '#545454': (84, 84, 84),     # Medium Gray (Healer CC) - Medium Gray
            '#0097b2': (178, 151, 0),    # Teal (Location) - Teal
            '#330a0a': (10, 50, 100),    # Dark Brown (Time) - Dark Brown
        }
        
        # Draw zones with thick borders and labels
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
            
            # Draw thick rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), bgr_color, 3)
            
            # Fill with semi-transparent color
            overlay = frame.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), bgr_color, -1)
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
            
            # Add zone annotation
            if w > 50 and h > 20:  # Only if zone is large enough
                text = annotation[:20] + "..." if len(annotation) > 20 else annotation
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                text_x = x + (w - text_size[0]) // 2
                text_y = y + (h + text_size[1]) // 2
                
                # Text background
                cv2.rectangle(frame, (text_x-2, text_y-text_size[1]-2), 
                             (text_x+text_size[0]+2, text_y+2), (0, 0, 0), -1)
                cv2.putText(frame, text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def _draw_coverage_analysis(self, frame: np.ndarray):
        """Draw coverage analysis indicators"""
        
        if 'zones' not in self.zone_data:
            return
        
        # Calculate coverage
        max_x = max_y = 0
        for zone in self.zone_data['zones']:
            bbox = zone['bbox']
            right_edge = bbox['x'] + bbox['width']
            bottom_edge = bbox['y'] + bbox['height']
            max_x = max(max_x, right_edge)
            max_y = max(max_y, bottom_edge)
        
        # Draw coverage boundary
        coverage_x = int(max_x)
        coverage_y = int(max_y)
        
        # Vertical coverage line
        cv2.line(frame, (coverage_x, 0), (coverage_x, self.frame_height), (0, 255, 255), 3)
        cv2.putText(frame, f'Max Coverage X: {coverage_x}', 
                   (coverage_x + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Horizontal coverage line
        cv2.line(frame, (0, coverage_y), (self.frame_width, coverage_y), (0, 255, 255), 3)
        cv2.putText(frame, f'Max Coverage Y: {coverage_y}', 
                   (10, coverage_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Uncovered areas
        if coverage_x < self.frame_width:
            cv2.rectangle(frame, (coverage_x, 0), (self.frame_width, self.frame_height), 
                         (0, 0, 255), 3)
            cv2.putText(frame, 'UNCOVERED AREA', 
                       (coverage_x + 50, self.frame_height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        
        if coverage_y < self.frame_height:
            cv2.rectangle(frame, (0, coverage_y), (self.frame_width, self.frame_height), 
                         (0, 0, 255), 3)
    
    def _add_resolution_indicators(self, frame: np.ndarray):
        """Add resolution and coverage indicators"""
        
        # Title
        cv2.putText(frame, f'WoW Arena Zone Coverage Test - {self.frame_width}x{self.frame_height}', 
                   (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # Coverage statistics
        if 'zones' in self.zone_data:
            max_x = max_y = 0
            for zone in self.zone_data['zones']:
                bbox = zone['bbox']
                max_x = max(max_x, bbox['x'] + bbox['width'])
                max_y = max(max_y, bbox['y'] + bbox['height'])
            
            coverage_pct_x = (max_x / self.frame_width) * 100
            coverage_pct_y = (max_y / self.frame_height) * 100
            
            coverage_text = f'Coverage: {coverage_pct_x:.1f}% width, {coverage_pct_y:.1f}% height'
            cv2.putText(frame, coverage_text, 
                       (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            
            zone_count_text = f'Total Zones: {len(self.zone_data["zones"])}'
            cv2.putText(frame, zone_count_text, 
                       (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Corner indicators
        cv2.circle(frame, (0, 0), 10, (0, 255, 0), -1)  # Top-left
        cv2.circle(frame, (self.frame_width-1, 0), 10, (0, 255, 0), -1)  # Top-right
        cv2.circle(frame, (0, self.frame_height-1), 10, (0, 255, 0), -1)  # Bottom-left
        cv2.circle(frame, (self.frame_width-1, self.frame_height-1), 10, (0, 255, 0), -1)  # Bottom-right
    
    def create_zone_priority_overlay(self) -> np.ndarray:
        """Create overlay showing OCR priority zones"""
        
        frame = np.full((self.frame_height, self.frame_width, 3), (20, 20, 20), dtype=np.uint8)
        
        if 'zones' not in self.zone_data:
            return frame
        
        # Priority color mapping
        priority_colors = {
            10: (0, 255, 0),    # Highest priority - Green
            9: (0, 255, 255),   # High priority - Cyan
            8: (0, 165, 255),   # Medium-high - Orange
            7: (0, 100, 255),   # Medium - Red
            6: (255, 255, 0),   # Medium-low - Yellow
            5: (255, 0, 255),   # Low - Magenta
        }
        
        # Draw zones by priority
        for zone in self.zone_data['zones']:
            bbox = zone['bbox']
            annotation = zone.get('annotation', '')
            
            # Determine priority
            priority = self._get_zone_priority(annotation)
            if priority < 5:
                continue  # Skip very low priority zones
            
            x = max(0, min(int(bbox['x']), self.frame_width-1))
            y = max(0, min(int(bbox['y']), self.frame_height-1))
            w = max(1, min(int(bbox['width']), self.frame_width-x))
            h = max(1, min(int(bbox['height']), self.frame_height-y))
            
            color = priority_colors.get(priority, (128, 128, 128))
            
            # Draw priority zone
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Add priority label
            if w > 30 and h > 20:
                cv2.putText(frame, f'P{priority}', (x + 2, y + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Add legend
        legend_y = 50
        for priority, color in priority_colors.items():
            cv2.rectangle(frame, (50, legend_y), (80, legend_y + 20), color, -1)
            cv2.putText(frame, f'Priority {priority}', (90, legend_y + 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            legend_y += 30
        
        return frame
    
    def _get_zone_priority(self, annotation: str) -> int:
        """Get OCR priority for zone annotation"""
        annotation_lower = annotation.lower()
        
        if 'player health' in annotation_lower:
            return 10
        elif 'target health' in annotation_lower:
            return 9
        elif 'arena enemy' in annotation_lower and 'health' in annotation_lower:
            return 8
        elif 'cast bar' in annotation_lower:
            return 9
        elif 'resource' in annotation_lower:
            return 8
        elif 'time' in annotation_lower:
            return 6
        elif 'abilities' in annotation_lower:
            return 7
        elif 'name' in annotation_lower:
            return 6
        else:
            return 4
    
    def create_comparison_view(self) -> np.ndarray:
        """Create side-by-side comparison of zones and priorities"""
        
        # Create individual frames
        zones_frame = self.create_full_resolution_test_frame()
        priority_frame = self.create_zone_priority_overlay()
        
        # Scale frames to fit side by side
        scale_factor = 0.5
        new_width = int(self.frame_width * scale_factor)
        new_height = int(self.frame_height * scale_factor)
        
        zones_scaled = cv2.resize(zones_frame, (new_width, new_height))
        priority_scaled = cv2.resize(priority_frame, (new_width, new_height))
        
        # Create combined frame
        combined = np.zeros((new_height, new_width * 2, 3), dtype=np.uint8)
        combined[:, :new_width] = zones_scaled
        combined[:, new_width:] = priority_scaled
        
        # Add labels
        cv2.putText(combined, 'Zone Coverage Analysis', 
                   (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(combined, 'OCR Priority Mapping', 
                   (new_width + 20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return combined

def main():
    """Generate enhanced test frames"""
    print("ENHANCED TEST FRAME GENERATOR: Starting...")
    
    generator = EnhancedTestFrameGenerator()
    
    # Create full resolution test frame
    print("Creating full resolution coverage test frame...")
    full_frame = generator.create_full_resolution_test_frame()
    cv2.imwrite('test_frame_full_resolution.png', full_frame)
    print("SAVED: test_frame_full_resolution.png")
    
    # Create priority overlay
    print("Creating OCR priority overlay...")
    priority_frame = generator.create_zone_priority_overlay()
    cv2.imwrite('test_frame_priority_overlay.png', priority_frame)
    print("SAVED: test_frame_priority_overlay.png")
    
    # Create comparison view
    print("Creating comparison view...")
    comparison_frame = generator.create_comparison_view()
    cv2.imwrite('test_frame_comparison.png', comparison_frame)
    print("SAVED: test_frame_comparison.png")
    
    print("\nENHANCED TEST FRAMES: Complete")
    print("Files generated:")
    print("  - test_frame_full_resolution.png: Full coverage analysis")
    print("  - test_frame_priority_overlay.png: OCR priority mapping")
    print("  - test_frame_comparison.png: Side-by-side comparison")

if __name__ == "__main__":
    main()