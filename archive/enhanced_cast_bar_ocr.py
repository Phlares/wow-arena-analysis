"""
Enhanced cast bar detection with spell name OCR for WoW Arena analysis.
Memory-efficient implementation staying under 22GB limit.
"""

import cv2
import numpy as np
import pytesseract
from pathlib import Path
import gc
import os

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class CastBarDetector:
    def __init__(self):
        self.resolution = (3440, 1440)
        self.cast_bar_region = self._define_cast_bar_region()
        
        # Common WoW spell names for validation
        self.common_spells = {
            # Warlock spells
            'chaos bolt', 'fear', 'mortal coil', 'shadowfury', 'unstable affliction',
            'agony', 'corruption', 'drain life', 'hellfire', 'rain of fire',
            
            # General spells  
            'polymorph', 'counterspell', 'fireball', 'frostbolt', 'pyroblast',
            'greater heal', 'mind control', 'psychic scream', 'shadow word pain',
            'lightning bolt', 'chain lightning', 'healing wave', 'earth shock',
            
            # Common abilities
            'mount up', 'hearthstone', 'bandage', 'first aid'
        }
    
    def _define_cast_bar_region(self):
        """Define cast bar region based on resolution analysis."""
        width, height = self.resolution
        
        return {
            "region": (int(width*0.3), int(height*0.8), int(width*0.7), int(height*0.9)),
            "description": "Player cast bar with spell name"
        }
    
    def detect_cast_bar_activity(self, cast_region):
        """Detect if cast bar is active and estimate progress."""
        if cast_region.size == 0:
            return {"casting": False}
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(cast_region, cv2.COLOR_BGR2HSV)
        
        # Cast bar colors - yellow/orange progress bar
        cast_lower = np.array([15, 100, 100])  # More saturated yellow
        cast_upper = np.array([35, 255, 255])
        cast_mask = cv2.inRange(hsv, cast_lower, cast_upper)
        
        # Calculate cast bar activity
        total_pixels = cast_region.shape[0] * cast_region.shape[1]
        cast_pixels = np.sum(cast_mask > 0)
        cast_percentage = (cast_pixels / total_pixels) * 100
        
        # Detect cast bar frame (darker edges)
        gray = cv2.cvtColor(cast_region, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = np.sum(edges > 0)
        edge_percentage = (edge_pixels / total_pixels) * 100
        
        # Casting detected if significant color activity + UI elements
        casting_detected = cast_percentage > 1.0 and edge_percentage > 3.0
        
        # Clean up
        del hsv, cast_mask, gray, edges
        gc.collect()
        
        return {
            "casting": casting_detected,
            "cast_progress_percentage": cast_percentage,
            "ui_complexity": edge_percentage
        }
    
    def preprocess_for_spell_ocr(self, cast_region):
        """Preprocess cast bar region for optimal spell name OCR."""
        if cast_region.size == 0:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(cast_region, cv2.COLOR_BGR2GRAY)
        
        # Focus on text area (typically top portion of cast bar)
        height = gray.shape[0]
        text_region = gray[0:int(height*0.4), :]  # Top 40% for spell name
        
        # Enhance contrast for text
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(text_region)
        
        # Threshold for white text on dark background
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up text
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Scale up for better OCR (2x)
        height, width = cleaned.shape
        scaled = cv2.resize(cleaned, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
        
        return scaled
    
    def extract_spell_name(self, cast_region):
        """Extract spell name from cast bar using OCR."""
        preprocessed = self.preprocess_for_spell_ocr(cast_region)
        
        if preprocessed is None:
            return {"spell_detected": False}
        
        try:
            # OCR configuration for spell names
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\' \''
            
            # Extract text
            spell_text = pytesseract.image_to_string(preprocessed, config=custom_config).strip()
            
            # Clean up the text
            spell_text = spell_text.lower().replace('\n', ' ').strip()
            
            # Validate against known spells
            spell_confidence = 0.0
            best_match = ""
            
            if len(spell_text) > 2:  # Minimum viable spell name length
                for known_spell in self.common_spells:
                    # Simple fuzzy matching - check if spell text contains known spell
                    if known_spell in spell_text or spell_text in known_spell:
                        confidence = len(known_spell) / max(len(spell_text), len(known_spell))
                        if confidence > spell_confidence:
                            spell_confidence = confidence
                            best_match = known_spell
            
            # Clean up
            del preprocessed
            gc.collect()
            
            return {
                "spell_detected": len(spell_text) > 0,
                "raw_text": spell_text,
                "spell_name": best_match if spell_confidence > 0.5 else spell_text,
                "confidence": spell_confidence,
                "validated": spell_confidence > 0.5
            }
            
        except Exception as e:
            # Clean up on error
            if 'preprocessed' in locals():
                del preprocessed
            gc.collect()
            
            return {
                "spell_detected": False,
                "error": str(e)
            }
    
    def analyze_cast_bar(self, frame):
        """Complete cast bar analysis with activity detection and spell OCR."""
        x1, y1, x2, y2 = self.cast_bar_region["region"]
        cast_region = frame[y1:y2, x1:x2]
        
        # Detect casting activity
        activity_result = self.detect_cast_bar_activity(cast_region)
        
        # If casting detected, try OCR
        spell_result = {"spell_detected": False}
        if activity_result.get("casting", False):
            spell_result = self.extract_spell_name(cast_region)
        
        # Combine results
        result = {
            "region": f"({x1},{y1})-({x2},{y2})",
            "region_size": f"{x2-x1}x{y2-y1}",
            **activity_result,
            **spell_result
        }
        
        # Clean up
        del cast_region
        gc.collect()
        
        return result

def test_cast_bar_detection():
    """Test cast bar detection and OCR on sample frames."""
    detector = CastBarDetector()
    samples_dir = Path("ui_samples")
    
    if not samples_dir.exists():
        print("ERROR: ui_samples directory not found. Run sample_monthly_frames.py first.")
        return
    
    print("Testing cast bar detection and spell OCR...")
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
        
        # Analyze cast bar
        result = detector.analyze_cast_bar(frame)
        
        # Print results
        casting = result.get("casting", False)
        cast_progress = result.get("cast_progress_percentage", 0)
        
        print(f"Cast Bar Region: {result['region_size']}")
        
        if casting:
            print(f"CASTING: Progress {cast_progress:.1f}%")
            
            if result.get("spell_detected", False):
                spell_name = result.get("spell_name", "Unknown")
                confidence = result.get("confidence", 0)
                validated = result.get("validated", False)
                raw_text = result.get("raw_text", "")
                
                print(f"Spell: '{spell_name}' (Confidence: {confidence:.2f})")
                if not validated and raw_text != spell_name:
                    print(f"Raw OCR: '{raw_text}'")
                if validated:
                    print("[VALIDATED SPELL]")
            else:
                error = result.get("error")
                if error:
                    print(f"OCR Error: {error}")
                else:
                    print("No spell text detected")
        else:
            print("No casting activity detected")
        
        # Clean up
        del frame
        gc.collect()
    
    print(f"\n{'='*60}")
    print("Cast bar detection testing complete!")

if __name__ == "__main__":
    test_cast_bar_detection()