#!/usr/bin/env python3
"""
Development: Advanced Aura Tracking System

Implements complex buff/debuff state management for enhanced combat analysis.
Tracks aura uptimes, overlaps, interactions, and provides detailed aura analytics.

Based on roadmap: "Advanced Aura Tracking - Complex buff/debuff state management"
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

from dev_spell_metadata_system import SpellMetadataSystem, SpellType, CrowdControlType

class AuraType(Enum):
    """Aura effect types."""
    BUFF = "Buff"
    DEBUFF = "Debuff"
    NEUTRAL = "Neutral"
    
class AuraCategory(Enum):
    """Aura categories for tracking."""
    DAMAGE_INCREASE = "Damage Increase"
    DAMAGE_REDUCTION = "Damage Reduction"
    HEALING_INCREASE = "Healing Increase"
    CROWD_CONTROL = "Crowd Control"
    MOBILITY = "Mobility"
    RESOURCE = "Resource"
    IMMUNITY = "Immunity"
    DISPEL_PROTECTION = "Dispel Protection"
    
@dataclass
class AuraDefinition:
    """Definition of an aura effect."""
    spell_id: int
    name: str
    aura_type: AuraType
    category: AuraCategory
    
    # Duration properties
    base_duration: float = 0.0  # seconds
    max_stacks: int = 1
    refresh_behavior: str = "refresh"  # "refresh", "pandemic", "stack"
    
    # Effect properties
    damage_modifier: float = 1.0
    healing_modifier: float = 1.0
    movement_modifier: float = 1.0
    
    # Interaction properties
    is_dispellable: bool = True
    dispel_priority: int = 5  # 1-10, higher = more important
    breaks_on_damage: bool = False
    breaks_on_movement: bool = False
    
    # PvP modifiers
    pvp_duration_modifier: float = 1.0
    diminishing_returns: bool = False
    dr_category: str = ""
    
    # Tags for classification
    tags: Set[str] = field(default_factory=set)

@dataclass
class AuraInstance:
    """An active aura instance on a unit."""
    aura_def: AuraDefinition
    unit_id: str
    applied_at: datetime
    expires_at: datetime
    stacks: int = 1
    
    # Application context
    caster_id: str = ""
    application_spell_id: int = 0
    
    # State tracking
    is_active: bool = True
    removed_at: Optional[datetime] = None
    removal_reason: str = ""  # "expired", "dispelled", "broken", "replaced"
    
    def get_duration(self) -> float:
        """Get current duration of the aura."""
        end_time = self.removed_at or self.expires_at
        return (end_time - self.applied_at).total_seconds()
    
    def get_remaining_duration(self, current_time: datetime) -> float:
        """Get remaining duration at a specific time."""
        if not self.is_active or current_time >= self.expires_at:
            return 0.0
        return (self.expires_at - current_time).total_seconds()
    
    def refresh(self, new_expires_at: datetime, new_stacks: int = None):
        """Refresh the aura instance."""
        self.expires_at = new_expires_at
        if new_stacks is not None:
            self.stacks = min(new_stacks, self.aura_def.max_stacks)
    
    def remove(self, removed_at: datetime, reason: str):
        """Remove the aura instance."""
        self.is_active = False
        self.removed_at = removed_at
        self.removal_reason = reason

class AdvancedAuraTracker:
    """
    Advanced aura tracking system for complex buff/debuff state management.
    
    Provides real-time aura state tracking, uptime analysis, and interaction detection.
    """
    
    def __init__(self, spell_system: SpellMetadataSystem):
        self.spell_system = spell_system
        
        # Active aura tracking
        self.active_auras: Dict[str, List[AuraInstance]] = defaultdict(list)  # unit_id -> auras
        self.aura_history: List[AuraInstance] = []
        
        # Aura definitions
        self.aura_definitions: Dict[int, AuraDefinition] = {}
        
        # Diminishing returns tracking
        self.dr_tracking: Dict[Tuple[str, str], List[datetime]] = defaultdict(list)  # (unit_id, dr_category) -> applications
        
        # Initialize with common auras
        self._initialize_aura_definitions()
    
    def _initialize_aura_definitions(self):
        """Initialize with common arena aura definitions."""
        
        common_auras = [
            # Crowd Control Auras
            AuraDefinition(
                spell_id=5782, name="Fear", aura_type=AuraType.DEBUFF, category=AuraCategory.CROWD_CONTROL,
                base_duration=8.0, pvp_duration_modifier=0.5, diminishing_returns=True, dr_category="fear",
                breaks_on_damage=True, is_dispellable=True, dispel_priority=9,
                tags={"cc", "fear", "incapacitate"}
            ),
            
            AuraDefinition(
                spell_id=118, name="Polymorph", aura_type=AuraType.DEBUFF, category=AuraCategory.CROWD_CONTROL,
                base_duration=8.0, pvp_duration_modifier=0.5, diminishing_returns=True, dr_category="incapacitate",
                breaks_on_damage=True, is_dispellable=True, dispel_priority=10,
                tags={"cc", "polymorph", "incapacitate"}
            ),
            
            AuraDefinition(
                spell_id=20066, name="Repentance", aura_type=AuraType.DEBUFF, category=AuraCategory.CROWD_CONTROL,
                base_duration=8.0, pvp_duration_modifier=0.5, diminishing_returns=True, dr_category="incapacitate",
                breaks_on_damage=True, is_dispellable=True, dispel_priority=10,
                tags={"cc", "repentance", "incapacitate"}
            ),
            
            # Damage Buffs
            AuraDefinition(
                spell_id=1719, name="Recklessness", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=12.0, damage_modifier=1.20, is_dispellable=False, dispel_priority=0,
                tags={"damage_buff", "warrior", "cooldown"}
            ),
            
            AuraDefinition(
                spell_id=31884, name="Avenging Wrath", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=20.0, damage_modifier=1.20, healing_modifier=1.20, is_dispellable=False,
                tags={"damage_buff", "healing_buff", "paladin", "wings"}
            ),
            
            AuraDefinition(
                spell_id=12472, name="Icy Veins", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=20.0, damage_modifier=1.30, is_dispellable=False,
                tags={"damage_buff", "mage", "frost", "cooldown"}
            ),
            
            # Defensive Buffs
            AuraDefinition(
                spell_id=871, name="Shield Wall", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_REDUCTION,
                base_duration=8.0, damage_modifier=0.60, is_dispellable=False,
                tags={"defensive", "warrior", "damage_reduction"}
            ),
            
            AuraDefinition(
                spell_id=498, name="Divine Protection", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_REDUCTION,
                base_duration=10.0, damage_modifier=0.80, is_dispellable=False,
                tags={"defensive", "paladin", "damage_reduction"}
            ),
            
            AuraDefinition(
                spell_id=45438, name="Ice Block", aura_type=AuraType.BUFF, category=AuraCategory.IMMUNITY,
                base_duration=10.0, damage_modifier=0.0, is_dispellable=False,
                tags={"immunity", "mage", "frost", "invulnerable"}
            ),
            
            # Damage over Time
            AuraDefinition(
                spell_id=589, name="Shadow Word: Pain", aura_type=AuraType.DEBUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=16.0, is_dispellable=True, dispel_priority=3,
                tags={"dot", "priest", "shadow", "periodic"}
            ),
            
            AuraDefinition(
                spell_id=172, name="Corruption", aura_type=AuraType.DEBUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=14.0, is_dispellable=True, dispel_priority=3,
                tags={"dot", "warlock", "shadow", "periodic"}
            ),
            
            AuraDefinition(
                spell_id=1943, name="Rupture", aura_type=AuraType.DEBUFF, category=AuraCategory.DAMAGE_INCREASE,
                base_duration=16.0, max_stacks=1, is_dispellable=False,
                tags={"dot", "rogue", "bleed", "finisher"}
            ),
            
            # Healing over Time
            AuraDefinition(
                spell_id=774, name="Rejuvenation", aura_type=AuraType.BUFF, category=AuraCategory.HEALING_INCREASE,
                base_duration=12.0, is_dispellable=True, dispel_priority=4,
                tags={"hot", "druid", "restoration", "periodic"}
            ),
            
            AuraDefinition(
                spell_id=8936, name="Regrowth", aura_type=AuraType.BUFF, category=AuraCategory.HEALING_INCREASE,
                base_duration=12.0, is_dispellable=True, dispel_priority=4,
                tags={"hot", "druid", "restoration", "periodic"}
            ),
            
            # Mobility Buffs
            AuraDefinition(
                spell_id=2983, name="Sprint", aura_type=AuraType.BUFF, category=AuraCategory.MOBILITY,
                base_duration=8.0, movement_modifier=1.70, is_dispellable=True, dispel_priority=2,
                tags={"mobility", "rogue", "speed"}
            ),
            
            AuraDefinition(
                spell_id=1850, name="Dash", aura_type=AuraType.BUFF, category=AuraCategory.MOBILITY,
                base_duration=10.0, movement_modifier=1.60, is_dispellable=True, dispel_priority=2,
                tags={"mobility", "druid", "cat_form", "speed"}
            ),
            
            # Utility Effects
            AuraDefinition(
                spell_id=1044, name="Blessing of Freedom", aura_type=AuraType.BUFF, category=AuraCategory.DISPEL_PROTECTION,
                base_duration=8.0, is_dispellable=True, dispel_priority=8,
                tags={"utility", "paladin", "freedom", "movement"}
            ),
            
            AuraDefinition(
                spell_id=23920, name="Spell Reflection", aura_type=AuraType.BUFF, category=AuraCategory.DAMAGE_REDUCTION,
                base_duration=5.0, is_dispellable=True, dispel_priority=9,
                tags={"utility", "warrior", "reflect", "spell_immunity"}
            ),
        ]
        
        for aura_def in common_auras:
            self.aura_definitions[aura_def.spell_id] = aura_def
    
    def add_aura_definition(self, aura_def: AuraDefinition):
        """Add an aura definition to the system."""
        self.aura_definitions[aura_def.spell_id] = aura_def
    
    def apply_aura(self, spell_id: int, unit_id: str, caster_id: str, 
                   applied_at: datetime, stacks: int = 1) -> Optional[AuraInstance]:
        """Apply an aura to a unit."""
        aura_def = self.aura_definitions.get(spell_id)
        if not aura_def:
            return None
        
        # Calculate expiration time
        duration = aura_def.base_duration * aura_def.pvp_duration_modifier
        expires_at = applied_at + timedelta(seconds=duration)
        
        # Apply diminishing returns if applicable
        if aura_def.diminishing_returns:
            dr_modifier = self._calculate_dr_modifier(unit_id, aura_def.dr_category, applied_at)
            duration *= dr_modifier
            expires_at = applied_at + timedelta(seconds=duration)
        
        # Check for existing aura
        existing_aura = self._find_active_aura(unit_id, spell_id)
        
        if existing_aura:
            # Handle refresh behavior
            if aura_def.refresh_behavior == "refresh":
                existing_aura.refresh(expires_at, stacks)
                return existing_aura
            elif aura_def.refresh_behavior == "stack" and existing_aura.stacks < aura_def.max_stacks:
                new_stacks = min(existing_aura.stacks + stacks, aura_def.max_stacks)
                existing_aura.refresh(expires_at, new_stacks)
                return existing_aura
            elif aura_def.refresh_behavior == "pandemic":
                # Pandemic refresh: add remaining time up to 30% of base duration
                remaining = existing_aura.get_remaining_duration(applied_at)
                pandemic_cap = aura_def.base_duration * 0.3
                bonus_time = min(remaining, pandemic_cap)
                new_expires = applied_at + timedelta(seconds=duration + bonus_time)
                existing_aura.refresh(new_expires, stacks)
                return existing_aura
        
        # Create new aura instance
        aura_instance = AuraInstance(
            aura_def=aura_def,
            unit_id=unit_id,
            applied_at=applied_at,
            expires_at=expires_at,
            stacks=stacks,
            caster_id=caster_id,
            application_spell_id=spell_id
        )
        
        # Add to active auras
        self.active_auras[unit_id].append(aura_instance)
        self.aura_history.append(aura_instance)
        
        return aura_instance
    
    def remove_aura(self, unit_id: str, spell_id: int, removed_at: datetime, reason: str = "expired"):
        """Remove an aura from a unit."""
        aura = self._find_active_aura(unit_id, spell_id)
        if aura:
            aura.remove(removed_at, reason)
            self.active_auras[unit_id].remove(aura)
    
    def dispel_aura(self, unit_id: str, dispeller_id: str, dispel_at: datetime, 
                    aura_type: AuraType = None) -> List[AuraInstance]:
        """Dispel auras from a unit, returning list of dispelled auras."""
        unit_auras = self.active_auras.get(unit_id, [])
        dispellable_auras = [
            aura for aura in unit_auras 
            if aura.aura_def.is_dispellable and 
            (aura_type is None or aura.aura_def.aura_type == aura_type)
        ]
        
        if not dispellable_auras:
            return []
        
        # Sort by dispel priority (highest first)
        dispellable_auras.sort(key=lambda a: a.aura_def.dispel_priority, reverse=True)
        
        # Dispel the highest priority aura
        dispelled_aura = dispellable_auras[0]
        dispelled_aura.remove(dispel_at, "dispelled")
        self.active_auras[unit_id].remove(dispelled_aura)
        
        return [dispelled_aura]
    
    def break_auras_on_damage(self, unit_id: str, damage_at: datetime) -> List[AuraInstance]:
        """Break auras that break on damage."""
        unit_auras = self.active_auras.get(unit_id, [])
        broken_auras = []
        
        for aura in unit_auras[:]:  # Copy list to avoid modification during iteration
            if aura.aura_def.breaks_on_damage:
                aura.remove(damage_at, "broken_by_damage")
                self.active_auras[unit_id].remove(aura)
                broken_auras.append(aura)
        
        return broken_auras
    
    def update_expired_auras(self, current_time: datetime):
        """Remove expired auras."""
        for unit_id, unit_auras in self.active_auras.items():
            for aura in unit_auras[:]:  # Copy to avoid modification during iteration
                if current_time >= aura.expires_at:
                    aura.remove(current_time, "expired")
                    unit_auras.remove(aura)
    
    def get_active_auras(self, unit_id: str, current_time: datetime = None) -> List[AuraInstance]:
        """Get all active auras for a unit."""
        if current_time:
            self.update_expired_auras(current_time)
        return self.active_auras.get(unit_id, []).copy()
    
    def get_auras_by_category(self, unit_id: str, category: AuraCategory, 
                             current_time: datetime = None) -> List[AuraInstance]:
        """Get active auras by category."""
        active_auras = self.get_active_auras(unit_id, current_time)
        return [aura for aura in active_auras if aura.aura_def.category == category]
    
    def get_damage_modifiers(self, unit_id: str, current_time: datetime = None) -> Dict[str, float]:
        """Get current damage modifiers for a unit."""
        active_auras = self.get_active_auras(unit_id, current_time)
        
        damage_increase = 1.0
        damage_reduction = 1.0
        
        for aura in active_auras:
            if aura.aura_def.damage_modifier > 1.0:
                damage_increase *= aura.aura_def.damage_modifier
            elif aura.aura_def.damage_modifier < 1.0:
                damage_reduction *= aura.aura_def.damage_modifier
        
        return {
            'damage_increase': damage_increase,
            'damage_reduction': damage_reduction,
            'total_modifier': damage_increase * damage_reduction
        }
    
    def _find_active_aura(self, unit_id: str, spell_id: int) -> Optional[AuraInstance]:
        """Find an active aura instance."""
        unit_auras = self.active_auras.get(unit_id, [])
        for aura in unit_auras:
            if aura.aura_def.spell_id == spell_id and aura.is_active:
                return aura
        return None
    
    def _calculate_dr_modifier(self, unit_id: str, dr_category: str, applied_at: datetime) -> float:
        """Calculate diminishing returns modifier."""
        if not dr_category:
            return 1.0
        
        dr_key = (unit_id, dr_category)
        applications = self.dr_tracking[dr_key]
        
        # Remove applications older than 15 seconds
        cutoff_time = applied_at - timedelta(seconds=15)
        applications = [app for app in applications if app > cutoff_time]
        self.dr_tracking[dr_key] = applications
        
        # Add current application
        applications.append(applied_at)
        
        # Calculate DR modifier
        num_applications = len(applications)
        if num_applications == 1:
            return 1.0  # Full duration
        elif num_applications == 2:
            return 0.5  # 50% duration
        elif num_applications == 3:
            return 0.25  # 25% duration
        else:
            return 0.0  # Immune
    
    def analyze_aura_uptime(self, unit_id: str, start_time: datetime, 
                          end_time: datetime, spell_id: int = None) -> Dict:
        """Analyze aura uptime for a unit over a time period."""
        duration = (end_time - start_time).total_seconds()
        
        if spell_id:
            # Analyze specific aura
            relevant_auras = [
                aura for aura in self.aura_history 
                if (aura.unit_id == unit_id and 
                    aura.aura_def.spell_id == spell_id and
                    aura.applied_at < end_time and
                    (aura.removed_at is None or aura.removed_at > start_time))
            ]
        else:
            # Analyze all auras
            relevant_auras = [
                aura for aura in self.aura_history
                if (aura.unit_id == unit_id and
                    aura.applied_at < end_time and
                    (aura.removed_at is None or aura.removed_at > start_time))
            ]
        
        if not relevant_auras:
            return {
                'total_uptime': 0.0,
                'uptime_percentage': 0.0,
                'applications': 0,
                'average_duration': 0.0
            }
        
        # Calculate uptime
        total_uptime = 0.0
        applications = len(relevant_auras)
        total_duration = 0.0
        
        for aura in relevant_auras:
            # Calculate overlap with analysis period
            aura_start = max(aura.applied_at, start_time)
            aura_end = min(aura.removed_at or aura.expires_at, end_time)
            
            if aura_end > aura_start:
                uptime = (aura_end - aura_start).total_seconds()
                total_uptime += uptime
                total_duration += aura.get_duration()
        
        return {
            'total_uptime': total_uptime,
            'uptime_percentage': (total_uptime / duration * 100) if duration > 0 else 0,
            'applications': applications,
            'average_duration': total_duration / applications if applications > 0 else 0
        }
    
    def get_aura_statistics(self) -> Dict:
        """Get system-wide aura statistics."""
        total_auras = len(self.aura_history)
        active_auras = sum(len(auras) for auras in self.active_auras.values())
        
        # Count by category
        category_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for aura in self.aura_history:
            category_counts[aura.aura_def.category.value] += 1
            type_counts[aura.aura_def.aura_type.value] += 1
        
        # Calculate average durations
        total_duration = sum(aura.get_duration() for aura in self.aura_history)
        avg_duration = total_duration / total_auras if total_auras > 0 else 0
        
        return {
            'total_aura_applications': total_auras,
            'currently_active': active_auras,
            'average_duration': avg_duration,
            'category_distribution': dict(category_counts),
            'type_distribution': dict(type_counts),
            'aura_definitions': len(self.aura_definitions)
        }

def main():
    """Test the advanced aura tracking system."""
    print("=== ADVANCED AURA TRACKING SYSTEM TEST ===")
    
    # Initialize systems
    spell_system = SpellMetadataSystem()
    aura_tracker = AdvancedAuraTracker(spell_system)
    
    # Test aura applications
    start_time = datetime.now()
    
    print(f"\nTesting Aura Applications:")
    
    # Apply some auras
    fear_aura = aura_tracker.apply_aura(5782, "player1", "enemy1", start_time)
    print(f"Applied Fear: {fear_aura.aura_def.name} expires at {fear_aura.expires_at}")
    
    recklessness = aura_tracker.apply_aura(1719, "player1", "player1", start_time)
    print(f"Applied Recklessness: {recklessness.aura_def.name} expires at {recklessness.expires_at}")
    
    # Test damage modifiers
    modifiers = aura_tracker.get_damage_modifiers("player1", start_time)
    print(f"\nDamage Modifiers for player1:")
    print(f"  Increase: {modifiers['damage_increase']:.2f}")
    print(f"  Reduction: {modifiers['damage_reduction']:.2f}")
    print(f"  Total: {modifiers['total_modifier']:.2f}")
    
    # Test breaking auras on damage
    later_time = start_time + timedelta(seconds=2)
    broken_auras = aura_tracker.break_auras_on_damage("player1", later_time)
    print(f"\nBroken auras on damage: {len(broken_auras)}")
    for aura in broken_auras:
        print(f"  {aura.aura_def.name} (reason: {aura.removal_reason})")
    
    # Test diminishing returns
    print(f"\nTesting Diminishing Returns:")
    for i in range(4):
        fear_time = start_time + timedelta(seconds=i * 20)
        fear_aura = aura_tracker.apply_aura(5782, "player2", "enemy1", fear_time)
        if fear_aura:
            duration = (fear_aura.expires_at - fear_aura.applied_at).total_seconds()
            print(f"  Fear #{i+1}: {duration:.1f}s duration")
    
    # Test uptime analysis
    end_time = start_time + timedelta(seconds=60)
    uptime_analysis = aura_tracker.analyze_aura_uptime("player1", start_time, end_time, 1719)
    print(f"\nRecklessness Uptime Analysis:")
    print(f"  Uptime: {uptime_analysis['uptime_percentage']:.1f}%")
    print(f"  Applications: {uptime_analysis['applications']}")
    print(f"  Average Duration: {uptime_analysis['average_duration']:.1f}s")
    
    # Get system statistics
    stats = aura_tracker.get_aura_statistics()
    print(f"\nSystem Statistics:")
    print(f"  Total applications: {stats['total_aura_applications']}")
    print(f"  Currently active: {stats['currently_active']}")
    print(f"  Average duration: {stats['average_duration']:.1f}s")
    print(f"  Aura definitions: {stats['aura_definitions']}")
    
    print(f"\nType Distribution:")
    for aura_type, count in stats['type_distribution'].items():
        print(f"  {aura_type}: {count}")

if __name__ == "__main__":
    main()