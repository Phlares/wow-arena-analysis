#!/usr/bin/env python3
"""
Development: Support Damage Attribution System

Implements support damage and healing attribution tracking for advanced combat analysis.
Tracks damage amplification effects, healing bonuses, and provides attribution metrics.

Based on roadmap: "Support Damage Attribution - Track damage amplification effects"
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

from dev_spell_metadata_system import SpellMetadataSystem, SpellSchool, SpellType
from dev_advanced_aura_tracker import AdvancedAuraTracker, AuraType, AuraCategory

class SupportType(Enum):
    """Types of support effects."""
    DAMAGE_AMPLIFICATION = "Damage Amplification"
    HEALING_AMPLIFICATION = "Healing Amplification"
    DAMAGE_REDUCTION = "Damage Reduction"
    UTILITY_EFFECT = "Utility Effect"
    
class AttributionMethod(Enum):
    """Methods for calculating attribution."""
    MULTIPLICATIVE = "Multiplicative"  # Track % increase
    ADDITIVE = "Additive"  # Track flat increase
    ENABLING = "Enabling"  # Track enabling effects (e.g., making target vulnerable)
    
@dataclass
class SupportEffect:
    """Definition of a support effect."""
    spell_id: int
    name: str
    support_type: SupportType
    attribution_method: AttributionMethod
    
    # Effect properties
    damage_multiplier: float = 1.0
    healing_multiplier: float = 1.0
    flat_damage_bonus: int = 0
    flat_healing_bonus: int = 0
    
    # Application properties
    affects_all_damage: bool = True
    affects_schools: Set[SpellSchool] = field(default_factory=set)
    affects_spell_types: Set[SpellType] = field(default_factory=set)
    
    # Duration and stacking
    duration: float = 0.0
    max_stacks: int = 1
    stack_behavior: str = "refresh"  # "refresh", "stack", "replace"
    
    # Restrictions
    max_targets: int = 0  # 0 = unlimited
    requires_line_of_sight: bool = False
    range_limit: float = 0.0  # 0 = unlimited range
    
    # Tags for classification
    tags: Set[str] = field(default_factory=set)

@dataclass
class AttributionEvent:
    """A support attribution event."""
    support_spell_id: int
    supporter_id: str
    beneficiary_id: str
    applied_at: datetime
    expires_at: datetime
    
    # Effect tracking
    damage_attributed: int = 0
    healing_attributed: int = 0
    events_affected: int = 0
    
    # Context
    support_effect: SupportEffect = None
    is_active: bool = True
    
    def add_attribution(self, base_amount: int, actual_amount: int, event_type: str):
        """Add attribution for a damage/healing event."""
        if event_type == "damage":
            attributed = actual_amount - base_amount
            self.damage_attributed += max(0, attributed)
        elif event_type == "healing":
            attributed = actual_amount - base_amount
            self.healing_attributed += max(0, attributed)
        
        self.events_affected += 1

class SupportDamageAttributionSystem:
    """
    System for tracking and attributing support effects on damage and healing.
    
    Provides detailed analysis of how support spells and abilities contribute
    to overall combat effectiveness through damage amplification and healing bonuses.
    """
    
    def __init__(self, spell_system: SpellMetadataSystem, aura_tracker: AdvancedAuraTracker):
        self.spell_system = spell_system
        self.aura_tracker = aura_tracker
        
        # Active support effects
        self.active_effects: Dict[str, List[AttributionEvent]] = defaultdict(list)  # beneficiary_id -> effects
        self.attribution_history: List[AttributionEvent] = []
        
        # Support effect definitions
        self.support_effects: Dict[int, SupportEffect] = {}
        
        # Initialize with common support effects
        self._initialize_support_effects()
    
    def _initialize_support_effects(self):
        """Initialize with common arena support effects."""
        
        support_effects = [
            # Damage Amplification Effects
            SupportEffect(
                spell_id=116014, name="Rune of Power", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.40,
                duration=60.0, affects_all_damage=True, max_targets=1,
                tags={"mage", "damage_buff", "ground_effect"}
            ),
            
            SupportEffect(
                spell_id=1459, name="Arcane Intellect", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.05,
                duration=3600.0, affects_all_damage=True, max_targets=0,
                tags={"mage", "buff", "party_wide", "intellect"}
            ),
            
            SupportEffect(
                spell_id=21562, name="Power Word: Fortitude", support_type=SupportType.HEALING_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, healing_multiplier=1.05,
                duration=3600.0, affects_all_damage=False, max_targets=0,
                tags={"priest", "buff", "party_wide", "stamina"}
            ),
            
            # Paladin Support
            SupportEffect(
                spell_id=465, name="Devotion Aura", support_type=SupportType.DAMAGE_REDUCTION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=0.96,
                duration=3600.0, affects_all_damage=True, max_targets=0,
                tags={"paladin", "aura", "party_wide", "armor"}
            ),
            
            SupportEffect(
                spell_id=31884, name="Avenging Wrath", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.20,
                healing_multiplier=1.20, duration=20.0, affects_all_damage=True, max_targets=1,
                tags={"paladin", "wings", "cooldown", "self_buff"}
            ),
            
            # Warlock Support
            SupportEffect(
                spell_id=1454, name="Life Tap", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.ENABLING, damage_multiplier=1.0,
                duration=0.0, affects_all_damage=False, max_targets=1,
                tags={"warlock", "mana_conversion", "self_harm"}
            ),
            
            # Demon Hunter Support
            SupportEffect(
                spell_id=258920, name="Immolation Aura", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.ADDITIVE, flat_damage_bonus=200,
                duration=6.0, affects_all_damage=False, max_targets=0,
                affects_schools={SpellSchool.FIRE}, tags={"demon_hunter", "aoe", "fire"}
            ),
            
            # Monk Support  
            SupportEffect(
                spell_id=116841, name="Tiger's Lust", support_type=SupportType.UTILITY_EFFECT,
                attribution_method=AttributionMethod.ENABLING, damage_multiplier=1.0,
                duration=6.0, affects_all_damage=False, max_targets=1,
                tags={"monk", "mobility", "freedom", "utility"}
            ),
            
            # Death Knight Support
            SupportEffect(
                spell_id=51271, name="Unbreakable Armor", support_type=SupportType.DAMAGE_REDUCTION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=0.80,
                duration=20.0, affects_all_damage=True, max_targets=1,
                tags={"death_knight", "defensive", "armor", "cooldown"}
            ),
            
            # Hunter Support
            SupportEffect(
                spell_id=13159, name="Aspect of the Pack", support_type=SupportType.UTILITY_EFFECT,
                attribution_method=AttributionMethod.ENABLING, damage_multiplier=1.0,
                duration=3600.0, affects_all_damage=False, max_targets=0,
                tags={"hunter", "aspect", "movement", "party_wide"}
            ),
            
            # Shaman Support
            SupportEffect(
                spell_id=8512, name="Windfury Totem", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.15,
                duration=120.0, affects_all_damage=False, max_targets=0,
                affects_spell_types={SpellType.DAMAGE}, tags={"shaman", "totem", "melee", "party_wide"}
            ),
            
            SupportEffect(
                spell_id=8227, name="Flametongue Totem", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.10,
                duration=120.0, affects_all_damage=False, max_targets=0,
                affects_schools={SpellSchool.FIRE}, tags={"shaman", "totem", "spell_damage", "party_wide"}
            ),
            
            # Druid Support
            SupportEffect(
                spell_id=1126, name="Mark of the Wild", support_type=SupportType.DAMAGE_REDUCTION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=0.98,
                healing_multiplier=1.02, duration=3600.0, max_targets=0,
                tags={"druid", "buff", "party_wide", "stats"}
            ),
            
            # Warrior Support
            SupportEffect(
                spell_id=6673, name="Battle Shout", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.05,
                duration=3600.0, affects_all_damage=True, max_targets=0,
                tags={"warrior", "shout", "party_wide", "attack_power"}
            ),
            
            # Rogue Support
            SupportEffect(
                spell_id=57934, name="Tricks of the Trade", support_type=SupportType.DAMAGE_AMPLIFICATION,
                attribution_method=AttributionMethod.MULTIPLICATIVE, damage_multiplier=1.15,
                duration=6.0, affects_all_damage=True, max_targets=1,
                tags={"rogue", "tricks", "threat", "damage_transfer"}
            ),
        ]
        
        for effect in support_effects:
            self.support_effects[effect.spell_id] = effect
    
    def apply_support_effect(self, spell_id: int, supporter_id: str, beneficiary_id: str,
                           applied_at: datetime) -> Optional[AttributionEvent]:
        """Apply a support effect to a beneficiary."""
        support_effect = self.support_effects.get(spell_id)
        if not support_effect:
            return None
        
        # Calculate expiration time
        expires_at = applied_at + timedelta(seconds=support_effect.duration)
        
        # Check for existing effect
        existing_event = self._find_active_effect(beneficiary_id, spell_id)
        
        if existing_event and support_effect.stack_behavior == "refresh":
            # Refresh existing effect
            existing_event.expires_at = expires_at
            existing_event.applied_at = applied_at
            return existing_event
        elif existing_event and support_effect.stack_behavior == "replace":
            # Remove existing and create new
            self._remove_effect(existing_event)
        
        # Create new attribution event
        attribution_event = AttributionEvent(
            support_spell_id=spell_id,
            supporter_id=supporter_id,
            beneficiary_id=beneficiary_id,
            applied_at=applied_at,
            expires_at=expires_at,
            support_effect=support_effect
        )
        
        # Add to active effects
        self.active_effects[beneficiary_id].append(attribution_event)
        self.attribution_history.append(attribution_event)
        
        return attribution_event
    
    def calculate_damage_attribution(self, damage_dealer_id: str, spell_id: int, base_damage: int,
                                   actual_damage: int, damage_at: datetime) -> Dict:
        """Calculate damage attribution from support effects."""
        # Get active support effects on the damage dealer
        active_effects = self._get_active_effects(damage_dealer_id, damage_at)
        
        if not active_effects:
            return {
                'base_damage': base_damage,
                'actual_damage': actual_damage,
                'total_attribution': 0,
                'support_contributions': []
            }
        
        # Get spell metadata for damage event
        spell_meta = self.spell_system.get_spell(spell_id)
        
        total_attribution = 0
        support_contributions = []
        
        for effect_event in active_effects:
            effect = effect_event.support_effect
            attribution = 0
            
            # Check if effect applies to this damage event
            if not self._effect_applies_to_damage(effect, spell_meta):
                continue
            
            # Calculate attribution based on method
            if effect.attribution_method == AttributionMethod.MULTIPLICATIVE:
                if effect.damage_multiplier != 1.0:
                    # Calculate what damage would have been without this effect
                    damage_without_effect = actual_damage / effect.damage_multiplier
                    attribution = actual_damage - damage_without_effect
            
            elif effect.attribution_method == AttributionMethod.ADDITIVE:
                attribution = min(effect.flat_damage_bonus, actual_damage - base_damage)
            
            elif effect.attribution_method == AttributionMethod.ENABLING:
                # For enabling effects, attribute based on whether damage would have been possible
                if actual_damage > 0:
                    attribution = actual_damage * 0.1  # 10% attribution for enabling
            
            if attribution > 0:
                # Add attribution to the effect
                effect_event.add_attribution(base_damage, actual_damage, "damage")
                total_attribution += attribution
                
                support_contributions.append({
                    'supporter_id': effect_event.supporter_id,
                    'spell_id': effect_event.support_spell_id,
                    'spell_name': effect.name,
                    'attribution': attribution,
                    'attribution_percentage': (attribution / actual_damage * 100) if actual_damage > 0 else 0
                })
        
        return {
            'base_damage': base_damage,
            'actual_damage': actual_damage,
            'total_attribution': total_attribution,
            'support_contributions': support_contributions
        }
    
    def calculate_healing_attribution(self, healer_id: str, spell_id: int, base_healing: int,
                                    actual_healing: int, heal_at: datetime) -> Dict:
        """Calculate healing attribution from support effects."""
        # Get active support effects on the healer
        active_effects = self._get_active_effects(healer_id, heal_at)
        
        if not active_effects:
            return {
                'base_healing': base_healing,
                'actual_healing': actual_healing,
                'total_attribution': 0,
                'support_contributions': []
            }
        
        # Get spell metadata for healing event
        spell_meta = self.spell_system.get_spell(spell_id)
        
        total_attribution = 0
        support_contributions = []
        
        for effect_event in active_effects:
            effect = effect_event.support_effect
            attribution = 0
            
            # Check if effect applies to this healing event
            if not self._effect_applies_to_healing(effect, spell_meta):
                continue
            
            # Calculate attribution based on method
            if effect.attribution_method == AttributionMethod.MULTIPLICATIVE:
                if effect.healing_multiplier != 1.0:
                    # Calculate what healing would have been without this effect
                    healing_without_effect = actual_healing / effect.healing_multiplier
                    attribution = actual_healing - healing_without_effect
            
            elif effect.attribution_method == AttributionMethod.ADDITIVE:
                attribution = min(effect.flat_healing_bonus, actual_healing - base_healing)
            
            if attribution > 0:
                # Add attribution to the effect
                effect_event.add_attribution(base_healing, actual_healing, "healing")
                total_attribution += attribution
                
                support_contributions.append({
                    'supporter_id': effect_event.supporter_id,
                    'spell_id': effect_event.support_spell_id,
                    'spell_name': effect.name,
                    'attribution': attribution,
                    'attribution_percentage': (attribution / actual_healing * 100) if actual_healing > 0 else 0
                })
        
        return {
            'base_healing': base_healing,
            'actual_healing': actual_healing,
            'total_attribution': total_attribution,
            'support_contributions': support_contributions
        }
    
    def _get_active_effects(self, unit_id: str, current_time: datetime) -> List[AttributionEvent]:
        """Get active support effects for a unit."""
        # Update expired effects
        self._update_expired_effects(current_time)
        
        return [effect for effect in self.active_effects.get(unit_id, []) if effect.is_active]
    
    def _find_active_effect(self, unit_id: str, spell_id: int) -> Optional[AttributionEvent]:
        """Find an active support effect for a specific spell."""
        unit_effects = self.active_effects.get(unit_id, [])
        for effect in unit_effects:
            if effect.support_spell_id == spell_id and effect.is_active:
                return effect
        return None
    
    def _remove_effect(self, effect: AttributionEvent):
        """Remove a support effect."""
        effect.is_active = False
        if effect.beneficiary_id in self.active_effects:
            try:
                self.active_effects[effect.beneficiary_id].remove(effect)
            except ValueError:
                pass  # Effect already removed
    
    def _update_expired_effects(self, current_time: datetime):
        """Remove expired support effects."""
        for unit_id, unit_effects in self.active_effects.items():
            for effect in unit_effects[:]:  # Copy to avoid modification during iteration
                if current_time >= effect.expires_at:
                    effect.is_active = False
                    unit_effects.remove(effect)
    
    def _effect_applies_to_damage(self, effect: SupportEffect, spell_meta) -> bool:
        """Check if a support effect applies to a damage spell."""
        if effect.support_type != SupportType.DAMAGE_AMPLIFICATION:
            return False
        
        if effect.affects_all_damage:
            return True
        
        if spell_meta:
            # Check school restrictions
            if effect.affects_schools and spell_meta.school not in effect.affects_schools:
                return False
            
            # Check spell type restrictions
            if effect.affects_spell_types and spell_meta.spell_type not in effect.affects_spell_types:
                return False
        
        return True
    
    def _effect_applies_to_healing(self, effect: SupportEffect, spell_meta) -> bool:
        """Check if a support effect applies to a healing spell."""
        if effect.support_type != SupportType.HEALING_AMPLIFICATION:
            return False
        
        if spell_meta and spell_meta.spell_type != SpellType.HEAL:
            return False
        
        return True
    
    def get_supporter_statistics(self, supporter_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """Get support statistics for a specific supporter."""
        # Find all attribution events by this supporter in time range
        relevant_events = [
            event for event in self.attribution_history
            if (event.supporter_id == supporter_id and
                start_time <= event.applied_at <= end_time)
        ]
        
        if not relevant_events:
            return {
                'total_effects_applied': 0,
                'total_damage_attributed': 0,
                'total_healing_attributed': 0,
                'average_effect_duration': 0,
                'most_effective_spell': None
            }
        
        total_damage = sum(event.damage_attributed for event in relevant_events)
        total_healing = sum(event.healing_attributed for event in relevant_events)
        total_events = sum(event.events_affected for event in relevant_events)
        
        # Calculate average effect duration
        durations = [(event.expires_at - event.applied_at).total_seconds() for event in relevant_events]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Find most effective spell
        spell_effectiveness = defaultdict(lambda: {'damage': 0, 'healing': 0, 'events': 0})
        for event in relevant_events:
            spell_effectiveness[event.support_spell_id]['damage'] += event.damage_attributed
            spell_effectiveness[event.support_spell_id]['healing'] += event.healing_attributed
            spell_effectiveness[event.support_spell_id]['events'] += event.events_affected
        
        most_effective_spell = None
        max_total = 0
        for spell_id, stats in spell_effectiveness.items():
            total = stats['damage'] + stats['healing']
            if total > max_total:
                max_total = total
                most_effective_spell = {
                    'spell_id': spell_id,
                    'spell_name': self.support_effects.get(spell_id, {}).name if spell_id in self.support_effects else f"Spell {spell_id}",
                    'total_contribution': total
                }
        
        return {
            'total_effects_applied': len(relevant_events),
            'total_damage_attributed': total_damage,
            'total_healing_attributed': total_healing,
            'total_events_affected': total_events,
            'average_effect_duration': avg_duration,
            'most_effective_spell': most_effective_spell,
            'spell_breakdown': dict(spell_effectiveness)
        }
    
    def get_system_statistics(self) -> Dict:
        """Get system-wide attribution statistics."""
        total_events = len(self.attribution_history)
        active_effects = sum(len(effects) for effects in self.active_effects.values())
        
        total_damage_attributed = sum(event.damage_attributed for event in self.attribution_history)
        total_healing_attributed = sum(event.healing_attributed for event in self.attribution_history)
        
        # Count by support type
        type_counts = defaultdict(int)
        for event in self.attribution_history:
            if event.support_effect:
                type_counts[event.support_effect.support_type.value] += 1
        
        return {
            'total_attribution_events': total_events,
            'currently_active_effects': active_effects,
            'total_damage_attributed': total_damage_attributed,
            'total_healing_attributed': total_healing_attributed,
            'support_effect_definitions': len(self.support_effects),
            'type_distribution': dict(type_counts)
        }

def main():
    """Test the support damage attribution system."""
    print("=== SUPPORT DAMAGE ATTRIBUTION SYSTEM TEST ===")
    
    # Initialize systems
    spell_system = SpellMetadataSystem()
    aura_tracker = AdvancedAuraTracker(spell_system)
    attribution_system = SupportDamageAttributionSystem(spell_system, aura_tracker)
    
    # Test support effect application
    start_time = datetime.now()
    
    print(f"\nTesting Support Effect Applications:")
    
    # Apply Avenging Wrath (damage/healing buff)
    wings_effect = attribution_system.apply_support_effect(31884, "paladin1", "paladin1", start_time)
    print(f"Applied Avenging Wrath: {wings_effect.support_effect.name}")
    print(f"  Damage multiplier: {wings_effect.support_effect.damage_multiplier}")
    print(f"  Healing multiplier: {wings_effect.support_effect.healing_multiplier}")
    
    # Apply Battle Shout (party-wide damage buff)
    shout_effect = attribution_system.apply_support_effect(6673, "warrior1", "paladin1", start_time)
    print(f"Applied Battle Shout: {shout_effect.support_effect.name}")
    print(f"  Damage multiplier: {shout_effect.support_effect.damage_multiplier}")
    
    # Test damage attribution
    print(f"\nTesting Damage Attribution:")
    damage_time = start_time + timedelta(seconds=5)
    
    # Simulate a Templar's Verdict hit
    base_damage = 5000
    actual_damage = 7200  # With buffs applied
    
    attribution_result = attribution_system.calculate_damage_attribution(
        "paladin1", 85256, base_damage, actual_damage, damage_time
    )
    
    print(f"Damage Event Analysis:")
    print(f"  Base damage: {attribution_result['base_damage']}")
    print(f"  Actual damage: {attribution_result['actual_damage']}")
    print(f"  Total attribution: {attribution_result['total_attribution']:.0f}")
    
    print(f"Support Contributions:")
    for contrib in attribution_result['support_contributions']:
        print(f"  {contrib['spell_name']}: +{contrib['attribution']:.0f} ({contrib['attribution_percentage']:.1f}%)")
    
    # Test healing attribution
    print(f"\nTesting Healing Attribution:")
    heal_time = start_time + timedelta(seconds=8)
    
    # Simulate a Flash of Light heal
    base_healing = 3000
    actual_healing = 3600  # With Avenging Wrath
    
    heal_attribution = attribution_system.calculate_healing_attribution(
        "paladin1", 82326, base_healing, actual_healing, heal_time
    )
    
    print(f"Healing Event Analysis:")
    print(f"  Base healing: {heal_attribution['base_healing']}")
    print(f"  Actual healing: {heal_attribution['actual_healing']}")
    print(f"  Total attribution: {heal_attribution['total_attribution']:.0f}")
    
    for contrib in heal_attribution['support_contributions']:
        print(f"  {contrib['spell_name']}: +{contrib['attribution']:.0f} ({contrib['attribution_percentage']:.1f}%)")
    
    # Test supporter statistics
    end_time = start_time + timedelta(seconds=30)
    paladin_stats = attribution_system.get_supporter_statistics("paladin1", start_time, end_time)
    print(f"\nPaladin Support Statistics:")
    print(f"  Effects applied: {paladin_stats['total_effects_applied']}")
    print(f"  Damage attributed: {paladin_stats['total_damage_attributed']:.0f}")
    print(f"  Healing attributed: {paladin_stats['total_healing_attributed']:.0f}")
    
    # System statistics
    system_stats = attribution_system.get_system_statistics()
    print(f"\nSystem Statistics:")
    print(f"  Attribution events: {system_stats['total_attribution_events']}")
    print(f"  Active effects: {system_stats['currently_active_effects']}")
    print(f"  Support definitions: {system_stats['support_effect_definitions']}")
    print(f"  Total damage attributed: {system_stats['total_damage_attributed']:.0f}")
    print(f"  Total healing attributed: {system_stats['total_healing_attributed']:.0f}")

if __name__ == "__main__":
    main()