#!/usr/bin/env python3
"""
Simple coordinate analysis to understand coordinate systems on same arena map.
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
from dev_corrected_movement_tracker import CorrectedAdvancedCombatAction

def analyze_mugambala_coordinates():
    """Analyze coordinates for multiple Mugambala matches."""
    
    production_parser = EnhancedProductionCombatParser(".")
    
    # Known Mugambala matches from our testing
    mugambala_matches = [
        {
            'filename': '2025-05-06_19-03-32_-_Phlurbotomy_-_3v3_Mugambala_(Win).mp4',
            'log_file': './Logs/WoWCombatLog-050625_182406.txt',
            'start_time': '2025-05-06 19:04:28',
            'duration': 200
        },
        {
            'filename': '2025-05-06_19-23-32_-_Phlurbotomy_-_3v3_Mugambala_(Loss).mp4', 
            'log_file': './Logs/WoWCombatLog-050625_182406.txt',
            'start_time': '2025-05-06 19:25:07',
            'duration': 240
        }
    ]
    
    print("ANALYZING MUGAMBALA ARENA COORDINATE SYSTEMS")
    print("="*60)
    
    all_coordinates = {}
    
    for i, match in enumerate(mugambala_matches):
        print(f"\nMatch {i+1}: {match['filename']}")
        
        log_file = Path(match['log_file'])
        if not log_file.exists():
            print(f"  Log file not found: {log_file}")
            continue
        
        # Get arena boundaries
        match_start = datetime.fromisoformat(match['start_time'])
        
        arena_start, arena_end = production_parser.find_verified_arena_boundaries(
            log_file,
            match_start - timedelta(seconds=60),
            match_start + timedelta(seconds=match['duration'] + 60), 
            match_start,
            match['filename'],
            match['duration']
        )
        
        if not arena_start:
            print(f"  No arena boundaries found")
            continue
            
        print(f"  Arena: {arena_start} to {arena_end}")
        
        # Extract coordinates
        coordinates = []
        coordinate_clusters = defaultdict(list)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if count > 50000:  # Limit processing
                    break
                    
                action = CorrectedAdvancedCombatAction(line)
                
                if (action.timestamp and 
                    arena_start <= action.timestamp <= arena_end and
                    action.is_valid_position()):
                    
                    x, y = action.position_x, action.position_y
                    coordinates.append((x, y, action.event, action.source_name))
                    
                    # Cluster by rough coordinate ranges
                    if abs(x) < 100 and abs(y) < 100:
                        coordinate_clusters['local_small'].append((x, y))
                    elif abs(x) < 1000 and abs(y) < 1000:
                        coordinate_clusters['local_medium'].append((x, y))
                    elif x < -1000:
                        coordinate_clusters['world_negative'].append((x, y))
                    elif x > 1000:
                        coordinate_clusters['world_positive'].append((x, y))
                    else:
                        coordinate_clusters['mixed'].append((x, y))
                    
                    count += 1
                    if len(coordinates) >= 100:  # Get first 100 coordinates
                        break
        
        print(f"  Total coordinates extracted: {len(coordinates)}")
        
        # Analyze clusters
        print(f"  Coordinate clusters:")
        for cluster_name, cluster_coords in coordinate_clusters.items():
            if len(cluster_coords) < 3:
                continue
                
            x_coords = [x for x, y in cluster_coords]
            y_coords = [y for x, y in cluster_coords]
            
            print(f"    {cluster_name}: {len(cluster_coords)} coords")
            print(f"      X range: {min(x_coords):.1f} to {max(x_coords):.1f}")
            print(f"      Y range: {min(y_coords):.1f} to {max(y_coords):.1f}")
            print(f"      Sample: {cluster_coords[:3]}")
        
        all_coordinates[match['filename']] = {
            'coordinates': coordinates[:20],  # Store first 20 for comparison
            'clusters': {k: v for k, v in coordinate_clusters.items() if len(v) >= 3}
        }
    
    # Compare coordinate systems across matches
    print(f"\n{'='*60}")
    print("CROSS-MATCH COMPARISON")
    print("="*60)
    
    if len(all_coordinates) >= 2:
        match_names = list(all_coordinates.keys())
        match1, match2 = match_names[0], match_names[1]
        
        print(f"\nComparing {match1} vs {match2}:")
        
        clusters1 = all_coordinates[match1]['clusters']
        clusters2 = all_coordinates[match2]['clusters']
        
        # Find common cluster types
        common_clusters = set(clusters1.keys()) & set(clusters2.keys())
        print(f"Common coordinate systems: {list(common_clusters)}")
        
        for cluster_type in common_clusters:
            coords1 = clusters1[cluster_type]
            coords2 = clusters2[cluster_type]
            
            print(f"\n{cluster_type} system:")
            
            # Calculate centers
            center1_x = sum(x for x, y in coords1) / len(coords1)
            center1_y = sum(y for x, y in coords1) / len(coords1)
            center2_x = sum(x for x, y in coords2) / len(coords2)
            center2_y = sum(y for x, y in coords2) / len(coords2)
            
            print(f"  Match 1 center: ({center1_x:.1f}, {center1_y:.1f})")
            print(f"  Match 2 center: ({center2_x:.1f}, {center2_y:.1f})")
            
            # Check consistency
            x_diff = abs(center1_x - center2_x)  
            y_diff = abs(center1_y - center2_y)
            
            print(f"  Center difference: ({x_diff:.1f}, {y_diff:.1f})")
            print(f"  Consistent: {x_diff < 100 and y_diff < 100}")
    
    # Save results
    output_file = "simple_coordinate_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(all_coordinates, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    analyze_mugambala_coordinates()