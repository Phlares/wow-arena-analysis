"""
Memory-efficient health and resource bar detection for WoW Arena UI.
Detects Party1/Party2/Player/Arena1-3 health bars and resource bars.
Stays under 22GB memory limit.
"""

import cv2
import numpy as np
import os
from pathlib import Path
import gc

class WoWUIDetector:
    def __init__(self):
        self.resolution = (3440, 1440)  # Standard resolution from analysis
        self.ui_regions = self._define_ui_regions()
    
    def _define_ui_regions(self):
        """Define UI regions based on monthly analysis."""
        width, height = self.resolution
        
        return {
            # Player and target frames
            "player_frame": {
                "region": (int(width*0.02), int(height*0.05), int(width*0.25), int(height*0.25)),
                "type": "player_health",
                "description": "Player health/mana"
            },
            "target_frame": {
                "region": (int(width*0.75), int(height*0.05), int(width*0.98), int(height*0.25)),
                "type": "target_health", 
                "description": "Target health/mana"
            },
            
            # Party frames (2v2/3v3)
            "party1_frame": {
                "region": (int(width*0.02), int(height*0.25), int(width*0.20), int(height*0.35)),
                "type": "party_health",
                "description": "Party member 1"
            },
            "party2_frame": {
                "region": (int(width*0.02), int(height*0.35), int(width*0.20), int(height*0.45)),
                "type": "party_health",
                "description": "Party member 2"
            },
            
            # Arena enemy frames
            "arena_frames": {
                "region": (int(width*0.75), int(height*0.25), int(width*0.98), int(height*0.55)),
                "type": "arena_health",
                "description": "Arena enemies 1-3"
            },
            
            # Cast bar
            "cast_bar": {
                "region": (int(width*0.3), int(height*0.8), int(width*0.7), int(height*0.9)),
                "type": "cast_bar",
                "description": "Player cast bar"
            },
            
            # Combat log panels
            "combat_log_left": {
                "region": (int(width*0.02), int(height*0.50), int(width*0.35), int(height*0.75)),
                "type": "combat_log",
                "description": "Left combat log panel"
            },
            "combat_log_right": {
                "region": (int(width*0.65), int(height*0.50), int(width*0.98), int(height*0.75)),
                "type": "combat_log", 
                "description": "Right combat log panel"
            }
        }
    
    def detect_health_bars(self, frame_region, region_name):
        """Detect health bars in a UI region with memory efficiency."""
        if frame_region.size == 0:
            return {"health_detected": False}
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame_region, cv2.COLOR_BGR2HSV)
        
        # Health bar detection (green hues)
        # HSV ranges for health (green): H=35-85, S=50-255, V=50-255
        health_lower = np.array([35, 50, 50])
        health_upper = np.array([85, 255, 255])
        health_mask = cv2.inRange(hsv, health_lower, health_upper)
        
        # Mana bar detection (blue hues)  
        # HSV ranges for mana (blue): H=100-130, S=50-255, V=50-255
        mana_lower = np.array([100, 50, 50])
        mana_upper = np.array([130, 255, 255])
        mana_mask = cv2.inRange(hsv, mana_lower, mana_upper)
        
        # Energy/Rage detection (yellow/orange hues)
        # HSV ranges for energy: H=15-35, S=50-255, V=50-255
        energy_lower = np.array([15, 50, 50])
        energy_upper = np.array([35, 255, 255])
        energy_mask = cv2.inRange(hsv, energy_lower, energy_upper)
        
        # Count pixels for each resource type
        total_pixels = frame_region.shape[0] * frame_region.shape[1]
        health_pixels = np.sum(health_mask > 0)
        mana_pixels = np.sum(mana_mask > 0)
        energy_pixels = np.sum(energy_mask > 0)
        
        # Calculate percentages
        health_pct = (health_pixels / total_pixels) * 100
        mana_pct = (mana_pixels / total_pixels) * 100
        energy_pct = (energy_pixels / total_pixels) * 100
        
        # Determine bar presence (threshold: >0.5% coverage)
        health_detected = health_pct > 0.5
        mana_detected = mana_pct > 0.5
        energy_detected = energy_pct > 0.5
        
        # Clean up masks
        del hsv, health_mask, mana_mask, energy_mask
        gc.collect()
        
        return {
            "health_detected": health_detected,
            "health_percentage": health_pct,
            "mana_detected": mana_detected, 
            "mana_percentage": mana_pct,
            "energy_detected": energy_detected,
            "energy_percentage": energy_pct,
            "total_resources": int(health_detected) + int(mana_detected) + int(energy_detected)
        }
    
    def analyze_arena_enemies(self, arena_region):
        """Detect multiple enemy health bars in arena frame region."""
        if arena_region.size == 0:
            return {"enemies_detected": 0}
        
        height = arena_region.shape[0]
        
        # Split arena region into 3 potential enemy slots
        enemy_height = height // 3
        enemies = []
        
        for i in range(3):
            y_start = i * enemy_height
            y_end = (i + 1) * enemy_height
            enemy_slice = arena_region[y_start:y_end, :]
            
            if enemy_slice.size > 0:
                enemy_result = self.detect_health_bars(enemy_slice, f"arena_enemy_{i+1}")
                enemy_result["slot"] = i + 1
                enemies.append(enemy_result)
        
        active_enemies = sum(1 for enemy in enemies if enemy.get("health_detected", False))
        
        return {
            "enemies_detected": active_enemies,
            "enemy_details": enemies
        }
    
    def detect_combat_log_panel(self, frame_region, region_name):
        """Detect combat log panel presence and text activity."""
        if frame_region.size == 0:
            return {"panel_detected": False}
        
        # Convert to grayscale for text detection
        gray = cv2.cvtColor(frame_region, cv2.COLOR_BGR2GRAY)
        
        # Text detection using edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Count edge pixels (indicates text/UI elements)
        edge_pixels = np.sum(edges > 0)
        total_pixels = frame_region.shape[0] * frame_region.shape[1]
        edge_percentage = (edge_pixels / total_pixels) * 100
        
        # Panel background detection (darker regions for text panels)
        dark_threshold = 50
        dark_pixels = np.sum(gray < dark_threshold)
        dark_percentage = (dark_pixels / total_pixels) * 100
        
        # Detect text activity (white/light text on dark background)
        text_threshold = 200
        text_pixels = np.sum(gray > text_threshold)
        text_percentage = (text_pixels / total_pixels) * 100
        
        # Panel presence criteria
        panel_detected = (
            edge_percentage > 2.0 and  # Sufficient edge content
            dark_percentage > 30.0 and # Dark background present
            text_percentage > 1.0      # Some light text visible
        )
        
        # Clean up
        del gray, edges
        gc.collect()
        
        return {
            "panel_detected": panel_detected,
            "edge_percentage": edge_percentage,
            "dark_background_percentage": dark_percentage, 
            "text_percentage": text_percentage,
            "activity_score": edge_percentage + text_percentage  # Combined activity metric
        }
    
    def process_frame(self, frame):
        """Process single frame for all UI elements with memory management."""
        results = {
            "frame_size": f"{frame.shape[1]}x{frame.shape[0]}",
            "ui_elements": {}
        }
        
        for region_name, region_info in self.ui_regions.items():
            x1, y1, x2, y2 = region_info["region"]
            region_frame = frame[y1:y2, x1:x2]
            
            if region_name == "arena_frames":
                # Special handling for multiple arena enemies
                analysis = self.analyze_arena_enemies(region_frame)
            elif region_info["type"] == "combat_log":
                # Combat log panel detection
                analysis = self.detect_combat_log_panel(region_frame, region_name)
            else:
                # Standard health/resource bar detection
                analysis = self.detect_health_bars(region_frame, region_name)
            
            analysis["region_type"] = region_info["type"]
            analysis["description"] = region_info["description"]
            analysis["coordinates"] = f"({x1},{y1})-({x2},{y2})"
            
            results["ui_elements"][region_name] = analysis
            
            # Clean up region
            del region_frame
        
        return results

def test_ui_detection():
    """Test UI detection on sample frames."""
    detector = WoWUIDetector()
    samples_dir = Path("ui_samples")
    
    if not samples_dir.exists():
        print("ERROR: ui_samples directory not found. Run sample_monthly_frames.py first.")
        return
    
    print("Testing UI detection on monthly samples...")
    print("="*60)
    
    sample_files = list(samples_dir.glob("*.jpg"))
    
    for sample_file in sorted(sample_files):
        print(f"\nAnalyzing: {sample_file.name}")
        print("-" * 40)
        
        # Load frame
        frame = cv2.imread(str(sample_file))
        if frame is None:
            print(f"ERROR: Could not load {sample_file}")
            continue
        
        # Resize to standard resolution if needed
        if frame.shape[:2] != (1440, 3440):
            frame = cv2.resize(frame, (3440, 1440))
        
        # Process frame
        results = detector.process_frame(frame)
        
        # Print results
        print(f"Frame: {results['frame_size']}")
        
        for ui_name, ui_data in results["ui_elements"].items():
            desc = ui_data["description"]
            
            if ui_name == "arena_frames":
                enemies = ui_data.get("enemies_detected", 0)
                print(f"  {desc}: {enemies} enemies detected")
                
                for enemy in ui_data.get("enemy_details", []):
                    slot = enemy.get("slot", "?")
                    health = enemy.get("health_detected", False)
                    health_pct = enemy.get("health_percentage", 0)
                    if health:
                        print(f"    Enemy {slot}: Health {health_pct:.1f}%")
            elif ui_data.get("region_type") == "combat_log":
                panel_detected = ui_data.get("panel_detected", False)
                activity_score = ui_data.get("activity_score", 0)
                text_pct = ui_data.get("text_percentage", 0)
                
                if panel_detected:
                    print(f"  {desc}: ACTIVE (Activity: {activity_score:.1f}, Text: {text_pct:.1f}%)")
                else:
                    print(f"  {desc}: No panel detected")
            else:
                health = ui_data.get("health_detected", False)
                mana = ui_data.get("mana_detected", False)
                energy = ui_data.get("energy_detected", False)
                total = ui_data.get("total_resources", 0)
                
                resources = []
                if health:
                    resources.append(f"Health {ui_data.get('health_percentage', 0):.1f}%")
                if mana:
                    resources.append(f"Mana {ui_data.get('mana_percentage', 0):.1f}%")
                if energy:
                    resources.append(f"Energy {ui_data.get('energy_percentage', 0):.1f}%")
                
                if resources:
                    print(f"  {desc}: {', '.join(resources)}")
                else:
                    print(f"  {desc}: No resources detected")
        
        # Clean up
        del frame
        gc.collect()
    
    print(f"\n{'='*60}")
    print("UI detection testing complete!")

if __name__ == "__main__":
    test_ui_detection()