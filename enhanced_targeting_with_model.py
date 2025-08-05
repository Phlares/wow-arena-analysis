"""
Enhanced Targeting Analysis with Arena Match Model

Uses structured arena match model to provide much more accurate team coordination
and strategic analysis by understanding player roles, team composition, and
targeting context.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from arena_match_model import ArenaMatchModel, ArenaMatchModelBuilder, PlayerInfo, TeamSide
from development_standards import SafeLogger
import pandas as pd


class ModelBasedTargetingAnalyzer:
    """Targeting analyzer that uses arena match model for context"""
    
    def __init__(self, match_model: ArenaMatchModel):
        self.match_model = match_model
        self.targeting_windows = []  # List of time windows with targeting data
        
    def analyze_team_coordination(self, combat_events: List[dict], 
                                 window_size_seconds: int = 3) -> Dict:
        """
        Analyze team coordination using match model context.
        
        Much more accurate than raw event analysis because we know:
        - Who is on which team
        - Player roles and priorities
        - Expected coordination patterns
        """
        SafeLogger.info(f"Analyzing team coordination with {len(combat_events)} events")
        
        if not self.match_model.friendly_team.players:
            SafeLogger.warning("No team composition data available")
            return {'average_coordination': 0.0, 'analysis_available': False}
        
        # Group events by time windows
        time_windows = self._group_events_by_time(combat_events, window_size_seconds)
        SafeLogger.info(f"Created {len(time_windows)} time windows")
        
        coordination_scores = []
        detailed_analysis = []
        
        for window_start, window_events in time_windows:
            window_score = self._analyze_window_coordination(window_events)
            if window_score is not None:
                coordination_scores.append(window_score['score'])
                detailed_analysis.append({
                    'window_start': window_start,
                    'coordination_score': window_score['score'],
                    'coordinated_attacks': window_score['coordinated_attacks'],
                    'total_attacks': window_score['total_attacks'],
                    'primary_target': window_score['primary_target'],
                    'attacking_teammates': window_score['attacking_teammates']
                })
        
        if not coordination_scores:
            SafeLogger.warning("No coordination windows found")
            return {'average_coordination': 0.0, 'analysis_available': False}
        
        average_coordination = sum(coordination_scores) / len(coordination_scores)
        
        SafeLogger.success(f"Team coordination analysis complete: {average_coordination:.3f}")
        SafeLogger.info(f"Analyzed {len(coordination_scores)} coordination windows")
        
        return {
            'average_coordination': average_coordination,
            'analysis_available': True,
            'coordination_windows': len(coordination_scores),
            'detailed_windows': detailed_analysis[:10],  # First 10 for inspection
            'window_size_seconds': window_size_seconds
        }
    
    def _group_events_by_time(self, events: List[dict], 
                            window_size: int) -> List[Tuple[datetime, List[dict]]]:
        """Group combat events into time windows"""
        
        if not events:
            return []
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.get('timestamp', datetime.min))
        
        windows = []
        current_window_start = sorted_events[0]['timestamp']
        current_window_events = []
        
        for event in sorted_events:
            event_time = event['timestamp']
            
            # Check if event is within current window
            if (event_time - current_window_start).total_seconds() <= window_size:
                current_window_events.append(event)
            else:
                # Save current window if it has events
                if current_window_events:
                    windows.append((current_window_start, current_window_events))
                
                # Start new window
                current_window_start = event_time
                current_window_events = [event]
        
        # Add final window
        if current_window_events:
            windows.append((current_window_start, current_window_events))
        
        return windows
    
    def _analyze_window_coordination(self, window_events: List[dict]) -> Optional[Dict]:
        """Analyze coordination within a single time window"""
        
        # Filter to damage/offensive events only
        offensive_events = [
            e for e in window_events 
            if e.get('event_type') in ['SPELL_DAMAGE', 'SWING_DAMAGE', 'SWING_DAMAGE_LANDED', 'RANGE_DAMAGE']
        ]
        
        if len(offensive_events) < 2:
            return None  # Need at least 2 attacks for coordination
        
        # Group attacks by target
        attacks_by_target = defaultdict(list)
        
        for event in offensive_events:
            source_name = event.get('source_name', '')
            dest_name = event.get('dest_name', '')
            
            # Get player objects to understand team context
            source_player = self.match_model.get_player_by_name(source_name.split('-')[0])
            dest_player = self.match_model.get_player_by_name(dest_name.split('-')[0])
            
            # Only count attacks from friendly team to enemy team
            if (source_player and dest_player and 
                source_player.team == TeamSide.FRIENDLY and 
                dest_player.team == TeamSide.ENEMY):
                
                attacks_by_target[dest_name].append({
                    'attacker': source_name,
                    'attacker_player': source_player,
                    'target': dest_name,
                    'target_player': dest_player,
                    'timestamp': event.get('timestamp'),
                    'spell': event.get('spell', 'Unknown')
                })
        
        if not attacks_by_target:
            return None
        
        # Find the most attacked target (primary focus target)
        primary_target = max(attacks_by_target.keys(), key=lambda t: len(attacks_by_target[t]))
        primary_target_attacks = attacks_by_target[primary_target]
        
        # Count unique attackers on primary target with role-based weighting
        unique_attackers = set(attack['attacker'] for attack in primary_target_attacks)
        
        # Calculate weighted coordination score (DPS coordination weighted double vs healer)
        coordination_weight = 0.0
        total_possible_weight = 0.0
        
        for player in self.match_model.friendly_team.players:
            # Calculate possible weight for this player
            if player.role.value == 'Healer':
                player_weight = 1.0  # Healers count as 1.0 (they may CC/heal instead of damage)
            else:
                player_weight = 2.0  # DPS count as 2.0 (damage coordination is priority)
            
            total_possible_weight += player_weight
            
            # Check if this player participated in primary target focus
            player_attacking = any(
                attack['attacker_player'].name == player.name 
                for attack in primary_target_attacks
            )
            
            if player_attacking:
                coordination_weight += player_weight
        
        # Calculate weighted coordination score
        coordination_score = coordination_weight / max(total_possible_weight, 1) if total_possible_weight > 0 else 0
        
        # Count total coordinated attacks (multiple people hitting same target)
        coordinated_attacks = sum(
            len(attacks) for target, attacks in attacks_by_target.items() 
            if len(set(attack['attacker'] for attack in attacks)) > 1
        )
        
        total_attacks = sum(len(attacks) for attacks in attacks_by_target.values())
        
        return {
            'score': coordination_score,
            'coordinated_attacks': coordinated_attacks,
            'total_attacks': total_attacks,
            'primary_target': primary_target,
            'attacking_teammates': list(unique_attackers),
            'attacks_breakdown': dict(attacks_by_target),
            'weighted_coordination': True,
            'coordination_weight_achieved': coordination_weight,
            'total_possible_weight': total_possible_weight,
            'dps_weight_multiplier': 2.0,
            'healer_weight_multiplier': 1.0
        }
    
    def analyze_target_prioritization(self, combat_events: List[dict]) -> Dict:
        """Analyze target prioritization patterns using match model"""
        
        SafeLogger.info("Analyzing target prioritization patterns")
        
        # Count attacks on each enemy player
        enemy_attack_counts = Counter()
        role_attack_counts = defaultdict(int)
        
        for event in combat_events:
            if event.get('event_type') not in ['SPELL_DAMAGE', 'SWING_DAMAGE', 'SWING_DAMAGE_LANDED']:
                continue
            
            source_name = event.get('source_name', '').split('-')[0]
            dest_name = event.get('dest_name', '').split('-')[0]
            
            source_player = self.match_model.get_player_by_name(source_name)
            dest_player = self.match_model.get_player_by_name(dest_name)
            
            # Count attacks from friendly to enemy
            if (source_player and dest_player and
                source_player.team == TeamSide.FRIENDLY and 
                dest_player.team == TeamSide.ENEMY):
                
                enemy_attack_counts[dest_name] += 1
                role_attack_counts[dest_player.role.value] += 1
        
        if not enemy_attack_counts:
            return {'prioritization_analysis': 'No targeting data available'}
        
        # Analyze prioritization patterns
        most_targeted = enemy_attack_counts.most_common()
        
        # Calculate if healer-first strategy was used
        healer_attacks = role_attack_counts.get('Healer', 0)
        total_attacks = sum(enemy_attack_counts.values())
        healer_focus_ratio = healer_attacks / max(total_attacks, 1)
        
        return {
            'target_priority_ranking': most_targeted,
            'role_attack_distribution': dict(role_attack_counts),
            'healer_focus_ratio': healer_focus_ratio,
            'total_attacks_analyzed': total_attacks,
            'prioritization_strategy': self._infer_strategy(most_targeted, role_attack_counts)
        }
    
    def _infer_strategy(self, target_ranking: List[Tuple[str, int]], 
                       role_attacks: Dict[str, int]) -> str:
        """Infer the targeting strategy used"""
        
        if not target_ranking:
            return "No clear strategy"
        
        healer_attacks = role_attacks.get('Healer', 0)
        total_attacks = sum(role_attacks.values())
        
        if healer_attacks / max(total_attacks, 1) > 0.6:
            return "Healer Focus"
        elif role_attacks.get('Ranged DPS', 0) > role_attacks.get('Melee DPS', 0):
            return "Ranged Priority"
        else:
            return "Balanced Targeting"


def create_match_model_from_index(filename: str, master_index_path: str = "master_index_enhanced.csv") -> Optional[ArenaMatchModel]:
    """Create match model from master index data"""
    
    try:
        master_df = pd.read_csv(master_index_path)
        match_row = master_df[master_df['filename'] == filename]
        
        if match_row.empty:
            SafeLogger.error(f"Match {filename} not found in master index")
            return None
        
        row_data = match_row.iloc[0].to_dict()
        return ArenaMatchModelBuilder.from_master_index_row(row_data)
        
    except Exception as e:
        SafeLogger.error(f"Error creating match model: {e}")
        return None


def enhanced_targeting_analysis_with_model(combat_events: List[dict], 
                                         match_filename: str) -> Dict:
    """
    Run enhanced targeting analysis using arena match model.
    
    This provides much more accurate results than raw event analysis because
    it understands team composition, player roles, and targeting context.
    """
    
    SafeLogger.info(f"Running model-based targeting analysis for {match_filename}")
    
    # Create match model
    match_model = create_match_model_from_index(match_filename)
    if not match_model:
        return {
            'analysis_available': False,
            'error': 'Could not create match model'
        }
    
    SafeLogger.info(f"Match model created: {match_model.match_summary}")
    
    # TODO: Extract player information from combat events to populate the model
    # For now, we'll work with the basic structure
    
    # Run model-based analysis
    analyzer = ModelBasedTargetingAnalyzer(match_model)
    
    # Analyze team coordination
    coordination_analysis = analyzer.analyze_team_coordination(combat_events)
    
    # Analyze target prioritization
    prioritization_analysis = analyzer.analyze_target_prioritization(combat_events)
    
    return {
        'analysis_available': True,
        'match_model': {
            'arena_size': match_model.arena_size.value,
            'arena_map': match_model.arena_map,
            'primary_player': match_model.primary_player,
            'total_players': match_model.total_players
        },
        'team_coordination': coordination_analysis,
        'target_prioritization': prioritization_analysis,
        'model_based_analysis': True
    }


if __name__ == "__main__":
    # Test the enhanced targeting analysis
    SafeLogger.info("Testing Enhanced Targeting Analysis with Match Model")
    
    # Create sample combat events (this would come from real log parsing)
    sample_events = [
        {
            'timestamp': datetime(2025, 5, 6, 22, 19, 4),
            'event_type': 'SPELL_DAMAGE',
            'source_name': 'Phlargus-Eredar-US',
            'dest_name': 'Zlr-BleedingHollow-US',
            'spell': 'Chaos Bolt'
        },
        {
            'timestamp': datetime(2025, 5, 6, 22, 19, 5),
            'event_type': 'SPELL_DAMAGE', 
            'source_name': 'Melonha-Tichondrius-US',
            'dest_name': 'Zlr-BleedingHollow-US',
            'spell': 'Tiger Palm'
        }
    ]
    
    # Test with a real match filename
    result = enhanced_targeting_analysis_with_model(
        sample_events, 
        "2025-05-06_22-11-04_-_Phlargus_-_3v3_Ruins_of_Lordaeron_(Win).mp4"
    )
    
    SafeLogger.info(f"Analysis result: {result.get('analysis_available', False)}")
    if result.get('team_coordination'):
        coord = result['team_coordination'].get('average_coordination', 0)
        SafeLogger.info(f"Team coordination: {coord:.3f}")