#!/usr/bin/env python3
"""
WoW Arena System Validator - Unified Interface
Consolidates all validation functionality
"""

import sys
import argparse
from pathlib import Path

def import_validation_functions():
    """Import validation functions from existing modules"""
    try:
        from validate_production_parser_ROBUST import main as validate_parser
        from validate_cv_setup import main as validate_cv
        from pet_index_validation_test import main as validate_pets
        from focused_pet_validation_test import main as validate_pets_focused
        
        return {
            'validate_parser': validate_parser,
            'validate_cv': validate_cv, 
            'validate_pets': validate_pets,
            'validate_pets_focused': validate_pets_focused
        }
    except ImportError as e:
        print(f"ERROR: Missing required validation modules: {e}")
        return None

def validate_parser_system():
    """Validate production parser system"""
    funcs = import_validation_functions()
    if not funcs:
        return False
    
    print("Validating Production Parser System...")
    print("=" * 50)
    
    try:
        funcs['validate_parser']()
        return True
    except Exception as e:
        print(f"ERROR: Parser validation failed: {e}")
        return False

def validate_computer_vision():
    """Validate computer vision setup"""
    funcs = import_validation_functions()
    if not funcs:
        return False
    
    print("Validating Computer Vision Setup...")
    print("=" * 50)
    
    try:
        funcs['validate_cv']()
        return True
    except Exception as e:
        print(f"ERROR: CV validation failed: {e}")
        return False

def validate_pet_system(focused: bool = False):
    """Validate pet detection and tracking system"""
    funcs = import_validation_functions()
    if not funcs:
        return False
    
    if focused:
        print("Validating Pet System (Focused Test)...")
        validation_func = funcs['validate_pets_focused']
    else:
        print("Validating Pet System (Full Test)...")
        validation_func = funcs['validate_pets']
    
    print("=" * 50)
    
    try:
        validation_func()
        return True
    except Exception as e:
        print(f"ERROR: Pet validation failed: {e}")
        return False

def validate_dependencies():
    """Validate all system dependencies"""
    print("Validating System Dependencies...")
    print("=" * 40)
    
    dependencies = {
        'OpenCV': ('cv2', 'Computer vision processing'),
        'NumPy': ('numpy', 'Numerical computations'),
        'Pandas': ('pandas', 'Data processing'),
        'Tesseract': ('pytesseract', 'OCR functionality'),
        'SQLite3': ('sqlite3', 'Database operations'),
        'JSON': ('json', 'Data serialization'),
        'Pathlib': ('pathlib', 'File system operations')
    }
    
    missing_deps = []
    
    for name, (module, description) in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {name:12} - {description}")
        except ImportError:
            print(f"✗ {name:12} - {description} (MISSING)")
            missing_deps.append(name)
    
    if missing_deps:
        print(f"\nERROR: Missing dependencies: {', '.join(missing_deps)}")
        return False
    else:
        print(f"\n✓ All dependencies validated successfully")
        return True

def validate_file_structure():
    """Validate required file structure"""
    print("Validating File Structure...")
    print("=" * 30)
    
    required_files = [
        'CLAUDE.md',
        'scaled_zone_mapping.json',
        'player_pet_index.json',
        'master_index_enhanced.csv'
    ]
    
    required_dirs = [
        '2023-05',
        '2023-06',
        '2025-05'
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"✓ File: {file_name}")
        else:
            print(f"✗ File: {file_name} (MISSING)")
            missing_files.append(file_name)
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✓ Directory: {dir_name}")
        else:
            print(f"✗ Directory: {dir_name} (MISSING)")
            missing_dirs.append(dir_name)
    
    if missing_files or missing_dirs:
        print(f"\nWARNING: Missing files/directories found")
        if missing_files:
            print(f"  Missing files: {', '.join(missing_files)}")
        if missing_dirs:
            print(f"  Missing directories: {', '.join(missing_dirs)}")
        return False
    else:
        print(f"\n✓ File structure validated successfully")
        return True

def validate_tesseract_config():
    """Validate Tesseract OCR configuration"""
    print("Validating Tesseract Configuration...")
    print("=" * 40)
    
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    if Path(tesseract_path).exists():
        print(f"✓ Tesseract executable found: {tesseract_path}")
        
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Test basic OCR
            import numpy as np
            test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
            import cv2
            cv2.putText(test_image, 'TEST', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            result = pytesseract.image_to_string(test_image).strip()
            if 'TEST' in result:
                print(f"✓ Tesseract OCR test successful")
                return True
            else:
                print(f"⚠ Tesseract OCR test returned: '{result}' (expected 'TEST')")
                return False
                
        except Exception as e:
            print(f"✗ Tesseract OCR test failed: {e}")
            return False
    else:
        print(f"✗ Tesseract executable not found: {tesseract_path}")
        return False

def main():
    """Main unified validation interface"""
    parser = argparse.ArgumentParser(
        description="WoW Arena System Validator - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                                    # Validate everything
  %(prog)s --parser --cv                           # Validate parser and CV
  %(prog)s --dependencies --files                  # Check deps and files
  %(prog)s --pets --focused                        # Quick focused pet test
  %(prog)s --tesseract                             # Test OCR configuration
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Run all validation tests')
    parser.add_argument('--parser', action='store_true',
                       help='Validate production parser system')
    parser.add_argument('--cv', action='store_true',
                       help='Validate computer vision setup')
    parser.add_argument('--pets', action='store_true',
                       help='Validate pet detection system')
    parser.add_argument('--dependencies', action='store_true',
                       help='Validate system dependencies')
    parser.add_argument('--files', action='store_true',
                       help='Validate file structure')
    parser.add_argument('--tesseract', action='store_true',
                       help='Validate Tesseract OCR configuration')
    
    parser.add_argument('--focused', action='store_true',
                       help='Use focused/quick tests where available')
    
    args = parser.parse_args()
    
    # If no specific validation requested, show help
    if not any([args.all, args.parser, args.cv, args.pets, args.dependencies, 
               args.files, args.tesseract]):
        print("No validation specified. Use --all for complete validation or see --help")
        parser.print_help()
        return 1
    
    print("WoW Arena System Validator")
    print("=" * 50)
    
    success = True
    tests_run = []
    
    try:
        if args.all or args.dependencies:
            tests_run.append("Dependencies")
            success &= validate_dependencies()
            print()
        
        if args.all or args.files:
            tests_run.append("File Structure")
            success &= validate_file_structure()
            print()
        
        if args.all or args.tesseract:
            tests_run.append("Tesseract")
            success &= validate_tesseract_config()
            print()
        
        if args.all or args.cv:
            tests_run.append("Computer Vision")
            success &= validate_computer_vision()
            print()
        
        if args.all or args.parser:
            tests_run.append("Parser System")
            success &= validate_parser_system()
            print()
        
        if args.all or args.pets:
            tests_run.append("Pet System")
            success &= validate_pet_system(args.focused)
            print()
            
    except KeyboardInterrupt:
        print("\nValidation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: Validation failed: {e}")
        return 1
    
    # Final summary
    print("=" * 50)
    print(f"VALIDATION SUMMARY:")
    print(f"  Tests run: {', '.join(tests_run)}")
    
    if success:
        print(f"  Status: ✓ ALL TESTS PASSED")
        print(f"\n🎉 System validation completed successfully!")
        return 0
    else:
        print(f"  Status: ✗ SOME TESTS FAILED")
        print(f"\n⚠️  Please address the issues above before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())