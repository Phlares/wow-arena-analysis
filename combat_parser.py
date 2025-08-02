#!/usr/bin/env python3
"""
WoW Arena Combat Parser - Unified Interface
Consolidates all combat parsing functionality with mode selection
"""

import sys
import argparse
from pathlib import Path

def import_parser_functions():
    """Import all parser functions and handle dependencies"""
    try:
        # Import from existing enhanced parser
        from enhanced_combat_parser_production_ENHANCED import (
            EnhancedCombatParser, 
            main as production_main
        )
        from run_enhanced_parser_selective import main as selective_main
        
        return {
            'production_main': production_main,
            'selective_main': selective_main,
            'EnhancedCombatParser': EnhancedCombatParser
        }
    except ImportError as e:
        print(f"ERROR: Missing required parser modules: {e}")
        return None

def debug_single_match(match_path: str, detailed: bool = True):
    """Debug single match with detailed logging"""
    try:
        from debug_enhanced_parser_with_detailed_logging import main as debug_main
        # Set the match path and run debug
        sys.argv = ['debug_parser', match_path]
        if detailed:
            sys.argv.append('--detailed')
        debug_main()
    except ImportError:
        print("ERROR: Debug parser module not found")
        return False
    return True

def test_specific_features(test_type: str = 'all'):
    """Test specific parser features"""
    try:
        from test_enhanced_parser_specific import main as test_main
        sys.argv = ['test_parser', '--type', test_type]
        test_main()
    except ImportError:
        print("ERROR: Test parser module not found")
        return False
    return True

def main():
    """Main unified parser interface"""
    parser = argparse.ArgumentParser(
        description="WoW Arena Combat Parser - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode production                    # Run full production parser
  %(prog)s --mode selective                     # Run selective parsing menu
  %(prog)s --mode debug --match match.mp4      # Debug specific match
  %(prog)s --mode test --feature timestamps    # Test specific features
  %(prog)s --mode validate                      # Validate parser setup
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['production', 'selective', 'debug', 'test', 'validate'],
                       required=True,
                       help='Parser operation mode')
    
    parser.add_argument('--match', 
                       help='Specific match file for debug mode')
    
    parser.add_argument('--feature', 
                       choices=['timestamps', 'pets', 'arena_detection', 'all'],
                       default='all',
                       help='Specific feature to test')
    
    parser.add_argument('--detailed', 
                       action='store_true',
                       help='Enable detailed logging for debug mode')
    
    args = parser.parse_args()
    
    # Load parser functions
    parser_funcs = import_parser_functions()
    if not parser_funcs:
        return 1
    
    print(f"WoW Arena Combat Parser - Mode: {args.mode}")
    print("=" * 50)
    
    try:
        if args.mode == 'production':
            print("Running production parser...")
            parser_funcs['production_main']()
            
        elif args.mode == 'selective':
            print("Running selective parser menu...")
            parser_funcs['selective_main']()
            
        elif args.mode == 'debug':
            if not args.match:
                print("ERROR: Debug mode requires --match parameter")
                return 1
            print(f"Debugging match: {args.match}")
            debug_single_match(args.match, args.detailed)
            
        elif args.mode == 'test':
            print(f"Testing feature: {args.feature}")
            test_specific_features(args.feature)
            
        elif args.mode == 'validate':
            print("Validating parser setup...")
            try:
                from validate_production_parser_ROBUST import main as validate_main
                validate_main()
            except ImportError:
                print("ERROR: Validation module not found")
                return 1
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    print("Parser operation completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())