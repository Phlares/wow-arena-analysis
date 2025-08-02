# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WoW (World of Warcraft) Arena gameplay analysis system that processes 6TB+ of arena match recordings to extract performance metrics for AI model training. The system parses combat logs and matches them with video recordings to create a comprehensive dataset for machine learning analysis.

## Key Commands (Updated - Consolidated Interface)

### Combat Parser Operations
```bash
# Unified combat parser interface (RECOMMENDED)
python combat_parser.py --mode production              # Run full production parser
python combat_parser.py --mode selective               # Run selective parsing menu
python combat_parser.py --mode debug --match match.mp4 # Debug specific match
python combat_parser.py --mode test --feature all      # Test parser features
python combat_parser.py --mode validate                # Validate parser setup

# Legacy commands (still functional)
python run_enhanced_parser_selective.py               # Menu interface
python enhanced_combat_parser_production_ENHANCED.py  # Direct production run
```

### Zone Extraction & Computer Vision
```bash
# Unified zone extraction interface (RECOMMENDED)
python zone_extractor.py --extract --svg file.svg --format scaled  # Extract zones
python zone_extractor.py --validate                                 # Validate zones
python zone_extractor.py --lookup --zone 25                        # Look up zone
python zone_extractor.py --mismatch                                 # Analyze mismatches

# Legacy zone operations (archived)
# python scaled_zone_extractor.py  # Now: zone_extractor.py --extract --format scaled
```

### OCR Analysis & Testing
```bash
# Unified OCR analyzer interface (RECOMMENDED)
python ocr_analyzer.py --debug --video match.mp4 --time 90  # Comprehensive debug
python ocr_analyzer.py --quick --video match.mp4            # Quick OCR test
python ocr_analyzer.py --validate                           # Validate OCR setup
python ocr_analyzer.py --test-basic                         # Test basic OCR

# Legacy OCR operations (archived)
# python debug_ocr_tester.py      # Now: ocr_analyzer.py --debug
# python frame_ocr_tester.py      # Now: ocr_analyzer.py --quick
```

### Frame Generation & Testing
```bash
# Unified frame generator interface (RECOMMENDED)
python frame_generator.py --test-frames --type scaled       # Generate test frames
python frame_generator.py --extract --video match.mp4       # Extract from video
python frame_generator.py --sample --output sample.png      # Create sample frame

# Legacy frame operations (archived)
# python scaled_test_frame_generator.py  # Now: frame_generator.py --test-frames
```

### System Validation
```bash
# Unified validation interface (RECOMMENDED)
python system_validator.py --all                      # Validate everything
python system_validator.py --parser --cv              # Validate specific systems
python system_validator.py --dependencies --files     # Check setup
python system_validator.py --tesseract                # Test OCR config

# Legacy validation (still available)
python validate_production_parser_ROBUST.py           # Parser validation
python validate_cv_setup.py                           # CV validation
```

### Data Processing & Setup
```bash
# Core utilities (unchanged)
python build_index.py                    # Build video index
python pet_index_builder.py              # Build pet index
python test_timestamp_matching.py        # Test timestamp matching
python pet_index_validation_test.py      # Validate pet detection
python focused_pet_validation_test.py    # Focused pet validation

# Zone lookup utility
python zone_definition_lookup.py         # Show all 73 zone definitions
python zone_definition_lookup.py 25      # Look up specific zone
```

### Project Maintenance
```bash
# Project organization
python cleanup_outputs.py               # Clean and organize output files
```

## Architecture Overview

### Core Components (Consolidated)

1. **Unified Combat Parser** (`combat_parser.py`)
   - Consolidates all parsing functionality with mode selection
   - Production, selective, debug, test, and validation modes
   - Integrates enhanced parser, selective runner, and debug tools
   - Processes 2,480+ matches with smart arena boundary detection

2. **Zone Extraction System** (`zone_extractor.py`)
   - Unified interface for all zone mapping operations
   - Scaled extraction with 1.33x factor for 3440x1440 resolution
   - 73 zones mapped with 83% accuracy on 2025 footage
   - Validation and lookup functionality integrated

3. **OCR Analysis Framework** (`ocr_analyzer.py`)
   - Comprehensive OCR testing and debugging
   - Tesseract OCR 5.5.0 integration with proper configuration
   - Multi-preprocessing techniques for WoW UI elements
   - Debug mode with detailed zone-by-zone analysis

4. **Frame Generation Tools** (`frame_generator.py`)
   - Test frame creation with zone overlays
   - Video frame extraction for analysis
   - Sample frame generation for testing
   - Multiple output formats and resolution support

5. **System Validation Suite** (`system_validator.py`)
   - Comprehensive validation of all system components
   - Dependency checking and configuration validation
   - Parser, CV, pet system, and Tesseract testing
   - Automated setup verification

6. **Computer Vision System** (Production Ready)
   - OpenCV 4.12.0 for video frame extraction and analysis
   - Tesseract OCR 5.5.0 for spell name and UI text recognition
   - Supports 3440x1440 ultrawide resolution with 60fps video
   - 73 zones mapped with proper coordinate transformation

### Data Flow

1. **Video Archive**: 11,355+ matches dating back to 2023
2. **Combat Logs**: Available from January 2025 onwards (`/Logs/` directory)
3. **Enhanced Index**: `master_index_enhanced.csv` with precise timestamp matching
4. **Feature Extraction**: Combat events parsed into structured metrics
5. **Zone Mapping**: `scaled_zone_mapping.json` with 73 UI zones for OCR
6. **Output**: `match_features_enhanced_VERIFIED.csv` ready for AI training

### Solo Shuffle Handling

Solo Shuffle matches require special processing:
- 6-round sessions with single session boundaries
- Bracket name equivalence: "Solo Shuffle" ↔ "Rated Solo Shuffle"
- Death correlation across all rounds for validation
- Complex scoring: 3+ rounds won = overall win

### Zone ID Mapping

The system maps numeric zone IDs to arena names:
- 572: "Ruins of Lordaeron"
- 1134: "Tiger's Peak"  
- 1505: "Nagrand"
- 2509: "Maldraxxus"
- And 10+ additional arenas

### Computer Vision Zone System

The system identifies 73 distinct UI zones across 9 categories:
- **Health zones**: Player, target, and arena enemy health bars
- **Resource zones**: Mana, energy, and specialized resources
- **Name zones**: Player and character name displays
- **Ability zones**: Player and enemy spell tracking
- **Cast bar zones**: Spell casting progress indicators
- **Combat log zones**: Text-based combat information
- **Arena info zones**: Match time, location, and status
- **CC tracking zones**: Crowd control and effect monitoring
- **Medallion zones**: PvP trinket and racial ability tracking

## File Organization (Updated)

### Core Production Scripts (Consolidated)
- `combat_parser.py` - Unified combat parsing interface
- `zone_extractor.py` - Zone extraction and validation system
- `ocr_analyzer.py` - OCR testing and analysis framework
- `frame_generator.py` - Frame generation and extraction tools
- `system_validator.py` - Comprehensive system validation
- `cleanup_outputs.py` - Project organization utility

### Essential Data Processing
- `build_index.py` - Builds master index from JSON files
- `pet_index_builder.py` - Builds comprehensive pet index for detection
- `test_timestamp_matching.py` - Timestamp matching accuracy validation
- `pet_index_validation_test.py` - Pet index validation
- `focused_pet_validation_test.py` - Focused pet testing

### Legacy Scripts (Archived)
- `archive/` - Contains 17 superseded scripts preserved for reference
  - `parse_logs_fast.py` - Original parser implementation
  - `debug_enhanced_parser_with_detailed_logging.py` - Old debug parser
  - `test_enhanced_parser_specific.py` - Old parser testing
  - `*_zone_extractor.py` - Previous zone extraction versions
  - `*_ocr_tester.py` - Previous OCR testing versions
  - `*_frame_generator.py` - Previous frame generation versions

### Current Production Data
- `master_index_enhanced.csv` - Video index with precise timestamps
- `match_features_enhanced_VERIFIED.csv` - Parser output with combat metrics
- `scaled_zone_mapping.json` - 73 UI zones with proper scaling
- `player_pet_index.json` - Pet name mappings for dispel tracking
- `Zone_Colour_Definitions.md` - Computer vision zone documentation

### Organized Output Directories
- `archive_outputs/` - Superseded output files
- `debug_outputs/` - Debug and analysis files
- `debug_ocr_output/` - Detailed OCR debugging (653 files)

### Data Directories
- `/2023-05/`, `/2023-06/`, etc. - Monthly video archive directories
- `/Logs/` - Combat log files (WoWCombatLog-*.txt format)
- `arena.db` - SQLite database for match storage

## Development Notes

### Current Status (Updated)
- **Project refactored**: 29 scripts consolidated into 6 focused modules
- **83% zone accuracy** achieved on 2025 WoW Arena footage
- **73 zones mapped** with proper 3440x1440 scaling factor
- Enhanced parser processing 2,480+ matches successfully
- Computer vision system operational with Tesseract OCR integration
- Clean project structure with organized archives and outputs

### Key Algorithms
1. **Smart Arena Boundary Detection**: Multi-strategy search with validation
2. **Death Correlation**: Cross-verify deaths between combat logs and video metadata
3. **Enhanced Tiebreaking**: Differentiate back-to-back matches on same map/bracket
4. **Zone Coordinate Transformation**: 1.33x scaling for proper resolution coverage
5. **Multi-preprocessing OCR**: Various techniques for WoW UI text recognition

### Performance Metrics Tracked
- `cast_success_own`: Player spells cast successfully  
- `interrupt_success_own`: Interrupts performed
- `times_interrupted`: Times player was interrupted
- `precog_gained_own/enemy`: Precognition buffs gained
- `purges_own`: Pet dispels performed
- `spells_cast/spells_purged`: Detailed spell tracking lists

### Computer Vision Metrics
- **Zone coverage**: 99.3% width, 95.5% height of 3440x1440 resolution
- **Zone accuracy**: 83% correct positioning on 2025 footage
- **OCR targets**: 55 priority regions for text recognition
- **Validation score**: 100/100 on coordinate transformation

### Expected Dataset Output
- ~2,480 matches with verified unique features
- 14-field feature schema per match
- 73 UI zones available for computer vision analysis
- Processing rate >95% for matches with available combat logs
- <5% zero-value matches target
- Ready for AI model training pipeline

## Testing & Validation

Comprehensive testing through consolidated validation system:
- **System Validator**: `python system_validator.py --all`
- **Combat Parser**: Built-in validation modes and debug output
- **Zone Mapping**: Visual validation with mismatch analysis
- **OCR System**: Multi-configuration testing with confidence scoring
- **Frame Generation**: Test frame creation with overlay validation

### Quick Validation Commands
```bash
# Complete system check
python system_validator.py --all

# Test specific components
python combat_parser.py --mode validate
python ocr_analyzer.py --validate
python zone_extractor.py --validate

# Debug specific issues
python ocr_analyzer.py --debug --video match.mp4
python zone_extractor.py --mismatch
```

## Usage Examples

### Typical Workflow
```bash
# 1. Validate system setup
python system_validator.py --all

# 2. Extract and validate zones
python zone_extractor.py --extract --validate

# 3. Test OCR on actual footage
python ocr_analyzer.py --debug --video "2025-05-31_23-59-18_-_Phlurbotomy_-_3v3_Enigma_Crucible_(Loss).mp4"

# 4. Run production parser
python combat_parser.py --mode production

# 5. Generate test frames for verification
python frame_generator.py --test-frames --type scaled
```

### Zone Analysis Workflow
```bash
# Look up specific zones
python zone_definition_lookup.py 25

# Analyze zone mapping accuracy
python zone_extractor.py --mismatch

# Generate test frames with overlays
python frame_generator.py --test-frames --type all
```

The system is now **streamlined, documented, and production-ready** for AI training data extraction from WoW Arena recordings.