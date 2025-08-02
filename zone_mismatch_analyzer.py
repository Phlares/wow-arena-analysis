#!/usr/bin/env python3
"""
Zone Mismatch Analyzer
Analyzes the mismatch between expected zones and actual WoW UI layout
"""

import json
import cv2
import numpy as np
import os

def analyze_zone_mismatch():
    """Analyze mismatch between zones and actual game UI"""
    
    # Load extracted frame
    frame_path = 'debug_ocr_output/extracted_frame.png'
    if not os.path.exists(frame_path):
        print("ERROR: No extracted frame found. Run debug_ocr_tester.py first.")
        return
    
    frame = cv2.imread(frame_path)
    print(f"FRAME ANALYSIS: {frame.shape}")
    
    # Load zone mapping
    with open('scaled_zone_mapping.json', 'r') as f:
        zone_data = json.load(f)
    
    # Create overlay showing zone mismatches
    overlay = frame.copy()
    
    # Enhanced color mapping for zones
    color_map = {
        '#ff3131': (31, 49, 255),    # Red (Health) - Bright Red
        '#5ce1e6': (230, 225, 92),   # Cyan (Resources) - Cyan
        '#7ed957': (87, 217, 126),   # Light Green (Names) - Green
        '#5a321d': (60, 80, 140),    # Brown (Cast Bars) - Brown
        '#330a0a': (10, 50, 100),    # Dark Brown (Time) - Dark Brown
    }
    
    # Focus on key zone types that should be most visible
    key_zone_types = ['health', 'resource', 'name', 'cast bar', 'time']
    
    mismatch_count = 0
    analyzed_zones = 0
    
    print("\nZONE MISMATCH ANALYSIS:")
    print("=" * 60)
    
    for zone in zone_data['zones']:
        annotation = zone.get('annotation', '').lower()
        
        # Only analyze key zones
        is_key_zone = any(key_type in annotation for key_type in key_zone_types)
        if not is_key_zone:
            continue
            
        analyzed_zones += 1
        
        bbox = zone['bbox']
        color = zone['color']
        
        x = int(bbox['x'])
        y = int(bbox['y'])
        w = int(bbox['width'])
        h = int(bbox['height'])
        
        # Extract region from actual frame
        roi = frame[y:y+h, x:x+w]
        
        # Analyze if zone contains expected UI elements
        mismatch = analyze_roi_content(roi, annotation)
        if mismatch:
            mismatch_count += 1
        
        # Draw zone on overlay
        zone_color = color_map.get(color, (128, 128, 128))
        cv2.rectangle(overlay, (x, y), (x + w, y + h), zone_color, 2)
        
        # Add annotation
        if w > 50 and h > 20:
            text = annotation[:15] + "..." if len(annotation) > 15 else annotation
            cv2.putText(overlay, text, (x + 2, y + 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, zone_color, 1)
        
        # Show mismatch status
        status = "MISMATCH" if mismatch else "OK"
        status_color = (0, 0, 255) if mismatch else (0, 255, 0)
        cv2.putText(overlay, status, (x + 2, y + h - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, status_color, 1)
        
        print(f"Zone: {annotation:30} | Status: {status:8} | Pos: ({x:4}, {y:4})")
    
    # Save mismatch overlay
    cv2.imwrite('zone_mismatch_analysis.png', overlay)
    
    print("=" * 60)
    print(f"ANALYSIS COMPLETE:")
    print(f"  Key zones analyzed: {analyzed_zones}")
    print(f"  Zones with mismatches: {mismatch_count}")
    print(f"  Mismatch rate: {(mismatch_count/analyzed_zones*100):.1f}%")
    print(f"  Overlay saved: zone_mismatch_analysis.png")
    
    # Recommendations
    print(f"\nRECOMMENDATIONS:")
    if mismatch_count / analyzed_zones > 0.5:
        print("  - MAJOR UI LAYOUT CHANGE: Zones don't match current UI")
        print("  - Need to re-annotate SVG for 2025 UI layout")
        print("  - Consider creating era-specific zone mappings")
    else:
        print("  - Minor adjustments needed to zone positioning")
        print("  - Fine-tune zone coordinates for better accuracy")

def analyze_roi_content(roi, expected_annotation):
    """Analyze if ROI contains expected content type"""
    
    if roi.size == 0:
        return True  # Empty ROI is definitely a mismatch
    
    # Convert to grayscale for analysis
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Basic content analysis
    mean_intensity = np.mean(gray)
    std_intensity = np.std(gray)
    
    # Expected content characteristics
    if 'health' in expected_annotation:
        # Health bars should have green/red colors and specific patterns
        # Look for green (health) or red (low health) dominance
        green_channel = roi[:, :, 1]  # Green channel
        red_channel = roi[:, :, 2]    # Red channel
        
        green_dominance = np.mean(green_channel) > np.mean(gray) * 1.2
        red_dominance = np.mean(red_channel) > np.mean(gray) * 1.2
        
        has_health_colors = green_dominance or red_dominance
        return not has_health_colors
        
    elif 'name' in expected_annotation:
        # Character names should have text-like characteristics
        # Look for sufficient contrast variation
        return std_intensity < 20  # Low variation = probably not text
        
    elif 'time' in expected_annotation:
        # Time display should be in top area and have text
        return std_intensity < 15
        
    elif 'cast bar' in expected_annotation:
        # Cast bars should have horizontal patterns
        return std_intensity < 25
    
    # Default: assume mismatch if very low variation (likely empty/wrong area)
    return std_intensity < 10

if __name__ == "__main__":
    analyze_zone_mismatch()