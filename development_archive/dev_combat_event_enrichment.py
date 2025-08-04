#!/usr/bin/env python3
"""
Development: Combat Event Enrichment System

Adds context and metadata to combat events for enhanced analysis.
Enriches combat log events with spell metadata, aura context, positioning data,
and tactical significance scoring.

Based on roadmap: "Combat Event Enrichment - Add context and metadata to events"
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import json
from pathlib import Path

from advanced_combat_parser import AdvancedCombatParser, AdvancedCombatAction
from dev_spell_metadata_system import SpellMetadataSystem, SpellType, SpellSchool, SpellRole
from dev_advanced_aura_tracker import AdvancedAuraTracker, AuraType, AuraCategory
from dev_support_damage_attribution import SupportDamageAttributionSystem

class EventSignificance(Enum):
    """Tactical significance levels for combat events."""
    CRITICAL = "Critical"      # Game-changing events (kills, major cooldowns)
    HIGH = "High"             # Important tactical events (CC, major damage)
    MEDIUM = "Medium"         # Standard combat events (regular abilities)
    LOW = "Low"              # Minor events (auto-attacks, movement)
    
class EventContext(Enum):
    """Context categories for combat events."""
    OPENING = "Opening"       # Match opening (first 15 seconds)
    BURST = "Burst"          # Burst damage windows
    PRESSURE = "Pressure"    # Sustained pressure phases
    DEFENSIVE = "Defensive"   # Defensive/survival phases
    RESET = "Reset"          # Reset/disengagement phases
    CLOSING = "Closing"      # Match closing/decisive moments

@dataclass
class EnrichedCombatEvent:
    """Enriched combat event with full context and metadata."""
    # Original event data
    timestamp: datetime
    event_type: str
    source_id: str
    target_id: str
    spell_id: int = 0
    damage: int = 0
    healing: int = 0
    
    # Spell metadata enrichment
    spell_name: str = ""
    spell_school: str = ""
    spell_type: str = ""
    spell_role: str = ""
    spell_tags: Set[str] = field(default_factory=set)
    
    # Positional context
    source_position: Optional[Dict[str, float]] = None
    target_position: Optional[Dict[str, float]] = None
    distance: float = 0.0
    in_optimal_range: bool = False
    
    # Aura context
    source_active_auras: List[str] = field(default_factory=list)
    target_active_auras: List[str] = field(default_factory=list)
    damage_modifiers: Dict[str, float] = field(default_factory=dict)
    
    # Support attribution
    support_contribution: int = 0
    support_effects: List[str] = field(default_factory=list)
    
    # Tactical context
    significance: EventSignificance = EventSignificance.MEDIUM
    context: EventContext = EventContext.PRESSURE
    tactical_score: float = 0.0
    
    # Additional metadata
    is_critical_hit: bool = False
    is_killing_blow: bool = False
    breaks_cc: bool = False
    enables_follow_up: bool = False
    
    # Sequence analysis
    combo_position: int = 0  # Position in a spell sequence (0 = standalone)
    preceded_by: List[str] = field(default_factory=list)
    followed_by: List[str] = field(default_factory=list)

class CombatEventEnrichmentSystem:
    """
    System for enriching combat events with comprehensive context and metadata.
    
    Transforms raw combat log events into rich, analyzable data points with
    tactical significance, positional context, and spell metadata.
    """
    
    def __init__(self, spell_system: SpellMetadataSystem, aura_tracker: AdvancedAuraTracker,
                 attribution_system: SupportDamageAttributionSystem, advanced_parser: AdvancedCombatParser):
        self.spell_system = spell_system
        self.aura_tracker = aura_tracker
        self.attribution_system = attribution_system
        self.advanced_parser = advanced_parser
        
        # Event tracking
        self.enriched_events: List[EnrichedCombatEvent] = []
        self.event_sequences: Dict[str, List[EnrichedCombatEvent]] = {}  # player_id -> events
        
        # Context tracking
        self.match_phases: List[Dict] = []
        self.burst_windows: List[Dict] = []
        self.defensive_phases: List[Dict] = []
        
        # Configuration
        self.optimal_ranges = {
            "melee": 5.0,
            "ranged": 30.0,
            "caster": 35.0
        }
    
    def enrich_combat_events(self, combat_log_path: Path, start_time: datetime, 
                           end_time: datetime) -> List[EnrichedCombatEvent]:
        """
        Enrich all combat events from a combat log within the specified time range.
        
        Args:
            combat_log_path: Path to the combat log file
            start_time: Start time for event enrichment
            end_time: End time for event enrichment
            
        Returns:
            List of enriched combat events
        """
        print(f"Enriching combat events from {combat_log_path.name}")
        print(f"Time range: {start_time} to {end_time}")
        
        # Parse combat log
        parse_result = self.advanced_parser.parse_combat_log(combat_log_path, start_time, end_time)
        
        if 'error' in parse_result:
            print(f"Error parsing combat log: {parse_result['error']}")
            return []
        
        # Get all advanced actions
        advanced_actions = parse_result.get('actions', [])
        print(f"Processing {len(advanced_actions)} advanced actions")
        
        # Detect match phases
        self._analyze_match_phases(advanced_actions, start_time, end_time)
        
        # Enrich each event
        enriched_events = []
        for action in advanced_actions:
            enriched_event = self._enrich_single_event(action, start_time, end_time)
            if enriched_event:
                enriched_events.append(enriched_event)
        
        # Perform sequence analysis
        self._analyze_event_sequences(enriched_events)
        
        # Calculate tactical significance
        self._calculate_tactical_significance(enriched_events)
        
        self.enriched_events = enriched_events
        return enriched_events
    
    def _enrich_single_event(self, action: AdvancedCombatAction, start_time: datetime, 
                           end_time: datetime) -> Optional[EnrichedCombatEvent]:
        """Enrich a single combat event with all available context."""
        
        # Extract basic event data
        event = EnrichedCombatEvent(
            timestamp=action.timestamp,
            event_type=action.event,
            source_id=action.get_player_name(),
            target_id="",  # Would need to extract from raw log
            spell_id=0     # Would need to extract from raw log
        )
        
        # Add spell metadata if available
        if event.spell_id:
            self._add_spell_metadata(event, event.spell_id)
        
        # Add positional context
        self._add_positional_context(event, action)
        
        # Add aura context
        self._add_aura_context(event, action.timestamp)
        
        # Add support attribution
        self._add_support_attribution(event)
        
        # Determine match context
        self._determine_match_context(event, start_time, end_time)
        
        return event
    
    def _add_spell_metadata(self, event: EnrichedCombatEvent, spell_id: int):
        """Add spell metadata to an event."""
        spell_meta = self.spell_system.get_spell(spell_id)
        if spell_meta:
            event.spell_name = spell_meta.name
            event.spell_school = spell_meta.school.value
            event.spell_type = spell_meta.spell_type.value
            event.spell_role = spell_meta.role.value
            event.spell_tags = spell_meta.tags.copy()
    
    def _add_positional_context(self, event: EnrichedCombatEvent, action: AdvancedCombatAction):
        """Add positional context to an event."""
        if action.is_valid_position():
            event.source_position = {
                'x': action.advanced_actor_position_x,
                'y': action.advanced_actor_position_y,
                'facing': action.advanced_actor_facing
            }
            
            # Determine if in optimal range (would need target position for full calculation)
            # For now, we'll use a heuristic based on spell type
            if "ranged" in event.spell_tags:
                event.in_optimal_range = True  # Assume ranged spells are used at optimal range
            elif "melee" in event.spell_tags:
                event.in_optimal_range = True  # Assume melee spells are used at optimal range
    
    def _add_aura_context(self, event: EnrichedCombatEvent, timestamp: datetime):
        """Add aura context to an event."""
        # Get active auras on source
        source_auras = self.aura_tracker.get_active_auras(event.source_id, timestamp)
        event.source_active_auras = [aura.aura_def.name for aura in source_auras]
        
        # Get damage modifiers
        modifiers = self.aura_tracker.get_damage_modifiers(event.source_id, timestamp)
        event.damage_modifiers = modifiers
        
        # Check if event breaks CC
        if event.damage > 0:
            broken_auras = self.aura_tracker.break_auras_on_damage(event.target_id, timestamp)
            event.breaks_cc = len(broken_auras) > 0
    
    def _add_support_attribution(self, event: EnrichedCombatEvent):
        """Add support attribution to damage/healing events."""
        if event.damage > 0:
            attribution = self.attribution_system.calculate_damage_attribution(
                event.source_id, event.spell_id, event.damage, event.damage, event.timestamp
            )
            event.support_contribution = attribution['total_attribution']
            event.support_effects = [contrib['spell_name'] for contrib in attribution['support_contributions']]
        
        elif event.healing > 0:
            attribution = self.attribution_system.calculate_healing_attribution(
                event.source_id, event.spell_id, event.healing, event.healing, event.timestamp
            )
            event.support_contribution = attribution['total_attribution']
            event.support_effects = [contrib['spell_name'] for contrib in attribution['support_contributions']]
    
    def _determine_match_context(self, event: EnrichedCombatEvent, start_time: datetime, end_time: datetime):
        """Determine the match context for an event."""
        elapsed_time = (event.timestamp - start_time).total_seconds()
        total_time = (end_time - start_time).total_seconds()
        
        # Determine context based on time and event characteristics
        if elapsed_time < 15:
            event.context = EventContext.OPENING
        elif elapsed_time > total_time * 0.8:
            event.context = EventContext.CLOSING
        elif event.spell_role == SpellRole.DPS_BURST.value:
            event.context = EventContext.BURST
        elif event.spell_role == SpellRole.TANK_SURVIVAL.value or "defensive" in event.spell_tags:
            event.context = EventContext.DEFENSIVE
        else:
            event.context = EventContext.PRESSURE
    
    def _analyze_match_phases(self, actions: List[AdvancedCombatAction], start_time: datetime, end_time: datetime):
        """Analyze match phases for context determination."""
        # Detect burst windows (periods of high damage output)
        damage_timeline = []
        current_window = {'start': start_time, 'damage': 0, 'events': 0}
        
        for action in actions:
            # This would analyze damage events to detect burst windows
            # For now, we'll create sample phases
            pass
        
        # Create sample phases for demonstration
        total_duration = (end_time - start_time).total_seconds()
        self.match_phases = [
            {'phase': 'opening', 'start': 0, 'end': 15, 'description': 'Match opening'},
            {'phase': 'pressure', 'start': 15, 'end': total_duration * 0.7, 'description': 'Sustained pressure'},
            {'phase': 'closing', 'start': total_duration * 0.7, 'end': total_duration, 'description': 'Match closing'}
        ]
    
    def _analyze_event_sequences(self, events: List[EnrichedCombatEvent]):
        """Analyze event sequences to detect combos and patterns."""
        # Group events by player
        player_events = {}
        for event in events:
            if event.source_id not in player_events:
                player_events[event.source_id] = []
            player_events[event.source_id].append(event)
        
        # Analyze sequences for each player
        for player_id, player_event_list in player_events.items():
            self._detect_spell_combos(player_event_list)
    
    def _detect_spell_combos(self, events: List[EnrichedCombatEvent]):
        """Detect spell combos and sequences within events."""
        combo_threshold = 3.0  # seconds
        
        for i, event in enumerate(events):
            if i == 0:
                continue
            
            prev_event = events[i-1]
            time_diff = (event.timestamp - prev_event.timestamp).total_seconds()
            
            if time_diff <= combo_threshold:
                # Part of a potential combo
                event.preceded_by.append(prev_event.spell_name)
                prev_event.followed_by.append(event.spell_name)
                
                # Assign combo position
                if prev_event.combo_position == 0:
                    prev_event.combo_position = 1
                    event.combo_position = 2
                else:
                    event.combo_position = prev_event.combo_position + 1
    
    def _calculate_tactical_significance(self, events: List[EnrichedCombatEvent]):
        """Calculate tactical significance for each event."""
        for event in events:
            score = 0.0
            
            # Base score from spell role
            if event.spell_role == SpellRole.DPS_BURST.value:
                score += 30
            elif event.spell_role == SpellRole.HEALER_THROUGHPUT.value:
                score += 25
            elif event.spell_type == SpellType.CROWD_CONTROL.value:
                score += 40
            else:
                score += 10
            
            # Context modifiers
            if event.context == EventContext.OPENING:
                score *= 1.2
            elif event.context == EventContext.CLOSING:
                score *= 1.5
            elif event.context == EventContext.BURST:
                score *= 1.3
            
            # Damage/healing magnitude
            if event.damage > 0:
                score += min(20, event.damage / 500)  # Up to 20 points for high damage
            if event.healing > 0:
                score += min(15, event.healing / 500)  # Up to 15 points for high healing
            
            # Support contribution
            if event.support_contribution > 0:
                score += min(10, event.support_contribution / 200)
            
            # Special circumstances
            if event.breaks_cc:
                score += 15
            if event.is_critical_hit:
                score += 5
            if event.is_killing_blow:
                score += 50
            
            # Combo bonus
            if event.combo_position > 1:
                score += event.combo_position * 2
            
            event.tactical_score = min(100.0, score)
            
            # Assign significance level
            if event.tactical_score >= 70:
                event.significance = EventSignificance.CRITICAL
            elif event.tactical_score >= 50:
                event.significance = EventSignificance.HIGH
            elif event.tactical_score >= 25:
                event.significance = EventSignificance.MEDIUM
            else:
                event.significance = EventSignificance.LOW
    
    def get_events_by_significance(self, significance: EventSignificance) -> List[EnrichedCombatEvent]:
        """Get events filtered by tactical significance."""
        return [event for event in self.enriched_events if event.significance == significance]
    
    def get_events_by_context(self, context: EventContext) -> List[EnrichedCombatEvent]:
        """Get events filtered by match context."""
        return [event for event in self.enriched_events if event.context == context]
    
    def export_enriched_events(self, output_path: Path, format: str = "json"):
        """Export enriched events to file."""
        if format == "json":
            export_data = []
            for event in self.enriched_events:
                event_dict = {
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type,
                    'source_id': event.source_id,
                    'target_id': event.target_id,
                    'spell_id': event.spell_id,
                    'spell_name': event.spell_name,
                    'spell_school': event.spell_school,
                    'spell_type': event.spell_type,
                    'spell_role': event.spell_role,
                    'damage': event.damage,
                    'healing': event.healing,
                    'source_position': event.source_position,
                    'distance': event.distance,
                    'source_active_auras': event.source_active_auras,
                    'damage_modifiers': event.damage_modifiers,
                    'support_contribution': event.support_contribution,
                    'support_effects': event.support_effects,
                    'significance': event.significance.value,
                    'context': event.context.value,
                    'tactical_score': event.tactical_score,
                    'is_critical_hit': event.is_critical_hit,
                    'breaks_cc': event.breaks_cc,
                    'combo_position': event.combo_position,
                    'preceded_by': event.preceded_by,
                    'followed_by': event.followed_by
                }
                export_data.append(event_dict)
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
    
    def get_enrichment_statistics(self) -> Dict:
        """Get statistics about the enrichment process."""
        if not self.enriched_events:
            return {}
        
        # Count by significance
        sig_counts = {sig.value: 0 for sig in EventSignificance}
        for event in self.enriched_events:
            sig_counts[event.significance.value] += 1
        
        # Count by context
        context_counts = {ctx.value: 0 for ctx in EventContext}
        for event in self.enriched_events:
            context_counts[event.context.value] += 1
        
        # Calculate average tactical score
        avg_score = sum(event.tactical_score for event in self.enriched_events) / len(self.enriched_events)
        
        # Count enriched fields
        events_with_position = sum(1 for e in self.enriched_events if e.source_position)
        events_with_auras = sum(1 for e in self.enriched_events if e.source_active_auras)
        events_with_support = sum(1 for e in self.enriched_events if e.support_contribution > 0)
        events_in_combos = sum(1 for e in self.enriched_events if e.combo_position > 0)
        
        return {
            'total_events': len(self.enriched_events),
            'significance_distribution': sig_counts,
            'context_distribution': context_counts,
            'average_tactical_score': avg_score,
            'events_with_position': events_with_position,
            'events_with_auras': events_with_auras,
            'events_with_support': events_with_support,
            'events_in_combos': events_in_combos,
            'enrichment_completeness': {
                'position_data': (events_with_position / len(self.enriched_events)) * 100,
                'aura_data': (events_with_auras / len(self.enriched_events)) * 100,
                'support_data': (events_with_support / len(self.enriched_events)) * 100,
                'combo_data': (events_in_combos / len(self.enriched_events)) * 100
            }
        }

def main():
    """Test the combat event enrichment system."""
    print("=== COMBAT EVENT ENRICHMENT SYSTEM TEST ===")
    
    # Initialize all systems
    spell_system = SpellMetadataSystem()
    aura_tracker = AdvancedAuraTracker(spell_system)
    attribution_system = SupportDamageAttributionSystem(spell_system, aura_tracker)
    advanced_parser = AdvancedCombatParser()
    
    # Initialize enrichment system
    enrichment_system = CombatEventEnrichmentSystem(
        spell_system, aura_tracker, attribution_system, advanced_parser
    )
    
    # Test with reference log
    log_file = Path("./reference movement tracking from arena logs/WoWCombatLog-080325_093118.txt")
    
    if log_file.exists():
        print(f"\nTesting event enrichment on: {log_file.name}")
        
        # Define time range (first 60 seconds)
        start_time = datetime.now() - timedelta(hours=1)  # Sample start time
        end_time = start_time + timedelta(seconds=60)
        
        # Enrich events
        enriched_events = enrichment_system.enrich_combat_events(log_file, start_time, end_time)
        
        print(f"\nEnriched {len(enriched_events)} combat events")
        
        # Show sample enriched events
        print(f"\nSample Enriched Events:")
        for i, event in enumerate(enriched_events[:3]):  # Show first 3 events
            print(f"  Event {i+1}:")
            print(f"    Type: {event.event_type}")
            print(f"    Source: {event.source_id}")
            print(f"    Spell: {event.spell_name} ({event.spell_school})")
            print(f"    Context: {event.context.value}")
            print(f"    Significance: {event.significance.value}")
            print(f"    Tactical Score: {event.tactical_score:.1f}")
            print(f"    Active Auras: {', '.join(event.source_active_auras[:2])}{'...' if len(event.source_active_auras) > 2 else ''}")
            if event.combo_position > 0:
                print(f"    Combo Position: {event.combo_position}")
            print()
        
        # Get statistics
        stats = enrichment_system.get_enrichment_statistics()
        print(f"Enrichment Statistics:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Average tactical score: {stats['average_tactical_score']:.1f}")
        
        print(f"\nSignificance Distribution:")
        for sig, count in stats['significance_distribution'].items():
            percentage = (count / stats['total_events']) * 100 if stats['total_events'] > 0 else 0
            print(f"  {sig}: {count} ({percentage:.1f}%)")
        
        print(f"\nContext Distribution:")
        for ctx, count in stats['context_distribution'].items():
            percentage = (count / stats['total_events']) * 100 if stats['total_events'] > 0 else 0
            print(f"  {ctx}: {count} ({percentage:.1f}%)")
        
        print(f"\nEnrichment Completeness:")
        completeness = stats['enrichment_completeness']
        print(f"  Position data: {completeness['position_data']:.1f}%")
        print(f"  Aura data: {completeness['aura_data']:.1f}%")
        print(f"  Support data: {completeness['support_data']:.1f}%")
        print(f"  Combo data: {completeness['combo_data']:.1f}%")
        
        # Export enriched events
        output_file = Path("enriched_combat_events.json")
        enrichment_system.export_enriched_events(output_file)
        print(f"\nEnriched events exported to: {output_file}")
        
    else:
        print("Reference log file not found")

if __name__ == "__main__":
    main()