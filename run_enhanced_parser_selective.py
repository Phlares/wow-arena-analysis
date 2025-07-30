#!/usr/bin/env python3
# run_enhanced_parser_selective.py - Run enhanced parser with selective re-processing for zero interrupt matches

import sys
import os
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def run_selective_reprocessing():
    """Run selective re-processing for matches with zero interrupts using enhanced pet logic."""

    print("🚀 Starting SELECTIVE Re-processing for Zero Interrupt Matches")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Setup paths
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/match_features_enhanced_VERIFIED.csv"

    print(f"📁 Base directory: {base_dir}")
    print(f"📄 Enhanced index: {enhanced_index}")
    print(f"📁 Logs directory: {logs_dir}")
    print(f"💾 Output file: {output_csv}")

    # Check if output file exists
    if not os.path.exists(output_csv):
        print(f"❌ Output file not found! Please run full processing first.")
        return False

    try:
        # Import the enhanced parser
        print(f"\n🔧 Importing enhanced parser with pet index...")
        from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
        print(f"✅ Import successful")

        # Initialize parser
        print(f"🔧 Initializing parser with pet index...")
        parser = EnhancedProductionCombatParser(base_dir)
        print(f"✅ Parser initialized")

        # Check pet index
        pet_count = len(parser.pet_index.get('player_pets', {}))
        if pet_count == 0:
            print(f"❌ Pet index is empty! Run pet_index_builder.py first.")
            return False
        print(f"✅ Pet index loaded with {pet_count} players")

        # Start selective processing
        print(f"\n🎯 Starting selective re-processing...")
        print(f"⏳ This will only re-process matches with zero interrupts")
        print(f"📊 Progress updates every 10 matches")
        print(f"-" * 80)

        # Call the selective parsing function
        parser.parse_enhanced_matches_selective(enhanced_index, logs_dir, output_csv)

        print(f"\n🎉 Selective re-processing completed successfully!")
        print(f"💾 Results saved to: {output_csv}")

        # Show summary stats
        show_interrupt_stats(output_csv)

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"🔧 Make sure enhanced_combat_parser_production_ENHANCED.py is in the same directory")
        return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True


def run_full_processing():
    """Run full processing with enhanced pet logic (force rebuild)."""

    print("🚀 Starting FULL Enhanced Combat Parser Processing")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Setup paths
    base_dir = "E:/Footage/Footage/WoW - Warcraft Recorder/Wow Arena Matches"
    enhanced_index = f"{base_dir}/master_index_enhanced.csv"
    logs_dir = f"{base_dir}/Logs"
    output_csv = f"{base_dir}/match_features_enhanced_VERIFIED.csv"

    print(f"📁 Base directory: {base_dir}")
    print(f"📄 Enhanced index: {enhanced_index}")
    print(f"📁 Logs directory: {logs_dir}")
    print(f"💾 Output file: {output_csv}")

    # Check if output file exists
    if os.path.exists(output_csv):
        print(f"⚠️ Output file already exists - will be deleted and rebuilt")

    try:
        # Import the enhanced parser
        print(f"\n🔧 Importing enhanced parser with pet index...")
        from enhanced_combat_parser_production_ENHANCED import EnhancedProductionCombatParser
        print(f"✅ Import successful")

        # Initialize parser
        print(f"🔧 Initializing parser with pet index...")
        parser = EnhancedProductionCombatParser(base_dir)
        print(f"✅ Parser initialized")

        # Check pet index
        pet_count = len(parser.pet_index.get('player_pets', {}))
        if pet_count == 0:
            print(f"❌ Pet index is empty! Run pet_index_builder.py first.")
            return False
        print(f"✅ Pet index loaded with {pet_count} players")

        # Start processing
        print(f"\n🚀 Starting enhanced parsing with force rebuild...")
        print(f"⏳ This will process ~2,480 matches - estimated time: 30-60 minutes")
        print(f"📊 Progress updates every 50 matches")
        print(f"-" * 80)

        # Call the main parsing function
        parser.parse_enhanced_matches(enhanced_index, logs_dir, output_csv, force_rebuild=True)

        print(f"\n🎉 Enhanced parsing completed successfully!")
        print(f"💾 Results saved to: {output_csv}")

        # Show summary stats
        show_interrupt_stats(output_csv)

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"🔧 Make sure enhanced_combat_parser_production_ENHANCED.py is in the same directory")
        return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True


def show_interrupt_stats(output_csv: str):
    """Show interrupt statistics from the output file."""
    try:
        import pandas as pd
        df = pd.read_csv(output_csv)
        
        total_matches = len(df)
        zero_interrupts = len(df[df['interrupt_success_own'] == 0])
        has_interrupts = len(df[df['interrupt_success_own'] > 0])
        avg_interrupts = df['interrupt_success_own'].mean()
        max_interrupts = df['interrupt_success_own'].max()
        
        print(f"\n📊 INTERRUPT STATISTICS:")
        print(f"   Total matches: {total_matches}")
        print(f"   Matches with interrupts: {has_interrupts} ({has_interrupts/total_matches*100:.1f}%)")
        print(f"   Matches with zero interrupts: {zero_interrupts} ({zero_interrupts/total_matches*100:.1f}%)")
        print(f"   Average interrupts per match: {avg_interrupts:.2f}")
        print(f"   Maximum interrupts in a match: {max_interrupts}")
        
    except Exception as e:
        print(f"⚠️ Could not show stats: {e}")


def main():
    """Main function with menu."""
    print("🎮 Enhanced Combat Parser with Pet Index Logic")
    print("=" * 60)
    print("Choose processing mode:")
    print("1. Selective Re-processing (only zero interrupt matches)")
    print("2. Full Processing (force rebuild all matches)")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                print("\n🎯 Starting selective re-processing...")
                success = run_selective_reprocessing()
                break
            elif choice == '2':
                print("\n🚀 Starting full processing...")
                success = run_full_processing()
                break
            elif choice == '3':
                print("👋 Goodbye!")
                return
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
                continue
                
        except KeyboardInterrupt:
            print(f"\n⚠️ Processing interrupted by user")
            return
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return
    
    if success:
        print(f"✅ Processing completed successfully!")
    else:
        print(f"❌ Processing failed - check error messages above")


if __name__ == '__main__':
    main()