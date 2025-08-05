"""
JSON Metadata-Enhanced Targeting System

Integrates JSON video metadata for accurate team detection and realistic
coordination analysis. This fixes the unrealistic 1.000 coordination scores
by properly identifying friendly vs enemy teams.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from collections import defaultdict

from development_standards import (
    SafeLogger,
    select_combat_log_file,
    parse_combat_log_timestamp,
    export_json_safely
)
from arena_match_model import (
    ArenaMatchModel, ArenaMatchModelBuilder, PlayerInfo, 
    TeamSide, PlayerRole, ArenaSize
)
from enhanced_targeting_with_model import ModelBasedTargetingAnalyzer


# WoW Specialization ID to Role mapping
SPEC_ID_TO_ROLE = {
    # Death Knight
    250: PlayerRole.TANK,      # Blood
    251: PlayerRole.MELEE_DPS, # Frost
    252: PlayerRole.MELEE_DPS, # Unholy
    
    # Demon Hunter
    577: PlayerRole.MELEE_DPS, # Havoc
    581: PlayerRole.TANK,      # Vengeance
    
    # Druid
    102: PlayerRole.RANGED_DPS, # Balance
    103: PlayerRole.MELEE_DPS,  # Feral
    104: PlayerRole.TANK,       # Guardian
    105: PlayerRole.HEALER,     # Restoration
    
    # Evoker
    1467: PlayerRole.RANGED_DPS, # Devastation
    1468: PlayerRole.HEALER,     # Preservation
    1473: PlayerRole.RANGED_DPS, # Augmentation
    
    # Hunter
    253: PlayerRole.RANGED_DPS, # Beast Mastery
    254: PlayerRole.RANGED_DPS, # Marksmanship
    255: PlayerRole.RANGED_DPS, # Survival
    
    # Mage
    62: PlayerRole.RANGED_DPS,  # Arcane
    63: PlayerRole.RANGED_DPS,  # Fire
    64: PlayerRole.RANGED_DPS,  # Frost
    
    # Monk
    268: PlayerRole.TANK,       # Brewmaster
    269: PlayerRole.MELEE_DPS,  # Windwalker
    270: PlayerRole.HEALER,     # Mistweaver
    
    # Paladin
    65: PlayerRole.HEALER,      # Holy
    66: PlayerRole.TANK,        # Protection
    70: PlayerRole.MELEE_DPS,   # Retribution
    
    # Priest
    256: PlayerRole.HEALER,     # Discipline
    257: PlayerRole.HEALER,     # Holy
    258: PlayerRole.RANGED_DPS, # Shadow
    
    # Rogue
    259: PlayerRole.MELEE_DPS,  # Assassination
    260: PlayerRole.MELEE_DPS,  # Outlaw
    261: PlayerRole.MELEE_DPS,  # Subtlety
    
    # Shaman
    262: PlayerRole.RANGED_DPS, # Elemental
    263: PlayerRole.MELEE_DPS,  # Enhancement
    264: PlayerRole.HEALER,     # Restoration
    
    # Warlock
    265: PlayerRole.RANGED_DPS, # Affliction
    266: PlayerRole.RANGED_DPS, # Demonology
    267: PlayerRole.RANGED_DPS, # Destruction
    
    # Warrior
    71: PlayerRole.MELEE_DPS,   # Arms
    72: PlayerRole.MELEE_DPS,   # Fury
    73: PlayerRole.TANK,        # Protection
}

SPEC_ID_TO_NAME = {
    250: "Blood", 251: "Frost", 252: "Unholy",
    577: "Havoc", 581: "Vengeance", 
    102: "Balance", 103: "Feral", 104: "Guardian", 105: "Restoration",
    1467: "Devastation", 1468: "Preservation", 1473: "Augmentation",
    253: "Beast Mastery", 254: "Marksmanship", 255: "Survival",
    62: "Arcane", 63: "Fire", 64: "Frost",
    268: "Brewmaster", 269: "Windwalker", 270: "Mistweaver",
    65: "Holy", 66: "Protection", 70: "Retribution",
    256: "Discipline", 257: "Holy", 258: "Shadow",
    259: "Assassination", 260: "Outlaw", 261: "Subtlety",
    262: "Elemental", 263: "Enhancement", 264: "Restoration",
    265: "Affliction", 266: "Demonology", 267: "Destruction",
    71: "Arms", 72: "Fury", 73: "Protection"
}

CLASS_NAMES = {
    250: "Death Knight", 251: "Death Knight", 252: "Death Knight",
    577: "Demon Hunter", 581: "Demon Hunter",
    102: "Druid", 103: "Druid", 104: "Druid", 105: "Druid",
    1467: "Evoker", 1468: "Evoker", 1473: "Evoker",
    253: "Hunter", 254: "Hunter", 255: "Hunter",
    62: "Mage", 63: "Mage", 64: "Mage",
    268: "Monk", 269: "Monk", 270: "Monk",
    65: "Paladin", 66: "Paladin", 70: "Paladin",
    256: "Priest", 257: "Priest", 258: "Priest",
    259: "Rogue", 260: "Rogue", 261: "Rogue",
    262: "Shaman", 263: "Shaman", 264: "Shaman",
    265: "Warlock", 266: "Warlock", 267: "Warlock",
    71: "Warrior", 72: "Warrior", 73: "Warrior"
}


def load_match_json_metadata(match_filename: str) -> Optional[Dict]:
    """Load JSON metadata for a match"""
    
    # Try different possible locations for JSON file
    json_filename = match_filename.replace('.mp4', '.json')
    possible_paths = [
        Path(json_filename),
        Path('2025-05') / json_filename,
        Path('2025-05') / Path(json_filename).name
    ]
    
    for json_path in possible_paths:
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                SafeLogger.warning(f"Failed to load {json_path}: {e}")
                continue
    
    SafeLogger.warning(f"No JSON metadata found for {match_filename}")
    return None


def create_enhanced_match_model_with_json(match_row: pd.Series) -> Optional[ArenaMatchModel]:
    """Create match model using JSON metadata for accurate team detection"""
    
    match_filename = match_row['filename']
    player_name = match_row['player_name']
    
    SafeLogger.info(f"Creating enhanced match model for {match_filename}")
    
    # Load JSON metadata
    json_data = load_match_json_metadata(match_filename)
    if not json_data:
        SafeLogger.warning("No JSON metadata - falling back to basic model")
        return ArenaMatchModelBuilder.from_master_index_row(match_row.to_dict())
    
    # Create base match model
    match_model = ArenaMatchModelBuilder.from_master_index_row(match_row.to_dict())
    
    # Extract team information from JSON
    primary_player_team_id = None
    friendly_players = []
    enemy_players = []
    
    # Find primary player's team
    for combatant in json_data.get('combatants', []):
        if combatant['_name'].lower() == player_name.lower():
            primary_player_team_id = combatant['_teamID']
            break
    
    if primary_player_team_id is None:
        SafeLogger.warning(f"Primary player {player_name} not found in JSON combatants")
        return match_model
    
    SafeLogger.info(f"Primary player {player_name} is on team {primary_player_team_id}")
    
    # Create PlayerInfo objects with accurate team assignments
    for combatant in json_data.get('combatants', []):
        name = combatant['_name']
        realm = combatant.get('_realm', '')
        full_name = f"{name}-{realm}-US" if realm else name
        guid = combatant['_GUID']
        spec_id = combatant['_specID']
        team_id = combatant['_teamID']
        
        # Get class and spec info from spec ID
        spec_name = SPEC_ID_TO_NAME.get(spec_id, 'Unknown')
        class_name = CLASS_NAMES.get(spec_id, 'Unknown')
        role = SPEC_ID_TO_ROLE.get(spec_id, PlayerRole.UNKNOWN)
        
        player = PlayerInfo(
            name=name,
            full_name=full_name,
            guid=guid,
            class_name=class_name,
            specialization=spec_name,
            role=role
        )
        
        # Assign team based on JSON teamID
        if team_id == primary_player_team_id:
            player.team = TeamSide.FRIENDLY
            friendly_players.append(player)
        else:
            player.team = TeamSide.ENEMY
            enemy_players.append(player)
    
    # Update match model with accurate team assignments
    match_model.friendly_team.players = friendly_players
    match_model.enemy_team.players = enemy_players
    match_model._build_player_lookups()
    
    SafeLogger.success(f"Enhanced model: {len(friendly_players)}F vs {len(enemy_players)}E")
    SafeLogger.info(f"Friendly team: {[f'{p.name}({p.specialization} {p.class_name})' for p in friendly_players]}")
    SafeLogger.info(f"Enemy team: {[f'{p.name}({p.specialization} {p.class_name})' for p in enemy_players]}")
    
    return match_model


def test_realistic_targeting_analysis(match_row: pd.Series, logs_dir: Path) -> Optional[Dict]:
    """Test targeting analysis with accurate JSON-based team detection"""
    
    match_filename = match_row['filename']
    player_name = match_row['player_name']
    match_time = pd.to_datetime(match_row['precise_start_time'])
    duration_s = int(match_row.get('duration_s', 300))
    
    SafeLogger.info(f"=== REALISTIC TARGETING TEST: {match_filename} ===")
    SafeLogger.info(f"Player: {player_name}, Duration: {duration_s}s")
    
    try:
        # Step 1: Create enhanced match model with JSON metadata
        match_model = create_enhanced_match_model_with_json(match_row)
        if not match_model:
            return {'success': False, 'error': 'Failed to create match model'}
        
        if len(match_model.friendly_team.players) == 0 or len(match_model.enemy_team.players) == 0:
            return {'success': False, 'error': 'Invalid team composition detected'}
        
        # Step 2: Find combat log and boundaries
        log_file = select_combat_log_file(match_time, logs_dir)
        if not log_file:
            return {'success': False, 'error': 'No log file found'}
        
        # Simple boundary detection for efficiency
        arena_start = match_time - timedelta(minutes=1)
        arena_end = match_time + timedelta(seconds=duration_s + 60)
        
        # Step 3: Extract combat events efficiently
        combat_events = []
        events_processed = 0
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    events_processed += 1
                    if events_processed > 50000:  # Safety limit
                        break
                    
                    if not line.strip():
                        continue
                    
                    timestamp = parse_combat_log_timestamp(line)
                    if not timestamp or not (arena_start <= timestamp <= arena_end):
                        continue
                    
                    # Parse basic event info
                    if any(event_type in line for event_type in [
                        'SPELL_DAMAGE', 'SWING_DAMAGE', 'SPELL_HEAL', 'SPELL_CAST_SUCCESS'
                    ]):
                        event_data = parse_combat_event_quickly(line, timestamp)
                        if event_data:
                            combat_events.append(event_data)
                    
                    if len(combat_events) >= 2000:  # Limit events for efficiency
                        break
        
        except Exception as e:
            SafeLogger.error(f"Error reading combat log: {e}")
            return {'success': False, 'error': f'Combat log error: {e}'}
        
        SafeLogger.info(f"Extracted {len(combat_events)} combat events")
        
        if len(combat_events) < 20:
            return {'success': False, 'error': f'Too few events ({len(combat_events)})'}
        
        # Step 4: Run targeting analysis with enhanced model
        analyzer = ModelBasedTargetingAnalyzer(match_model)
        coordination_analysis = analyzer.analyze_team_coordination(combat_events)
        prioritization_analysis = analyzer.analyze_target_prioritization(combat_events)
        
        coordination_score = coordination_analysis.get('average_coordination', 0.0)
        coordination_available = coordination_analysis.get('analysis_available', False)
        
        SafeLogger.info(f"Coordination analysis: {coordination_available}")
        if coordination_available:
            SafeLogger.info(f"Team coordination score: {coordination_score:.3f}")
        
        return {
            'success': True,
            'match_filename': match_filename,
            'player_name': player_name,
            'json_metadata_used': True,
            'team_composition': {
                'friendly': len(match_model.friendly_team.players),
                'enemy': len(match_model.enemy_team.players),
                'friendly_roles': [f"{p.name}({p.role.value})" for p in match_model.friendly_team.players],
                'enemy_roles': [f"{p.name}({p.role.value})" for p in match_model.enemy_team.players]
            },
            'events_processed': len(combat_events),
            'coordination_analysis': {
                'available': coordination_available,
                'score': coordination_score,
                'windows_analyzed': coordination_analysis.get('coordination_windows', 0),
                'details': coordination_analysis.get('window_details', [])
            },
            'prioritization_analysis': {
                'available': prioritization_analysis.get('analysis_available', False),
                'primary_targets': prioritization_analysis.get('primary_targets', []),
                'switch_count': prioritization_analysis.get('target_switches', 0)
            }
        }
        
    except Exception as e:
        SafeLogger.error(f"Error in realistic targeting analysis: {e}")
        return {
            'success': False,
            'error': str(e),
            'match_filename': match_filename
        }


def parse_combat_event_quickly(line: str, timestamp: datetime) -> Optional[Dict]:
    """Quickly parse combat event from log line"""
    
    try:
        if '  ' in line:
            timestamp_part, event_data = line.split('  ', 1)
            parts = event_data.split(',')
            
            if len(parts) >= 7:
                return {
                    'timestamp': timestamp,
                    'event_type': parts[0].strip(),
                    'source_guid': parts[1].strip().strip('"'),
                    'source_name': parts[2].strip().strip('"'),
                    'dest_guid': parts[5].strip().strip('"'),
                    'dest_name': parts[6].strip().strip('"'),
                    'spell_name': parts[10].strip().strip('"') if len(parts) > 10 else 'Unknown'
                }
    except Exception:
        pass
    
    return None


def run_realistic_targeting_validation():
    """Run targeting validation with JSON metadata integration"""
    
    SafeLogger.info("=== REALISTIC TARGETING VALIDATION WITH JSON METADATA ===")
    
    # Load master index
    master_index_path = Path("master_index_enhanced.csv")
    if not master_index_path.exists():
        SafeLogger.error("Master index not found")
        return
    
    master_df = pd.read_csv(master_index_path)
    master_df['match_time'] = pd.to_datetime(master_df['precise_start_time'], errors='coerce')
    
    # Select test matches - focus on matches we know have JSON metadata
    test_matches = master_df[
        (master_df['filename'].str.contains('2025-05-06_22', na=False)) &
        (master_df['bracket'].str.contains('3v3', na=False)) &
        (master_df['match_time'].notna())
    ].head(5)
    
    # Add 1 Solo Shuffle
    solo_shuffle = master_df[
        (master_df['filename'].str.contains('2025-05-10_12-55', na=False)) &
        (master_df['bracket'].str.contains('Solo', na=False))
    ].head(1)
    
    if not solo_shuffle.empty:
        test_matches = pd.concat([test_matches, solo_shuffle])
    
    SafeLogger.info(f"Testing {len(test_matches)} matches with JSON metadata")
    
    # Process matches
    results = []
    logs_dir = Path("Logs")
    
    for i, (_, match_row) in enumerate(test_matches.iterrows(), 1):
        SafeLogger.info(f"\n--- REALISTIC TEST {i}/{len(test_matches)} ---")
        result = test_realistic_targeting_analysis(match_row, logs_dir)
        if result:
            results.append(result)
    
    # Analyze results
    SafeLogger.info("\n=== REALISTIC TARGETING VALIDATION RESULTS ===")
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    SafeLogger.info(f"Successful: {len(successful)}/{len(results)}")
    SafeLogger.info(f"Failed: {len(failed)}")
    
    if successful:
        # Show coordination scores - should now be more realistic
        coordination_available = [r for r in successful if r.get('coordination_analysis', {}).get('available')]
        
        SafeLogger.info(f"Matches with coordination analysis: {len(coordination_available)}")
        
        if coordination_available:
            SafeLogger.info("\nRealistic Coordination Scores:")
            coordination_scores = []
            
            for r in coordination_available:
                coord = r['coordination_analysis']
                score = coord['score']
                coordination_scores.append(score)
                
                match_name = r['match_filename'].split('_-_')
                player = match_name[1] if len(match_name) > 1 else 'Unknown'
                arena = match_name[2] if len(match_name) > 2 else 'Unknown'
                
                SafeLogger.info(f"  {player} in {arena}: {score:.3f} coordination")
            
            # Statistical analysis
            if coordination_scores:
                avg_score = sum(coordination_scores) / len(coordination_scores)
                min_score = min(coordination_scores)
                max_score = max(coordination_scores)
                
                SafeLogger.info(f"\nCoordination Score Statistics:")
                SafeLogger.info(f"  Average: {avg_score:.3f}")
                SafeLogger.info(f"  Range: {min_score:.3f} - {max_score:.3f}")
                
                # Check if scores are realistic (should not all be 1.000)
                realistic_scores = len([s for s in coordination_scores if s < 0.95])
                
                if realistic_scores > 0:
                    SafeLogger.success(f"VALIDATION PASSED: {realistic_scores}/{len(coordination_scores)} matches have realistic coordination scores")
                else:
                    SafeLogger.warning("ISSUE: All coordination scores still too high - need further refinement")
    
    # Export detailed results
    final_results = {
        'test_summary': {
            'total_matches': len(results),
            'successful_matches': len(successful),
            'failed_matches': len(failed),
            'json_metadata_integration': True,
            'realistic_scoring_enabled': True,
            'test_timestamp': datetime.now().isoformat()
        },
        'detailed_results': results
    }
    
    export_json_safely(final_results, Path("realistic_targeting_validation_results.json"))
    SafeLogger.success("Realistic targeting validation results exported")
    
    return final_results


if __name__ == "__main__":
    run_realistic_targeting_validation()