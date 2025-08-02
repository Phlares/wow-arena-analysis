#!/usr/bin/env python3
"""
WoW Arena Zone Extractor - Unified Interface
Consolidates all zone extraction functionality with multiple output formats
"""

import sys
import argparse
import json
from pathlib import Path

def import_extraction_functions():
    """Import extraction functions from existing modules"""
    try:
        from scaled_zone_extractor import ScaledZoneExtractor
        from correct_zone_extractor import main as correct_main
        
        return {
            'ScaledZoneExtractor': ScaledZoneExtractor,
            'correct_main': correct_main
        }
    except ImportError as e:
        print(f"ERROR: Missing required extraction modules: {e}")
        return None

def extract_zones(svg_file: str, output_format: str = 'scaled', validate: bool = True):
    """Extract zones with specified format and optional validation"""
    
    funcs = import_extraction_functions()
    if not funcs:
        return False
    
    print(f"Extracting zones from: {svg_file}")
    print(f"Output format: {output_format}")
    
    try:
        if output_format == 'scaled':
            # Use scaled extractor (current production)
            extractor = funcs['ScaledZoneExtractor'](svg_file)
            mapping = extractor.generate_scaled_mapping()
            
            if mapping:
                # Save mapping
                with open('zone_mapping_scaled.json', 'w') as f:
                    json.dump(mapping, f, indent=2)
                
                print(f"SUCCESS: Extracted {mapping['metadata']['total_zones']} zones")
                print(f"Coverage: {mapping['metadata']['coverage_validation']['coverage']['width_coverage_pct']:.1f}% width")
                
                if validate:
                    validation = mapping['metadata']['coverage_validation']
                    if validation['valid']:
                        print("✓ VALIDATION: Coverage targets met")
                    else:
                        print("⚠ VALIDATION: Coverage targets not fully met")
                        print(f"  Right edge: {validation['validation']['right_edge_diff']:.1f}px from target")
                        print(f"  Bottom edge: {validation['validation']['bottom_edge_diff']:.1f}px from target")
                
                return True
            else:
                print("ERROR: Failed to extract zones")
                return False
                
        elif output_format == 'corrected':
            # Use corrected extractor 
            print("Running corrected zone extraction...")
            funcs['correct_main']()
            return True
            
        else:
            print(f"ERROR: Unknown output format: {output_format}")
            return False
            
    except Exception as e:
        print(f"ERROR: Zone extraction failed: {e}")
        return False

def validate_zones(mapping_file: str = 'zone_mapping_scaled.json'):
    """Validate existing zone mapping"""
    try:
        from corrected_zone_validator import main as validate_main
        
        if Path(mapping_file).exists():
            print(f"Validating zones from: {mapping_file}")
            validate_main()
            return True
        else:
            print(f"ERROR: Mapping file not found: {mapping_file}")
            return False
            
    except ImportError:
        print("ERROR: Zone validator module not found")
        return False

def lookup_zone(zone_number: int = None, show_all: bool = False):
    """Look up zone definitions"""
    try:
        from zone_definition_lookup import show_zone_definitions, lookup_zone as lookup_func
        
        if show_all or zone_number is None:
            show_zone_definitions()
        else:
            lookup_func(zone_number)
        return True
        
    except ImportError:
        print("ERROR: Zone lookup module not found")
        return False

def analyze_mismatch(frame_path: str = None):
    """Analyze zone mapping mismatch with actual game frames"""
    try:
        from zone_mismatch_analyzer import analyze_zone_mismatch
        
        if frame_path:
            print(f"Analyzing mismatch with frame: {frame_path}")
        else:
            print("Analyzing mismatch with debug frame...")
            
        analyze_zone_mismatch()
        return True
        
    except ImportError:
        print("ERROR: Mismatch analyzer module not found")
        return False

def main():
    """Main unified zone extractor interface"""
    parser = argparse.ArgumentParser(
        description="WoW Arena Zone Extractor - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --extract --svg file.svg --format scaled    # Extract with scaling
  %(prog)s --validate                                   # Validate existing zones  
  %(prog)s --lookup --zone 25                          # Look up specific zone
  %(prog)s --lookup --all                              # Show all zone definitions
  %(prog)s --mismatch                                   # Analyze zone mismatches
        """
    )
    
    parser.add_argument('--extract', action='store_true', 
                       help='Extract zones from SVG')
    parser.add_argument('--validate', action='store_true',
                       help='Validate existing zone mapping')
    parser.add_argument('--lookup', action='store_true',
                       help='Look up zone definitions')
    parser.add_argument('--mismatch', action='store_true',
                       help='Analyze zone mapping mismatches')
    
    parser.add_argument('--svg', default='COLOURS AND PIXELS_Annotated_Revised.svg',
                       help='SVG file to extract from')
    parser.add_argument('--format', choices=['scaled', 'corrected'], default='scaled',
                       help='Extraction format')
    parser.add_argument('--zone', type=int,
                       help='Specific zone number to lookup')
    parser.add_argument('--all', action='store_true',
                       help='Show all zones (for lookup)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation after extraction')
    
    args = parser.parse_args()
    
    # Check that at least one action is specified
    if not any([args.extract, args.validate, args.lookup, args.mismatch]):
        print("ERROR: Must specify at least one action (--extract, --validate, --lookup, or --mismatch)")
        parser.print_help()
        return 1
    
    print("WoW Arena Zone Extractor")
    print("=" * 40)
    
    success = True
    
    try:
        if args.extract:
            if not Path(args.svg).exists():
                print(f"ERROR: SVG file not found: {args.svg}")
                return 1
            success &= extract_zones(args.svg, args.format, not args.no_validate)
        
        if args.validate:
            success &= validate_zones()
        
        if args.lookup:
            success &= lookup_zone(args.zone, args.all)
        
        if args.mismatch:
            success &= analyze_mismatch()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    if success:
        print("\nZone extraction operations completed successfully")
        return 0
    else:
        print("\nSome operations failed - check output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())