#!/usr/bin/env python3
"""
Output File Cleanup Tool
Organizes and removes redundant output files
"""

import os
import shutil
from pathlib import Path

def cleanup_output_files():
    """Clean up redundant output files"""
    
    # Create organized directories
    directories = {
        'archive_outputs': 'Superseded output files',
        'current_outputs': 'Current production outputs',
        'debug_outputs': 'Debug and analysis outputs'
    }
    
    for dir_name, description in directories.items():
        Path(dir_name).mkdir(exist_ok=True)
        print(f"Created: {dir_name}/ - {description}")
    
    # Files to keep in root (current production outputs)
    keep_in_root = {
        # Core production outputs
        'scaled_zone_mapping.json',
        'player_pet_index.json', 
        'master_index_enhanced.csv',
        'match_features_enhanced_VERIFIED.csv',
        'zone_mismatch_analysis.png',
        
        # Essential references
        'Zone_Colour_Definitions.md',
        'Zone colour Definitions - Sheet1.csv',
        'CLAUDE.md',
        'COLOURS AND PIXELS_Annotated_Revised.svg',
        'COLOURS AND PIXELS_Annotated_Revised_IMG.png'
    }
    
    # Files to archive (superseded versions)
    archive_files = {
        # Superseded zone mappings
        'corrected_zone_mapping.json': 'Superseded by scaled_zone_mapping.json',
        'corrected_ocr_targets.json': 'Superseded OCR targets',
        'corrected_zone_overlay.png': 'Superseded zone overlay',
        'zone_overlay.png': 'Original zone overlay',
        'cv_zone_extraction.json': 'Early zone extraction',
        'zone_coordinate_mapping.json': 'Superseded coordinate mapping',
        
        # Old validation reports
        'corrected_validation_report.txt': 'Superseded validation',
        'ocr_validation_report.txt': 'Old OCR validation',
        'coordinate_mapping_summary.txt': 'Old coordinate summary',
        
        # Legacy data files
        'master_index.csv': 'Superseded by enhanced version',
        'match_features_enhanced.csv': 'Superseded by VERIFIED version',
        'debug_match_features.csv': 'Debug version only',
        'match_log_features.csv': 'Early version',
        'parsed_logs.json': 'Legacy parsed data',
        'pet_index_validation_12_matches.csv': 'Validation subset',
        'old_packages.txt': 'Development notes',
        
        # Test frames (superseded)
        'test_frame_comparison.png': 'Superseded test frame',
        'test_frame_full_resolution.png': 'Superseded test frame', 
        'test_frame_priority_overlay.png': 'Superseded test frame',
        'sample_test_frame.png': 'Superseded sample frame'
    }
    
    # Files to move to debug outputs
    debug_files = {
        'ocr_test_report.txt': 'OCR test results',
        'ocr_visualization.png': 'OCR visualization', 
        'test_frame_scaled_coverage.png': 'Current test frame',
        'build_index_errors.log': 'Build process log'
    }
    
    # Execute moves
    print("\nCleaning up output files...")
    
    # Move files to archive
    for filename, description in archive_files.items():
        if Path(filename).exists():
            shutil.move(filename, f'archive_outputs/{filename}')
            print(f"Archived: {filename} - {description}")
    
    # Move files to debug
    for filename, description in debug_files.items():
        if Path(filename).exists():
            shutil.move(filename, f'debug_outputs/{filename}')
            print(f"Debug: {filename} - {description}")
    
    # Keep important files in root
    print(f"\nKept in root directory:")
    for filename in keep_in_root:
        if Path(filename).exists():
            print(f"  + {filename}")
        else:
            print(f"  - {filename} (missing)")
    
    # Handle debug_ocr_output directory
    if Path('debug_ocr_output').exists():
        print(f"\nNote: debug_ocr_output/ directory contains {len(list(Path('debug_ocr_output').iterdir()))} files")
        print("This directory is kept for detailed OCR debugging")
    
    print(f"\nCLEANUP COMPLETE")
    print(f"Root directory now contains only current production files")
    print(f"Archived files moved to: archive_outputs/")
    print(f"Debug files moved to: debug_outputs/")

def create_gitignore():
    """Create comprehensive .gitignore file"""
    
    gitignore_content = """# WoW Arena Analysis Project .gitignore

# Ignore video files (too large for git)
*.mp4
*.avi
*.mov
*.mkv

# Ignore large data files
*.db
master_index*.csv
match_features*.csv

# Ignore debug output directories
debug_ocr_output/
debug_outputs/
archive_outputs/
extracted_frames/
annotation_frames/

# Ignore temporary files
*.tmp
*.temp
nul
*.log

# Ignore Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/

# Ignore IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# Ignore OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Keep important config and mapping files
!player_pet_index.json
!scaled_zone_mapping.json
!CLAUDE.md
!Zone_Colour_Definitions.md
!*.svg
!*_IMG.png

# Keep core scripts
!*.py
!README.md
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    print("Created comprehensive .gitignore file")

def main():
    """Main cleanup function"""
    print("WoW Arena Output File Cleanup")
    print("=" * 40)
    
    cleanup_output_files()
    print()
    create_gitignore()
    
    print("\nProject cleanup completed!")
    print("\nDirectory structure:")
    print("  - Core scripts (consolidated)")
    print("  - Current production outputs")
    print("  - archive/ (old scripts)")  
    print("  - archive_outputs/ (old outputs)")
    print("  - debug_outputs/ (debug files)")
    print("  - .gitignore (comprehensive)")

if __name__ == "__main__":
    main()