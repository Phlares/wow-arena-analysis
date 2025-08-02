#!/usr/bin/env python3
"""
WoW Arena OCR Analyzer - Unified Interface
Consolidates all OCR testing and analysis functionality
"""

import sys
import argparse
import os
from pathlib import Path

def import_ocr_functions():
    """Import OCR functions from existing modules"""
    try:
        from debug_ocr_tester import DebugOCRTester
        from frame_ocr_tester import FrameOCRTester
        from test_wow_ocr import main as test_ocr_main
        
        return {
            'DebugOCRTester': DebugOCRTester,
            'FrameOCRTester': FrameOCRTester,
            'test_ocr_main': test_ocr_main
        }
    except ImportError as e:
        print(f"ERROR: Missing required OCR modules: {e}")
        return None

def configure_tesseract():
    """Configure Tesseract path"""
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✓ Tesseract configured: {tesseract_path}")
            return True
        except ImportError:
            print("ERROR: pytesseract not installed")
            return False
    else:
        print(f"ERROR: Tesseract not found at {tesseract_path}")
        return False

def debug_analysis(video_path: str, timestamp: float = 90.0):
    """Run comprehensive debug OCR analysis"""
    
    funcs = import_ocr_functions()
    if not funcs:
        return False
    
    if not configure_tesseract():
        return False
    
    print(f"Debug OCR Analysis: {video_path}")
    print(f"Timestamp: {timestamp}s")
    print("=" * 60)
    
    try:
        tester = funcs['DebugOCRTester']()
        
        # Extract frame
        frame = tester.extract_frame_from_video(video_path, timestamp)
        if frame is None:
            print("ERROR: Could not extract frame from video")
            return False
        
        # Run comprehensive analysis
        debug_results = tester.debug_full_frame_analysis(frame)
        
        # Generate report
        report = tester.generate_debug_report(debug_results, video_path)
        
        # Save results
        report_path = os.path.join(tester.debug_output_dir, 'ocr_debug_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Print summary
        summary = debug_results['summary']
        print(f"\nDEBUG ANALYSIS COMPLETE:")
        print(f"  Success Rate: {(summary['zones_with_text']/summary['zones_processed']*100):.1f}%")
        print(f"  High Confidence Rate: {(summary['zones_high_confidence']/summary['zones_processed']*100):.1f}%")
        print(f"  Average Confidence: {summary['avg_confidence']:.1f}%")
        print(f"  Debug report: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Debug analysis failed: {e}")
        return False

def quick_test(video_path: str = None, use_sample: bool = False):
    """Run quick OCR test"""
    
    funcs = import_ocr_functions()
    if not funcs:
        return False
    
    if not configure_tesseract():
        return False
    
    print("Quick OCR Test")
    print("=" * 30)
    
    try:
        tester = funcs['FrameOCRTester']()
        
        if video_path and Path(video_path).exists():
            print(f"Testing with video: {video_path}")
            frame = tester.extract_frame_from_video(video_path, 60.0)
        elif use_sample:
            print("Creating sample frame for testing...")
            frame = tester.create_sample_frame()
        else:
            print("ERROR: No valid video path provided and sample not requested")
            return False
        
        if frame is None:
            print("ERROR: Could not get test frame")
            return False
        
        # Test OCR
        ocr_results = tester.test_frame_ocr(frame)
        
        # Create visualization
        tester.create_ocr_visualization(frame, ocr_results, 'quick_ocr_test.png')
        
        # Generate report
        report = tester.generate_ocr_report(ocr_results)
        print(report)
        
        # Save report
        with open('quick_ocr_report.txt', 'w') as f:
            f.write(report)
        
        print(f"\nQuick test complete - check 'quick_ocr_test.png' and 'quick_ocr_report.txt'")
        return True
        
    except Exception as e:
        print(f"ERROR: Quick test failed: {e}")
        return False

def validate_setup():
    """Validate OCR setup and dependencies"""
    try:
        from validate_cv_setup import main as validate_main
        print("Validating computer vision setup...")
        validate_main()
        return True
    except ImportError:
        print("ERROR: CV validation module not found")
        return False

def test_basic_ocr():
    """Test basic OCR functionality"""
    funcs = import_ocr_functions()
    if not funcs:
        return False
    
    try:
        print("Testing basic OCR functionality...")
        funcs['test_ocr_main']()
        return True
    except Exception as e:
        print(f"ERROR: Basic OCR test failed: {e}")
        return False

def main():
    """Main unified OCR analyzer interface"""
    parser = argparse.ArgumentParser(
        description="WoW Arena OCR Analyzer - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --debug --video match.mp4 --time 90        # Debug analysis at 90s
  %(prog)s --quick --video match.mp4                  # Quick OCR test
  %(prog)s --quick --sample                           # Quick test with sample
  %(prog)s --validate                                 # Validate OCR setup
  %(prog)s --test-basic                               # Test basic OCR
        """
    )
    
    parser.add_argument('--debug', action='store_true',
                       help='Run comprehensive debug analysis')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick OCR test')
    parser.add_argument('--validate', action='store_true',
                       help='Validate OCR setup and dependencies')
    parser.add_argument('--test-basic', action='store_true',
                       help='Test basic OCR functionality')
    
    parser.add_argument('--video', 
                       help='Video file to extract frame from')
    parser.add_argument('--time', type=float, default=90.0,
                       help='Timestamp (seconds) to extract frame at')
    parser.add_argument('--sample', action='store_true',
                       help='Use sample frame instead of video')
    
    args = parser.parse_args()
    
    # Check that at least one action is specified
    if not any([args.debug, args.quick, args.validate, args.test_basic]):
        print("ERROR: Must specify at least one action (--debug, --quick, --validate, or --test-basic)")
        parser.print_help()
        return 1
    
    print("WoW Arena OCR Analyzer")
    print("=" * 40)
    
    success = True
    
    try:
        if args.validate:
            success &= validate_setup()
        
        if args.test_basic:
            success &= test_basic_ocr()
        
        if args.debug:
            if not args.video:
                print("ERROR: Debug mode requires --video parameter")
                return 1
            if not Path(args.video).exists():
                print(f"ERROR: Video file not found: {args.video}")
                return 1
            success &= debug_analysis(args.video, args.time)
        
        if args.quick:
            success &= quick_test(args.video, args.sample)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    if success:
        print("\nOCR analysis operations completed successfully")
        return 0
    else:
        print("\nSome operations failed - check output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())