#!/usr/bin/env python3
# focused_pet_validation_test.py - Test the focused pet index on specific 12-match window

import os
import sys
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_combat_parser_with_pet_index import EnhancedCombatParserWithPetIndex
    from debug_enhanced_parser_with_detailed_logging import DebugEnhancedCombatParserWithDetailedLogging
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure both parser files are in the same directory")
    sys.exit(1)


class FocusedPetValidationTester:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.parser = EnhancedCombatParserWithPetIndex(base_dir)
        self.debug_parser = DebugEnhancedCombatParserWithDetailedLogging(base_dir)

    def run_12_match_validation_test(self):
        """Run the specific 12-match validation test around the known problematic area."""
        print("🎯 12-Match Pet Index Validation Test")
        print("=" * 80)

        # Step 1: Verify pet index is loaded and focused
        if not self._verify_pet_index_loaded():
            return False

        # Step 2: Find the target 12-match window
        target_matches = self._find_target_12_matches()
        if target_matches is None or target_matches.empty:
            return False

        # Step 3: Process the 12 matches with pet index
        results = self._process_target_matches(target_matches)

        # Step 4: Analyze and validate results
        self._analyze_results(results)

        # Step 5: Generate focused output file
        self._generate_focused_output(results)

        return True

    def _verify_pet_index_loaded(self) -> bool:
        """Verify the focused pet index is properly loaded."""
        print("\n🔍 Step 1: Verifying Focused Pet Index")
        print("-" * 50)

        pet_index = self.parser.pet_index
        if not pet_index or 'player_pets' not in pet_index:
            print("❌ Pet index not loaded or malformed!")
            print("   Run: python pet_index_builder.py first")
            return False

        players = pet_index['player_pets']
        print(f"✅ Pet index loaded with {len(players)} characters")

        # Show our characters and their pets
        for player_name, data in players.items():
            pets = data.get('pet_names', [])
            summon_count = data.get('summon_count', 0)
            print(f"   🧙 {player_name}: {len(pets)} pets ({summon_count} summons)")
            if pets:
                print(f"      Pets: {', '.join(pets[:3])}{'...' if len(pets) > 3 else ''}")

        return len(players) > 0

    def _clean_timestamp(self, timestamp_str):
        """Clean timestamp string for parsing."""
        if pd.isna(timestamp_str):
            return timestamp_str
        ts = str(timestamp_str).strip()
        if '.' in ts and len(ts.split('.')[-1]) > 3:
            parts = ts.split('.')
            if len(parts) == 2:
                base, microsec = parts
                microsec = microsec[:6].ljust(6, '0')
                ts = f"{base}.{microsec}"
        return ts

    def _find_target_12_matches(self) -> pd.DataFrame:
        """Find the specific 12-match window: 2 before + target match + 10 after line 1178."""
        print("\n🎯 Step 2: Finding Specific Line 1178 Target Window")
        print("-" * 50)

        # Load enhanced index
        enhanced_index = self.base_dir / "master_index_enhanced.csv"
        if not enhanced_index.exists():
            print("❌ Enhanced index not found!")
            return None

        df = pd.read_csv(enhanced_index)

        # Handle timestamp parsing robustly (same as enhanced parser)
        print("🔧 Parsing timestamps...")
        try:
            df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='ISO8601')
        except ValueError:
            try:
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'], format='mixed')
            except ValueError:
                print("⚠️ Using manual timestamp cleaning...")
                df['precise_start_time'] = df['precise_start_time'].apply(self._clean_timestamp)
                df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

        # Filter to 2025 matches (when combat logs are available)
        matches_2025 = df[df['precise_start_time'] >= '2025-01-01'].copy()
        matches_2025 = matches_2025.sort_values('precise_start_time').reset_index(drop=True)

        print(f"📊 Found {len(matches_2025)} matches from 2025 onwards")

        if len(matches_2025) < 12:
            print("❌ Not enough 2025 matches for 12-match validation")
            return None

        # The line 1178 issue was described as a known case where interrupts were 0 but should be 8
        # Let's look for the target match around the area that would correspond to line 1178
        # Since we don't have the exact original CSV, we'll approximate based on the timing

        # Look for matches that could be the problematic one - focusing on mid-dataset
        # Line 1178 suggests we're looking somewhere in the middle of a large dataset
        total_matches = len(matches_2025)

        # Calculate approximate position (line 1178 out of what was likely ~2000-3000 lines)
        # Assume line 1178 represents roughly 40-50% through the dataset
        estimated_position = int(total_matches * 0.45)  # Around 45% through

        print(f"🎯 Estimated line 1178 equivalent position: {estimated_position} of {total_matches}")

        # Define the 12-match window: 2 before + target + 9 after = 12 total
        start_idx = max(0, estimated_position - 2)
        end_idx = min(total_matches, start_idx + 12)

        # Adjust if we're too close to the end
        if end_idx - start_idx < 12:
            start_idx = max(0, end_idx - 12)

        target_matches = matches_2025.iloc[start_idx:end_idx].copy()

        print(f"📍 Selected window: matches {start_idx + 1} to {end_idx} of {total_matches}")
        print(
            f"📅 Date range: {target_matches['precise_start_time'].min()} to {target_matches['precise_start_time'].max()}")

        # Show the filenames to help identify if this looks like the right area
        print(f"\n🎮 Target matches in window:")
        for i, (_, match) in enumerate(target_matches.iterrows()):
            marker = "🎯" if i == 2 else "  "  # Mark the estimated "line 1178" match
            filename_short = match['filename'][:60] + "..." if len(match['filename']) > 60 else match['filename']
            print(f"   {marker} {i + 1:2d}. {filename_short}")

        return target_matches

    def _process_target_matches(self, target_matches: pd.DataFrame) -> list:
        """Process the target matches using the DEBUG parser with detailed logging."""
        print("\n⚙️ Step 3: Processing 12 Matches with DEBUG Parser (Detailed Logging)")
        print("-" * 80)

        log_files = list(Path(self.base_dir / "Logs").glob('*.txt'))
        log_files.sort()
        print(f"📁 Found {len(log_files)} combat log files")

        results = []

        for idx, (_, match) in enumerate(target_matches.iterrows(), 1):
            filename = match['filename']
            player_name = self.parser.extract_player_name(filename)

            print(f"\n{'=' * 100}")
            print(f"🎮 PROCESSING MATCH {idx}/12: {filename}")
            print(f"{'=' * 100}")
            print(f"   Player: {player_name}")

            # Check known pets for this player
            known_pets = self.parser.get_player_pets(player_name)
            print(f"   Known pets: {known_pets}")

            # Find combat log
            relevant_log = self.parser.find_combat_log_for_match(match, log_files)
            if not relevant_log:
                print(f"   ❌ No combat log found")
                results.append({
                    'match_num': idx,
                    'filename': filename,
                    'player': player_name,
                    'status': 'No combat log',
                    'features': None
                })
                continue

            print(f"   📄 Combat log: {relevant_log.name}")

            # Extract features using DEBUG parser with detailed logging
            features = self.debug_parser.debug_process_single_match(match, relevant_log)

            if features:
                status = "SUCCESS"
                total_activity = (features['cast_success_own'] + features['interrupt_success_own'] +
                                  features['purges_own'])

                print(f"\n🎯 MATCH {idx} SUMMARY:")
                print(f"   ✅ Features extracted successfully")
                print(f"   📊 Casts: {features['cast_success_own']}")
                print(f"   ⚡ Interrupts: {features['interrupt_success_own']}")
                print(f"   🔄 Purges: {features['purges_own']}")
                print(f"   🛡️ Times Interrupted: {features['times_interrupted']}")
                print(f"   🔮 Precog Own: {features['precog_gained_own']}")
                print(f"   📈 Total Activity: {total_activity}")

                # Highlight high-activity matches
                if features['interrupt_success_own'] >= 8:
                    print(f"   🎯 POTENTIAL LINE 1178 EQUIVALENT - 8+ interrupts!")
                elif features['interrupt_success_own'] >= 5:
                    print(f"   🔥 HIGH INTERRUPT MATCH ({features['interrupt_success_own']} interrupts)")
                elif total_activity > 50:
                    print(f"   🔥 HIGH ACTIVITY MATCH (total: {total_activity})")

            else:
                status = "FAILED"
                print(f"   ❌ Feature extraction failed")

            results.append({
                'match_num': idx,
                'filename': filename,
                'player': player_name,
                'known_pets': known_pets,
                'combat_log': relevant_log.name if relevant_log else None,
                'status': status,
                'features': features
            })

            # Add separator between matches
            print(f"{'=' * 100}")

        return results

    def _analyze_results(self, results: list):
        """Analyze the validation results."""
        print("\n📊 Step 4: Results Analysis")
        print("-" * 50)

        successful_matches = [r for r in results if r['features'] is not None]
        failed_matches = [r for r in results if r['features'] is None]

        print(f"📈 Processing Summary:")
        print(f"   Total matches tested: {len(results)}")
        print(f"   Successful extractions: {len(successful_matches)}")
        print(f"   Failed extractions: {len(failed_matches)}")
        print(f"   Success rate: {len(successful_matches) / len(results) * 100:.1f}%")

        if len(successful_matches) == 0:
            print("❌ No successful matches - cannot analyze")
            return

        # Calculate statistics
        stats = {
            'total_casts': sum(r['features']['cast_success_own'] for r in successful_matches),
            'total_interrupts': sum(r['features']['interrupt_success_own'] for r in successful_matches),
            'total_purges': sum(r['features']['purges_own'] for r in successful_matches),
            'total_times_interrupted': sum(r['features']['times_interrupted'] for r in successful_matches),
            'total_precog_own': sum(r['features']['precog_gained_own'] for r in successful_matches)
        }

        avg_stats = {k: v / len(successful_matches) for k, v in stats.items()}

        print(f"\n📊 Average Statistics Per Match:")
        print(f"   Casts: {avg_stats['total_casts']:.1f}")
        print(f"   Interrupts: {avg_stats['total_interrupts']:.1f}")
        print(f"   Purges: {avg_stats['total_purges']:.1f}")
        print(f"   Times Interrupted: {avg_stats['total_times_interrupted']:.1f}")
        print(f"   Precognition Gained: {avg_stats['total_precog_own']:.1f}")

        # Identify high-value matches
        high_interrupt_matches = [r for r in successful_matches
                                  if r['features']['interrupt_success_own'] >= 5]
        high_purge_matches = [r for r in successful_matches
                              if r['features']['purges_own'] >= 3]

        print(f"\n🎯 High-Activity Matches:")
        print(f"   Matches with 5+ interrupts: {len(high_interrupt_matches)}")
        print(f"   Matches with 3+ purges: {len(high_purge_matches)}")

        # Show the highest interrupt match (potential line 1178 equivalent)
        if high_interrupt_matches:
            best_interrupt = max(high_interrupt_matches,
                                 key=lambda x: x['features']['interrupt_success_own'])
            print(f"\n🏆 Highest Interrupt Match:")
            print(f"   Match #{best_interrupt['match_num']}: {best_interrupt['filename']}")
            print(f"   Player: {best_interrupt['player']}")
            print(f"   Interrupts: {best_interrupt['features']['interrupt_success_own']}")
            print(f"   Purges: {best_interrupt['features']['purges_own']}")
            if best_interrupt['features']['interrupt_success_own'] >= 8:
                print(f"   🎯 THIS IS LIKELY OUR LINE 1178 EQUIVALENT - was showing 0 before!")
            else:
                print(f"   📝 High activity but may not be the exact line 1178 match")

        # Check for zero-value issues
        zero_interrupt_matches = [r for r in successful_matches
                                  if r['features']['interrupt_success_own'] == 0]
        zero_purge_matches = [r for r in successful_matches
                              if r['features']['purges_own'] == 0]

        zero_interrupt_rate = len(zero_interrupt_matches) / len(successful_matches) * 100
        zero_purge_rate = len(zero_purge_matches) / len(successful_matches) * 100

        print(f"\n⚠️ Zero-Value Analysis:")
        print(
            f"   Zero interrupt matches: {len(zero_interrupt_matches)}/{len(successful_matches)} ({zero_interrupt_rate:.1f}%)")
        print(f"   Zero purge matches: {len(zero_purge_matches)}/{len(successful_matches)} ({zero_purge_rate:.1f}%)")

        # Success criteria
        if zero_interrupt_rate < 30 and zero_purge_rate < 50:
            print(f"✅ VALIDATION PASSED - Low zero-value rates!")
        else:
            print(f"⚠️ VALIDATION CONCERNS - High zero-value rates may indicate remaining issues")

    def _generate_focused_output(self, results: list):
        """Generate a focused CSV output file with the 12 test matches."""
        print("\n💾 Step 5: Generating Focused Output")
        print("-" * 50)

        output_file = self.base_dir / "pet_index_validation_12_matches.csv"

        # Prepare CSV data
        csv_data = []
        for result in results:
            if result['features']:
                features = result['features']
                csv_data.append({
                    'match_num': result['match_num'],
                    'filename': result['filename'],
                    'player': result['player'],
                    'known_pets': '; '.join(result['known_pets']) if result['known_pets'] else '',
                    'combat_log': result['combat_log'],
                    'cast_success_own': features['cast_success_own'],
                    'interrupt_success_own': features['interrupt_success_own'],
                    'times_interrupted': features['times_interrupted'],
                    'precog_gained_own': features['precog_gained_own'],
                    'precog_gained_enemy': features['precog_gained_enemy'],
                    'purges_own': features['purges_own'],
                    'spells_cast_count': len(features['spells_cast']),
                    'spells_purged_count': len(features['spells_purged']),
                    'total_activity': (features['cast_success_own'] + features['interrupt_success_own'] +
                                       features['purges_own'])
                })

        # Save to CSV
        if csv_data:
            df_output = pd.DataFrame(csv_data)
            df_output.to_csv(output_file, index=False)
            print(f"✅ Saved {len(csv_data)} validated matches to: {output_file}")

            # Show summary table
            print(f"\n📋 Validation Results Summary:")
            print(df_output[['match_num', 'player', 'cast_success_own', 'interrupt_success_own',
                             'purges_own', 'total_activity']].to_string(index=False))
        else:
            print(f"❌ No successful matches to save")


def main():
    """Main function to run the focused pet validation test with DEBUG logging."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"

    print("🚀 Starting 12-Match Pet Index Validation with DEBUG Logging")
    print(f"📁 Base directory: {base_dir}")
    print(f"🔍 This will show DETAILED logging for every interrupt and purge found")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = FocusedPetValidationTester(base_dir)

    try:
        success = tester.run_12_match_validation_test()

        if success:
            print(f"\n🎉 12-MATCH DEBUG VALIDATION COMPLETE!")
            print(f"✅ Pet index system tested on target window with detailed logging")
            print(f"📊 Results saved for analysis")
            print(f"🔍 Check pet_index_validation_12_matches.csv for detailed results")
            print(f"📋 Review the detailed interrupt/purge logs above for accuracy verification")
        else:
            print(f"\n❌ VALIDATION FAILED!")
            print(f"🔧 Check error messages above for issues")

    except Exception as e:
        print(f"\n💥 Validation error: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()