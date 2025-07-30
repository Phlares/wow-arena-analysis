#!/usr/bin/env python3
# pet_index_validation_test.py - Test the pet index solution on specific problematic matches

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_combat_parser_with_pet_index import EnhancedCombatParserWithPetIndex
    from pet_index_builder import PetIndexBuilder
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure both enhanced_combat_parser_with_pet_index.py and pet_index_builder.py are in the same directory")
    sys.exit(1)


class PetIndexValidationTester:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.parser = EnhancedCombatParserWithPetIndex(base_dir)

    def run_comprehensive_test(self):
        """Run comprehensive validation tests on the pet index system."""
        print("🧪 Pet Index Validation Test Suite")
        print("=" * 80)

        # Test 1: Verify pet index exists and is populated
        if not self.test_pet_index_exists():
            print("❌ Pet index test failed - cannot continue")
            return False

        # Test 2: Test specific problematic match (line 1178 equivalent)
        if not self.test_specific_problematic_match():
            print("❌ Specific match test failed")
            return False

        # Test 3: Test range of matches around the problematic one
        if not self.test_match_range_validation():
            print("❌ Match range test failed")
            return False

        # Test 4: Compare before/after results
        self.compare_before_after_results()

        print("\n" + "=" * 80)
        print("🎉 Pet Index Validation Complete!")
        return True

    def test_pet_index_exists(self) -> bool:
        """Test 1: Verify pet index exists and contains expected data."""
        print("\n🔍 Test 1: Pet Index Validation")
        print("-" * 50)

        index_file = self.base_dir / "player_pet_index.json"
        if not index_file.exists():
            print("❌ Pet index file not found!")
            print("   Run: python pet_index_builder.py")
            return False

        # Check index content
        pet_index = self.parser.pet_index
        player_pets = pet_index.get('player_pets', {})

        print(f"✅ Pet index loaded with {len(player_pets)} players")

        # Check for known problematic players
        known_players = ['Phlurbotomy', 'Sluglishphsh', 'Phlares']

        for player in known_players:
            pets = self.parser.get_player_pets(player)
            if pets:
                print(f"   {player}: {len(pets)} pets - {pets}")
            else:
                print(f"   ⚠️ {player}: No pets found")

        return len(player_pets) > 0

    def test_specific_problematic_match(self) -> bool:
        """Test 2: Test on a specific match that we know should have interrupts/purges."""
        print("\n🎯 Test 2: Specific Problematic Match Test")
        print("-" * 50)

        # Load enhanced index to find a good test match
        enhanced_index = self.base_dir / "master_index_enhanced.csv"
        if not enhanced_index.exists():
            print("❌ Enhanced index not found!")
            return False

        df = pd.read_csv(enhanced_index)

        # Find matches from January 2025 that should have pet activity
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])
        jan_matches = df[df['precise_start_time'] >= '2025-01-01'].head(10)

        if len(jan_matches) == 0:
            print("❌ No 2025 matches found for testing")
            return False

        # Test the first few matches
        successful_tests = 0

        for idx, (_, match) in enumerate(jan_matches.iterrows()):
            if idx >= 3:  # Test first 3 matches
                break

            filename = match['filename']
            player_name = self.parser.extract_player_name(filename)

            print(f"\n🎮 Testing match: {filename}")
            print(f"   Player: {player_name}")

            # Check if player has pets in index
            pets = self.parser.get_player_pets(player_name)
            print(f"   Known pets: {pets}")

            if not pets:
                print(f"   ⚠️ No pets found for {player_name} - may indicate index issue")
                continue

            # Find combat log
            log_files = list(Path(self.base_dir / "Logs").glob('*.txt'))
            relevant_log = self.parser.find_combat_log_for_match(match, log_files)

            if not relevant_log:
                print(f"   ⚠️ No combat log found")
                continue

            print(f"   Combat log: {relevant_log.name}")

            # Extract features using pet index
            features = self.parser.extract_combat_features_with_pet_index(match, relevant_log)

            if features:
                print(f"   ✅ Features extracted successfully")
                print(f"      Casts: {features['cast_success_own']}")
                print(f"      Interrupts: {features['interrupt_success_own']}")
                print(f"      Purges: {features['purges_own']}")
                print(f"      Spells purged: {len(features['spells_purged'])}")

                # Consider test successful if we have some activity
                if (features['cast_success_own'] > 0 or
                        features['interrupt_success_own'] > 0 or
                        features['purges_own'] > 0):
                    successful_tests += 1

            else:
                print(f"   ❌ Feature extraction failed")

        print(f"\n📊 Specific Match Test Results: {successful_tests}/3 matches successful")
        return successful_tests >= 1  # At least one successful test

    def test_match_range_validation(self) -> bool:
        """Test 3: Test a range of 12 matches to validate consistency."""
        print("\n📈 Test 3: Match Range Validation (12 matches)")
        print("-" * 50)

        # Load enhanced index
        enhanced_index = self.base_dir / "master_index_enhanced.csv"
        df = pd.read_csv(enhanced_index)
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

        # Get matches from January 2025
        jan_matches = df[df['precise_start_time'] >= '2025-01-01'].head(12)

        if len(jan_matches) < 5:
            print("❌ Not enough 2025 matches for range testing")
            return False

        print(f"🎯 Testing {len(jan_matches)} matches for consistency")

        results = []
        log_files = list(Path(self.base_dir / "Logs").glob('*.txt'))

        for idx, (_, match) in enumerate(jan_matches.iterrows()):
            filename = match['filename']
            player_name = self.parser.extract_player_name(filename)

            # Extract features
            relevant_log = self.parser.find_combat_log_for_match(match, log_files)
            if relevant_log:
                features = self.parser.extract_combat_features_with_pet_index(match, relevant_log)
                if features:
                    results.append({
                        'filename': filename,
                        'player': player_name,
                        'casts': features['cast_success_own'],
                        'interrupts': features['interrupt_success_own'],
                        'purges': features['purges_own'],
                        'total_activity': features['cast_success_own'] + features['interrupt_success_own'] + features[
                            'purges_own']
                    })

        # Analyze results
        if len(results) == 0:
            print("❌ No matches processed successfully")
            return False

        print(f"\n📊 Range Test Results ({len(results)} matches processed):")

        # Show detailed results
        for i, result in enumerate(results):
            activity_indicator = "🟢" if result['total_activity'] > 20 else "🟡" if result['total_activity'] > 5 else "🔴"
            print(f"   {i + 1:2d}. {activity_indicator} {result['filename'][:50]}...")
            print(
                f"       Player: {result['player']}, Casts: {result['casts']}, Interrupts: {result['interrupts']}, Purges: {result['purges']}")

        # Calculate statistics
        total_casts = sum(r['casts'] for r in results)
        total_interrupts = sum(r['interrupts'] for r in results)
        total_purges = sum(r['purges'] for r in results)

        avg_casts = total_casts / len(results)
        avg_interrupts = total_interrupts / len(results)
        avg_purges = total_purges / len(results)

        print(f"\n📈 Statistics:")
        print(f"   Average casts per match: {avg_casts:.1f}")
        print(f"   Average interrupts per match: {avg_interrupts:.1f}")
        print(f"   Average purges per match: {avg_purges:.1f}")

        # Success criteria
        matches_with_activity = len([r for r in results if r['total_activity'] > 0])
        activity_rate = matches_with_activity / len(results) * 100

        print(f"   Matches with activity: {matches_with_activity}/{len(results)} ({activity_rate:.1f}%)")

        # Consider successful if >80% of matches have some activity
        success = activity_rate >= 80

        if success:
            print("✅ Range validation PASSED")
        else:
            print("❌ Range validation FAILED - too many zero-activity matches")

        return success

    def compare_before_after_results(self):
        """Test 4: Compare results before/after pet index implementation."""
        print("\n🔄 Test 4: Before/After Comparison")
        print("-" * 50)

        # Check if we have existing results to compare against
        old_results_file = self.base_dir / "match_features_enhanced.csv"
        new_results_file = self.base_dir / "match_features_enhanced_PET_INDEX.csv"

        if not old_results_file.exists():
            print("⚠️ No existing results file found for comparison")
            print("   Run the old parser first to generate baseline results")
            return

        if not new_results_file.exists():
            print("⚠️ No new results file found")
            print("   Run the enhanced parser with pet index first")
            return

        try:
            # Load both result sets
            old_df = pd.read_csv(old_results_file)
            new_df = pd.read_csv(new_results_file)

            print(f"📊 Comparison Data:")
            print(f"   Old results: {len(old_df)} matches")
            print(f"   New results: {len(new_df)} matches")

            if len(old_df) == 0 or len(new_df) == 0:
                print("⚠️ Insufficient data for comparison")
                return

            # Compare key metrics
            old_stats = {
                'avg_interrupts': old_df['interrupt_success_own'].mean(),
                'avg_purges': old_df.get('purges_own', pd.Series([0])).mean(),
                'zero_interrupt_rate': (old_df['interrupt_success_own'] == 0).mean() * 100,
                'zero_purge_rate': (old_df.get('purges_own', pd.Series([0])) == 0).mean() * 100
            }

            new_stats = {
                'avg_interrupts': new_df['interrupt_success_own'].mean(),
                'avg_purges': new_df['purges_own'].mean(),
                'zero_interrupt_rate': (new_df['interrupt_success_own'] == 0).mean() * 100,
                'zero_purge_rate': (new_df['purges_own'] == 0).mean() * 100
            }

            print(f"\n📈 Metric Comparison:")
            print(f"   Average Interrupts: {old_stats['avg_interrupts']:.2f} → {new_stats['avg_interrupts']:.2f}")
            print(f"   Average Purges: {old_stats['avg_purges']:.2f} → {new_stats['avg_purges']:.2f}")
            print(
                f"   Zero Interrupt Rate: {old_stats['zero_interrupt_rate']:.1f}% → {new_stats['zero_interrupt_rate']:.1f}%")
            print(f"   Zero Purge Rate: {old_stats['zero_purge_rate']:.1f}% → {new_stats['zero_purge_rate']:.1f}%")

            # Calculate improvements
            interrupt_improvement = new_stats['avg_interrupts'] - old_stats['avg_interrupts']
            purge_improvement = new_stats['avg_purges'] - old_stats['avg_purges']

            zero_int_improvement = old_stats['zero_interrupt_rate'] - new_stats['zero_interrupt_rate']
            zero_purge_improvement = old_stats['zero_purge_rate'] - new_stats['zero_purge_rate']

            print(f"\n🎯 Improvements:")
            improvement_icon = "📈" if interrupt_improvement > 0 else "📉" if interrupt_improvement < 0 else "➡️"
            print(f"   {improvement_icon} Interrupt detection: {interrupt_improvement:+.2f} avg/match")

            improvement_icon = "📈" if purge_improvement > 0 else "📉" if purge_improvement < 0 else "➡️"
            print(f"   {improvement_icon} Purge detection: {purge_improvement:+.2f} avg/match")

            improvement_icon = "📈" if zero_int_improvement > 0 else "📉" if zero_int_improvement < 0 else "➡️"
            print(f"   {improvement_icon} Zero interrupt reduction: {zero_int_improvement:+.1f}%")

            improvement_icon = "📈" if zero_purge_improvement > 0 else "📉" if zero_purge_improvement < 0 else "➡️"
            print(f"   {improvement_icon} Zero purge reduction: {zero_purge_improvement:+.1f}%")

            # Overall assessment
            if (interrupt_improvement > 0.5 and purge_improvement > 0.5 and
                    zero_int_improvement > 10 and zero_purge_improvement > 10):
                print("🎉 SIGNIFICANT IMPROVEMENT detected!")
            elif (interrupt_improvement > 0 and purge_improvement > 0):
                print("✅ Positive improvement detected")
            else:
                print("⚠️ Mixed or no improvement - may need further tuning")

        except Exception as e:
            print(f"❌ Error during comparison: {e}")

    def run_targeted_line_1178_test(self):
        """Run a targeted test on the specific problematic match equivalent."""
        print("\n🎯 Targeted Test: Line 1178 Equivalent Issue")
        print("-" * 60)

        # Load enhanced index and find matches from early January 2025
        enhanced_index = self.base_dir / "master_index_enhanced.csv"
        df = pd.read_csv(enhanced_index)
        df['precise_start_time'] = pd.to_datetime(df['precise_start_time'])

        # Look for matches around January 1-2, 2025 (likely area of line 1178)
        target_matches = df[
            (df['precise_start_time'] >= '2025-01-01') &
            (df['precise_start_time'] <= '2025-01-03')
            ]

        print(f"🔍 Found {len(target_matches)} matches in target date range")

        if len(target_matches) == 0:
            print("❌ No matches found in target range")
            return False

        # Test each match in the range
        log_files = list(Path(self.base_dir / "Logs").glob('*.txt'))

        high_interrupt_matches = []

        for idx, (_, match) in enumerate(target_matches.iterrows()):
            filename = match['filename']
            player_name = self.parser.extract_player_name(filename)

            relevant_log = self.parser.find_combat_log_for_match(match, log_files)
            if not relevant_log:
                continue

            features = self.parser.extract_combat_features_with_pet_index(match, relevant_log)
            if not features:
                continue

            # Look for matches that should have high interrupt counts
            if features['interrupt_success_own'] >= 5:  # Significant interrupt activity
                high_interrupt_matches.append({
                    'filename': filename,
                    'player': player_name,
                    'interrupts': features['interrupt_success_own'],
                    'purges': features['purges_own'],
                    'total_casts': features['cast_success_own']
                })

        print(f"\n🎯 High-Activity Matches Found: {len(high_interrupt_matches)}")

        for i, match in enumerate(high_interrupt_matches):
            print(f"   {i + 1}. {match['filename']}")
            print(f"      Player: {match['player']}")
            print(f"      Interrupts: {match['interrupts']} (target was 8+)")
            print(f"      Purges: {match['purges']}")
            print(f"      Total Casts: {match['total_casts']}")

            # Check if this could be our "line 1178" equivalent
            if match['interrupts'] >= 8:
                print(f"      🎯 POTENTIAL LINE 1178 EQUIVALENT - matches expected 8+ interrupts!")

        return len(high_interrupt_matches) > 0


def main():
    """Main function to run the validation tests."""
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"

    print("🚀 Starting Pet Index Validation Test Suite")
    print(f"📁 Base directory: {base_dir}")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = PetIndexValidationTester(base_dir)

    try:
        # Run comprehensive tests
        success = tester.run_comprehensive_test()

        # Run targeted line 1178 test
        tester.run_targeted_line_1178_test()

        if success:
            print(f"\n🎉 VALIDATION SUCCESSFUL!")
            print(f"✅ Pet index system is working correctly")
            print(f"🚀 Ready to process full dataset with enhanced parser")
        else:
            print(f"\n❌ VALIDATION FAILED!")
            print(f"🔧 Pet index system needs debugging")

    except Exception as e:
        print(f"\n💥 Validation suite error: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()