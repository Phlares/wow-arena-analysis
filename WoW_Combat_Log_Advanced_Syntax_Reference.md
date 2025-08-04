# WoW Combat Log Advanced Syntax Reference

## Overview
This document provides the definitive syntax for World of Warcraft Advanced Combat Logging, based on validated arena combat log analysis.

**Required Setup**: `advancedCombatLoggingDefault` CVar must be enabled.
**Coordinate Availability**: Position data only available during PvP arena matches with advanced logging enabled.

## Combat Log Line Structure

```
TIMESTAMP  EVENT_TYPE,sourceGUID,sourceName,sourceFlags,sourceRaidFlags,destGUID,destName,destFlags,destRaidFlags,[PREFIX_PARAMS],[ADVANCED_PARAMS],[SUFFIX_PARAMS]
```

## Validated Coordinate Event Types

**Events with Position Data (Arena Matches Only):**
- `SPELL_CAST_SUCCESS` (31 params) - Position at 26-27
- `SPELL_HEAL` (36 params) - Position at 26-27
- `SPELL_DAMAGE` (42 params) - Position at 26-27
- `SPELL_PERIODIC_DAMAGE` (42 params) - Position at 26-27
- `DAMAGE_SPLIT` (42 params) - Position at 26-27
- `SPELL_ENERGIZE` (35 params) - Position at 26-27
- `SPELL_PERIODIC_HEAL` (36 params) - Position at 26-27
- `SPELL_PERIODIC_ENERGIZE` (35 params) - Position at 26-27
- `SPELL_DRAIN` (35 params) - Position at 26-27
- `SWING_DAMAGE` (38 params) - Position at 23-24
- `SWING_DAMAGE_LANDED` (38 params) - Position at 23-24

## Parameter Breakdown

### Base Parameters (Always Present)
1. **EVENT_TYPE** (string): Combat event type (e.g., SPELL_DAMAGE, SPELL_HEAL)
2. **sourceGUID** (string): GUID of source entity
3. **sourceName** (string): Name of source entity (quoted)
4. **sourceFlags** (hex): Source entity flags
5. **sourceRaidFlags** (hex): Source raid flags
6. **destGUID** (string): GUID of destination entity
7. **destName** (string): Name of destination entity (quoted)
8. **destFlags** (hex): Destination entity flags
9. **destRaidFlags** (hex): Destination raid flags

### Prefix Parameters (Event-Specific, 0-3 params)
**For SPELL events:**
- **spellId** (number): Spell ID
- **spellName** (string): Spell name (quoted)
- **spellSchool** (hex): Spell school bitmask

**For DAMAGE/HEAL events (additional):**
- **amount** (number): Damage/heal amount
- **overkill/overheal** (number): Excess amount
- **school** (hex): Damage school
- **resisted** (number): Amount resisted
- **blocked** (number): Amount blocked
- **absorbed** (number): Amount absorbed
- **critical** (boolean): Critical hit flag
- **glancing** (boolean): Glancing blow flag
- **crushing** (boolean): Crushing blow flag
- **isOffHand** (boolean): Off-hand attack flag

### Advanced Parameters (17 params when enabled)
1. **infoGUID** (string): GUID of unit providing advanced info
2. **ownerGUID** (string): GUID of owner (for pets/minions)
3. **currentHP** (number): Current health points
4. **maxHP** (number): Maximum health points
5. **attackPower** (number): Attack power value
6. **spellPower** (number): Spell power value
7. **armor** (number): Armor value
8. **absorb** (number): Active absorb amount
9. **powerType** (number): Power type enum (0=Mana, 1=Rage, 2=Focus, 3=Energy, 6=Runic Power)
10. **currentPower** (number): Current power amount
11. **maxPower** (number): Maximum power amount
12. **powerCost** (number): Power cost of ability
13. **positionX** (number): X coordinate on map instance
14. **positionY** (number): Y coordinate on map instance
15. **uiMapID** (number): UI Map identifier
16. **facing** (number): Unit facing direction (0-2π radians)
17. **level** (number): NPC level or player item level

### Suffix Parameters (Event-Specific, 0-10 params)
**For DAMAGE events:**
- **unconsciousOnDeath** (boolean): Unit becomes unconscious on death
- **missType** (string): Miss type if applicable
- **isOffHand** (boolean): Off-hand weapon attack
- **multistrike** (boolean): Multistrike attack

## Position Data Specifics

### Coordinate Systems
Based on our analysis, WoW uses multiple coordinate systems simultaneously:

1. **World Coordinates**: Large-scale positioning (e.g., -1938.60, 1368.80)
2. **Instance Coordinates**: Local instance positioning (e.g., 7.0, 30.0)
3. **UI Map Coordinates**: Interface positioning (e.g., 3.0, 300.0)

### Position Parameter Locations
- **positionX**: Parameter 13 in advanced section (0-based index from start of advanced params)
- **positionY**: Parameter 14 in advanced section
- **facing**: Parameter 16 in advanced section

## Validated Combat Log Examples

### SPELL_CAST_SUCCESS (31 parameters, position at 26-27)
```
5/6/2025 19:04:25.703-4  SPELL_CAST_SUCCESS,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x512,0x40,0000000000000000,nil,0x80000000,0x80000000,115191,"Stealth",0x1,Player-11-0E366FE1,0000000000000000,10282260,10282260,98686,13440,33841,2396,0,0,3,300,300,0,-1938.60,1368.80,0,3.9970,673
```

**Parameter Breakdown:**
1. `SPELL_CAST_SUCCESS` - Event type
2. `Player-11-0E366FE1` - Source GUID
3. `"Morvx-Tichondrius-US"` - Source name
4. `0x512` - Source flags
5. `0x40` - Source raid flags
6. `0000000000000000` - Dest GUID
7. `nil` - Dest name
8. `0x80000000` - Dest flags
9. `0x80000000` - Dest raid flags
10. `115191` - Spell ID
11. `"Stealth"` - Spell name
12. `0x1` - Spell school
13. `Player-11-0E366FE1` - Info GUID (advanced logging starts)
14. `0000000000000000` - Owner GUID
15. `10282260` - Current HP
16. `10282260` - Max HP
17. `98686` - Attack power
18. `13440` - Spell power
19. `33841` - Armor
20. `2396` - Absorb
21. `0` - Unknown
22. `0` - Unknown
23. `3` - Power type (Energy)
24. `300` - Current power
25. `300` - Max power
26. `0` - Power cost
27. **`-1938.60`** - **Position X**
28. **`1368.80`** - **Position Y**
29. `0` - UI Map ID
30. `3.9970` - Facing
31. `673` - Level/Item level

### SWING_DAMAGE (38 parameters, position at 23-24)
```
5/6/2025 19:04:39.588-4  SWING_DAMAGE,Creature-0-3021-1911-5918-89-00001A958A,"Infernal",0x2148,0x0,Player-11-0E366FE1,"Morvx-Tichondrius-US",0x512,0x40,Creature-0-3021-1911-5918-89-00001A958A,Player-73-0F4BC0DB,9542657,9542657,229341,229341,211916,0,0,0,1,0,0,0,-1959.79,1281.14,0,0.2559,676,72307,119039,-1,1,0,0,0,nil,nil,nil
```

**Key Differences for SWING events:**
- No spell parameters (10-12 missing)
- Position coordinates at parameters 24-25 instead of 27-28
- Extended damage parameters at the end

## Power Type Enumeration

| Value | Power Type |
|-------|------------|
| 0 | Mana |
| 1 | Rage |
| 2 | Focus |
| 3 | Energy |
| 4 | Combo Points |
| 5 | Runes |
| 6 | Runic Power |
| 7 | Soul Shards |
| 8 | Lunar Power |
| 9 | Holy Power |
| 10 | Alternate Power |
| 11 | Maelstrom |
| 12 | Chi |
| 13 | Insanity |
| 14 | Burning Embers |
| 15 | Demonic Fury |
| 17 | Fury |
| 18 | Pain |

## Event Types We Track for Movement

### Primary Events (with reliable position data):
- **SPELL_CAST_SUCCESS**: Spell completion
- **SPELL_CAST_START**: Spell initiation  
- **SPELL_DAMAGE**: Direct spell damage
- **SPELL_PERIODIC_DAMAGE**: DoT ticks
- **SPELL_HEAL**: Direct healing
- **SPELL_PERIODIC_HEAL**: HoT ticks
- **SPELL_ENERGIZE**: Resource generation
- **SPELL_PERIODIC_ENERGIZE**: Periodic resource gain
- **SWING_DAMAGE**: Melee attacks
- **SWING_DAMAGE_LANDED**: Successful melee hits
- **RANGE_DAMAGE**: Ranged weapon attacks

## Important Notes

1. **Position Data Source**: Advanced parameters belong to the **SOURCE** entity, not the target
2. **GUID Tracking**: Use full GUID + Name combination for unique unit identification
3. **Coordinate Validation**: Expect multiple coordinate systems, don't suppress large movements
4. **Missing Data**: Some events may have nil/empty advanced parameters
5. **Pet Handling**: ownerGUID links pets to their owners
6. **Facing Range**: 0-2π radians (0 = North, π/2 = East, π = South, 3π/2 = West)

## Combat Log Parsing Best Practices

1. **Split Method**: Use `split('  ', 1)` to separate timestamp from event data
2. **Parameter Parsing**: Split event data by commas, handle quoted strings properly
3. **Advanced Detection**: Check parameter count (typically 20+ for advanced logging)
4. **Type Conversion**: Convert numeric parameters with proper error handling
5. **GUID Validation**: Verify GUID format and entity types
6. **Position Validation**: Accept reasonable coordinate ranges per system type

## Reference Implementation

```python
def parse_advanced_combat_line(line: str) -> Dict:
    """Parse advanced combat log line following WoWPedia specification."""
    parts = line.strip().split('  ', 1)
    if len(parts) != 2:
        return None
    
    timestamp_str, event_data = parts
    params = [p.strip() for p in event_data.split(',')]
    
    if len(params) < 20:  # No advanced logging
        return None
    
    # Extract advanced parameters (start after base + prefix params)
    # For SPELL_CAST_SUCCESS: 9 base + 3 spell = 12, advanced starts at index 12
    advanced_start = 12  # Adjust based on event type
    
    return {
        'timestamp': parse_timestamp(timestamp_str),
        'event': params[0],
        'source_guid': params[1],
        'source_name': extract_quoted_name(params[2]),
        'spell_id': int(params[9]) if len(params) > 9 else None,
        'spell_name': extract_quoted_name(params[10]) if len(params) > 10 else None,
        
        # Advanced parameters
        'info_guid': params[advanced_start] if len(params) > advanced_start else None,
        'owner_guid': params[advanced_start + 1] if len(params) > advanced_start + 1 else None,
        'current_hp': int(params[advanced_start + 2]) if len(params) > advanced_start + 2 else 0,
        'max_hp': int(params[advanced_start + 3]) if len(params) > advanced_start + 3 else 0,
        'position_x': float(params[advanced_start + 12]) if len(params) > advanced_start + 12 else 0.0,
        'position_y': float(params[advanced_start + 13]) if len(params) > advanced_start + 13 else 0.0,
        'facing': float(params[advanced_start + 15]) if len(params) > advanced_start + 15 else 0.0,
    }
```

This reference provides the complete specification for parsing WoW Advanced Combat Logs with proper parameter positioning and data types.