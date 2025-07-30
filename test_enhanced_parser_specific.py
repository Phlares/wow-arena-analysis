#!/usr/bin/env python3
# test_enhanced_parser_specific.py - Test on problematic back-to-back matches

import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure enhanced_combat_parser_production_ENHANCED.py is saved first")
    sys.exit(1)


def test_specific_problematic_matches():
    """Test the enhanced parser on the specific back-to-back matches that showed identical results."""

    print("🔬 Testing Enhanced Parser on Problematic Back-to-Back Matches")
    print("=" * 80)

    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"

    # The problematic matches you identified
    test_cases = [
        {
            'name': 'Back-to-back Ruins of Lordaeron matches',
            'matches': [
                "2025-01-01_20-31-43_-_Phlurbotomy_-_3v3_Ruins_of_Lordaeron_(Win).mp4",
                "2025-01-01_20-36-35_-_Phlurbotomy_-_3v3_Ruins_of_Lordaeron_(Loss).mp4"
            ]
        },
        {
            'name': 'Back-to-back Robodrome matches',
            'matches': [
                "2025-01-01_21-18-11_-_Phlurbotomy_-_3v3_Robodrome_(Win).mp4",
                "2025-01-01_21-23-29_-_Phlurbotomy_-_3v3_Robodrome_(Win).mp4"
            ]
        }
    ]

    parser = EnhancedProductionCombatParser(base_dir)

    # Load enhanced index to get match data
    enhanced_index = Path(base_dir) / "master_index_enhanced.csv"
    if not enhanced_index.exists():
        print("❌ Enhanced index not found")
        return

    df = pd.read_csv(enhanced_index)

    # Use robust timestamp parsing (same as enhanced parser)
    try:
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
    except ValueError:
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
        except ValueError:
            print("⚠️ Using manual timestamp cleaning...")

            def clean_timestamp(timestamp_str):
                if pd.isna(timestamp_str):
                    return timestamp_str
                ts = str(timestamp_str).strip()
                if '.' in ts and len(ts.split('.')[-1]) > 3:
                    parts = ts.split('.')
                    if len(parts) == 2:
                        base, microsec = parts
                        microsec = microsec[:6].ljust(6, '0')
                        ts = f"{base}.{microsec}"
                return ts

            df['precise_start_time'] = df['precise_start_time'].apply(clean_timestamp)
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

    # Get combat logs
    log_files = list(Path(base_dir).glob('Logs/*.txt'))

    for test_case in test_cases:
        print(f"\n🎯 Testing: {test_case['name']}")
        print("-" * 50)

        results = []

        for filename in test_case['matches']:
            # Find match data
            match_data = df[df['filename'] == filename]
            if len(match_data) == 0:
                print(f"❌ Match not found in index: {filename}")
                continue

            match = match_data.iloc[0]
            print(f"\n🎮 Processing: {filename}")
            print(f"   Video start time: {match['precise_start_time']}")
            print(f"   Expected duration: {match.get('duration_s', 'Unknown')}s")

            # Find combat log
            relevant_log = parser.find_combat_log_for_match(match, log_files)
            if not relevant_log:
                print("   ❌ No combat log found")
                continue

            print(f"   📄 Combat log: {relevant_log.name}")

            # Extract features with enhanced verification
            features = parser.extract_combat_features_enhanced(match, relevant_log, time_window=120)

            if features:
                print(f"   ✅ Features extracted:")
                key_metrics = {
                    'cast_success_own': features['cast_success_own'],
                    'interrupt_success_own': features['interrupt_success_own'],
                    'times_interrupted': features['times_interrupted'],
                    'purges_own': features['purges_own'],
                    'times_died': features['times_died']
                }

                for metric, value in key_metrics.items():
                    print(f"      {metric}: {value}")

                results.append({
                    'filename': filename,
                    'features': key_metrics
                })
            else:
                print("   ❌ Feature extraction failed")

        # Compare results for this test case
        print(f"\n📊 Comparison for {test_case['name']}:")
        if len(results) >= 2:
            match1, match2 = results[0], results[1]

            print(f"Match 1: {match1['filename']}")
            print(f"Match 2: {match2['filename']}")

            differences_found = False
            for metric in match1['features']:
                val1 = match1['features'][metric]
                val2 = match2['features'][metric]

                if val1 != val2:
                    differences_found = True
                    print(f"   {metric}: {val1} vs {val2} ✅ DIFFERENT")
                else:
                    print(f"   {metric}: {val1} vs {val2} ❌ IDENTICAL")

            if differences_found:
                print("   ✅ PASS: Enhanced parser found differences between back-to-back matches")
            else:
                print("   ❌ FAIL: Enhanced parser still shows identical results")
        else:
            print("   ⚠️ Could not compare - insufficient successful extractions")


def test_arena_boundary_detection_detail():
    """Test detailed arena boundary detection logic."""
    print(f"\n🔍 Detailed Arena Boundary Detection Test")
    print("-" * 50)

    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    parser = EnhancedProductionCombatParser(base_dir)

    # Load a specific test match
    enhanced_index = Path(base_dir) / "master_index_enhanced.csv"
    df = pd.read_csv(enhanced_index)

    # Use robust timestamp parsing (same as enhanced parser)
    try:
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
    except ValueError:
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
        except ValueError:
            print("⚠️ Using manual timestamp cleaning...")

            def clean_timestamp(timestamp_str):
                if pd.isna(timestamp_str):
                    return timestamp_str
                ts = str(timestamp_str).strip()
                if '.' in ts and len(ts.split('.')[-1]) > 3:
                    parts = ts.split('.')
                    if len(parts) == 2:
                        base, microsec = parts
                        microsec = microsec[:6].ljust(6, '0')
                        ts = f"{base}.{microsec}"
                return ts

            df['precise_start_time'] = df['precise_start_time'].apply(clean_timestamp)
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

    # Test on one of the problematic matches
    test_filename = "2025-01-01_20-31-43_-_Phlurbotomy_-_3v3_Ruins_of_Lordaeron_(Win).mp4"
    match_data = df[df['filename'] == test_filename]

    if len(match_data) == 0:
        print(f"❌ Test match not found: {test_filename}")
        return

    match = match_data.iloc[0]
    log_files = list(Path(base_dir).glob('Logs/*.txt'))
    relevant_log = parser.find_combat_log_for_match(match, log_files)

    if not relevant_log:
        print("❌ No combat log found for test")
        return

    print(f"🎮 Testing arena boundary detection for: {test_filename}")
    print(f"📄 Using combat log: {relevant_log.name}")

    # Test the enhanced boundary detection with debug output
    try:
        from datetime import timedelta
        match_start = match['precise_start_time']
        match_duration = match.get('duration_s', 300)
        window_start = match_start - timedelta(seconds=120)
        window_end = match_start + timedelta(seconds=match_duration) + timedelta(seconds=120)

        # Call the enhanced method
        arena_start, arena_end = parser.find_verified_arena_boundaries(
            relevant_log, window_start, window_end, match_start, match['filename'], match_duration
        )

        if arena_start and arena_end:
            print(f"✅ Arena boundaries found:")
            print(f"   Start: {arena_start}")
            print(f"   End: {arena_end}")
            print(f"   Duration: {(arena_end - arena_start).total_seconds():.0f}s")
            print(f"   Video offset: {(arena_start - match_start).total_seconds():.0f}s")
        else:
            print("❌ No arena boundaries found")

    except Exception as e:
        print(f"❌ Error in boundary detection: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function."""
    print("🧪 Enhanced Combat Parser Specific Match Testing")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Test 1: Specific problematic matches
        test_specific_problematic_matches()

        # Test 2: Detailed boundary detection
        test_arena_boundary_detection_detail()

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 Testing Complete!")


if __name__ == '__main__':
    main()