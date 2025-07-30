#!/usr/bin/env python3
# pet_index_builder.py - Build comprehensive player-pet index from all combat logs

import os
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Optional
from collections import defaultdict
import re


class PetIndexBuilder:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.logs_dir = self.base_dir / "Logs"

        # Load OUR character names from video filenames
        self.our_characters = self.load_our_character_names()
        print(f"🎯 Tracking pets for OUR characters only: {sorted(self.our_characters)}")

        # Pet index structure: {player_name: {pet_names: set, summon_events: list}}
        self.player_pet_index = defaultdict(lambda: {
            'pet_names': set(),
            'summon_events': [],
            'characters_found': set(),
            'logs_with_summons': set()
        })

    def load_our_character_names(self) -> Set[str]:
        """Load character names from our video filenames in master_index_enhanced.csv."""
        our_characters = set()

        # Try to load from master index
        index_files = ['master_index_enhanced.csv', 'master_index.csv']

        for index_file in index_files:
            index_path = self.base_dir / index_file
            if index_path.exists():
                print(f"📋 Loading character names from {index_file}")
                try:
                    df = pd.read_csv(index_path)

                    for filename in df['filename']:
                        character_name = self.extract_character_name_from_filename(filename)
                        if character_name:
                            our_characters.add(character_name)

                    print(f"   Found {len(our_characters)} unique character names")
                    return our_characters

                except Exception as e:
                    print(f"   ⚠️ Error reading {index_file}: {e}")
                    continue

        # Fallback: scan video files directly
        print("⚠️ No master index found, scanning video files directly...")
        video_extensions = ['*.mp4', '*.json']

        for ext in video_extensions:
            for video_file in self.base_dir.rglob(ext):
                character_name = self.extract_character_name_from_filename(video_file.name)
                if character_name:
                    our_characters.add(character_name)

        print(f"   Found {len(our_characters)} character names from video files")
        return our_characters

    def extract_character_name_from_filename(self, filename: str) -> Optional[str]:
        """Extract character name from filename format: YYYY-MM-DD_HH-MM-SS_-_CHARACTER_-_..."""
        try:
            parts = filename.split('_-_')
            if len(parts) >= 2:
                character_name = parts[1]  # The character name part
                # Basic validation
                if len(character_name) >= 3 and character_name.isalpha():
                    return character_name
        except Exception:
            pass
        return None

    def build_comprehensive_pet_index(self, output_file: str = "player_pet_index.json") -> Dict:
        """Build comprehensive pet index from all combat logs - OUR CHARACTERS ONLY."""
        print("🔍 Building Comprehensive Player-Pet Index (OUR CHARACTERS ONLY)")
        print(f"📁 Scanning logs directory: {self.logs_dir}")
        print(f"🎯 Target characters: {sorted(self.our_characters)}")

        if len(self.our_characters) == 0:
            print("❌ No character names found! Cannot build pet index.")
            return {}

        # Delete existing index file to start fresh
        index_path = self.base_dir / output_file
        if index_path.exists():
            index_path.unlink()
            print(f"🗑️ Deleted existing index file: {output_file}")

        # Get all combat log files
        log_files = list(self.logs_dir.glob('*.txt'))
        log_files.sort()

        print(f"📊 Found {len(log_files)} combat log files")

        total_summon_events = 0
        processed_logs = 0

        for log_file in log_files:
            print(f"⏳ Processing {log_file.name}...")

            summon_count = self.process_combat_log_for_our_pets(log_file)
            total_summon_events += summon_count
            processed_logs += 1

            if processed_logs % 10 == 0:
                print(f"   📈 Progress: {processed_logs}/{len(log_files)} logs processed")

        # Convert to serializable format and save
        index_output = self.prepare_index_for_output()

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_output, f, indent=2, default=self.json_serializer)

        # Print comprehensive summary
        self.print_index_summary(index_output, total_summon_events, processed_logs)

        print(f"💾 Pet index saved to: {index_path}")
        return index_output

    def process_combat_log_for_our_pets(self, log_file: Path) -> int:
        """Process a single combat log file to extract pet summons for OUR characters ONLY."""
        summon_events_found = 0

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Look for SPELL_SUMMON events
                    if 'SPELL_SUMMON' in line:
                        pet_info = self.parse_summon_event_filtered(line, log_file.name, line_num)
                        if pet_info:
                            player_name = pet_info['player']
                            pet_name = pet_info['pet']

                            # ONLY store if this is one of OUR characters
                            if player_name in self.our_characters:
                                # Add to index
                                self.player_pet_index[player_name]['pet_names'].add(pet_name)
                                self.player_pet_index[player_name]['summon_events'].append(pet_info)
                                self.player_pet_index[player_name]['characters_found'].add(player_name)
                                self.player_pet_index[player_name]['logs_with_summons'].add(log_file.name)

                                summon_events_found += 1

        except Exception as e:
            print(f"   ⚠️ Error processing {log_file.name}: {e}")

        return summon_events_found

    def parse_summon_event_filtered(self, line: str, log_filename: str, line_num: int) -> Optional[Dict]:
        """Parse a SPELL_SUMMON line to extract player and pet information - filtered for our characters."""
        try:
            parts = line.strip().split(',')
            if len(parts) >= 7:
                # Extract timestamp
                timestamp_part = line.split(',')[1].strip() if ',' in line else ''

                # Extract player (source) and pet (target)
                source_guid = parts[2].strip('"')
                player_name = source_guid.split('-', 1)[0] if '-' in source_guid else source_guid

                target_guid = parts[6].strip('"')
                pet_name = target_guid.split('-', 1)[0] if '-' in target_guid else target_guid

                # FILTER: Only process if player is one of OUR characters
                if player_name not in self.our_characters:
                    return None

                # Validate names (basic filtering)
                if (len(player_name) >= 3 and len(pet_name) >= 3 and
                        player_name != pet_name and
                        not player_name.startswith('0x') and
                        not pet_name.startswith('0x')):
                    return {
                        'player': player_name,
                        'pet': pet_name,
                        'log_file': log_filename,
                        'line_num': line_num,
                        'timestamp': timestamp_part,
                        'raw_line': line.strip()[:100]  # First 100 chars for debugging
                    }

        except Exception as e:
            pass

        return None

    def identify_character_from_spell_cast(self, line: str) -> Optional[Dict]:
        """Identify character names from spell cast events (backup detection)."""
        try:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                source_guid = parts[2].strip('"')
                player_name = source_guid.split('-', 1)[0] if '-' in source_guid else source_guid

                # Basic validation - character names are typically 3-12 characters
                if (3 <= len(player_name) <= 12 and
                        player_name.isalpha() and
                        not player_name.startswith('0x')):
                    return {'player': player_name}

        except Exception as e:
            pass

        return None

    def prepare_index_for_output(self) -> Dict:
        """Convert internal index to JSON-serializable format."""
        output_index = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_players': len(self.player_pet_index),
                'builder_version': '1.0'
            },
            'player_pets': {},
            'pet_lookup': {},  # Reverse lookup: pet_name -> [player_names]
            'statistics': {}
        }

        # Convert player-pet relationships
        pet_lookup = defaultdict(list)

        for player_name, data in self.player_pet_index.items():
            pet_names_list = list(data['pet_names'])

            output_index['player_pets'][player_name] = {
                'pet_names': pet_names_list,
                'summon_count': len(data['summon_events']),
                'logs_with_summons': list(data['logs_with_summons']),
                'characters_found': list(data['characters_found'])
            }

            # Build reverse lookup
            for pet_name in pet_names_list:
                pet_lookup[pet_name].append(player_name)

        output_index['pet_lookup'] = dict(pet_lookup)

        # Generate statistics
        total_pets = sum(len(data['pet_names']) for data in self.player_pet_index.values())
        total_summons = sum(len(data['summon_events']) for data in self.player_pet_index.values())

        output_index['statistics'] = {
            'total_unique_pets': total_pets,
            'total_summon_events': total_summons,
            'players_with_pets': len([p for p, d in self.player_pet_index.items() if len(d['pet_names']) > 0]),
            'average_pets_per_player': round(total_pets / len(self.player_pet_index), 2) if self.player_pet_index else 0
        }

        return output_index

    def print_index_summary(self, index_output: Dict, total_events: int, processed_logs: int):
        """Print comprehensive summary of the pet index - OUR CHARACTERS ONLY."""
        print(f"\n🎉 Pet Index Building Complete! (OUR CHARACTERS ONLY)")
        print(f"=" * 60)

        stats = index_output['statistics']
        players = index_output['player_pets']

        print(f"📊 Processing Summary:")
        print(f"   Combat logs processed: {processed_logs}")
        print(f"   Total summon events found: {total_events}")
        print(f"   OUR characters with pets: {len(players)}")
        print(f"   Total unique pets for OUR characters: {stats['total_unique_pets']}")
        print(f"   Average pets per character: {stats['average_pets_per_player']}")

        # Show ALL our characters and their pets (since this should be a small, focused list)
        print(f"\n🎯 OUR Characters and Their Pets:")
        sorted_players = sorted(players.items(), key=lambda x: x[0])  # Sort alphabetically

        for player_name, data in sorted_players:
            pet_names = ', '.join(sorted(data['pet_names']))
            summon_count = data['summon_count']
            log_count = len(data['logs_with_summons'])
            print(f"   🧙 {player_name}:")
            print(f"      Pets: {pet_names}")
            print(f"      Summon events: {summon_count} (across {log_count} logs)")

        # Show some example pet-to-player lookups (should be much cleaner now)
        print(f"\n🔍 Pet Lookup Examples:")
        pet_lookup = index_output['pet_lookup']
        example_pets = list(pet_lookup.keys())[:8]  # Show more since it's smaller

        for pet_name in example_pets:
            owners = pet_lookup[pet_name]
            print(f"   '{pet_name}' belongs to: {', '.join(owners)}")

        print(f"\n✅ Index is now focused on OUR {len(players)} characters only!")
        print(f"📉 Excluded all enemy/teammate pets from other players")

    def json_serializer(self, obj):
        """Custom JSON serializer for sets and other non-serializable objects."""
        if isinstance(obj, set):
            return list(obj)
        return str(obj)

    def get_player_pets(self, player_name: str, index_file: str = "player_pet_index.json") -> List[str]:
        """Get all known pets for a specific player."""
        try:
            index_path = self.base_dir / index_file
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    return index_data.get('player_pets', {}).get(player_name, {}).get('pet_names', [])
        except Exception as e:
            print(f"Error loading pet index: {e}")

        return []

    def verify_index_quality(self, index_file: str = "player_pet_index.json"):
        """Verify the quality and completeness of the built index - OUR CHARACTERS ONLY."""
        print(f"\n🔍 Verifying Pet Index Quality (OUR CHARACTERS)")

        try:
            index_path = self.base_dir / index_file
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            players = index_data['player_pets']

            # Check that we ONLY have our characters
            print(f"✅ Index Quality Check:")
            print(f"   Characters in index: {len(players)}")
            print(f"   Expected characters: {len(self.our_characters)}")

            # Verify all our characters are present
            missing_characters = []
            for expected_char in self.our_characters:
                if expected_char in players:
                    pets = players[expected_char]['pet_names']
                    summons = players[expected_char]['summon_count']
                    if len(pets) > 0:
                        print(f"   ✅ {expected_char}: {len(pets)} pets, {summons} summons - {pets}")
                    else:
                        print(f"   ⚠️ {expected_char}: No pets found (may not have summoned pets in logs)")
                else:
                    missing_characters.append(expected_char)
                    print(f"   ❌ {expected_char}: NOT FOUND in index")

            # Check for any unexpected characters (should be none)
            unexpected_characters = []
            for indexed_char in players.keys():
                if indexed_char not in self.our_characters:
                    unexpected_characters.append(indexed_char)

            if unexpected_characters:
                print(f"\n❌ UNEXPECTED characters found in index:")
                for char in unexpected_characters:
                    print(f"   - {char} (should not be here)")
            else:
                print(f"\n✅ No unexpected characters - index is properly filtered!")

            # Check for common pet names (should be much cleaner now)
            pet_lookup = index_data.get('pet_lookup', {})
            common_pets = ['Felhunter', 'Succubus', 'Voidwalker', 'Imp']

            print(f"\n✅ Common Pet Check:")
            for pet_type in common_pets:
                matching_pets = [pet for pet in pet_lookup.keys() if pet_type.lower() in pet.lower()]
                if matching_pets:
                    owners = set()
                    for pet in matching_pets:
                        owners.update(pet_lookup[pet])
                    print(f"   {pet_type}: {len(matching_pets)} variations owned by {sorted(owners)}")
                else:
                    print(f"   ⚠️ {pet_type}: No {pet_type.lower()}s found in our character data")

            # Final validation summary
            success = (len(missing_characters) == 0 and len(unexpected_characters) == 0)
            if success:
                print(f"\n🎉 INDEX VALIDATION SUCCESSFUL!")
                print(f"✅ Properly filtered to OUR {len(players)} characters only")
            else:
                print(f"\n⚠️ INDEX ISSUES DETECTED:")
                if missing_characters:
                    print(f"   Missing: {missing_characters}")
                if unexpected_characters:
                    print(f"   Unexpected: {unexpected_characters}")

        except Exception as e:
            print(f"❌ Error during verification: {e}")


def main():
    """Main function to build the pet index - OUR CHARACTERS ONLY."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"

    print("🚀 Starting Pet Index Builder (OUR CHARACTERS ONLY)")
    print(f"📁 Base directory: {base_dir}")

    builder = PetIndexBuilder(base_dir)

    # Verify we found our characters
    if len(builder.our_characters) == 0:
        print("❌ No character names found from video files!")
        print("   Make sure master_index_enhanced.csv exists or video files are present")
        return None

    # Build the focused index (our characters only)
    index_data = builder.build_comprehensive_pet_index()

    # Verify index quality
    builder.verify_index_quality()

    print(f"\n🎯 Pet index ready for enhanced combat parser integration!")
    print(f"📉 Index size dramatically reduced - contains ONLY our {len(builder.our_characters)} characters")
    return index_data


if __name__ == '__main__':
    main()