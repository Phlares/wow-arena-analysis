#!/usr/bin/env python3
# test_timestamp_matching.py

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the current directory to path so we can import our matcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from improved_timestamp_matcher import TimestampMatcher
except ImportError:
    print("Error: Cannot import TimestampMatcher. Make sure improved_timestamp_matcher.py is in the same directory.")
    sys.exit(1)

def test_single_match(base_dir: str, video_filename: str, expected_method: str = None):
    """Test timestamp matching for a single video file."""
    print(f"\n{'='*60}")
    print(f"Testing: {video_filename}")
    print(f"{'='*60}")
    
    matcher = TimestampMatcher(base_dir)
    
    try:
        # Test without combat log first (should use JSON start field for new format)
        start_time, metadata = matcher.get_precise_match_time(video_filename)
        
        print(f"✅ Match found!")
        print(f"   Start time: {start_time}")
        print(f"   Method: {metadata['method']}")
        print(f"   Reliability: {metadata['reliability']}")
        print(f"   Source: {metadata['source']}")
        
        if 'warning' in metadata:
            print(f"   ⚠️ Warning: {metadata['warning']}")
        
        # Validate against expected method if provided
        if expected_method and metadata['method'] != expected_method:
            print(f"   ❌ Expected method '{expected_method}' but got '{metadata['method']}'")
        else:
            print(f"   ✅ Method validation passed")
            
        return True, start_time, metadata
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None, None

def test_batch_matching(base_dir: str, sample_files: list):
    """Test timestamp matching for multiple files to validate the approach."""
    print(f"\n{'='*80}")
    print(f"BATCH TESTING: {len(sample_files)} files")
    print(f"{'='*80}")
    
    results = {
        'success': 0,
        'failed': 0,
        'methods': {},
        'reliability': {}
    }
    
    for video_filename in sample_files:
        success, start_time, metadata = test_single_match(base_dir, video_filename)
        
        if success:
            results['success'] += 1
            method = metadata['method']
            reliability = metadata['reliability']
            
            results['methods'][method] = results['methods'].get(method, 0) + 1
            results['reliability'][reliability] = results['reliability'].get(reliability, 0) + 1
        else:
            results['failed'] += 1
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"BATCH TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total files tested: {len(sample_files)}")
    print(f"Successful matches: {results['success']}")
    print(f"Failed matches: {results['failed']}")
    print(f"Success rate: {results['success']/len(sample_files)*100:.1f}%")
    
    print(f"\nMethods used:")
    for method, count in results['methods'].items():
        print(f"  {method}: {count} files")
    
    print(f"\nReliability distribution:")
    for reliability, count in results['reliability'].items():
        print(f"  {reliability}: {count} files")
    
    return results

def validate_json_formats(base_dir: str):
    """Check how many files use new vs old JSON format."""
    print(f"\n{'='*80}")
    print(f"JSON FORMAT ANALYSIS")
    print(f"{'='*80}")
    
    base_path = Path(base_dir)
    json_files = list(base_path.rglob('*.json'))
    
    new_format = 0
    old_format = 0
    errors = 0
    
    print(f"Found {len(json_files)} JSON files")
    
    # Sample a subset for analysis (to avoid processing thousands)
    sample_size = min(100, len(json_files))
    sample_files = json_files[:sample_size]
    
    print(f"Analyzing sample of {sample_size} files...")
    
    for json_file in sample_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'start' in data:
                new_format += 1
            else:
                old_format += 1
                
        except Exception as e:
            errors += 1
            print(f"Error reading {json_file}: {e}")
    
    print(f"\nFormat distribution (sample of {sample_size}):")
    print(f"  New format (has 'start' field): {new_format} files ({new_format/sample_size*100:.1f}%)")
    print(f"  Old format (no 'start' field): {old_format} files ({old_format/sample_size*100:.1f}%)")
    print(f"  Errors: {errors} files")
    
    # Estimate for full dataset
    if sample_size < len(json_files):
        est_new = int(new_format / sample_size * len(json_files))
        est_old = int(old_format / sample_size * len(json_files))
        print(f"\nEstimated for full dataset ({len(json_files)} files):")
        print(f"  New format: ~{est_new} files")
        print(f"  Old format: ~{est_old} files")
    
    return new_format, old_format, errors

def main():
    """Main test function."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    
    print("🚀 Starting Timestamp Matching Tests")
    print(f"Base directory: {base_dir}")
    
    # Test 1: Validate JSON formats
    validate_json_formats(base_dir)
    
    # Test 2: Test specific files (known examples)
    sample_files = [
        # New format examples (should have 'start' field)
        "2025-01-01_00-03-07_-_Iamlockedout_-_3v3_Empyrean_Domain_(Win).mp4",
        "2025-01-01_20-06-29_-_Phlurbotomy_-_3v3_Tol'viron_(Loss).mp4",
        
        # If you have older files, add them here
        # "2023-05-09_22-46-08_-_Iamlockedout_-_Skirmish_Nokhudon_(Loss).mp4",
    ]
    
    # Filter to only test files that exist
    existing_files = []
    for filename in sample_files:
        # Check if corresponding JSON exists
        json_name = filename.rsplit('.', 1)[0] + '.json'
        matcher = TimestampMatcher(base_dir)
        if matcher._find_json_file(filename):
            existing_files.append(filename)
        else:
            print(f"⚠️ Skipping {filename} - JSON file not found")
    
    if existing_files:
        # Test 3: Batch testing
        test_batch_matching(base_dir, existing_files)
    else:
        print("⚠️ No test files found. Please update the sample_files list with actual filenames.")
    
    print(f"\n{'='*80}")
    print("🎉 Testing complete!")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
