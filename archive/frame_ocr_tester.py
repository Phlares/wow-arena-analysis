#!/usr/bin/env python3
"""
Frame OCR Tester for WoW Arena Analysis
Tests OCR parsing on actual game frames using scaled zone mapping
"""

import json
import cv2
import numpy as np
import pytesseract
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class FrameOCRTester:
    """Test OCR on actual WoW Arena frames using zone mapping"""
    
    def __init__(self, zone_data_file: str = 'scaled_zone_mapping.json'):
        self.zone_data = self._load_zone_data(zone_data_file)
        self.frame_width = 3440
        self.frame_height = 1440
        
        # OCR configuration
        self.tesseract_config = {
            'health_numbers': '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789%/',
            'time': '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:',
            'spell_names': '--oem 3 --psm 8',
            'player_names': '--oem 3 --psm 8',
            'general_text': '--oem 3 --psm 8'
        }
        
    def _load_zone_data(self, file_path: str) -> Dict:
        """Load scaled zone data"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Zone data file {file_path} not found")
            return {}
    
    def extract_frame_from_video(self, video_path: str, timestamp_seconds: float = 30.0) -> Optional[np.ndarray]:
        """Extract a frame from video at specified timestamp"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                print(f"ERROR: Could not open video {video_path}")
                return None
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps
            
            print(f"VIDEO INFO: {fps:.1f} FPS, {duration:.1f}s duration, {frame_count} frames")
            
            # Calculate frame number
            target_frame = int(timestamp_seconds * fps)
            if target_frame >= frame_count:
                target_frame = frame_count // 2  # Use middle frame if timestamp too late
            
            # Seek to target frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Read frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print(f"ERROR: Could not read frame at {timestamp_seconds}s")
                return None
            
            print(f"EXTRACTED: Frame at {timestamp_seconds}s (frame #{target_frame})")
            print(f"Frame dimensions: {frame.shape[1]}x{frame.shape[0]}")
            
            return frame
            
        except Exception as e:
            print(f"ERROR: Extracting frame: {e}")
            return None
    
    def create_sample_frame(self) -> np.ndarray:
        """Create a sample frame for testing if no video available"""
        frame = np.full((self.frame_height, self.frame_width, 3), (20, 25, 30), dtype=np.uint8)
        
        # Add sample UI elements in expected locations
        sample_elements = [
            # Player health (red text on dark background)
            {'pos': (450, 380), 'text': '85%', 'color': (50, 50, 200), 'bg_color': (20, 20, 20)},
            {'pos': (450, 445), 'text': '12840', 'color': (50, 50, 200), 'bg_color': (20, 20, 20)},
            
            # Target health
            {'pos': (920, 670), 'text': '72%', 'color': (50, 50, 200), 'bg_color': (20, 20, 20)},
            
            # Arena enemy health
            {'pos': (2750, 450), 'text': '91%', 'color': (50, 50, 200), 'bg_color': (20, 20, 20)},
            {'pos': (2750, 630), 'text': '68%', 'color': (50, 50, 200), 'bg_color': (20, 20, 20)},
            
            # Current time
            {'pos': (3300, 25), 'text': '2:34', 'color': (200, 200, 200), 'bg_color': (10, 10, 10)},
            
            # Player names
            {'pos': (450, 340), 'text': 'PlayerName', 'color': (126, 217, 87), 'bg_color': (20, 20, 20)},
            {'pos': (920, 630), 'text': 'TargetName', 'color': (126, 217, 87), 'bg_color': (20, 20, 20)},
            
            # Cast bars
            {'pos': (450, 520), 'text': 'Shadow Bolt', 'color': (200, 200, 200), 'bg_color': (60, 80, 140)},
            {'pos': (2600, 500), 'text': 'Heal', 'color': (200, 200, 200), 'bg_color': (60, 80, 140)},
        ]
        
        for element in sample_elements:
            # Draw background rectangle
            text_size = cv2.getTextSize(element['text'], cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            bg_x = element['pos'][0] - 5
            bg_y = element['pos'][1] - text_size[1] - 5
            bg_w = text_size[0] + 10
            bg_h = text_size[1] + 10
            
            cv2.rectangle(frame, (bg_x, bg_y), (bg_x + bg_w, bg_y + bg_h), element['bg_color'], -1)
            
            # Draw text
            cv2.putText(frame, element['text'], element['pos'], 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, element['color'], 2)
        
        print("CREATED: Sample frame with mock UI elements")
        return frame
    
    def process_zone_ocr(self, frame: np.ndarray, zone: Dict) -> Dict:
        """Process OCR for a specific zone"""
        bbox = zone['bbox']
        annotation = zone.get('annotation', 'Unknown')
        color = zone['color']
        
        # Extract region of interest
        x = max(0, int(bbox['x']))
        y = max(0, int(bbox['y']))
        w = max(1, min(int(bbox['width']), frame.shape[1] - x))
        h = max(1, min(int(bbox['height']), frame.shape[0] - y))
        
        if w <= 0 or h <= 0:
            return {'error': 'Invalid bbox dimensions'}
        
        roi = frame[y:y+h, x:x+w]
        
        if roi.size == 0:
            return {'error': 'Empty ROI'}
        
        # Determine OCR configuration based on zone type
        ocr_config = self._get_ocr_config_for_zone(annotation)
        
        # Preprocess ROI for better OCR
        processed_roi = self._preprocess_roi(roi, annotation)
        
        try:
            # Perform OCR
            ocr_text = pytesseract.image_to_string(processed_roi, config=ocr_config).strip()
            
            # Get confidence data
            ocr_data = pytesseract.image_to_data(processed_roi, config=ocr_config, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            result = {
                'zone_id': zone['zone_id'],
                'annotation': annotation,
                'color': color,
                'bbox': bbox,
                'ocr_text': ocr_text,
                'confidence': round(avg_confidence, 1),
                'character_count': len(ocr_text),
                'config_used': ocr_config,
                'roi_size': f"{w}x{h}",
                'success': len(ocr_text) > 0 and avg_confidence > 30
            }
            
            return result
            
        except Exception as e:
            return {
                'zone_id': zone['zone_id'],
                'annotation': annotation,
                'error': str(e),
                'success': False
            }
    
    def _get_ocr_config_for_zone(self, annotation: str) -> str:
        """Get appropriate OCR configuration for zone type"""
        annotation_lower = annotation.lower()
        
        if 'health' in annotation_lower or 'resource' in annotation_lower:
            return self.tesseract_config['health_numbers']
        elif 'time' in annotation_lower:
            return self.tesseract_config['time']
        elif 'cast bar' in annotation_lower:
            return self.tesseract_config['spell_names']
        elif 'name' in annotation_lower:
            return self.tesseract_config['player_names']
        else:
            return self.tesseract_config['general_text']
    
    def _preprocess_roi(self, roi: np.ndarray, annotation: str) -> np.ndarray:
        """Preprocess ROI for better OCR results"""
        
        # Convert to grayscale
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        # Resize if too small
        if gray.shape[0] < 20 or gray.shape[1] < 50:
            scale_factor = max(2.0, 50.0 / max(gray.shape[0], gray.shape[1]))
            new_width = int(gray.shape[1] * scale_factor)
            new_height = int(gray.shape[0] * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply different preprocessing based on zone type
        annotation_lower = annotation.lower()
        
        if 'health' in annotation_lower or 'resource' in annotation_lower:
            # For health/resource numbers, use thresholding
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return thresh
        elif 'cast bar' in annotation_lower:
            # For cast bars, enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            return enhanced
        else:
            # General text processing
            return gray
    
    def test_frame_ocr(self, frame: np.ndarray) -> Dict:
        """Test OCR on all priority zones in frame"""
        
        if 'zones' not in self.zone_data:
            return {'error': 'No zone data available'}
        
        results = {
            'frame_info': {
                'dimensions': f"{frame.shape[1]}x{frame.shape[0]}",
                'total_zones': len(self.zone_data['zones'])
            },
            'ocr_results': [],
            'priority_results': {},
            'summary': {
                'zones_processed': 0,
                'successful_ocr': 0,
                'failed_ocr': 0,
                'avg_confidence': 0
            }
        }
        
        # Priority zones to focus on
        priority_zones = [
            'player health', 'target health', 'arena enemy', 'current time', 
            'cast bar', 'player name', 'target name'
        ]
        
        all_confidences = []
        
        for zone in self.zone_data['zones']:
            annotation = zone.get('annotation', '').lower()
            
            # Process all zones but focus on priority ones
            ocr_result = self.process_zone_ocr(frame, zone)
            results['ocr_results'].append(ocr_result)
            results['summary']['zones_processed'] += 1
            
            if ocr_result.get('success', False):
                results['summary']['successful_ocr'] += 1
                if 'confidence' in ocr_result:
                    all_confidences.append(ocr_result['confidence'])
            else:
                results['summary']['failed_ocr'] += 1
            
            # Check if this is a priority zone
            for priority in priority_zones:
                if priority in annotation:
                    results['priority_results'][f"{priority}_{zone['zone_id']}"] = ocr_result
                    break
        
        # Calculate average confidence
        if all_confidences:
            results['summary']['avg_confidence'] = round(sum(all_confidences) / len(all_confidences), 1)
        
        return results
    
    def create_ocr_visualization(self, frame: np.ndarray, ocr_results: Dict, output_path: str = 'ocr_visualization.png'):
        """Create visualization showing OCR results on frame"""
        
        viz_frame = frame.copy()
        
        for result in ocr_results.get('ocr_results', []):
            if not result.get('success', False):
                continue
                
            bbox = result.get('bbox', {})
            ocr_text = result.get('ocr_text', '')
            confidence = result.get('confidence', 0)
            
            if not bbox or not ocr_text:
                continue
            
            x = int(bbox['x'])
            y = int(bbox['y'])
            w = int(bbox['width'])
            h = int(bbox['height'])
            
            # Color based on confidence
            if confidence > 80:
                color = (0, 255, 0)  # Green - high confidence
            elif confidence > 60:
                color = (0, 255, 255)  # Yellow - medium confidence
            else:
                color = (0, 165, 255)  # Orange - low confidence
            
            # Draw bounding box
            cv2.rectangle(viz_frame, (x, y), (x + w, y + h), color, 2)
            
            # Add OCR text and confidence
            label = f"{ocr_text} ({confidence:.0f}%)"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            # Text background
            cv2.rectangle(viz_frame, (x, y - label_size[1] - 5), 
                         (x + label_size[0] + 5, y), (0, 0, 0), -1)
            
            # Text
            cv2.putText(viz_frame, label, (x + 2, y - 3), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Save visualization
        cv2.imwrite(output_path, viz_frame)
        print(f"OCR VISUALIZATION: Saved to {output_path}")
    
    def generate_ocr_report(self, ocr_results: Dict) -> str:
        """Generate comprehensive OCR test report"""
        
        report = []
        report.append("=" * 80)
        report.append("WoW Arena Frame OCR Test Report")
        report.append("=" * 80)
        
        # Summary
        summary = ocr_results['summary']
        report.append(f"\nSUMMARY:")
        report.append(f"  Frame: {ocr_results['frame_info']['dimensions']}")
        report.append(f"  Zones Processed: {summary['zones_processed']}")
        report.append(f"  Successful OCR: {summary['successful_ocr']}")
        report.append(f"  Failed OCR: {summary['failed_ocr']}")
        report.append(f"  Success Rate: {(summary['successful_ocr']/summary['zones_processed']*100):.1f}%")
        report.append(f"  Average Confidence: {summary['avg_confidence']:.1f}%")
        
        # Priority results
        if ocr_results['priority_results']:
            report.append(f"\nPRIORITY ZONE RESULTS:")
            for zone_key, result in ocr_results['priority_results'].items():
                success = "PASS" if result.get('success', False) else "FAIL"
                text = result.get('ocr_text', 'FAILED')
                confidence = result.get('confidence', 0)
                report.append(f"  {success} {zone_key}: '{text}' ({confidence:.0f}%)")
        
        # Top successful results
        successful_results = [r for r in ocr_results['ocr_results'] if r.get('success', False)]
        successful_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        report.append(f"\nTOP SUCCESSFUL OCR RESULTS:")
        for result in successful_results[:10]:
            annotation = result.get('annotation', 'Unknown')
            text = result.get('ocr_text', '')
            confidence = result.get('confidence', 0)
            report.append(f"  {annotation}: '{text}' ({confidence:.0f}%)")
        
        # Failed results
        failed_results = [r for r in ocr_results['ocr_results'] if not r.get('success', False)]
        if failed_results:
            report.append(f"\nFAILED OCR ZONES ({len(failed_results)} total):")
            for result in failed_results[:5]:  # Show first 5 failures
                annotation = result.get('annotation', 'Unknown')
                error = result.get('error', 'Low confidence or no text')
                report.append(f"  {annotation}: {error}")
        
        report.append("=" * 80)
        return "\n".join(report)

def main():
    """Main OCR testing function"""
    print("FRAME OCR TESTER: Starting OCR tests...")
    
    tester = FrameOCRTester()
    
    # Check if we have video files to test with
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    current_dir = Path('.')
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(list(current_dir.glob(f'*{ext}')))
    
    frame = None
    
    if video_files:
        # Use first available video
        video_path = str(video_files[0])
        print(f"FOUND VIDEO: {video_path}")
        frame = tester.extract_frame_from_video(video_path, 60.0)  # Extract at 1 minute
    
    if frame is None:
        print("NO VIDEO AVAILABLE: Creating sample frame for testing")
        frame = tester.create_sample_frame()
        cv2.imwrite('sample_test_frame.png', frame)
        print("SAVED: sample_test_frame.png")
    
    # Test OCR on frame
    print("TESTING: OCR on frame zones...")
    ocr_results = tester.test_frame_ocr(frame)
    
    # Create visualization
    tester.create_ocr_visualization(frame, ocr_results)
    
    # Generate and display report
    report = tester.generate_ocr_report(ocr_results)
    print(report)
    
    # Save report
    with open('ocr_test_report.txt', 'w') as f:
        f.write(report)
    
    print(f"\nOCR TESTING: Complete")
    print(f"  - Check 'ocr_visualization.png' for visual results")
    print(f"  - Review 'ocr_test_report.txt' for detailed analysis")

if __name__ == "__main__":
    main()