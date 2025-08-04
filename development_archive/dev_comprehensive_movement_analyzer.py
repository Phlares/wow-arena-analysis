#!/usr/bin/env python3
"""
Development: Comprehensive Movement Analyzer

Implements standard testing approach (1 game, then 3 before and 3 after) with extensive
debugging for movement tracking. Flags large movements for review but does not suppress them.
Ties movements back to combat log entries to identify potential errors vs legitimate gameplay.

Standard Testing Protocol:
1. Test 1 known game
2. Test 3 games before 
3. Test 3 games after
4. Extensive debugging output
5. Flag large movements but don't suppress
6. Tie to combat log entries
"""

import os
import json
import pandas as pd
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import re

from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
from advanced_combat_parser import AdvancedCombatParser, AdvancedCombatAction

class ComprehensiveMovementAnalyzer:
    """
    Comprehensive movement analyzer with extensive debugging and combat log correlation.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        
        # Initialize parsers
        self.production_parser = EnhancedProductionCombatParser(base_dir)
        self.advanced_parser = AdvancedCombatParser()
        
        # Movement analysis thresholds (for flagging, not suppressing)
        self.LARGE_MOVEMENT_THRESHOLD = 50.0  # Flag movements > 50 units in 1 second
        self.VERY_LARGE_MOVEMENT_THRESHOLD = 100.0  # Flag movements > 100 units in 1 second
        self.TELEPORT_THRESHOLD = 200.0  # Likely teleportation/displacement
        
        # Known high-mobility spells for context
        self.HIGH_MOBILITY_SPELLS = {
            # Demon Hunter
            195072: "Fel Rush",
            232893: "Felblade", 
            191427: "Metamorphosis",
            
            # Warrior  
            6544: "Heroic Leap",
            100: "Charge",
            57755: "Heroic Throw",
            
            # Death Knight
            49576: "Death Grip",
            47476: "Strangulate",
            
            # Hunter
            190925: "Harpoon",
            781: "Disengage",
            
            # Monk
            116844: "Ring of Peace",
            115546: "Provoke",
            109132: "Roll",
            
            # Druid
            132469: "Typhoon",
            102793: "Ursol's Vortex",
            
            # Priest
            73325: "Leap of Faith",
            
            # Mage
            1953: "Blink",
            212653: "Shimmer",
            
            # Warlock
            6789: "Mortal Coil",
        }
    
    def analyze_match_movement_comprehensive(self, log_file: Path, match_info: Dict) -> Dict:
        """
        Comprehensive movement analysis with extensive debugging.
        
        Args:
            log_file: Combat log file
            match_info: Match information from video metadata
            
        Returns:
            Comprehensive analysis results with debugging info
        """
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE MOVEMENT ANALYSIS")
        print(f"Match: {match_info['filename']}")
        print(f"Log: {log_file.name}")
        print(f"{'='*80}")
        
        # Extract match details
        player_name = self.production_parser.extract_player_name(match_info['filename'])
        expected_bracket, expected_map = self.production_parser.extract_arena_info_from_filename(match_info['filename'])
        outcome = self.extract_outcome_from_filename(match_info['filename'])
        
        print(f"Player: {player_name}")
        print(f"Expected: {expected_bracket} on {expected_map}")
        print(f"Outcome: {outcome}")
        
        if not player_name:
            return {'error': 'Could not extract player name', 'filename': match_info['filename']}
        
        # Get match timing
        match_start_time = match_info['precise_start_time']
        if hasattr(match_start_time, 'to_pydatetime'):
            match_start = match_start_time.to_pydatetime()
        elif isinstance(match_start_time, str):
            match_start = datetime.fromisoformat(match_start_time.replace('Z', '+00:00'))
        else:
            match_start = match_start_time
        
        match_duration = match_info.get('duration_s', 300)
        
        print(f"Video Start: {match_start}")
        print(f"Video Duration: {match_duration}s")
        
        # Find verified arena boundaries using production parser
        print(f"\n--- ARENA BOUNDARY DETECTION ---")
        arena_start, arena_end = self.production_parser.find_verified_arena_boundaries(
            log_file,
            match_start - timedelta(seconds=60),
            match_start + timedelta(seconds=match_duration + 60),
            match_start,
            match_info['filename'],
            match_duration
        )
        
        if not arena_start:
            print("ERROR: No verified arena boundaries found")
            return {'error': 'No verified arena boundaries', 'filename': match_info['filename']}
        
        print(f"Arena Start: {arena_start}")
        print(f"Arena End: {arena_end}")
        print(f"Arena Duration: {(arena_end - arena_start).total_seconds():.1f}s")
        
        # Parse movement data within boundaries
        print(f"\n--- MOVEMENT DATA PARSING ---")
        movement_data = self.advanced_parser.parse_combat_log(log_file, arena_start, arena_end)
        
        if 'error' in movement_data:
            print(f"ERROR: {movement_data['error']}")
            return {'error': movement_data['error'], 'filename': match_info['filename']}
        
        print(f"Total Actions: {movement_data.get('advanced_actions', 0)}")
        print(f"Players Found: {movement_data.get('unique_players', 0)}")
        print(f"Player List: {movement_data.get('players', [])}")
        
        if player_name not in movement_data.get('players', []):
            print(f"WARNING: Player {player_name} not found in movement data")
            print(f"Available players: {movement_data.get('players', [])}")
            # Try to find similar player names
            available_players = movement_data.get('players', [])
            for available in available_players:
                if player_name.split('-')[0] in available:
                    print(f"Found similar player: {available}")
                    player_name = available
                    break
        
        # Analyze movements for this player
        analysis = self.analyze_player_movements(log_file, player_name, arena_start, arena_end, movement_data)
        
        # Add match context
        analysis.update({
            'filename': match_info['filename'],
            'player_name': player_name,
            'expected_bracket': expected_bracket,
            'expected_map': expected_map,
            'outcome': outcome,
            'arena_start': arena_start.isoformat(),
            'arena_end': arena_end.isoformat() if arena_end else None,
            'arena_duration': (arena_end - arena_start).total_seconds() if arena_end else match_duration,
            'video_start': match_start.isoformat(),
            'video_duration': match_duration
        })
        
        return analysis
    
    def analyze_player_movements(self, log_file: Path, player_name: str, 
                                arena_start: datetime, arena_end: datetime, 
                                movement_data: Dict) -> Dict:
        """
        Analyze movements for a specific player with combat log correlation.
        """
        print(f"\n--- PLAYER MOVEMENT ANALYSIS: {player_name} ---")
        
        # Get player actions
        actions = movement_data.get('actions', [])
        player_actions = [action for action in actions if action.get_player_name() == player_name]
        
        print(f"Player Actions Found: {len(player_actions)}")
        
        if not player_actions:
            return {
                'error': f'No movement actions found for {player_name}',
                'total_actions': len(actions),
                'available_players': movement_data.get('players', [])
            }
        
        # Extract positions with timestamps
        positions = []
        for action in player_actions:
            if action.is_valid_position():
                positions.append({
                    'timestamp': action.timestamp,
                    'x': action.advanced_actor_position_x,
                    'y': action.advanced_actor_position_y,
                    'facing': action.advanced_actor_facing,
                    'event': action.event,
                    'raw_line': action.raw_line if hasattr(action, 'raw_line') else '',
                    'action': action
                })
        
        print(f"Valid Positions: {len(positions)}")
        
        if len(positions) < 2:
            return {
                'error': f'Insufficient position data for {player_name}',
                'positions_found': len(positions),
                'player_actions': len(player_actions)
            }
        
        # Sort by timestamp
        positions.sort(key=lambda x: x['timestamp'])
        
        # Calculate movement segments
        movement_segments = []
        total_distance = 0.0
        large_movements = []
        
        print(f"\n--- MOVEMENT SEGMENT ANALYSIS ---")
        print(f"Analyzing {len(positions)} position points...")
        
        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]
            
            # Calculate distance and time
            dx = curr_pos['x'] - prev_pos['x']
            dy = curr_pos['y'] - prev_pos['y']
            distance = math.sqrt(dx*dx + dy*dy)
            time_diff = (curr_pos['timestamp'] - prev_pos['timestamp']).total_seconds()
            speed = distance / time_diff if time_diff > 0 else float('inf')
            
            segment = {
                'segment_id': i,
                'start_time': prev_pos['timestamp'],
                'end_time': curr_pos['timestamp'],
                'time_diff': time_diff,
                'start_pos': (prev_pos['x'], prev_pos['y']),
                'end_pos': (curr_pos['x'], curr_pos['y']),
                'distance': distance,
                'speed': speed,
                'start_event': prev_pos['event'],
                'end_event': curr_pos['event'],
                'dx': dx,
                'dy': dy
            }
            
            movement_segments.append(segment)
            total_distance += distance
            
            # Flag large movements for review (but don't suppress)
            if speed > self.LARGE_MOVEMENT_THRESHOLD:
                large_movements.append(segment)
                
                flag_type = "NORMAL"
                if speed > self.TELEPORT_THRESHOLD:
                    flag_type = "TELEPORT"
                elif speed > self.VERY_LARGE_MOVEMENT_THRESHOLD:
                    flag_type = "VERY_LARGE"
                elif speed > self.LARGE_MOVEMENT_THRESHOLD:
                    flag_type = "LARGE"
                
                print(f"  {flag_type} MOVEMENT FLAGGED:")
                print(f"    Segment {i}: {distance:.1f} units in {time_diff:.3f}s = {speed:.1f} u/s")
                print(f"    From: ({prev_pos['x']:.1f}, {prev_pos['y']:.1f}) at {prev_pos['timestamp']}")
                print(f"    To:   ({curr_pos['x']:.1f}, {curr_pos['y']:.1f}) at {curr_pos['timestamp']}")
                print(f"    Events: {prev_pos['event']} -> {curr_pos['event']}")
        
        # Calculate overall statistics
        match_duration = (positions[-1]['timestamp'] - positions[0]['timestamp']).total_seconds()
        average_speed = total_distance / match_duration if match_duration > 0 else 0
        
        print(f"\n--- MOVEMENT STATISTICS ---")
        print(f"Total Distance: {total_distance:.1f} units")
        print(f"Match Duration: {match_duration:.1f}s")
        print(f"Average Speed: {average_speed:.1f} units/second")
        print(f"Position Changes: {len(positions)}")
        print(f"Movement Segments: {len(movement_segments)}")
        print(f"Large Movements Flagged: {len(large_movements)}")
        
        # Correlate large movements with combat log entries
        if large_movements:
            print(f"\n--- COMBAT LOG CORRELATION FOR LARGE MOVEMENTS ---")
            large_movements_with_context = self.correlate_movements_with_combat_log(
                log_file, large_movements, player_name, arena_start, arena_end
            )
        else:
            large_movements_with_context = []
        
        # Calculate arena coverage
        x_coords = [pos['x'] for pos in positions]
        y_coords = [pos['y'] for pos in positions]
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        coverage_area = x_range * y_range
        
        # Estimate arena size (rough estimate)
        estimated_arena_area = 40000
        arena_coverage_percent = min(100.0, (coverage_area / estimated_arena_area) * 100)
        
        print(f"Arena Coverage: {arena_coverage_percent:.1f}%")
        print(f"X Range: {x_range:.1f} units")
        print(f"Y Range: {y_range:.1f} units")
        
        return {
            'player_name': player_name,
            'total_distance': total_distance,
            'match_duration': match_duration,
            'average_speed': average_speed,
            'position_count': len(positions),
            'movement_segments': len(movement_segments),
            'large_movements_count': len(large_movements),
            'arena_coverage_percent': arena_coverage_percent,
            'x_range': x_range,
            'y_range': y_range,
            
            # Detailed data for review
            'positions': positions[:10],  # First 10 positions for debugging
            'movement_segments': movement_segments[:10],  # First 10 segments for debugging
            'large_movements': large_movements_with_context,  # All large movements with context
            
            # Movement quality flags (not suppressions)
            'movement_flags': {
                'has_large_movements': len(large_movements) > 0,
                'has_teleport_movements': any(seg['speed'] > self.TELEPORT_THRESHOLD for seg in large_movements),
                'max_speed': max([seg['speed'] for seg in movement_segments], default=0),
                'max_distance_segment': max([seg['distance'] for seg in movement_segments], default=0)
            }
        }
    
    def correlate_movements_with_combat_log(self, log_file: Path, large_movements: List[Dict], 
                                          player_name: str, arena_start: datetime, arena_end: datetime) -> List[Dict]:
        """
        Correlate large movements with combat log entries to identify potential causes.
        """
        print(f"Correlating {len(large_movements)} large movements with combat log...")
        
        # Parse combat log around the large movement times
        enhanced_movements = []
        
        for movement in large_movements:
            start_time = movement['start_time']
            end_time = movement['end_time']
            
            # Look for combat events in a 5-second window around the movement
            search_start = start_time - timedelta(seconds=2.5)
            search_end = end_time + timedelta(seconds=2.5)
            
            # Find relevant combat log entries
            combat_events = self.find_combat_events_in_window(
                log_file, search_start, search_end, player_name
            )
            
            # Analyze potential causes
            potential_causes = self.analyze_movement_causes(combat_events, movement)
            
            enhanced_movement = movement.copy()
            enhanced_movement.update({
                'combat_events': combat_events,
                'potential_causes': potential_causes,
                'analysis': self.classify_movement_type(movement, potential_causes)
            })
            
            enhanced_movements.append(enhanced_movement)
            
            print(f"  Large Movement at {start_time}:")
            print(f"    Distance: {movement['distance']:.1f} units, Speed: {movement['speed']:.1f} u/s")
            print(f"    Combat Events Found: {len(combat_events)}")
            if potential_causes:
                print(f"    Potential Causes: {', '.join(potential_causes)}")
            print(f"    Classification: {enhanced_movement['analysis']['classification']}")
        
        return enhanced_movements
    
    def find_combat_events_in_window(self, log_file: Path, start_time: datetime, 
                                   end_time: datetime, player_name: str) -> List[Dict]:
        """Find combat events in a time window around a movement."""
        events = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Parse timestamp
                    timestamp_match = re.match(r'^(\d{1,2}/\d{1,2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
                    if not timestamp_match:
                        continue
                    
                    try:
                        # Parse timestamp (assuming current year)
                        timestamp_str = f"2025/{timestamp_match.group(1)}"
                        event_time = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S.%f")
                        
                        if start_time <= event_time <= end_time:
                            # Check if event involves the player
                            if player_name in line:
                                events.append({
                                    'timestamp': event_time,
                                    'raw_line': line.strip(),
                                    'event_type': self.extract_event_type(line),
                                    'spell_id': self.extract_spell_id(line),
                                    'spell_name': self.get_spell_name(self.extract_spell_id(line))
                                })
                    except:
                        continue
        except Exception as e:
            print(f"Error reading combat log: {e}")
        
        return events
    
    def extract_event_type(self, line: str) -> str:
        """Extract event type from combat log line."""
        parts = line.split(',')
        return parts[0].split()[-1] if len(parts) > 0 else "UNKNOWN"
    
    def extract_spell_id(self, line: str) -> Optional[int]:
        """Extract spell ID from combat log line."""
        # Look for spell ID pattern
        match = re.search(r'"(\d+)"', line)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
        return None
    
    def get_spell_name(self, spell_id: Optional[int]) -> str:
        """Get spell name from spell ID."""
        if spell_id and spell_id in self.HIGH_MOBILITY_SPELLS:
            return self.HIGH_MOBILITY_SPELLS[spell_id]
        return f"Spell {spell_id}" if spell_id else "Unknown"
    
    def analyze_movement_causes(self, combat_events: List[Dict], movement: Dict) -> List[str]:
        """Analyze potential causes for a large movement."""
        causes = []
        
        for event in combat_events:
            spell_id = event['spell_id']
            event_type = event['event_type']
            
            # Check for known mobility spells
            if spell_id and spell_id in self.HIGH_MOBILITY_SPELLS:
                causes.append(f"{self.HIGH_MOBILITY_SPELLS[spell_id]} (ID: {spell_id})")
            
            # Check for displacement events
            if 'DAMAGE' in event_type and movement['speed'] > self.TELEPORT_THRESHOLD:
                causes.append(f"Potential displacement from {event_type}")
            
            # Check for teleportation-like events
            if movement['speed'] > self.TELEPORT_THRESHOLD:
                causes.append("Likely teleportation/instant movement")
        
        return causes
    
    def classify_movement_type(self, movement: Dict, potential_causes: List[str]) -> Dict:
        """Classify the type of movement based on analysis."""
        speed = movement['speed']
        distance = movement['distance']
        
        if speed > self.TELEPORT_THRESHOLD:
            classification = "TELEPORTATION"
            confidence = "HIGH"
            explanation = "Instantaneous movement >200 u/s suggests teleportation"
        elif speed > self.VERY_LARGE_MOVEMENT_THRESHOLD:
            classification = "HIGH_MOBILITY"
            confidence = "MEDIUM"
            explanation = "Very fast movement >100 u/s, likely mobility ability"
        elif speed > self.LARGE_MOVEMENT_THRESHOLD:
            classification = "MOBILITY_ABILITY"
            confidence = "LOW"
            explanation = "Fast movement >50 u/s, possible mobility ability"
        else:
            classification = "NORMAL"
            confidence = "HIGH"
            explanation = "Normal movement speed"
        
        # Increase confidence if we found known mobility spells
        if any("Fel Rush" in cause or "Heroic Leap" in cause or "Charge" in cause for cause in potential_causes):
            confidence = "HIGH"
        
        return {
            'classification': classification,
            'confidence': confidence,
            'explanation': explanation,
            'supported_by_causes': len(potential_causes) > 0
        }
    
    def extract_outcome_from_filename(self, filename: str) -> str:
        """Extract match outcome from filename."""
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
    
    def run_standard_testing_protocol(self, enhanced_index_csv: str, logs_dir: str):
        """
        Run standard testing protocol: 1 game, then 3 before and 3 after.
        """
        print(f"{'='*80}")
        print(f"STANDARD TESTING PROTOCOL - COMPREHENSIVE MOVEMENT ANALYSIS")
        print(f"Enhanced index: {enhanced_index_csv}")
        print(f"Logs directory: {logs_dir}")
        print(f"{'='*80}")
        
        # Load enhanced index
        try:
            index_df = pd.read_csv(enhanced_index_csv)
            index_df = self.production_parser._clean_timestamps_in_df(index_df)
            index_df = index_df[index_df['precise_start_time'] >= '2025-01-01'].copy()
            index_df = index_df.sort_values('precise_start_time').reset_index(drop=True)
            print(f"Total 2025+ matches available: {len(index_df)}")
        except Exception as e:
            print(f"ERROR: Failed to load enhanced index: {e}")
            return
        
        # Get available combat logs
        log_files = {f.stem: f for f in Path(logs_dir).glob('*.txt')}
        print(f"Available combat logs: {len(log_files)}")
        
        # Find a known working match (with movement data)
        test_matches = []
        
        # First, try to find matches that should have movement data
        # Look for matches from May 2025 (where we know logs exist)
        may_matches = index_df[
            (index_df['precise_start_time'] >= '2025-05-01') & 
            (index_df['precise_start_time'] < '2025-06-01')
        ].copy()
        print(f"May 2025 matches available: {len(may_matches)}")
        
        # Find matches with corresponding logs
        working_matches = []
        for idx, match in may_matches.iterrows():
            match_timestamp = match['precise_start_time']
            
            # Convert to datetime if it's not already
            if hasattr(match_timestamp, 'to_pydatetime'):
                date_obj = match_timestamp.to_pydatetime()
            elif hasattr(match_timestamp, 'strftime'):
                date_obj = match_timestamp
            elif isinstance(match_timestamp, str):
                try:
                    date_obj = datetime.fromisoformat(match_timestamp.replace('Z', '+00:00'))
                except:
                    continue
            else:
                continue
            
            try:
                log_date_format = date_obj.strftime('%m%d%y')
                log_candidates = [f for log_name, f in log_files.items() if log_date_format in log_name]
                
                if log_candidates:
                    working_matches.append((match, log_candidates[0]))
                    if len(working_matches) >= 7:  # 1 + 3 + 3
                        break
            except Exception as e:
                print(f"Error processing match timestamp: {e}")
                continue
        
        if len(working_matches) < 7:
            print(f"WARNING: Only found {len(working_matches)} matches with logs, need 7")
            working_matches = working_matches[:min(len(working_matches), 7)]
        
        print(f"Selected {len(working_matches)} matches for testing")
        
        # Standard protocol: 1 + 3 + 3
        if len(working_matches) >= 1:
            center_match = working_matches[len(working_matches)//2]  # Middle match
            before_matches = working_matches[:len(working_matches)//2]
            after_matches = working_matches[len(working_matches)//2 + 1:]
            
            test_sequence = []
            
            # 1 game (center)
            test_sequence.append(("CENTER", center_match))
            
            # 3 before (up to 3)
            for i, match in enumerate(before_matches[-3:]):  # Last 3 before center
                test_sequence.append((f"BEFORE-{i+1}", match))
            
            # 3 after (up to 3)  
            for i, match in enumerate(after_matches[:3]):  # First 3 after center
                test_sequence.append((f"AFTER-{i+1}", match))
        else:
            print("ERROR: No matches found for testing")
            return
        
        # Run comprehensive analysis on each match
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_matches_tested': len(test_sequence),
            'test_sequence': [],
            'movement_analysis': {},
            'large_movements_summary': {},
            'summary_statistics': {}
        }
        
        for test_type, (match, log_file) in test_sequence:
            print(f"\n{'='*80}")
            print(f"TESTING {test_type}: {match['filename']}")
            print(f"{'='*80}")
            
            # Run comprehensive movement analysis
            analysis = self.analyze_match_movement_comprehensive(log_file, match)
            
            # Store results
            results['test_sequence'].append({
                'test_type': test_type,
                'filename': match['filename'],
                'log_file': log_file.name,
                'analysis_success': 'error' not in analysis
            })
            
            if 'error' not in analysis:
                results['movement_analysis'][match['filename']] = analysis
                
                # Summarize large movements
                if analysis.get('large_movements'):
                    results['large_movements_summary'][match['filename']] = {
                        'count': len(analysis['large_movements']),
                        'max_speed': max(lm['speed'] for lm in analysis['large_movements']),
                        'classifications': [lm['analysis']['classification'] for lm in analysis['large_movements']]
                    }
        
        # Generate summary statistics
        successful_analyses = [a for a in results['movement_analysis'].values() if 'error' not in a]
        
        if successful_analyses:
            results['summary_statistics'] = {
                'successful_matches': len(successful_analyses),
                'total_large_movements': sum(len(a.get('large_movements', [])) for a in successful_analyses),
                'avg_distance_per_match': sum(a['total_distance'] for a in successful_analyses) / len(successful_analyses),
                'avg_speed_per_match': sum(a['average_speed'] for a in successful_analyses) / len(successful_analyses),
                'max_speed_observed': max(a['movement_flags']['max_speed'] for a in successful_analyses),
                'teleportation_events': sum(1 for a in successful_analyses if a['movement_flags']['has_teleport_movements'])
            }
        
        # Save comprehensive results
        output_file = "comprehensive_movement_analysis_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"Matches tested: {len(test_sequence)}")
        print(f"Successful analyses: {len(successful_analyses)}")
        if successful_analyses:
            print(f"Total large movements flagged: {results['summary_statistics']['total_large_movements']}")
            print(f"Average distance per match: {results['summary_statistics']['avg_distance_per_match']:.1f} units")
            print(f"Average speed per match: {results['summary_statistics']['avg_speed_per_match']:.1f} u/s")
            print(f"Maximum speed observed: {results['summary_statistics']['max_speed_observed']:.1f} u/s")
            print(f"Teleportation events: {results['summary_statistics']['teleportation_events']}")
        
        print(f"\nDetailed results saved to: {output_file}")
        
        return results

def main():
    """Run comprehensive movement analysis with standard testing protocol."""
    analyzer = ComprehensiveMovementAnalyzer(".")
    
    # Run standard testing protocol
    analyzer.run_standard_testing_protocol(
        enhanced_index_csv="master_index_enhanced.csv",
        logs_dir="./Logs"
    )

if __name__ == "__main__":
    main()