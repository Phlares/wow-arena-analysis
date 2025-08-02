#!/usr/bin/env python3
"""
WoW Arena OCR Testing Script
Tests Tesseract OCR on actual WoW UI elements and text
"""

import cv2
import os
import pytesseract
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import glob

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_basic_ocr():
    """Test basic OCR functionality"""
    print("=== Basic OCR Test ===")
    
    try:
        # Test Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"[OK] Tesseract version: {version}")
        
        # Create test image with text
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Frostbolt", fill='black', )
        draw.text((10, 40), "Shadow Word: Pain", fill='black')
        draw.text((10, 70), "Interrupted!", fill='red')
        
        # Test OCR
        text = pytesseract.image_to_string(img, config='--psm 6').strip()
        print(f"[OK] Basic OCR working - Detected: '{text}'")
        
        # Save test image
        img.save('test_frames/ocr_basic_test.png')
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Basic OCR test failed: {e}")
        return False

def preprocess_for_ocr(image, region_type="text"):
    """
    Preprocess image region for better OCR accuracy
    
    Args:
        image: Input image region
        region_type: Type of content ("text", "cast_bar", "damage")
    """
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    if region_type == "cast_bar":
        # Enhance cast bar text (usually yellow/white on dark background)
        # Increase contrast
        gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=50)
        
        # Apply threshold to get white text on black background
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
    elif region_type == "damage":
        # Enhance damage numbers (usually white/yellow text)
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=30)
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
    else:  # general text
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
    
    # Noise removal
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return binary

def test_wow_frame_ocr():
    """Test OCR on actual WoW frames"""
    print("\n=== WoW Frame OCR Test ===")
    
    # Find test frames
    frame_files = glob.glob("test_frames/frame_*.jpg")
    if not frame_files:
        print("[ERROR] No test frames found. Run test_frame_extraction.py first.")
        return False
    
    # Test first frame
    frame_path = sorted(frame_files)[0]
    print(f"Testing OCR on: {frame_path}")
    
    frame = cv2.imread(frame_path)
    if frame is None:
        print(f"[ERROR] Could not load frame")
        return False
    
    height, width = frame.shape[:2]
    
    # Define OCR test regions (based on common WoW UI locations)
    ocr_regions = {
        "cast_bar_text": {
            "region": (int(width*0.35), int(height*0.8), int(width*0.65), int(height*0.85)),
            "type": "cast_bar",
            "config": "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:' "
        },
        "player_name": {
            "region": (int(width*0.05), int(height*0.08), int(width*0.25), int(height*0.12)),
            "type": "text", 
            "config": "--psm 7"
        },
        "target_name": {
            "region": (int(width*0.4), int(height*0.08), int(width*0.6), int(height*0.12)),
            "type": "text",
            "config": "--psm 7"
        },
        "combat_text": {
            "region": (int(width*0.4), int(height*0.4), int(width*0.6), int(height*0.6)),
            "type": "damage",
            "config": "--psm 6"
        }
    }
    
    results = {}
    
    for region_name, region_info in ocr_regions.items():
        x1, y1, x2, y2 = region_info["region"]
        region_type = region_info["type"]
        ocr_config = region_info["config"]
        
        # Extract region
        region = frame[y1:y2, x1:x2]
        
        if region.size == 0:
            continue
        
        # Preprocess for OCR
        processed = preprocess_for_ocr(region, region_type)
        
        # Run OCR
        try:
            text = pytesseract.image_to_string(processed, config=ocr_config).strip()
            results[region_name] = text
            
            print(f"  {region_name}: '{text}'")
            
            # Save processed region for inspection
            region_path = f"test_frames/ocr_{region_name}_processed.jpg"
            cv2.imwrite(region_path, processed)
            
        except Exception as e:
            print(f"  {region_name}: OCR failed - {e}")
            results[region_name] = None
    
    # Create visual OCR result
    create_ocr_visualization(frame, ocr_regions, results)
    
    return True

def create_ocr_visualization(frame, regions, results):
    """Create visualization showing OCR regions and results"""
    
    vis_frame = frame.copy()
    
    for region_name, region_info in regions.items():
        x1, y1, x2, y2 = region_info["region"]
        text_result = results.get(region_name, "")
        
        # Draw bounding box
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        
        # Add label and result
        label = f"{region_name}: {text_result[:20]}..." if len(text_result) > 20 else f"{region_name}: {text_result}"
        cv2.putText(vis_frame, label, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Save visualization
    cv2.imwrite("test_frames/ocr_visualization.jpg", vis_frame)
    print(f"[OK] Saved OCR visualization: test_frames/ocr_visualization.jpg")

def test_spell_name_detection():
    """Test OCR specifically for WoW spell names"""
    print("\n=== Spell Name Detection Test ===")
    
    # Common WoW spell names to test
    spell_names = [
        "Frostbolt", "Fireball", "Polymorph", "Counterspell",
        "Shadow Word: Pain", "Mind Control", "Psychic Scream",
        "Kidney Shot", "Cheap Shot", "Sap", "Blind",
        "Chaos Bolt", "Fear", "Shadowfury", "Coil",
        "Aimed Shot", "Concussive Shot", "Freezing Trap"
    ]
    
    # Create test image with spell names
    img = Image.new('RGB', (400, 600), color=(20, 20, 30))  # Dark WoW-like background
    draw = ImageDraw.Draw(img)
    
    y_pos = 20
    for spell in spell_names:
        # Draw spell name in yellow (typical cast bar color)
        draw.text((20, y_pos), spell, fill=(255, 255, 0))
        y_pos += 30
    
    # Save test image
    img.save('test_frames/spell_names_test.png')
    
    # Convert to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Preprocess for OCR
    processed = preprocess_for_ocr(img_cv, "cast_bar")
    
    # Run OCR
    detected_text = pytesseract.image_to_string(processed, 
                                              config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:\' ')
    
    detected_lines = [line.strip() for line in detected_text.split('\n') if line.strip()]
    
    print(f"Created test with {len(spell_names)} spell names")
    print(f"OCR detected {len(detected_lines)} text lines:")
    
    # Compare results
    correct_matches = 0
    for spell in spell_names:
        found = any(spell.lower() in detected.lower() for detected in detected_lines)
        if found:
            correct_matches += 1
            print(f"  [OK] {spell}")
        else:
            print(f"  [MISS] {spell}")
    
    accuracy = (correct_matches / len(spell_names)) * 100
    print(f"\nSpell detection accuracy: {correct_matches}/{len(spell_names)} ({accuracy:.1f}%)")
    
    # Save processed image
    cv2.imwrite('test_frames/spell_names_processed.jpg', processed)
    
    return accuracy > 70  # Consider 70%+ accuracy as good

def main():
    """Run comprehensive WoW OCR tests"""
    print("WoW Arena OCR Testing Suite")
    print("=" * 40)
    
    # Ensure test_frames directory exists
    os.makedirs("test_frames", exist_ok=True)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Basic OCR
    if test_basic_ocr():
        success_count += 1
    
    # Test 2: WoW frame OCR
    if test_wow_frame_ocr():
        success_count += 1
    
    # Test 3: Spell name detection
    if test_spell_name_detection():
        success_count += 1
    
    print(f"\n=== OCR Test Summary ===")
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("[SUCCESS] OCR setup is working excellently!")
        print("\nGenerated files:")
        print("- test_frames/ocr_*.jpg - OCR test images and processed regions")
        print("- test_frames/ocr_visualization.jpg - Visual OCR region analysis")
        print("\nOCR is ready for WoW Arena analysis!")
    elif success_count >= 2:
        print("[OK] OCR setup is functional with minor issues")
    else:
        print("[WARN] OCR setup needs attention")
    
    return success_count >= 2

if __name__ == "__main__":
    main()