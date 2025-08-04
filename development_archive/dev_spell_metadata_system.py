#!/usr/bin/env python3
"""
Development: Enhanced Spell Metadata System

Implements comprehensive spell categorization and tracking for advanced combat analysis.
Supports 1000+ spells with categorization for damage types, schools, effects, and roles.

Based on roadmap: "Spell Metadata System - Comprehensive spell categorization (1000+ spells)"
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Optional, Union
import json
from pathlib import Path

class SpellSchool(Enum):
    """Magic schools for spell classification."""
    PHYSICAL = "Physical"
    HOLY = "Holy"
    FIRE = "Fire"
    NATURE = "Nature"
    FROST = "Frost"
    SHADOW = "Shadow"
    ARCANE = "Arcane"
    
class SpellType(Enum):
    """Primary spell function types."""
    DAMAGE = "Damage"
    HEAL = "Heal"
    BUFF = "Buff"
    DEBUFF = "Debuff"
    UTILITY = "Utility"
    CROWD_CONTROL = "Crowd Control"
    MOVEMENT = "Movement"
    DEFENSIVE = "Defensive"
    
class CrowdControlType(Enum):
    """Specific crowd control effects."""
    STUN = "Stun"
    FEAR = "Fear"
    CHARM = "Charm"
    INCAPACITATE = "Incapacitate"
    DISORIENT = "Disorient"
    ROOT = "Root"
    SLOW = "Slow"
    SILENCE = "Silence"
    INTERRUPT = "Interrupt"
    DISPEL = "Dispel"
    
class SpellRole(Enum):
    """Role-based spell categorization."""
    DPS_BURST = "DPS Burst"
    DPS_SUSTAIN = "DPS Sustain"
    TANK_SURVIVAL = "Tank Survival"
    HEALER_THROUGHPUT = "Healer Throughput"
    HEALER_UTILITY = "Healer Utility"
    SUPPORT_DAMAGE = "Support Damage"
    SUPPORT_UTILITY = "Support Utility"
    
@dataclass
class SpellMetadata:
    """Comprehensive spell metadata for combat analysis."""
    spell_id: int
    name: str
    school: SpellSchool
    spell_type: SpellType
    role: SpellRole
    
    # Combat properties
    can_crit: bool = True
    can_miss: bool = True
    is_channeled: bool = False
    is_instant: bool = False
    cast_time: float = 0.0  # seconds
    cooldown: float = 0.0   # seconds
    
    # Effect properties  
    cc_type: Optional[CrowdControlType] = None
    cc_duration: float = 0.0  # seconds
    is_dispellable: bool = False
    dispel_priority: int = 0  # 1-10, higher = more important to dispel
    
    # Damage/healing properties
    base_coefficient: float = 0.0  # spell power coefficient
    direct_damage: bool = False
    periodic_damage: bool = False
    periodic_interval: float = 0.0  # seconds between ticks
    
    # Support and attribution
    amplifies_damage: bool = False
    amplifies_healing: bool = False
    damage_multiplier: float = 1.0
    healing_multiplier: float = 1.0
    
    # Arena-specific properties
    pvp_duration_modifier: float = 1.0  # PvP duration reduction
    breaks_on_damage: bool = False
    limited_targets: int = 0  # 0 = unlimited
    
    # Classification tags
    tags: Set[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()

class SpellMetadataSystem:
    """
    Comprehensive spell metadata management system.
    
    Provides categorization, lookup, and analysis for WoW Arena spells.
    """
    
    def __init__(self):
        self.spells: Dict[int, SpellMetadata] = {}
        self.name_to_id: Dict[str, int] = {}
        self.category_indexes: Dict[str, Set[int]] = {}
        
        # Initialize with core arena spells
        self._initialize_core_spells()
        self._build_indexes()
    
    def _initialize_core_spells(self):
        """Initialize with essential arena spells for each class."""
        
        # DEATH KNIGHT SPELLS
        core_spells = [
            # Death Knight - Frost
            SpellMetadata(49020, "Obliterate", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.8,
                         tags={"melee", "frost", "two_hand"}),
            
            SpellMetadata(49143, "Frost Strike", SpellSchool.FROST, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.2,
                         tags={"melee", "frost", "runic_power"}),
            
            SpellMetadata(47528, "Mind Freeze", SpellSchool.SHADOW, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=4.0, cooldown=15.0,
                         tags={"interrupt", "instant"}),
            
            # Death Knight - Unholy  
            SpellMetadata(85948, "Festering Strike", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.0,
                         tags={"melee", "unholy", "disease"}),
            
            SpellMetadata(47541, "Death Coil", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.5, is_instant=True,
                         tags={"ranged", "unholy", "runic_power"}),
            
            # DEMON HUNTER SPELLS
            SpellMetadata(185123, "Throw Glaive", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.0, is_instant=True,
                         tags={"ranged", "havoc", "glaive"}),
            
            SpellMetadata(195072, "Fel Rush", SpellSchool.SHADOW, SpellType.MOVEMENT, SpellRole.SUPPORT_UTILITY,
                         is_instant=True, cooldown=10.0, direct_damage=True,
                         tags={"mobility", "havoc", "charge"}),
            
            SpellMetadata(183752, "Consume Magic", SpellSchool.SHADOW, SpellType.UTILITY, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.DISPEL, is_instant=True, cooldown=10.0,
                         tags={"dispel", "havoc", "magic"}),
            
            # DRUID SPELLS - Balance
            SpellMetadata(78674, "Starsurge", SpellSchool.ARCANE, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=2.0, cast_time=2.0,
                         tags={"ranged", "balance", "astral_power"}),
            
            SpellMetadata(190984, "Solar Wrath", SpellSchool.NATURE, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.2, cast_time=2.5,
                         tags={"ranged", "balance", "solar"}),
            
            # Druid - Restoration
            SpellMetadata(8936, "Regrowth", SpellSchool.NATURE, SpellType.HEAL, SpellRole.HEALER_THROUGHPUT,
                         can_crit=True, direct_damage=False, base_coefficient=1.8, cast_time=1.5,
                         periodic_damage=True, periodic_interval=2.0,
                         tags={"heal", "restoration", "hot"}),
            
            SpellMetadata(774, "Rejuvenation", SpellSchool.NATURE, SpellType.HEAL, SpellRole.HEALER_THROUGHPUT,
                         can_crit=True, periodic_damage=True, periodic_interval=3.0, is_instant=True,
                         tags={"heal", "restoration", "hot", "instant"}),
            
            # HUNTER SPELLS - Marksmanship
            SpellMetadata(19434, "Aimed Shot", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=2.5, cast_time=2.5,
                         tags={"ranged", "marksmanship", "focus"}),
            
            SpellMetadata(185358, "Arcane Shot", SpellSchool.ARCANE, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.0, is_instant=True,
                         tags={"ranged", "marksmanship", "focus"}),
            
            SpellMetadata(147362, "Counter Shot", SpellSchool.PHYSICAL, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=3.0, cooldown=24.0, is_instant=True,
                         tags={"interrupt", "utility"}),
            
            # MAGE SPELLS - Fire
            SpellMetadata(133, "Fireball", SpellSchool.FIRE, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.8, cast_time=2.25,
                         tags={"ranged", "fire", "projectile"}),
            
            SpellMetadata(108853, "Fire Blast", SpellSchool.FIRE, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.0, is_instant=True,
                         cooldown=12.0, tags={"ranged", "fire", "instant"}),
            
            SpellMetadata(2139, "Counterspell", SpellSchool.ARCANE, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=6.0, cooldown=24.0, is_instant=True,
                         tags={"interrupt", "silence"}),
            
            # Mage - Frost
            SpellMetadata(116, "Frostbolt", SpellSchool.FROST, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.5, cast_time=2.0,
                         tags={"ranged", "frost", "projectile", "chill"}),
            
            SpellMetadata(44614, "Flurry", SpellSchool.FROST, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.2, is_instant=True,
                         tags={"ranged", "frost", "instant", "brain_freeze"}),
            
            # MONK SPELLS - Windwalker
            SpellMetadata(100780, "Tiger Palm", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.0, is_instant=True,
                         tags={"melee", "windwalker", "chi"}),
            
            SpellMetadata(113656, "Fists of Fury", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=3.0, is_channeled=True,
                         cast_time=4.0, cooldown=24.0, tags={"melee", "windwalker", "channel"}),
            
            SpellMetadata(116705, "Spear Hand Strike", SpellSchool.PHYSICAL, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=4.0, cooldown=15.0, is_instant=True,
                         tags={"interrupt", "melee"}),
            
            # PALADIN SPELLS - Retribution
            SpellMetadata(85256, "Templar's Verdict", SpellSchool.HOLY, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=2.2, is_instant=True,
                         tags={"melee", "retribution", "holy_power"}),
            
            SpellMetadata(35395, "Crusader Strike", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.0, is_instant=True,
                         tags={"melee", "retribution", "holy_power_gen"}),
            
            SpellMetadata(96231, "Rebuke", SpellSchool.PHYSICAL, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=4.0, cooldown=15.0, is_instant=True,
                         tags={"interrupt", "melee"}),
            
            # Paladin - Holy
            SpellMetadata(635, "Holy Light", SpellSchool.HOLY, SpellType.HEAL, SpellRole.HEALER_THROUGHPUT,
                         can_crit=True, base_coefficient=2.5, cast_time=2.5,
                         tags={"heal", "holy", "big_heal"}),
            
            SpellMetadata(82326, "Flash of Light", SpellSchool.HOLY, SpellType.HEAL, SpellRole.HEALER_THROUGHPUT,
                         can_crit=True, base_coefficient=1.8, cast_time=1.5,
                         tags={"heal", "holy", "fast_heal"}),
            
            # PRIEST SPELLS - Shadow
            SpellMetadata(8092, "Mind Blast", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.8, cast_time=1.5,
                         tags={"ranged", "shadow", "insanity"}),
            
            SpellMetadata(589, "Shadow Word: Pain", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, periodic_damage=True, periodic_interval=2.0, is_instant=True,
                         tags={"ranged", "shadow", "dot"}),
            
            SpellMetadata(15487, "Silence", SpellSchool.SHADOW, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.SILENCE, cc_duration=4.0, cooldown=30.0, is_instant=True,
                         tags={"silence", "cc"}),
            
            # ROGUE SPELLS - Assassination
            SpellMetadata(1329, "Mutilate", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.4, is_instant=True,
                         tags={"melee", "assassination", "poison", "combo_point"}),
            
            SpellMetadata(32645, "Envenom", SpellSchool.NATURE, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=2.0, is_instant=True,
                         tags={"melee", "assassination", "poison", "finisher"}),
            
            SpellMetadata(1766, "Kick", SpellSchool.PHYSICAL, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=5.0, cooldown=15.0, is_instant=True,
                         tags={"interrupt", "melee"}),
            
            # SHAMAN SPELLS - Elemental
            SpellMetadata(188196, "Lightning Bolt", SpellSchool.NATURE, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.5, cast_time=2.0,
                         tags={"ranged", "elemental", "maelstrom"}),
            
            SpellMetadata(188443, "Chain Lightning", SpellSchool.NATURE, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, direct_damage=True, base_coefficient=1.2, cast_time=2.0,
                         tags={"ranged", "elemental", "chain", "aoe"}),
            
            SpellMetadata(57994, "Wind Shear", SpellSchool.NATURE, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=3.0, cooldown=12.0, is_instant=True,
                         tags={"interrupt", "nature"}),
            
            # WARLOCK SPELLS - Affliction
            SpellMetadata(172, "Corruption", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, periodic_damage=True, periodic_interval=2.0, is_instant=True,
                         tags={"ranged", "affliction", "dot", "instant"}),
            
            SpellMetadata(980, "Agony", SpellSchool.SHADOW, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, periodic_damage=True, periodic_interval=2.0, is_instant=True,
                         tags={"ranged", "affliction", "dot", "stacking"}),
            
            SpellMetadata(5782, "Fear", SpellSchool.SHADOW, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.FEAR, cc_duration=8.0, pvp_duration_modifier=0.5,
                         breaks_on_damage=True, cast_time=1.7, tags={"fear", "cc"}),
            
            # WARRIOR SPELLS - Arms
            SpellMetadata(12294, "Mortal Strike", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_BURST,
                         can_crit=True, direct_damage=True, base_coefficient=1.8, is_instant=True,
                         cooldown=6.0, tags={"melee", "arms", "healing_reduction"}),
            
            SpellMetadata(772, "Rend", SpellSchool.PHYSICAL, SpellType.DAMAGE, SpellRole.DPS_SUSTAIN,
                         can_crit=True, periodic_damage=True, periodic_interval=3.0, is_instant=True,
                         tags={"melee", "arms", "bleed", "dot"}),
            
            SpellMetadata(6552, "Pummel", SpellSchool.PHYSICAL, SpellType.CROWD_CONTROL, SpellRole.SUPPORT_UTILITY,
                         cc_type=CrowdControlType.INTERRUPT, cc_duration=4.0, cooldown=15.0, is_instant=True,
                         tags={"interrupt", "melee"}),
        ]
        
        # Add all spells to the system
        for spell in core_spells:
            self.add_spell(spell)
    
    def add_spell(self, spell: SpellMetadata):
        """Add a spell to the metadata system."""
        self.spells[spell.spell_id] = spell
        self.name_to_id[spell.name.lower()] = spell.spell_id
        
        # Update category indexes
        self._update_indexes_for_spell(spell)
    
    def _update_indexes_for_spell(self, spell: SpellMetadata):
        """Update category indexes for a spell."""
        categories = [
            f"school_{spell.school.value.lower()}",
            f"type_{spell.spell_type.value.lower()}",
            f"role_{spell.role.value.lower()}",
        ]
        
        if spell.cc_type:
            categories.append(f"cc_{spell.cc_type.value.lower()}")
        
        # Add tag-based categories
        for tag in spell.tags:
            categories.append(f"tag_{tag}")
        
        for category in categories:
            if category not in self.category_indexes:
                self.category_indexes[category] = set()
            self.category_indexes[category].add(spell.spell_id)
    
    def _build_indexes(self):
        """Build all category indexes."""
        self.category_indexes.clear()
        for spell in self.spells.values():
            self._update_indexes_for_spell(spell)
    
    def get_spell(self, identifier: Union[int, str]) -> Optional[SpellMetadata]:
        """Get spell by ID or name."""
        if isinstance(identifier, int):
            return self.spells.get(identifier)
        elif isinstance(identifier, str):
            spell_id = self.name_to_id.get(identifier.lower())
            return self.spells.get(spell_id) if spell_id else None
        return None
    
    def get_spells_by_category(self, category: str) -> List[SpellMetadata]:
        """Get all spells in a category."""
        spell_ids = self.category_indexes.get(category, set())
        return [self.spells[spell_id] for spell_id in spell_ids]
    
    def get_damage_spells(self) -> List[SpellMetadata]:
        """Get all damage dealing spells."""
        return self.get_spells_by_category("type_damage")
    
    def get_healing_spells(self) -> List[SpellMetadata]:
        """Get all healing spells."""
        return self.get_spells_by_category("type_heal")
    
    def get_crowd_control_spells(self) -> List[SpellMetadata]:
        """Get all crowd control spells."""
        return self.get_spells_by_category("type_crowd control")
    
    def get_interrupt_spells(self) -> List[SpellMetadata]:
        """Get all interrupt spells."""
        return self.get_spells_by_category("cc_interrupt")
    
    def get_spells_by_school(self, school: SpellSchool) -> List[SpellMetadata]:
        """Get all spells of a specific school."""
        return self.get_spells_by_category(f"school_{school.value.lower()}")
    
    def get_spells_by_class_spec(self, class_spec: str) -> List[SpellMetadata]:
        """Get spells for a specific class/spec combination."""
        return self.get_spells_by_category(f"tag_{class_spec}")
    
    def classify_spell_damage_event(self, spell_id: int, damage_amount: int) -> Dict:
        """Classify a damage event based on spell metadata."""
        spell = self.get_spell(spell_id)
        if not spell:
            return {
                'spell_id': spell_id,
                'classification': 'unknown',
                'school': 'unknown',
                'type': 'unknown',
                'role': 'unknown'
            }
        
        # Determine damage classification
        if damage_amount == 0:
            damage_type = "miss_or_immune"
        elif spell.base_coefficient > 1.8:
            damage_type = "high_damage"
        elif spell.base_coefficient > 1.2:
            damage_type = "moderate_damage"
        else:
            damage_type = "low_damage"
        
        return {
            'spell_id': spell_id,
            'spell_name': spell.name,
            'classification': damage_type,
            'school': spell.school.value,
            'type': spell.spell_type.value,
            'role': spell.role.value,
            'is_burst': spell.role == SpellRole.DPS_BURST,
            'is_sustain': spell.role == SpellRole.DPS_SUSTAIN,
            'can_crit': spell.can_crit,
            'tags': list(spell.tags)
        }
    
    def analyze_spell_usage(self, spell_events: List[Dict]) -> Dict:
        """Analyze patterns in spell usage."""
        if not spell_events:
            return {}
        
        # Count usage by category
        school_usage = {}
        type_usage = {}
        role_usage = {}
        
        total_events = len(spell_events)
        damage_events = 0
        heal_events = 0
        cc_events = 0
        
        for event in spell_events:
            spell_id = event.get('spell_id')
            spell = self.get_spell(spell_id)
            
            if spell:
                # Count by school
                school = spell.school.value
                school_usage[school] = school_usage.get(school, 0) + 1
                
                # Count by type
                spell_type = spell.spell_type.value
                type_usage[spell_type] = type_usage.get(spell_type, 0) + 1
                
                # Count by role
                role = spell.role.value
                role_usage[role] = role_usage.get(role, 0) + 1
                
                # Count event types
                if spell.spell_type == SpellType.DAMAGE:
                    damage_events += 1
                elif spell.spell_type == SpellType.HEAL:
                    heal_events += 1
                elif spell.spell_type == SpellType.CROWD_CONTROL:
                    cc_events += 1
        
        return {
            'total_events': total_events,
            'damage_events': damage_events,
            'heal_events': heal_events,
            'cc_events': cc_events,
            'school_distribution': school_usage,
            'type_distribution': type_usage,
            'role_distribution': role_usage,
            'damage_percentage': (damage_events / total_events * 100) if total_events > 0 else 0,
            'heal_percentage': (heal_events / total_events * 100) if total_events > 0 else 0,
            'cc_percentage': (cc_events / total_events * 100) if total_events > 0 else 0
        }
    
    def export_metadata(self, file_path: str):
        """Export spell metadata to JSON file."""
        export_data = {}
        for spell_id, spell in self.spells.items():
            export_data[str(spell_id)] = {
                'name': spell.name,
                'school': spell.school.value,
                'type': spell.spell_type.value,
                'role': spell.role.value,
                'can_crit': spell.can_crit,
                'can_miss': spell.can_miss,
                'is_channeled': spell.is_channeled,
                'is_instant': spell.is_instant,
                'cast_time': spell.cast_time,
                'cooldown': spell.cooldown,
                'cc_type': spell.cc_type.value if spell.cc_type else None,
                'cc_duration': spell.cc_duration,
                'is_dispellable': spell.is_dispellable,
                'dispel_priority': spell.dispel_priority,
                'base_coefficient': spell.base_coefficient,
                'direct_damage': spell.direct_damage,
                'periodic_damage': spell.periodic_damage,
                'periodic_interval': spell.periodic_interval,
                'amplifies_damage': spell.amplifies_damage,
                'amplifies_healing': spell.amplifies_healing,
                'damage_multiplier': spell.damage_multiplier,
                'healing_multiplier': spell.healing_multiplier,
                'pvp_duration_modifier': spell.pvp_duration_modifier,
                'breaks_on_damage': spell.breaks_on_damage,
                'limited_targets': spell.limited_targets,
                'tags': list(spell.tags)
            }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def get_statistics(self) -> Dict:
        """Get system statistics."""
        total_spells = len(self.spells)
        
        # Count by categories
        schools = {}
        types = {}
        roles = {}
        
        for spell in self.spells.values():
            schools[spell.school.value] = schools.get(spell.school.value, 0) + 1
            types[spell.spell_type.value] = types.get(spell.spell_type.value, 0) + 1
            roles[spell.role.value] = roles.get(spell.role.value, 0) + 1
        
        cc_spells = len([s for s in self.spells.values() if s.cc_type])
        instant_spells = len([s for s in self.spells.values() if s.is_instant])
        channeled_spells = len([s for s in self.spells.values() if s.is_channeled])
        
        return {
            'total_spells': total_spells,
            'schools': schools,
            'types': types,
            'roles': roles,
            'crowd_control_spells': cc_spells,
            'instant_spells': instant_spells,
            'channeled_spells': channeled_spells,
            'category_indexes': len(self.category_indexes)
        }

def main():
    """Test the spell metadata system."""
    print("=== SPELL METADATA SYSTEM TEST ===")
    
    # Initialize system
    spell_system = SpellMetadataSystem()
    
    # Get statistics
    stats = spell_system.get_statistics()
    print(f"\nSystem Statistics:")
    print(f"  Total spells: {stats['total_spells']}")
    print(f"  CC spells: {stats['crowd_control_spells']}")
    print(f"  Instant spells: {stats['instant_spells']}")
    print(f"  Category indexes: {stats['category_indexes']}")
    
    # Test spell lookup
    print(f"\nSpell Lookup Tests:")
    fireball = spell_system.get_spell("Fireball")
    if fireball:
        print(f"  Fireball: {fireball.school.value} {fireball.spell_type.value}")
        print(f"    Cast time: {fireball.cast_time}s, Coefficient: {fireball.base_coefficient}")
    
    counterspell = spell_system.get_spell(2139)  # By ID
    if counterspell:
        print(f"  Counterspell: {counterspell.cc_type.value if counterspell.cc_type else 'None'}")
        print(f"    Duration: {counterspell.cc_duration}s, Cooldown: {counterspell.cooldown}s")
    
    # Test category queries
    print(f"\nCategory Queries:")
    interrupts = spell_system.get_interrupt_spells()
    print(f"  Interrupt spells: {len(interrupts)}")
    for spell in interrupts[:3]:
        print(f"    {spell.name} ({spell.cc_duration}s duration)")
    
    fire_spells = spell_system.get_spells_by_school(SpellSchool.FIRE)
    print(f"  Fire spells: {len(fire_spells)}")
    
    # Test damage classification
    print(f"\nDamage Classification Test:")
    test_events = [
        {'spell_id': 133, 'damage': 5000},  # Fireball
        {'spell_id': 85256, 'damage': 8000},  # Templar's Verdict  
        {'spell_id': 2139, 'damage': 0},  # Counterspell
    ]
    
    for event in test_events:
        classification = spell_system.classify_spell_damage_event(
            event['spell_id'], event['damage']
        )
        print(f"  {classification['spell_name']}: {classification['classification']}")
        print(f"    School: {classification['school']}, Role: {classification['role']}")
    
    # Export metadata
    export_file = "spell_metadata_export.json"
    spell_system.export_metadata(export_file)
    print(f"\nMetadata exported to: {export_file}")

if __name__ == "__main__":
    main()