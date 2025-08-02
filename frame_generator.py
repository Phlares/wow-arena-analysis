#!/usr/bin/env python3
"""
WoW Arena Frame Generator - Unified Interface
Consolidates all test frame generation functionality
"""

import sys
import argparse
import cv2
import numpy as np
from pathlib import Path

def import_generator_functions():
    """Import frame generation functions"""
    try:
        from scaled_test_frame_generator import ScaledTestFrameGenerator
        from enhanced_test_frame_generator import EnhancedTestFrameGenerator
        from test_frame_extraction import main as extraction_main
        
        return {
            'ScaledTestFrameGenerator': ScaledTestFrameGenerator,
            'EnhancedTestFrameGenerator': EnhancedTestFrameGenerator,
            'extraction_main': extraction_main
        }
    except ImportError as e:
        print(f"ERROR: Missing required generator modules: {e}")
        return None

def generate_test_frames(frame_type: str = 'scaled', output_dir: str = '.'):
    """Generate test frames with zone overlays"""
    
    funcs = import_generator_functions()
    if not funcs:
        return False
    
    print(f"Generating {frame_type} test frames...")
    print(f"Output directory: {output_dir}")
    
    try:
        if frame_type == 'scaled':
            generator = funcs['ScaledTestFrameGenerator']()
            
            # Create scaled test frame
            print("Creating scaled resolution test frame...")
            scaled_frame = generator.create_scaled_test_frame()
            cv2.imwrite(f'{output_dir}/test_frame_scaled.png', scaled_frame)
            print("✓ Saved: test_frame_scaled.png")
            
            return True
            
        elif frame_type == 'enhanced':
            generator = funcs['EnhancedTestFrameGenerator']()
            
            # Create full resolution test frame
            print("Creating enhanced resolution test frame...")
            full_frame = generator.create_full_resolution_test_frame()
            cv2.imwrite(f'{output_dir}/test_frame_enhanced.png', full_frame)
            print("✓ Saved: test_frame_enhanced.png")
            
            # Create priority overlay
            print("Creating priority overlay...")
            priority_frame = generator.create_zone_priority_overlay()
            cv2.imwrite(f'{output_dir}/test_frame_priority.png', priority_frame)
            print("✓ Saved: test_frame_priority.png")
            
            # Create comparison view
            print("Creating comparison view...")
            comparison_frame = generator.create_comparison_view()
            cv2.imwrite(f'{output_dir}/test_frame_comparison.png', comparison_frame)
            print("✓ Saved: test_frame_comparison.png")
            
            return True
            
        elif frame_type == 'all':
            # Generate both types
            success = True
            success &= generate_test_frames('scaled', output_dir)
            success &= generate_test_frames('enhanced', output_dir)
            return success
            
        else:
            print(f"ERROR: Unknown frame type: {frame_type}")
            return False
            
    except Exception as e:
        print(f"ERROR: Frame generation failed: {e}")
        return False

def extract_from_video(video_path: str, output_dir: str = 'extracted_frames', 
                      frame_count: int = 10, interval: float = 30.0):
    """Extract frames from actual video for analysis"""
    
    if not Path(video_path).exists():
        print(f"ERROR: Video file not found: {video_path}")
        return False
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"Extracting frames from: {video_path}")
    print(f"Output directory: {output_dir}")
    print(f"Frame count: {frame_count}, Interval: {interval}s")
    
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"ERROR: Could not open video")
            return False
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_total / fps if fps > 0 else 0
        
        print(f"Video info: {fps:.1f} FPS, {duration:.1f}s duration")
        
        extracted = 0
        for i in range(frame_count):
            timestamp = i * interval
            if timestamp >= duration:
                break
                
            # Seek to timestamp
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print(f"Warning: Could not read frame at {timestamp}s")
                continue
            
            # Save frame
            frame_filename = f"{output_dir}/frame_{i:03d}_{timestamp:.1f}s.png"
            cv2.imwrite(frame_filename, frame)
            print(f"✓ Extracted frame {i+1}: {frame_filename}")
            extracted += 1
        
        cap.release()
        
        print(f"Successfully extracted {extracted} frames")
        return True
        
    except Exception as e:
        print(f"ERROR: Frame extraction failed: {e}")
        return False

def create_sample_frame(output_path: str = 'sample_frame.png'):
    """Create sample frame with mock UI elements"""
    
    print("Creating sample frame with mock UI elements...")
    
    try:
        # Create sample frame (3440x1440)
        frame = np.full((1440, 3440, 3), (20, 25, 30), dtype=np.uint8)
        
        # Add sample UI elements
        sample_elements = [
            # Player health (left side)
            {'pos': (450, 400), 'text': '85%', 'color': (50, 50, 200), 'bg': (20, 20, 20)},
            {'pos': (450, 450), 'text': '12840/15000', 'color': (50, 50, 200), 'bg': (20, 20, 20)},
            
            # Target health (center)
            {'pos': (1700, 700), 'text': '72%', 'color': (50, 50, 200), 'bg': (20, 20, 20)},
            {'pos': (1700, 750), 'text': 'Enemy Player', 'color': (126, 217, 87), 'bg': (20, 20, 20)},
            
            # Arena enemy health (right side)
            {'pos': (2800, 450), 'text': '91%', 'color': (50, 50, 200), 'bg': (20, 20, 20)},
            {'pos': (2800, 650), 'text': '68%', 'color': (50, 50, 200), 'bg': (20, 20, 20)},
            
            # Current time (top right)
            {'pos': (3300, 30), 'text': '2:34', 'color': (200, 200, 200), 'bg': (10, 10, 10)},
            
            # Cast bars
            {'pos': (1600, 950), 'text': 'Shadow Bolt', 'color': (200, 200, 200), 'bg': (60, 80, 140)},
            {'pos': (2600, 500), 'text': 'Greater Heal', 'color': (200, 200, 200), 'bg': (60, 80, 140)},
        ]
        
        for element in sample_elements:
            # Draw background rectangle
            text_size = cv2.getTextSize(element['text'], cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            bg_x = element['pos'][0] - 10
            bg_y = element['pos'][1] - text_size[1] - 10
            bg_w = text_size[0] + 20
            bg_h = text_size[1] + 20
            
            cv2.rectangle(frame, (bg_x, bg_y), (bg_x + bg_w, bg_y + bg_h), element['bg'], -1)
            
            # Draw text
            cv2.putText(frame, element['text'], element['pos'], 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, element['color'], 2)
        
        # Save frame
        cv2.imwrite(output_path, frame)
        print(f"✓ Sample frame created: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Sample frame creation failed: {e}")
        return False

def main():
    """Main unified frame generator interface"""
    parser = argparse.ArgumentParser(
        description="WoW Arena Frame Generator - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test-frames --type scaled              # Generate scaled test frames
  %(prog)s --test-frames --type enhanced            # Generate enhanced test frames  
  %(prog)s --test-frames --type all                 # Generate all test frame types
  %(prog)s --extract --video match.mp4 --count 5   # Extract 5 frames from video
  %(prog)s --sample --output sample.png             # Create sample frame
        """
    )
    
    parser.add_argument('--test-frames', action='store_true',
                       help='Generate test frames with zone overlays')
    parser.add_argument('--extract', action='store_true',
                       help='Extract frames from video')
    parser.add_argument('--sample', action='store_true',
                       help='Create sample frame with mock UI')
    
    parser.add_argument('--type', choices=['scaled', 'enhanced', 'all'], default='scaled',
                       help='Type of test frames to generate')
    parser.add_argument('--video', 
                       help='Video file to extract frames from')
    parser.add_argument('--output', default='.',
                       help='Output directory or file path')
    parser.add_argument('--count', type=int, default=10,
                       help='Number of frames to extract from video')
    parser.add_argument('--interval', type=float, default=30.0,
                       help='Interval (seconds) between extracted frames')
    
    args = parser.parse_args()
    
    # Check that at least one action is specified
    if not any([args.test_frames, args.extract, args.sample]):
        print("ERROR: Must specify at least one action (--test-frames, --extract, or --sample)")
        parser.print_help()
        return 1
    
    print("WoW Arena Frame Generator")
    print("=" * 40)
    
    success = True
    
    try:
        if args.test_frames:
            success &= generate_test_frames(args.type, args.output)
        
        if args.extract:
            if not args.video:
                print("ERROR: Extract mode requires --video parameter")
                return 1
            success &= extract_from_video(args.video, args.output, args.count, args.interval)
        
        if args.sample:
            output_path = args.output if args.output != '.' else 'sample_frame.png'
            success &= create_sample_frame(output_path)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    if success:
        print("\nFrame generation operations completed successfully")
        return 0
    else:
        print("\nSome operations failed - check output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())