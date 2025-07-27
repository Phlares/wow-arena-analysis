#!/usr/bin/env python3
# Quick test of the enhanced production parser

import pandas as pd
from enhanced_combat_parser_production import ProductionEnhancedCombatParser
from pathlib import Path

def main():
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    parser = ProductionEnhancedCombatParser(base_dir)
    
    # Load enhanced index
    df = pd.read_csv(f"{base_dir}/master_index_enhanced.csv")
    df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])
    
    # Find test match that we know should have good data
    test_match = df[df['filename'].str.contains('2025-01-01_20-06-29_-_Phlurbotomy_-_3v3')].iloc[0]
    
    print(f"Testing: {test_match['filename']}")
    
    # Find combat log
    log_files = list(Path(f"{base_dir}/Logs").glob('*.txt'))
    relevant_log = parser.find_combat_log_for_match(test_match, log_files)
    
    if relevant_log:
        print(f"Using log: {relevant_log.name}")
        
        # Extract features
        features = parser.extract_combat_features_smart(test_match, relevant_log, 120)
        
        if features:
            print(f"Cast success: {features['cast_success_own']}")
            print(f"Interrupts: {features['interrupt_success_own']}")
            print(f"Times interrupted: {features['times_interrupted']}")
            print(f"Precog own: {features['precog_gained_own']}")
            print(f"Purges: {features['purges_own']}")
            
            total = (features['cast_success_own'] + features['interrupt_success_own'] + 
                    features['times_interrupted'] + features['precog_gained_own'])
            print(f"Total activity: {total}")
            
            if total > 50:
                print("✅ SUCCESS - Parser working correctly!")
            else:
                print("❌ LOW ACTIVITY - May need debugging")
        else:
            print("❌ No features extracted")
    else:
        print("❌ No combat log found")

if __name__ == '__main__':
    main()
