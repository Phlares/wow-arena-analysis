#!/usr/bin/env python3
"""
Development: Production-Integrated Movement Tracker

Integrates the production parser's rigorous arena boundary detection and validation
with the advanced movement tracking system to ensure quality match boundaries
and prevent anomalous movement data.

This addresses the issue where movement tracking was using simple ARENA_MATCH_START/END
detection instead of the production parser's sophisticated validation.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import re

# Import production parser components
from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
from advanced_combat_parser import AdvancedCombatParser, AdvancedCombatAction

class ProductionIntegratedMovementTracker:
    """
    Movement tracker that uses production parser's arena boundary detection
    to ensure accurate match boundaries and prevent anomalous movement data.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        
        # Initialize production parser for boundary detection
        self.production_parser = EnhancedProductionCombatParser(base_dir)
        
        # Initialize advanced parser for movement data
        self.advanced_parser = AdvancedCombatParser()
        
        # Zone mapping (from production parser)
        self.zone_map = {
            '980': "Tol'viron Arena", 
            '1552': "Ashamane's Fall Arena", 
            '2759': "Cage of Carnage Arena",
            '1504': "Black Rook Hold Arena", 
            '2167': "Robodrome Arena", 
            '2563': "Nokhudon Arena",
            '1911': "Mugambala Arena", 
            '2373': "Empyrean Domain Arena", 
            '1134': "Tiger's Peak Arena",
            '1505': "Nagrand Arena", 
            '1825': "Hook Point Arena", 
            '2509': "Maldraxxus Arena",
            '572': "Ruins of Lordaeron Arena", 
            '617': "Dalaran Sewers Arena", 
            '2547': "Enigma Crucible Arena"
        }
    
    def validate_match_with_production_criteria(self, log_file: Path, match_info: Dict) -> Optional[Dict]:
        """
        Validate and extract movement data using production parser's criteria.
        
        Args:
            log_file: Path to combat log file
            match_info: Match information from video metadata
            
        Returns:
            Validated movement data or None if validation fails
        """
        print(f"Validating match: {match_info['filename']}")
        
        # Extract match details from filename (using production parser logic)
        player_name = self.production_parser.extract_player_name(match_info['filename'])
        if not player_name:
            print(f"  ERROR: Could not extract player name from {match_info['filename']}")
            return None
        
        # Extract arena and bracket info
        expected_bracket, expected_map = self.production_parser.extract_arena_info_from_filename(match_info['filename'])
        print(f"  Expected: {expected_bracket} on {expected_map}")
        print(f"  Player: {player_name}")
        
        # Extract outcome from filename (Win/Loss in parentheses)
        outcome = self.extract_outcome_from_filename(match_info['filename'])
        print(f"  Outcome: {outcome}")
        
        # Use production parser's enhanced arena boundary detection
        match_start_time = match_info['precise_start_time']
        if hasattr(match_start_time, 'to_pydatetime'):
            match_start = match_start_time.to_pydatetime()
        elif isinstance(match_start_time, str):
            match_start = datetime.fromisoformat(match_start_time.replace('Z', '+00:00'))
        else:
            match_start = match_start_time
        
        match_duration = match_info.get('duration_s', 300)
        
        arena_start, arena_end = self.production_parser.find_verified_arena_boundaries(
            log_file, 
            match_start - timedelta(seconds=60),  # Search window
            match_start + timedelta(seconds=match_duration + 60),
            match_start,
            match_info['filename'],
            match_duration
        )
        
        if not arena_start:
            print(f"  ERROR: No verified arena boundaries found")
            return None
        
        print(f"  Verified boundaries: {arena_start} - {arena_end}")
        
        # Parse movement data within verified boundaries
        movement_data = self.advanced_parser.parse_combat_log(log_file, arena_start, arena_end)
        
        if 'error' in movement_data:
            print(f"  ERROR: {movement_data['error']}")
            return None
        
        # Validate player count (should be 6 for arena matches)
        unique_players = movement_data.get('unique_players', 0)
        if unique_players != 6:
            print(f"  WARNING: Expected 6 players, found {unique_players}")
            if unique_players < 4:  # Too few players indicates bad match
                return None
        
        # Validate movement data quality
        movement_quality = self.validate_movement_quality(movement_data, player_name)
        if not movement_quality['valid']:
            print(f"  ERROR: Movement validation failed: {movement_quality['reason']}")
            return None
        
        # Validate against JSON metadata if available
        json_validation = self.validate_against_json_metadata(match_info['filename'], movement_data)
        
        return {
            'filename': match_info['filename'],
            'player_name': player_name,
            'arena_zone': movement_data.get('arena_zone'),
            'arena_name': self.zone_map.get(str(movement_data.get('arena_zone', 0)), f"Zone {movement_data.get('arena_zone', 0)}"),
            'bracket': expected_bracket,
            'map': expected_map,
            'outcome': outcome,
            'arena_start': arena_start.isoformat(),
            'arena_end': arena_end.isoformat() if arena_end else None,
            'match_duration': (arena_end - arena_start).total_seconds() if arena_end else match_duration,
            'movement_data': movement_data,
            'movement_quality': movement_quality,
            'json_validation': json_validation,
            'players_found': movement_data.get('players', []),
            'unique_players': unique_players
        }
    
    def extract_outcome_from_filename(self, filename: str) -> str:
        """Extract match outcome from filename (Win/Loss in parentheses)."""
        # Look for outcome in parentheses at the end: (Win) or (Loss)
        match = re.search(r'\(([^)]+)\)(?:\.[^.]*)?$', filename)
        if match:
            outcome = match.group(1)
            if outcome.lower() in ['win', 'victory']:
                return 'Win'
            elif outcome.lower() in ['loss', 'defeat']:
                return 'Loss'
            else:
                return outcome
        return 'Unknown'
    
    def validate_movement_quality(self, movement_data: Dict, player_name: str) -> Dict:
        """
        Validate movement data quality to catch anomalous data.
        
        Args:
            movement_data: Movement data from advanced parser
            player_name: Expected player name
            
        Returns:
            Dictionary with validation result and details
        """
        validation = {'valid': True, 'reason': '', 'details': {}}
        
        actions = movement_data.get('actions', [])
        if not actions:
            return {'valid': False, 'reason': 'No movement actions found', 'details': {}}
        
        # Get player-specific actions
        player_actions = [action for action in actions if action.get_player_name() == player_name]
        if not player_actions:
            return {'valid': False, 'reason': f'No actions found for player {player_name}', 'details': {}}
        
        # Calculate movement statistics
        positions = []
        for action in player_actions:
            if action.is_valid_position():
                positions.append({
                    'x': action.advanced_actor_position_x,
                    'y': action.advanced_actor_position_y,
                    'timestamp': action.timestamp
                })
        
        if len(positions) < 10:
            return {'valid': False, 'reason': 'Insufficient position data', 'details': {'positions': len(positions)}}
        
        # Calculate total distance
        total_distance = 0.0
        for i in range(1, len(positions)):
            dx = positions[i]['x'] - positions[i-1]['x']
            dy = positions[i]['y'] - positions[i-1]['y']
            distance = (dx*dx + dy*dy)**0.5
            total_distance += distance
        
        # Validate distance is reasonable (not anomalously high)
        match_duration = (positions[-1]['timestamp'] - positions[0]['timestamp']).total_seconds()
        if match_duration <= 0:
            return {'valid': False, 'reason': 'Invalid match duration', 'details': {'duration': match_duration}}
        
        average_speed = total_distance / match_duration
        
        # Reasonable limits for WoW movement (units per second)
        MAX_REASONABLE_SPEED = 50.0  # Even with movement abilities, this should be upper limit
        MAX_TOTAL_DISTANCE = 25000.0  # Maximum reasonable distance in a single arena match
        
        validation['details'] = {
            'position_count': len(positions),
            'total_distance': total_distance,
            'match_duration': match_duration,
            'average_speed': average_speed,
            'player_name': player_name
        }
        
        if average_speed > MAX_REASONABLE_SPEED:
            validation['valid'] = False
            validation['reason'] = f'Anomalous average speed: {average_speed:.1f} > {MAX_REASONABLE_SPEED}'
            return validation
        
        if total_distance > MAX_TOTAL_DISTANCE:
            validation['valid'] = False
            validation['reason'] = f'Anomalous total distance: {total_distance:.1f} > {MAX_TOTAL_DISTANCE}'
            return validation
        
        return validation
    
    def validate_against_json_metadata(self, filename: str, movement_data: Dict) -> Dict:
        """
        Validate movement data against corresponding JSON metadata.
        
        Args:
            filename: Video filename
            movement_data: Movement data from parser
            
        Returns:
            Validation results
        """
        validation = {'found': False, 'matches': False, 'details': {}}
        
        try:
            # Load corresponding JSON file
            json_name = filename.rsplit('.', 1)[0] + '.json'
            
            # Try date-organized subdirectory first
            try:
                date_part = filename.split('_', 1)[0]  # YYYY-MM-DD
                year_month = date_part.rsplit('-', 1)[0]  # YYYY-MM
                json_path = self.base_dir / year_month / json_name
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        validation['found'] = True
                        validation = self._compare_with_json(validation, json_data, movement_data)
            except:
                pass
            
            # Try root directory if not found
            if not validation['found']:
                json_path = self.base_dir / json_name
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        validation['found'] = True
                        validation = self._compare_with_json(validation, json_data, movement_data)
        
        except Exception as e:
            validation['error'] = str(e)
        
        return validation
    
    def _compare_with_json(self, validation: Dict, json_data: Dict, movement_data: Dict) -> Dict:
        """Compare movement data with JSON metadata."""
        try:
            # Compare player names
            json_players = set()
            if 'combatants' in json_data:
                for combatant in json_data['combatants']:
                    if '_name' in combatant:
                        json_players.add(combatant['_name'])
            
            movement_players = set(movement_data.get('players', []))
            
            validation['details'] = {
                'json_players': list(json_players),
                'movement_players': list(movement_players),
                'player_overlap': len(json_players.intersection(movement_players)),
                'expected_players': len(json_players)
            }
            
            # Consider match if majority of players overlap
            if len(json_players) > 0:
                overlap_ratio = len(json_players.intersection(movement_players)) / len(json_players)
                validation['matches'] = overlap_ratio >= 0.5  # At least 50% overlap
                validation['overlap_ratio'] = overlap_ratio
            
        except Exception as e:
            validation['error'] = str(e)
        
        return validation
    
    def test_comprehensive_validation(self, enhanced_index_csv: str, logs_dir: str, output_file: str):
        """
        Test comprehensive validation on multiple matches using production criteria.
        
        Args:
            enhanced_index_csv: Path to enhanced match index
            logs_dir: Directory containing combat logs  
            output_file: Output file for results
        """
        print("=== PRODUCTION-INTEGRATED MOVEMENT TRACKING TEST ===")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        
        # Load enhanced index
        try:
            index_df = pd.read_csv(enhanced_index_csv)
            index_df = self.production_parser._clean_timestamps_in_df(index_df)
            
            # Filter to recent matches with logs available
            index_df = index_df[index_df['precise_start_time'] >= '2025-01-01'].copy()
            index_df = index_df.sort_values('precise_start_time').reset_index(drop=True)
            print(f"Total 2025+ matches: {len(index_df)}")
            
        except Exception as e:
            print(f"ERROR: Failed to load enhanced index: {e}")
            return
        
        # Get available combat logs
        log_files = {f.stem: f for f in Path(logs_dir).glob('*.txt')}
        print(f"Available combat logs: {len(log_files)}")
        
        # Test on matches that we know have working data
        # Find matches with Chuanjianguo-Frostmourne-US (from our earlier tests)
        test_candidates = index_df[index_df['filename'].str.contains('Chuanjianguo', na=False)]
        
        if len(test_candidates) == 0:
            # Fallback to recent matches with logs available
            test_candidates = index_df[index_df['precise_start_time'] >= '2025-05-01'].head(5)
        
        test_matches = test_candidates.head(3)  # Test first 3 matches
        print(f"Selected test matches: {list(test_matches['filename'])}")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_matches_tested': len(test_matches),
            'successful_validations': 0,
            'failed_validations': 0,
            'validation_results': [],
            'movement_quality': {},
            'summary': {}
        }
        
        for idx, match in test_matches.iterrows():
            print(f"\n=== Testing Match {idx + 1}/{len(test_matches)} ===")
            
            # Find corresponding combat log
            match_timestamp = match['precise_start_time']
            if hasattr(match_timestamp, 'strftime'):
                match_date = match_timestamp.strftime('%Y-%m-%d')
            else:
                match_date = str(match_timestamp)[:10]  # YYYY-MM-DD
            
            # Convert to MMDDYY format used by combat logs (WoWCombatLog-010125_HHMMSS.txt)
            try:
                date_obj = datetime.strptime(match_date, '%Y-%m-%d')
                log_date_format = date_obj.strftime('%m%d%y')
                log_candidates = [
                    f for log_name, f in log_files.items() 
                    if log_date_format in log_name
                ]
                print(f"  Looking for logs with date: {log_date_format}")
            except:
                log_candidates = []
            
            if not log_candidates:
                print(f"  No combat log found for {match['filename']}")
                results['failed_validations'] += 1
                continue
            
            # Use the first matching log
            log_file = log_candidates[0]
            print(f"  Using log: {log_file.name}")
            
            # Validate with production criteria
            validation_result = self.validate_match_with_production_criteria(log_file, match)
            
            if validation_result:
                print(f"  SUCCESS: Validated match")
                results['successful_validations'] += 1
                results['validation_results'].append(validation_result)
                
                # Store movement quality data
                player_name = validation_result['player_name']
                movement_quality = validation_result['movement_quality']['details']
                results['movement_quality'][player_name] = movement_quality
                
            else:
                print(f"  FAILED: Validation failed")
                results['failed_validations'] += 1
        
        # Calculate summary statistics
        success_rate = (results['successful_validations'] / results['total_matches_tested']) * 100
        results['summary'] = {
            'success_rate': success_rate,
            'avg_players_per_match': sum(r['unique_players'] for r in results['validation_results']) / len(results['validation_results']) if results['validation_results'] else 0,
            'arenas_tested': list(set(r['arena_name'] for r in results['validation_results'])),
            'brackets_tested': list(set(r['bracket'] for r in results['validation_results'])),
            'outcomes_found': list(set(r['outcome'] for r in results['validation_results']))
        }
        
        print(f"\n=== VALIDATION SUMMARY ===")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Successful validations: {results['successful_validations']}")
        print(f"Failed validations: {results['failed_validations']}")
        print(f"Average players per match: {results['summary']['avg_players_per_match']:.1f}")
        print(f"Arenas tested: {', '.join(results['summary']['arenas_tested'])}")
        print(f"Brackets tested: {', '.join(results['summary']['brackets_tested'])}")
        print(f"Outcomes found: {', '.join(results['summary']['outcomes_found'])}")
        
        # Show movement quality comparison
        if results['movement_quality']:
            print(f"\n=== MOVEMENT QUALITY ===")
            for player, quality in results['movement_quality'].items():
                print(f"{player}:")
                print(f"  Position count: {quality['position_count']}")
                print(f"  Total distance: {quality['total_distance']:.1f}")
                print(f"  Average speed: {quality['average_speed']:.1f}")
        
        # Export results
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    def test_single_known_match(self, log_file: str, player_name: str, match_filename: str):
        """Test a single known working match for debugging."""
        print(f"=== TESTING SINGLE KNOWN MATCH ===")
        print(f"Log file: {log_file}")
        print(f"Player: {player_name}")
        print(f"Match: {match_filename}")
        
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"ERROR: Log file not found: {log_file}")
            return
        
        # Create mock match info
        mock_match = {
            'filename': match_filename,
            'precise_start_time': '2025-08-03 09:31:18',  # From the known working log
            'duration_s': 60
        }
        
        # Validate with production criteria
        result = self.validate_match_with_production_criteria(log_path, mock_match)
        
        if result:
            print("SUCCESS: Match validated successfully!")
            print(f"Arena: {result['arena_name']}")
            print(f"Players found: {result['players_found']}")
            print(f"Movement quality: {result['movement_quality']}")
        else:
            print("FAILED: Match validation failed")
        
        return result

def main():
    """Test production-integrated movement tracking."""
    # Initialize tracker
    tracker = ProductionIntegratedMovementTracker(".")
    
    # Test with known working match first
    tracker.test_single_known_match(
        log_file="./reference movement tracking from arena logs/WoWCombatLog-080325_093118.txt",
        player_name="Chuanjianguo-Frostmourne-US",
        match_filename="2025-08-03_09-31-18_-_Chuanjianguo-Frostmourne-US_-_3v3_Ashamanes_Fall_(Win).mp4"
    )
    
    print("\n" + "="*80 + "\n")
    
    # Test comprehensive validation
    tracker.test_comprehensive_validation(
        enhanced_index_csv="master_index_enhanced.csv",
        logs_dir="./Logs",
        output_file="production_integrated_validation_results.json"
    )

if __name__ == "__main__":
    main()