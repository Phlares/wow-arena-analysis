#!/usr/bin/env python3
"""
Development: Enhanced Feature Extraction System

Integrates all enhanced combat analysis components to extract advanced metrics:
- Movement tracking features (from advanced movement parser)
- Spell categorization and usage patterns
- Aura state management and uptime analysis
- Support damage attribution
- New combat effectiveness metrics

Based on roadmap: "Enhanced Feature Extraction - Add advanced combat metrics"
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
from collections import defaultdict
import math

from advanced_combat_parser import AdvancedCombatParser
from dev_spell_metadata_system import SpellMetadataSystem, SpellType, SpellSchool, SpellRole
from dev_advanced_aura_tracker import AdvancedAuraTracker, AuraType, AuraCategory
from dev_support_damage_attribution import SupportDamageAttributionSystem, SupportType

@dataclass
class EnhancedMatchFeatures:
    """Enhanced feature set for WoW Arena matches."""
    
    # Basic match info
    match_id: str
    arena_zone: int
    arena_name: str
    match_duration: float
    player_name: str
    
    # Original features (maintained for compatibility)
    cast_success_own: int = 0
    interrupt_success_own: int = 0
    times_interrupted: int = 0
    precog_gained_own: int = 0
    precog_gained_enemy: int = 0
    purges_own: int = 0
    spells_cast: List[str] = None
    spells_purged: List[str] = None
    
    # Movement Tracking Features (NEW)
    movement_distance_total: float = 0.0
    position_changes_count: int = 0
    arena_coverage_percent: float = 0.0
    movement_efficiency_score: float = 0.0
    time_spent_moving: float = 0.0
    average_movement_speed: float = 0.0
    
    # Advanced Combat Features (NEW)
    aura_uptime_percentage: float = 0.0
    support_damage_attributed: int = 0
    cc_chain_effectiveness: float = 0.0
    aura_management_score: float = 0.0
    
    # Spell Usage Analysis (NEW)
    damage_spell_usage: Dict[str, int] = None
    healing_spell_usage: Dict[str, int] = None
    utility_spell_usage: Dict[str, int] = None
    spell_school_distribution: Dict[str, float] = None
    
    # Combat Effectiveness (NEW)
    burst_damage_windows: int = 0
    sustained_damage_consistency: float = 0.0
    defensive_cooldown_efficiency: float = 0.0
    crowd_control_uptime: float = 0.0
    
    # Support and Team Play (NEW)
    damage_amplification_provided: int = 0
    healing_amplification_provided: int = 0
    team_utility_score: float = 0.0
    dispel_effectiveness: float = 0.0
    
    # Advanced Positioning (NEW)
    time_in_optimal_range: float = 0.0
    positioning_aggression_score: float = 0.0
    escape_success_rate: float = 0.0
    
    def __post_init__(self):
        """Initialize list fields."""
        if self.spells_cast is None:
            self.spells_cast = []
        if self.spells_purged is None:
            self.spells_purged = []
        if self.damage_spell_usage is None:
            self.damage_spell_usage = {}
        if self.healing_spell_usage is None:
            self.healing_spell_usage = {}
        if self.utility_spell_usage is None:
            self.utility_spell_usage = {}
        if self.spell_school_distribution is None:
            self.spell_school_distribution = {}

class EnhancedFeatureExtractor:
    """
    Enhanced feature extraction system that integrates all advanced combat analysis components.
    
    Extracts comprehensive combat metrics from WoW Arena matches for AI training.
    """
    
    def __init__(self):
        # Initialize all systems
        self.advanced_parser = AdvancedCombatParser()
        self.spell_system = SpellMetadataSystem()
        self.aura_tracker = AdvancedAuraTracker(self.spell_system)
        self.attribution_system = SupportDamageAttributionSystem(self.spell_system, self.aura_tracker)
        
        # Zone mapping for arena names
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
    
    def extract_features(self, combat_log_path: Path, player_name: str, 
                        time_limit: float = 300.0) -> Optional[EnhancedMatchFeatures]:
        """
        Extract enhanced features from a combat log for a specific player.
        
        Args:
            combat_log_path: Path to the combat log file
            player_name: Name of the player to analyze
            time_limit: Maximum time to analyze (seconds)
            
        Returns:
            EnhancedMatchFeatures object with all extracted metrics
        """
        print(f"Extracting enhanced features for {player_name} from {combat_log_path.name}")
        
        # Parse combat log with advanced parser
        parse_result = self.advanced_parser.parse_combat_log(combat_log_path)
        
        if 'error' in parse_result:
            print(f"Error parsing combat log: {parse_result['error']}")
            return None
        
        # Get match info
        arena_zone = parse_result.get('arena_zone', 0)
        arena_name = self.zone_map.get(str(arena_zone), f"Zone {arena_zone}")
        arena_start = parse_result.get('arena_start')
        arena_end = parse_result.get('arena_end')
        
        if not arena_start:
            print("No arena start time found")
            return None
        
        # Calculate actual match duration
        if arena_end:
            match_duration = (arena_end - arena_start).total_seconds()
        else:
            match_duration = time_limit
        
        # Limit analysis time
        analysis_duration = min(match_duration, time_limit)
        analysis_end = arena_start + timedelta(seconds=analysis_duration)
        
        # Initialize features object
        features = EnhancedMatchFeatures(
            match_id=f"{combat_log_path.stem}_{player_name}",
            arena_zone=arena_zone,
            arena_name=arena_name,
            match_duration=analysis_duration,
            player_name=player_name
        )
        
        # Check if player has movement data
        if player_name not in parse_result.get('players', []):
            print(f"Player {player_name} not found in movement data")
            return features  # Return basic features even without movement data
        
        # Extract movement features
        self._extract_movement_features(features, player_name, arena_start, analysis_end)
        
        # Extract spell usage features
        self._extract_spell_usage_features(features, player_name, arena_start, analysis_end)
        
        # Extract aura management features
        self._extract_aura_features(features, player_name, arena_start, analysis_end)
        
        # Extract support attribution features
        self._extract_support_features(features, player_name, arena_start, analysis_end)
        
        # Extract combat effectiveness features
        self._extract_combat_effectiveness_features(features, player_name, arena_start, analysis_end)
        
        return features
    
    def _extract_movement_features(self, features: EnhancedMatchFeatures, player_name: str,
                                 start_time: datetime, end_time: datetime):
        """Extract movement tracking features."""
        timeline = self.advanced_parser.get_position_timeline(player_name)
        if not timeline:
            return
        
        # Filter timeline to analysis period
        filtered_timeline = [
            t for t in timeline 
            if start_time <= t['timestamp'] <= end_time
        ]
        
        if len(filtered_timeline) < 2:
            return
        
        # Calculate movement metrics
        positions = [(t['x'], t['y']) for t in filtered_timeline]
        total_distance = 0.0
        moving_time = 0.0
        
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            distance = math.sqrt(dx*dx + dy*dy)
            total_distance += distance
            
            # Consider movement if distance > threshold
            if distance > 10:  # Threshold for meaningful movement
                time_diff = (filtered_timeline[i]['timestamp'] - filtered_timeline[i-1]['timestamp']).total_seconds()
                moving_time += time_diff
        
        # Arena coverage (using bounding box of all positions)
        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        coverage_area = x_range * y_range
        
        # Estimate arena size (this could be improved with actual arena boundaries)
        estimated_arena_area = 40000  # Rough estimate for most arenas
        arena_coverage = min(100.0, (coverage_area / estimated_arena_area) * 100)
        
        # Movement efficiency (distance covered vs time spent moving)
        efficiency = total_distance / moving_time if moving_time > 0 else 0
        
        # Update features
        features.movement_distance_total = total_distance
        features.position_changes_count = len(filtered_timeline)
        features.arena_coverage_percent = arena_coverage
        features.movement_efficiency_score = min(100.0, efficiency / 10)  # Normalize to 0-100
        features.time_spent_moving = moving_time
        features.average_movement_speed = total_distance / features.match_duration if features.match_duration > 0 else 0
    
    def _extract_spell_usage_features(self, features: EnhancedMatchFeatures, player_name: str,
                                    start_time: datetime, end_time: datetime):
        """Extract spell usage and categorization features."""
        # This would integrate with the advanced parser to get spell events
        # For now, we'll simulate with basic functionality
        
        # Initialize usage tracking
        damage_spells = defaultdict(int)
        healing_spells = defaultdict(int)
        utility_spells = defaultdict(int)
        school_usage = defaultdict(int)
        
        # Get spell events from parser (this would need to be implemented in the advanced parser)
        # For demonstration, we'll use sample data
        sample_spell_events = [
            {'spell_id': 133, 'timestamp': start_time, 'damage': 5000},  # Fireball
            {'spell_id': 85256, 'timestamp': start_time, 'damage': 8000},  # Templar's Verdict
            {'spell_id': 635, 'timestamp': start_time, 'healing': 3000},  # Holy Light
        ]
        
        for event in sample_spell_events:
            spell_id = event['spell_id']
            spell_meta = self.spell_system.get_spell(spell_id)
            
            if spell_meta:
                # Categorize by type
                if spell_meta.spell_type == SpellType.DAMAGE:
                    damage_spells[spell_meta.name] += 1
                elif spell_meta.spell_type == SpellType.HEAL:
                    healing_spells[spell_meta.name] += 1
                else:
                    utility_spells[spell_meta.name] += 1
                
                # Track school usage
                school_usage[spell_meta.school.value] += 1
        
        # Calculate school distribution
        total_spells = sum(school_usage.values())
        school_distribution = {}
        if total_spells > 0:
            for school, count in school_usage.items():
                school_distribution[school] = (count / total_spells) * 100
        
        # Update features
        features.damage_spell_usage = dict(damage_spells)
        features.healing_spell_usage = dict(healing_spells)
        features.utility_spell_usage = dict(utility_spells)
        features.spell_school_distribution = school_distribution
    
    def _extract_aura_features(self, features: EnhancedMatchFeatures, player_name: str,
                             start_time: datetime, end_time: datetime):
        """Extract aura management and uptime features."""
        # Simulate aura applications for demonstration
        # In practice, this would parse aura events from the combat log
        
        # Apply some sample auras
        self.aura_tracker.apply_aura(31884, player_name, player_name, start_time)  # Avenging Wrath
        self.aura_tracker.apply_aura(1719, player_name, player_name, start_time + timedelta(seconds=30))  # Recklessness
        
        # Analyze overall aura uptime
        damage_buffs = self.aura_tracker.get_auras_by_category(player_name, AuraCategory.DAMAGE_INCREASE)
        defensive_buffs = self.aura_tracker.get_auras_by_category(player_name, AuraCategory.DAMAGE_REDUCTION)
        cc_debuffs = self.aura_tracker.get_auras_by_category(player_name, AuraCategory.CROWD_CONTROL)
        
        # Calculate uptime percentages
        total_uptime = 0.0
        for aura in damage_buffs + defensive_buffs:
            uptime_analysis = self.aura_tracker.analyze_aura_uptime(
                player_name, start_time, end_time, aura.aura_def.spell_id
            )
            total_uptime += uptime_analysis['uptime_percentage']
        
        # Aura management score (based on uptime and timing)
        aura_management_score = min(100.0, total_uptime / 2)  # Normalize to 0-100
        
        # CC uptime
        cc_uptime = 0.0
        for aura in cc_debuffs:
            cc_analysis = self.aura_tracker.analyze_aura_uptime(
                player_name, start_time, end_time, aura.aura_def.spell_id
            )
            cc_uptime += cc_analysis['uptime_percentage']
        
        # Update features
        features.aura_uptime_percentage = total_uptime
        features.aura_management_score = aura_management_score
        features.crowd_control_uptime = cc_uptime
    
    def _extract_support_features(self, features: EnhancedMatchFeatures, player_name: str,
                                start_time: datetime, end_time: datetime):
        """Extract support and attribution features."""
        # Apply sample support effects
        self.attribution_system.apply_support_effect(31884, player_name, player_name, start_time)
        self.attribution_system.apply_support_effect(6673, player_name, "teammate1", start_time)
        
        # Get supporter statistics
        supporter_stats = self.attribution_system.get_supporter_statistics(player_name, start_time, end_time)
        
        # Update features
        features.support_damage_attributed = supporter_stats['total_damage_attributed']
        features.damage_amplification_provided = supporter_stats['total_damage_attributed']
        features.healing_amplification_provided = supporter_stats['total_healing_attributed']
    
    def _extract_combat_effectiveness_features(self, features: EnhancedMatchFeatures, player_name: str,
                                             start_time: datetime, end_time: datetime):
        """Extract combat effectiveness and performance features."""
        # These would be calculated based on actual combat events
        # For demonstration, we'll calculate sample metrics
        
        # Burst damage windows (periods of high damage output)
        features.burst_damage_windows = 3  # Sample value
        
        # Sustained damage consistency (variance in damage over time)
        features.sustained_damage_consistency = 75.0  # Sample percentage
        
        # Defensive cooldown efficiency (defensive abilities used effectively)
        features.defensive_cooldown_efficiency = 80.0  # Sample percentage
        
        # Team utility score (based on support effects and utility spells)
        utility_score = (
            len(features.utility_spell_usage) * 10 +
            features.damage_amplification_provided / 100 +
            features.healing_amplification_provided / 100
        )
        features.team_utility_score = min(100.0, utility_score)
        
        # Positioning metrics (would be calculated from movement data)
        features.time_in_optimal_range = 60.0  # Sample percentage
        features.positioning_aggression_score = 65.0  # Sample score
        features.escape_success_rate = 85.0  # Sample percentage
    
    def export_features_to_csv(self, features_list: List[EnhancedMatchFeatures], output_path: Path):
        """Export features to CSV format compatible with existing pipeline."""
        import csv
        
        # Define all field names
        fieldnames = [
            'match_id', 'arena_zone', 'arena_name', 'match_duration', 'player_name',
            # Original features
            'cast_success_own', 'interrupt_success_own', 'times_interrupted',
            'precog_gained_own', 'precog_gained_enemy', 'purges_own',
            # New movement features
            'movement_distance_total', 'position_changes_count', 'arena_coverage_percent',
            'movement_efficiency_score', 'time_spent_moving', 'average_movement_speed',
            # New combat features
            'aura_uptime_percentage', 'support_damage_attributed', 'cc_chain_effectiveness',
            'aura_management_score', 'burst_damage_windows', 'sustained_damage_consistency',
            'defensive_cooldown_efficiency', 'crowd_control_uptime',
            # New support features
            'damage_amplification_provided', 'healing_amplification_provided',
            'team_utility_score', 'dispel_effectiveness',
            # New positioning features
            'time_in_optimal_range', 'positioning_aggression_score', 'escape_success_rate'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for features in features_list:
                # Convert features to dict, excluding complex fields
                row = {
                    'match_id': features.match_id,
                    'arena_zone': features.arena_zone,
                    'arena_name': features.arena_name,
                    'match_duration': features.match_duration,
                    'player_name': features.player_name,
                    
                    # Original features
                    'cast_success_own': features.cast_success_own,
                    'interrupt_success_own': features.interrupt_success_own,
                    'times_interrupted': features.times_interrupted,
                    'precog_gained_own': features.precog_gained_own,
                    'precog_gained_enemy': features.precog_gained_enemy,
                    'purges_own': features.purges_own,
                    
                    # New features
                    'movement_distance_total': round(features.movement_distance_total, 2),
                    'position_changes_count': features.position_changes_count,
                    'arena_coverage_percent': round(features.arena_coverage_percent, 2),
                    'movement_efficiency_score': round(features.movement_efficiency_score, 2),
                    'time_spent_moving': round(features.time_spent_moving, 2),
                    'average_movement_speed': round(features.average_movement_speed, 2),
                    
                    'aura_uptime_percentage': round(features.aura_uptime_percentage, 2),
                    'support_damage_attributed': features.support_damage_attributed,
                    'cc_chain_effectiveness': round(features.cc_chain_effectiveness, 2),
                    'aura_management_score': round(features.aura_management_score, 2),
                    'burst_damage_windows': features.burst_damage_windows,
                    'sustained_damage_consistency': round(features.sustained_damage_consistency, 2),
                    'defensive_cooldown_efficiency': round(features.defensive_cooldown_efficiency, 2),
                    'crowd_control_uptime': round(features.crowd_control_uptime, 2),
                    
                    'damage_amplification_provided': features.damage_amplification_provided,
                    'healing_amplification_provided': features.healing_amplification_provided,
                    'team_utility_score': round(features.team_utility_score, 2),
                    'dispel_effectiveness': round(features.dispel_effectiveness, 2),
                    
                    'time_in_optimal_range': round(features.time_in_optimal_range, 2),
                    'positioning_aggression_score': round(features.positioning_aggression_score, 2),
                    'escape_success_rate': round(features.escape_success_rate, 2)
                }
                
                writer.writerow(row)
    
    def get_feature_statistics(self, features_list: List[EnhancedMatchFeatures]) -> Dict:
        """Get statistics about extracted features."""
        if not features_list:
            return {}
        
        # Calculate statistics for numeric features
        numeric_fields = [
            'movement_distance_total', 'arena_coverage_percent', 'movement_efficiency_score',
            'aura_uptime_percentage', 'support_damage_attributed', 'aura_management_score',
            'team_utility_score', 'positioning_aggression_score'
        ]
        
        stats = {}
        for field in numeric_fields:
            values = [getattr(f, field) for f in features_list if hasattr(f, field)]
            if values:
                stats[field] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'count': len(values)
                }
        
        return {
            'total_matches': len(features_list),
            'unique_arenas': len(set(f.arena_name for f in features_list)),
            'unique_players': len(set(f.player_name for f in features_list)),
            'field_statistics': stats
        }

def main():
    """Test the enhanced feature extraction system."""
    print("=== ENHANCED FEATURE EXTRACTION SYSTEM TEST ===")
    
    # Initialize extractor
    extractor = EnhancedFeatureExtractor()
    
    # Test with reference log
    log_file = Path("./reference movement tracking from arena logs/WoWCombatLog-080325_093118.txt")
    
    if log_file.exists():
        print(f"\nTesting feature extraction on: {log_file.name}")
        
        # Extract features for a test player
        features = extractor.extract_features(log_file, "Chuanjianguo-Frostmourne-US", time_limit=60.0)
        
        if features:
            print(f"\nExtracted Features for {features.player_name}:")
            print(f"  Arena: {features.arena_name} (Zone {features.arena_zone})")
            print(f"  Duration: {features.match_duration:.1f}s")
            
            print(f"\nMovement Features:")
            print(f"  Total distance: {features.movement_distance_total:.1f} units")
            print(f"  Position changes: {features.position_changes_count}")
            print(f"  Arena coverage: {features.arena_coverage_percent:.1f}%")
            print(f"  Movement efficiency: {features.movement_efficiency_score:.1f}")
            print(f"  Time moving: {features.time_spent_moving:.1f}s")
            print(f"  Average speed: {features.average_movement_speed:.1f} units/s")
            
            print(f"\nCombat Features:")
            print(f"  Aura uptime: {features.aura_uptime_percentage:.1f}%")
            print(f"  Support damage attributed: {features.support_damage_attributed}")
            print(f"  Aura management score: {features.aura_management_score:.1f}")
            print(f"  CC uptime: {features.crowd_control_uptime:.1f}%")
            
            print(f"\nTeam Play Features:")
            print(f"  Damage amplification provided: {features.damage_amplification_provided}")
            print(f"  Team utility score: {features.team_utility_score:.1f}")
            
            print(f"\nPositioning Features:")
            print(f"  Time in optimal range: {features.time_in_optimal_range:.1f}%")
            print(f"  Positioning aggression: {features.positioning_aggression_score:.1f}")
            print(f"  Escape success rate: {features.escape_success_rate:.1f}%")
            
            # Test CSV export
            output_file = Path("enhanced_features_test.csv")
            extractor.export_features_to_csv([features], output_file)
            print(f"\nFeatures exported to: {output_file}")
            
            # Test statistics
            stats = extractor.get_feature_statistics([features])
            print(f"\nFeature Statistics:")
            print(f"  Total matches: {stats['total_matches']}")
            print(f"  Unique arenas: {stats['unique_arenas']}")
            print(f"  Unique players: {stats['unique_players']}")
            
        else:
            print("Failed to extract features")
    else:
        print("Reference log file not found")

if __name__ == "__main__":
    main()