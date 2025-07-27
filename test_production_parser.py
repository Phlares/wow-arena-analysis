#!/usr/bin/env python3
# test_production_parser.py - Quick test of enhanced production parser

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_combat_parser_production import ProductionEnhancedCombatParser
import pandas as pd

def test_single_match():
    """Test the production parser on a single known working match."""
    
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    parser = ProductionEnhancedCombatParser(base_dir)
    
    # Load enhanced index
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    df = pd.read_csv(enhanced_index)
    df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])
    
    # Find a test match that we know has good data
    test_matches = df[df['filename'].str.contains('2025-01-01_20-06-29_-_Phlurbotomy_-_3v3')].copy()
    
    if len(test_matches) == 0:
        print("❌ Test match not found in index")
        return False
    
    match = test_matches.iloc[0]
    print(f"🎯 Testing match: {match['filename']}")
    print(f"   Start time: {match['precise_start_time']}")
    print(f"   Reliability: {match.get('matching_reliability', 'unknown')}")
    
    # Find relevant combat log
    log_files = list(parser.base_dir.glob('Logs/*.txt'))
    relevant_log = parser.find_combat_log_for_match(match, log_files)
    
    if not relevant_log:
        print("❌ No relevant combat log found")
        return False
    
    print(f"   Combat log: {relevant_log.name}")
    
    # Extract features
    features = parser.extract_combat_features_smart(match, relevant_log, time_window=120)
    
    if not features:
        print("❌ Failed to extract features")
        return False
    
    print(f"\n📊 Extracted Features:")
    print(f"   cast_success_own: {features['cast_success_own']}")
    print(f"   interrupt_success_own: {features['interrupt_success_own']}")
    print(f"   times_interrupted: {features['times_interrupted']}")
    print(f"   precog_gained_own: {features['precog_gained_own']}")
    print(f"   precog_gained_enemy: {features['precog_gained_enemy']}")
    print(f"   purges_own: {features['purges_own']}")
    print(f"   times_died: {features['times_died']}")
    
    # Check if we got meaningful data
    total_activity = (features['cast_success_own'] + features['interrupt_success_own'] + 
                     features['times_interrupted'] + features['precog_gained_own'] + 
                     features['precog_gained_enemy'] + features['purges_own'])
    
    print(f"\n🎯 Total activity events: {total_activity}")
    
    if total_activity >= 50:  # Should have substantial activity
        print("✅ Test PASSED - Production parser extracting meaningful data!")
        return True
    else:
        print("❌ Test FAILED - Low activity count suggests parsing issues")
        return False

def compare_with_existing_results():
    """Compare with existing results to see if we're getting better data."""
    
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    existing_csv = f"{base_dir}/match_features_enhanced.csv"
    
    if not os.path.exists(existing_csv):
        print("⚠️ No existing results to compare against")
        return
    
    df = pd.read_csv(existing_csv)
    
    print(f"\n📈 Existing Results Analysis:")
    print(f"   Total matches: {len(df)}")
    print(f"   Avg cast_success_own: {df['cast_success_own'].mean():.1f}")
    print(f"   Avg interrupt_success_own: {df['interrupt_success_own'].mean():.1f}")
    print(f"   Avg times_interrupted: {df['times_interrupted'].mean():.1f}")
    print(f"   Avg precog_gained_own: {df['precog_gained_own'].mean():.1f}")
    
    # Count zero-value matches
    zero_matches = len(df[df['cast_success_own'] == 0])
    print(f"   Zero-cast matches: {zero_matches}/{len(df)} ({zero_matches/len(df)*100:.1f}%)")
    
    # Find high-activity matches for reference
    high_activity = df[df['cast_success_own'] > 100]
    print(f"   High-activity matches (>100 casts): {len(high_activity)}")
    
    if len(high_activity) > 0:
        print(f"   Example high-activity match: {high_activity.iloc[0]['filename']}")
        print(f"      Casts: {high_activity.iloc[0]['cast_success_own']}")
        print(f"      Interrupts: {high_activity.iloc[0]['interrupt_success_own']}")

if __name__ == '__main__':
    print("🧪 Testing Enhanced Production Combat Parser")
    print("=" * 60)
    
    # Test single match
    success = test_single_match()
    
    # Compare with existing results
    compare_with_existing_results()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Production parser appears to be working correctly!")
        print("✅ Ready to process full dataset")
    else:
        print("❌ Production parser needs further debugging")
        print("🔧 Check arena boundary detection and event parsing logic")
