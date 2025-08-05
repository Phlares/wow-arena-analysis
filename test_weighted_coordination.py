"""
Test Weighted Coordination Scoring

Tests the enhanced coordination algorithm that weights DPS coordination
as double the healer coordination, reflecting realistic arena gameplay.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from development_standards import SafeLogger, export_json_safely
from json_metadata_targeting_system import (
    create_enhanced_match_model_with_json,
    test_realistic_targeting_analysis
)


def test_weighted_coordination_scoring():
    """Test the weighted coordination scoring algorithm"""
    
    SafeLogger.info("=== TESTING WEIGHTED COORDINATION SCORING ===")
    SafeLogger.info("DPS coordination weighted 2x vs Healer coordination")
    
    # Load master index
    master_index_path = Path("master_index_enhanced.csv")
    if not master_index_path.exists():
        SafeLogger.error("Master index not found")
        return
    
    master_df = pd.read_csv(master_index_path)
    master_df['match_time'] = pd.to_datetime(master_df['precise_start_time'], errors='coerce')
    
    # Test the same matches as before to see the difference
    test_matches = master_df[
        (master_df['filename'].str.contains('2025-05-06_22', na=False)) &
        (master_df['bracket'].str.contains('3v3', na=False)) &
        (master_df['match_time'].notna())
    ].head(3)
    
    SafeLogger.info(f"Testing weighted coordination on {len(test_matches)} matches")
    
    results = []
    logs_dir = Path("Logs")
    
    for i, (_, match_row) in enumerate(test_matches.iterrows(), 1):
        SafeLogger.info(f"\n--- WEIGHTED COORDINATION TEST {i}/{len(test_matches)} ---")
        
        result = test_realistic_targeting_analysis(match_row, logs_dir)
        if result and result.get('success'):
            results.append(result)
            
            # Show detailed results
            coord = result.get('coordination_analysis', {})
            team_comp = result.get('team_composition', {})
            
            SafeLogger.info(f"Match: {result['match_filename']}")
            SafeLogger.info(f"Team: {team_comp.get('friendly_roles', [])}")
            SafeLogger.info(f"Weighted Coordination Score: {coord.get('score', 0):.3f}")
            SafeLogger.info(f"Windows Analyzed: {coord.get('windows_analyzed', 0)}")
    
    # Compare with theoretical expectations
    SafeLogger.info("\n=== WEIGHTED COORDINATION ANALYSIS ===")
    
    if results:
        coordination_scores = [
            r['coordination_analysis']['score'] 
            for r in results 
            if r.get('coordination_analysis', {}).get('available')
        ]
        
        if coordination_scores:
            avg_score = sum(coordination_scores) / len(coordination_scores)
            min_score = min(coordination_scores)
            max_score = max(coordination_scores)
            
            SafeLogger.info(f"Weighted Coordination Results:")
            SafeLogger.info(f"  Average: {avg_score:.3f}")
            SafeLogger.info(f"  Range: {min_score:.3f} - {max_score:.3f}")
            
            # Show theoretical ranges for weighted system
            SafeLogger.info(f"\nWeighted Coordination Theory (3v3 with 1 Healer, 2 DPS):")
            SafeLogger.info(f"  Perfect (All 3 attack): 5.0/5.0 = 1.000")
            SafeLogger.info(f"  High (2 DPS attack):   4.0/5.0 = 0.800") 
            SafeLogger.info(f"  Medium (1 DPS + Healer): 3.0/5.0 = 0.600")
            SafeLogger.info(f"  Low (1 DPS only):      2.0/5.0 = 0.400")
            SafeLogger.info(f"  Minimal (Healer only): 1.0/5.0 = 0.200")
            SafeLogger.info(f"  None (No attacks):     0.0/5.0 = 0.000")
            
            # Analysis of results
            if max_score > 0.600:
                SafeLogger.success("EXCELLENT: Detecting high-quality DPS coordination!")
            elif avg_score > 0.400:
                SafeLogger.success("GOOD: Weighted system showing realistic coordination levels")
            else:
                SafeLogger.info("Results show lower coordination - may indicate room for improvement")
    
    # Export weighted results
    weighted_results = {
        'test_summary': {
            'algorithm': 'weighted_coordination_scoring',
            'dps_weight': 2.0,
            'healer_weight': 1.0,
            'total_matches': len(results),
            'successful_analyses': len([r for r in results if r.get('coordination_analysis', {}).get('available')]),
            'test_timestamp': datetime.now().isoformat()
        },
        'coordination_scores': coordination_scores if results else [],
        'detailed_results': results
    }
    
    export_json_safely(weighted_results, Path("weighted_coordination_test_results.json"))
    SafeLogger.success("Weighted coordination test results exported")
    
    return weighted_results


def compare_coordination_algorithms():
    """Compare old vs new coordination algorithms"""
    
    SafeLogger.info("=== COORDINATION ALGORITHM COMPARISON ===")
    
    # Load previous results (unweighted)
    old_results_file = Path("realistic_targeting_validation_results.json")
    new_results_file = Path("weighted_coordination_test_results.json")
    
    if not old_results_file.exists():
        SafeLogger.warning("Previous results not found - run json_metadata_targeting_system.py first")
        return
    
    if not new_results_file.exists():
        SafeLogger.warning("New results not found - run weighted test first")
        return
    
    import json
    
    with open(old_results_file, 'r') as f:
        old_results = json.load(f)
    
    with open(new_results_file, 'r') as f:
        new_results = json.load(f)
    
    # Extract coordination scores
    old_scores = []
    for result in old_results.get('detailed_results', []):
        if result.get('success') and result.get('coordination_analysis', {}).get('available'):
            old_scores.append(result['coordination_analysis']['score'])
    
    new_scores = new_results.get('coordination_scores', [])
    
    SafeLogger.info("Algorithm Comparison:")
    SafeLogger.info(f"  Unweighted Algorithm: {len(old_scores)} scores, avg {sum(old_scores)/len(old_scores):.3f}" if old_scores else "  Unweighted: No scores")
    SafeLogger.info(f"  Weighted Algorithm:   {len(new_scores)} scores, avg {sum(new_scores)/len(new_scores):.3f}" if new_scores else "  Weighted: No scores")
    
    if old_scores and new_scores:
        # Show side-by-side comparison
        SafeLogger.info("\nSide-by-side Comparison:")
        for i, (old, new) in enumerate(zip(old_scores, new_scores)):
            change = new - old
            change_str = f"(+{change:.3f})" if change > 0 else f"({change:.3f})"
            SafeLogger.info(f"  Match {i+1}: {old:.3f} -> {new:.3f} {change_str}")
    
    return {'old_scores': old_scores, 'new_scores': new_scores}


if __name__ == "__main__":
    # Test weighted coordination scoring
    weighted_results = test_weighted_coordination_scoring()
    
    # Compare algorithms
    comparison = compare_coordination_algorithms()