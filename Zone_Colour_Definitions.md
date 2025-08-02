# Zone Colour Definitions

This document defines the color coding system used for computer vision zone delineation in the WoW Arena analysis system (3440x1440 resolution).

## Color Definitions

| Colour | Hex Code | Signification | Notes |
|--------|----------|---------------|-------|
| Red | #ff3131 | Healthbars | These are health bars belonging to party members, enemy combatant characters, the player, and the target. |
| Dark Blue | #1800ad | Major Abilities | This is a summary of major abilities that each party or enemy player has access to. For party members it lists them all, and shows a timer on top of them when they are on cooldown or unavailable. For enemies it shows them on cooldown when unavailable, but otherwise hides the ability icon from view. |
| Light Cyan/Turquoise | #5ce1e6 | Resource Bars | These are resource bars (mana, rage, energy, etc) belonging to party members, enemy combatant characters, the player, and the target. |
| Yellow | #ffde59 | Specialized secondary Resource for Player | This resource bar tracks specialized resources like soul shards, combo points, and others. |
| Light Green | #7ed957 | Names of characters in party, player, player pets, target, or spell | These are where the names of the characters appear, they are adjacent or within the healthbars or cast bars of their corresponding pet/character/player. |
| Orange | #ff914d | Combat log details | Many onscreen at once, titles near the top qualify what metric is being measured, underneath it a list of characters, sometimes nicknames are used and may need to be matched logically with combat log to track changes effectively. |
| White | #ffffff | Enemy Arena Medallion | This area shows the cooldown of the enemy combatant's arena medallion, which removes all crowd control, if they have one. |
| Dark Gray/Almost Black | #171717 | Enemy dispell | This area shows the cooldown of the enemy combatant's dispell if they have one. |
| Pink/Magenta | #ff66c4 | Enemy Arena Combatant Racial Ability | This zone shows the enemy arena combatant's racial ability and tracks the cooldown on it if used. |
| Brown | #5a321d | Player and enemy cast bars | These represent the cast bars of players and enemies, depending on which zone they represent the player, or Arena Enemy 1, 2 or 3. |
| Purple | #5e17eb | Player Ability Icons | These represent the zones where the icons for player abilities or icons are. They are fully illuminated when available, greyed out when unavailable, and can have a timer on top of them with a grey swiping texture demonstrating how long we need to wait to use them again. |
| Light Purple | #8c52ff | Player Pet Ability Icons | These represent the zones where the icons for player pet abilities or icons are. They are fully illuminated when available, greyed out when unavailable, and can have a timer on top of them with a grey swiping texture demonstrating how long we need to wait to use them again. |
| Red-Orange | #e84d20 | Debuffs - Player & Target | These represent AURAs in the combat log that are negative, there is one zone for the player and one zone for the enemies. |
| Olive Green | #768047 | Buffs - Player & Target | These represent AURAs in the combat log that are positive/neutral, there is one zone for the player and one zone for the enemies. |
| Light Gray | #a6a6a6 | Enemy Crowd Control Diminishing Return Tracker | This section populates any time an arena enemy ends up on a crowd control diminishing return timer. The color of the border represents what stage the diminishing return the crowd control is subject to (Green - 3/4 duration, Yellow - 1/2 duration, Orange - 1/4 duration, Red - immune to that type of crowd control until timer is complete). |
| Light Red | #ff5757 | Arena Information | This section displays text for how many living players are on each team, how much time is left in the arena, what round of solo shuffle (if applicable) and what percentage dampening is. |
| Blue | #5170ff | Major affect on player | If the player is crowd controlled, or interrupted, the affect and icon of the source spell shows up here. |
| Medium Gray | #545454 | Party Healer is in Crowd Control | This zone populates when the friendly healer is in crowd control (cannot act). It has a healer CC text zone, the icon representing the crowd control affecting them, and a timer at the bottom. |
| Teal/Cyan | #0097b2 | Location Title | This text area shows the title of the current Zone. |
| Dark Brown/Maroon | #330a0a | Current Time | This zone always represents the current time. |

## Multi-Instance Zone Enumeration - CORRECTED

Based on the corrected zone extraction from the annotated SVG, the following zones have been properly identified:

### Red (#ff3131) - Healthbars
- **Count**: 9 instances (CORRECTED from 6)
- **Locations**: Player Health (multiple bars), Target Health, Arena Enemy Health bars

### Dark Blue (#1800ad) - Major Abilities  
- **Count**: 6 instances
- **Locations**: Need enumeration for Party 1, Party 2, Player, Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

### Light Cyan/Turquoise (#5ce1e6) - Resource Bars
- **Count**: 6 instances  
- **Locations**: Need enumeration for Party 1, Party 2, Player, Target, Arena Enemy 1, Arena Enemy 2

### Yellow (#ffde59) - Specialized secondary Resource for Player
- **Count**: 3 instances
- **Locations**: Need enumeration for different specialized resource types

### Light Green (#7ed957) - Character Names
- **Count**: 5 instances
- **Locations**: Need enumeration for Party 1, Party 2, Player, Target, Arena Enemy names

### Orange (#ff914d) - Combat log details
- **Count**: 8 instances
- **Locations**: Need enumeration for different combat metrics sections

### White (#ffffff) - Enemy Arena Medallion
- **Count**: 3 instances
- **Locations**: Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

### Dark Gray/Almost Black (#171717) - Enemy dispell
- **Count**: 3 instances
- **Locations**: Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

### Pink/Magenta (#ff66c4) - Enemy Arena Combatant Racial Ability
- **Count**: 3 instances
- **Locations**: Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

### Brown (#5a321d) - Player and enemy cast bars
- **Count**: 4 instances
- **Locations**: Player, Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

### Red-Orange (#e84d20) - Debuffs
- **Count**: 2 instances
- **Locations**: Player Debuffs, Target/Enemy Debuffs

### Olive Green (#768047) - Buffs
- **Count**: 2 instances
- **Locations**: Player Buffs, Target/Enemy Buffs

### Light Gray (#a6a6a6) - Enemy Crowd Control Diminishing Return Tracker
- **Count**: 3 instances
- **Locations**: Arena Enemy 1, Arena Enemy 2, Arena Enemy 3

---

*Generated for WoW Arena Computer Vision Analysis System*
*Resolution: 3440x1440*
*Last Updated: 2025-08-01*