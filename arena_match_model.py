"""
Arena Match Data Model

Comprehensive data model for arena matches that enables sophisticated team coordination
and strategic analysis by providing structured context about players, teams, roles,
and match state.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum


class ArenaSize(Enum):
    """Arena bracket sizes"""
    TWO_V_TWO = "2v2"
    THREE_V_THREE = "3v3"
    SOLO_SHUFFLE = "Solo Shuffle"
    SKIRMISH = "Skirmish"


class PlayerRole(Enum):
    """Player roles inferred from specialization"""
    TANK = "Tank"
    HEALER = "Healer" 
    MELEE_DPS = "Melee DPS"
    RANGED_DPS = "Ranged DPS"
    UNKNOWN = "Unknown"


class TeamSide(Enum):
    """Team sides in arena"""
    FRIENDLY = "Friendly"
    ENEMY = "Enemy"


@dataclass
class PlayerInfo:
    """Complete player information"""
    name: str  # Base name without server
    full_name: str  # Full name with server (e.g., "Phlargus-Eredar-US")
    guid: str  # Player GUID from combat log
    class_name: str = "Unknown"
    specialization: str = "Unknown"
    role: PlayerRole = PlayerRole.UNKNOWN
    team: TeamSide = TeamSide.FRIENDLY
    pet_name: Optional[str] = None
    pet_guid: Optional[str] = None
    
    def __post_init__(self):
        """Infer role from class and specialization"""
        self.role = self._infer_role()
    
    def _infer_role(self) -> PlayerRole:
        """Infer player role from class and specialization"""
        # Common healing specializations
        healing_specs = {
            'Holy Priest', 'Discipline Priest', 'Holy Paladin', 'Restoration Shaman',
            'Restoration Druid', 'Mistweaver Monk', 'Holy Priest', 'Preservation Evoker'
        }
        
        # Common tank specializations  
        tank_specs = {
            'Protection Paladin', 'Protection Warrior', 'Blood Death Knight',
            'Guardian Druid', 'Brewmaster Monk', 'Vengeance Demon Hunter'
        }
        
        # Melee DPS classes (generally)
        melee_classes = {
            'Warrior', 'Rogue', 'Death Knight', 'Demon Hunter', 'Monk', 'Paladin'
        }
        
        spec_key = f"{self.specialization} {self.class_name}".strip()
        
        if spec_key in healing_specs or 'Holy' in self.specialization or 'Restoration' in self.specialization:
            return PlayerRole.HEALER
        elif spec_key in tank_specs or 'Protection' in self.specialization:
            return PlayerRole.TANK
        elif self.class_name in melee_classes:
            return PlayerRole.MELEE_DPS
        elif self.class_name in {'Mage', 'Warlock', 'Hunter', 'Evoker'}:
            return PlayerRole.RANGED_DPS
        else:
            return PlayerRole.UNKNOWN


@dataclass
class TeamComposition:
    """Team composition and strategy info"""
    players: List[PlayerInfo] = field(default_factory=list)
    healers: List[PlayerInfo] = field(default_factory=list)
    dps: List[PlayerInfo] = field(default_factory=list)
    tanks: List[PlayerInfo] = field(default_factory=list)
    
    def __post_init__(self):
        """Categorize players by role"""
        self.healers = [p for p in self.players if p.role == PlayerRole.HEALER]
        self.dps = [p for p in self.players if p.role in [PlayerRole.MELEE_DPS, PlayerRole.RANGED_DPS]]
        self.tanks = [p for p in self.players if p.role == PlayerRole.TANK]
    
    @property
    def composition_string(self) -> str:
        """String representation of team composition"""
        healer_count = len(self.healers)
        dps_count = len(self.dps)
        tank_count = len(self.tanks)
        
        if tank_count > 0:
            return f"{healer_count}H{dps_count}D{tank_count}T"
        else:
            return f"{healer_count}H{dps_count}D"
    
    def get_player_by_name(self, name: str) -> Optional[PlayerInfo]:
        """Find player by base name"""
        for player in self.players:
            if player.name.lower() == name.lower():
                return player
        return None
    
    def get_player_by_guid(self, guid: str) -> Optional[PlayerInfo]:
        """Find player by GUID"""
        for player in self.players:
            if player.guid == guid:
                return player
        return None


@dataclass 
class SoloShuffleRound:
    """Solo Shuffle round information"""
    round_number: int
    friendly_team: TeamComposition
    enemy_team: TeamComposition
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    outcome: Optional[str] = None  # "Win", "Loss", "Draw"
    duration_seconds: Optional[int] = None


@dataclass
class ArenaMatchModel:
    """Complete arena match data model"""
    # Basic match info
    filename: str
    match_id: str  # Unique identifier
    arena_size: ArenaSize
    arena_map: str
    start_time: datetime
    primary_player: str  # The player we're analyzing
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    outcome: Optional[str] = None  # "Win", "Loss", "Draw"
    friendly_team: TeamComposition = field(default_factory=TeamComposition)
    enemy_team: TeamComposition = field(default_factory=TeamComposition)
    
    # Solo Shuffle specific
    solo_shuffle_rounds: List[SoloShuffleRound] = field(default_factory=list)
    
    # Combat log boundaries  
    arena_start_time: Optional[datetime] = None
    arena_end_time: Optional[datetime] = None
    combat_log_file: Optional[str] = None
    
    # Match state tracking
    _all_players: Dict[str, PlayerInfo] = field(default_factory=dict)
    _guid_to_player: Dict[str, PlayerInfo] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize player lookups"""
        self._build_player_lookups()
    
    def _build_player_lookups(self):
        """Build fast lookup dictionaries for players"""
        all_players = self.friendly_team.players + self.enemy_team.players
        
        for player in all_players:
            self._all_players[player.name.lower()] = player
            self._guid_to_player[player.guid] = player
    
    def get_player_by_name(self, name: str) -> Optional[PlayerInfo]:
        """Get player by name from either team"""
        return self._all_players.get(name.lower())
    
    def get_player_by_guid(self, guid: str) -> Optional[PlayerInfo]:
        """Get player by GUID from either team"""
        return self._guid_to_player.get(guid)
    
    def is_teammate(self, player1: str, player2: str) -> bool:
        """Check if two players are on the same team"""
        p1 = self.get_player_by_name(player1)
        p2 = self.get_player_by_name(player2)
        
        if not p1 or not p2:
            return False
        
        return p1.team == p2.team
    
    def get_enemy_players(self, from_player_perspective: str) -> List[PlayerInfo]:
        """Get all enemy players from a specific player's perspective"""
        player = self.get_player_by_name(from_player_perspective)
        if not player:
            return []
        
        if player.team == TeamSide.FRIENDLY:
            return self.enemy_team.players
        else:
            return self.friendly_team.players
    
    def get_teammates(self, of_player: str) -> List[PlayerInfo]:
        """Get all teammates of a specific player"""
        player = self.get_player_by_name(of_player)
        if not player:
            return []
        
        if player.team == TeamSide.FRIENDLY:
            return [p for p in self.friendly_team.players if p.name != player.name]
        else:
            return [p for p in self.enemy_team.players if p.name != player.name]
    
    def get_priority_targets(self, from_perspective: str) -> List[PlayerInfo]:
        """Get priority target list (healers first, then DPS)"""
        enemies = self.get_enemy_players(from_perspective)
        
        # Prioritize healers, then DPS, then tanks
        healers = [p for p in enemies if p.role == PlayerRole.HEALER]
        dps = [p for p in enemies if p.role in [PlayerRole.MELEE_DPS, PlayerRole.RANGED_DPS]]
        tanks = [p for p in enemies if p.role == PlayerRole.TANK]
        
        return healers + dps + tanks
    
    @property
    def is_solo_shuffle(self) -> bool:
        """Check if this is a Solo Shuffle match"""
        return self.arena_size == ArenaSize.SOLO_SHUFFLE
    
    @property
    def total_players(self) -> int:
        """Total number of players in the match"""
        return len(self.friendly_team.players) + len(self.enemy_team.players)
    
    @property
    def match_summary(self) -> str:
        """Human-readable match summary"""
        friendly_comp = self.friendly_team.composition_string
        enemy_comp = self.enemy_team.composition_string
        
        return f"{self.arena_size.value} {self.arena_map}: {friendly_comp} vs {enemy_comp}"


class ArenaMatchModelBuilder:
    """Builder class for creating arena match models from various data sources"""
    
    @staticmethod
    def from_video_metadata(filename: str, json_data: dict, primary_player: str) -> ArenaMatchModel:
        """Build match model from video JSON metadata"""
        
        # Extract basic info from filename
        # Format: YYYY-MM-DD_HH-MM-SS_-_PlayerName_-_Bracket_Map_(Outcome).mp4
        parts = filename.replace('.mp4', '').split('_-_')
        
        datetime_str = parts[0]
        match_datetime = datetime.strptime(datetime_str, "%Y-%m-%d_%H-%M-%S")
        
        player_name = parts[1] if len(parts) > 1 else primary_player
        bracket_map = parts[2] if len(parts) > 2 else "Unknown"
        outcome = parts[3].strip('()') if len(parts) > 3 else None
        
        # Determine arena size
        if 'Solo_Shuffle' in bracket_map or 'Solo Shuffle' in bracket_map:
            arena_size = ArenaSize.SOLO_SHUFFLE
        elif '3v3' in bracket_map:
            arena_size = ArenaSize.THREE_V_THREE
        elif '2v2' in bracket_map:
            arena_size = ArenaSize.TWO_V_TWO
        elif 'Skirmish' in bracket_map:
            arena_size = ArenaSize.SKIRMISH
        else:
            arena_size = ArenaSize.THREE_V_THREE  # Default
        
        # Extract map name
        arena_map = bracket_map.split('_')[-1] if '_' in bracket_map else bracket_map
        arena_map = arena_map.replace('(', '').replace(')', '')
        
        # Create match model
        match_model = ArenaMatchModel(
            filename=filename,
            match_id=f"{datetime_str}_{player_name}",
            arena_size=arena_size,
            arena_map=arena_map,
            start_time=match_datetime,
            primary_player=player_name,
            outcome=outcome
        )
        
        # Extract player info from JSON if available
        if 'combatants' in json_data:
            match_model = ArenaMatchModelBuilder._extract_players_from_json(
                match_model, json_data, primary_player
            )
        
        return match_model
    
    @staticmethod
    def _extract_players_from_json(match_model: ArenaMatchModel, 
                                 json_data: dict, primary_player: str) -> ArenaMatchModel:
        """Extract player information from JSON metadata"""
        
        friendly_players = []
        enemy_players = []
        
        for combatant in json_data.get('combatants', []):
            name = combatant.get('_name', '')
            if not name:
                continue
            
            # Create player info
            player = PlayerInfo(
                name=name.split('-')[0] if '-' in name else name,
                full_name=name,
                guid=combatant.get('_guid', ''),
                class_name=combatant.get('_className', 'Unknown'),
                specialization=combatant.get('_specName', 'Unknown')
            )
            
            # Determine team (primary player and their team are friendly)
            if player.name.lower() == primary_player.lower():
                player.team = TeamSide.FRIENDLY
                friendly_players.append(player)
            else:
                # For now, assume others are enemies (we'd need more logic for team detection)
                player.team = TeamSide.ENEMY
                enemy_players.append(player)
        
        match_model.friendly_team.players = friendly_players
        match_model.enemy_team.players = enemy_players
        match_model._build_player_lookups()
        
        return match_model
    
    @staticmethod
    def from_master_index_row(row: dict) -> ArenaMatchModel:
        """Build match model from master index CSV row"""
        
        from datetime import datetime
        
        # Parse timestamp manually instead of using pandas
        time_str = row['precise_start_time']
        try:
            match_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            match_time = datetime.now()  # Fallback
        
        # Determine arena size from bracket
        bracket = row.get('bracket', '')
        if 'Solo Shuffle' in bracket:
            arena_size = ArenaSize.SOLO_SHUFFLE
        elif '3v3' in bracket:
            arena_size = ArenaSize.THREE_V_THREE
        elif '2v2' in bracket:
            arena_size = ArenaSize.TWO_V_TWO
        else:
            arena_size = ArenaSize.SKIRMISH
        
        return ArenaMatchModel(
            filename=row['filename'],
            match_id=f"{row['filename']}_{row['player_name']}",
            arena_size=arena_size,
            arena_map=row.get('map', 'Unknown'),
            start_time=match_time,
            duration_seconds=int(row.get('duration_s', 300)),
            outcome=row.get('outcome'),
            primary_player=row['player_name']
        )


# Convenience functions for team coordination analysis
def calculate_team_focus_coordination(match_model: ArenaMatchModel, 
                                    combat_events: List[dict],
                                    time_window_seconds: int = 5) -> float:
    """
    Calculate team coordination based on focus fire patterns.
    
    Returns coordination score 0.0-1.0 based on how often teammates
    target the same enemies within time windows.
    """
    if not match_model.friendly_team.players:
        return 0.0
    
    # Implementation would analyze combat events to find coordinated targeting
    # This is a placeholder for the actual algorithm
    coordination_events = 0
    total_opportunities = 0
    
    # Algorithm:
    # 1. Group events by time windows
    # 2. For each window, check if multiple teammates targeted same enemy
    # 3. Calculate coordination ratio
    
    return coordination_events / max(total_opportunities, 1)


def identify_focus_targets(match_model: ArenaMatchModel,
                          combat_events: List[dict]) -> Dict[str, int]:
    """
    Identify which enemy players were focus targets based on
    damage/CC concentration from the friendly team.
    """
    target_focus = {}
    
    for event in combat_events:
        # Implementation would analyze targeting patterns
        pass
    
    return target_focus


if __name__ == "__main__":
    # Example usage
    from development_standards import SafeLogger
    
    SafeLogger.info("Arena Match Data Model Example")
    
    # Create a sample match model
    match = ArenaMatchModel(
        filename="2025-05-06_22-11-04_-_Phlargus_-_3v3_Ruins_of_Lordaeron_(Win).mp4",
        match_id="test_match_1",
        arena_size=ArenaSize.THREE_V_THREE,
        arena_map="Ruins of Lordaeron",
        start_time=datetime(2025, 5, 6, 22, 11, 4),
        primary_player="Phlargus"
    )
    
    # Add some players
    phlargus = PlayerInfo(
        name="Phlargus",
        full_name="Phlargus-Eredar-US", 
        guid="Player-53-0D5553B6",
        class_name="Warlock",
        specialization="Destruction",
        team=TeamSide.FRIENDLY
    )
    
    healer = PlayerInfo(
        name="Melonha",
        full_name="Melonha-Tichondrius-US",
        guid="Player-3661-091D4E47", 
        class_name="Monk",
        specialization="Mistweaver",
        team=TeamSide.FRIENDLY
    )
    
    enemy_dps = PlayerInfo(
        name="Zlr",
        full_name="Zlr-BleedingHollow-US",
        guid="Player-73-0EFECD52",
        class_name="Mage", 
        specialization="Fire",
        team=TeamSide.ENEMY
    )
    
    match.friendly_team.players = [phlargus, healer]
    match.enemy_team.players = [enemy_dps]
    match._build_player_lookups()
    
    SafeLogger.success(f"Created match model: {match.match_summary}")
    SafeLogger.info(f"Friendly composition: {match.friendly_team.composition_string}")
    SafeLogger.info(f"Enemy composition: {match.enemy_team.composition_string}")
    SafeLogger.info(f"Priority targets for {phlargus.name}: {[p.name for p in match.get_priority_targets(phlargus.name)]}")
    SafeLogger.info(f"Teammates of {phlargus.name}: {[p.name for p in match.get_teammates(phlargus.name)]}")