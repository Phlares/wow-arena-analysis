# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WoW (World of Warcraft) Arena gameplay analysis system that processes 6TB+ of arena match recordings to extract performance metrics for AI model training. The system parses combat logs and matches them with video recordings to create a comprehensive dataset for machine learning analysis.

## Key Commands

### Running the Combat Parser
```bash
# Main parser runner with menu interface (RECOMMENDED)
python run_enhanced_parser_selective.py

# Direct production parser execution (advanced users)
python enhanced_combat_parser_production_ENHANCED.py

# Debug single match with detailed logging
python debug_enhanced_parser_with_detailed_logging.py

# Validate parser output
python validate_production_parser_ROBUST.py

# Test specific parser features
python test_enhanced_parser_specific.py
```

### Data Processing & Setup
```bash
# Build video index with enhanced timestamps
python build_index.py

# Build pet index for comprehensive pet detection
python pet_index_builder.py

# Test timestamp matching accuracy
python test_timestamp_matching.py

# Validate pet index for dispel tracking
python pet_index_validation_test.py

# Focused pet validation on specific matches
python focused_pet_validation_test.py
```

### Computer Vision & Video Analysis
```bash
# Validate CV setup and dependencies
python validate_cv_setup.py

# Extract frames from WoW videos for UI analysis
python test_frame_extraction.py

# Test OCR on WoW UI elements and spell names
python test_wow_ocr.py
```

## Architecture Overview

### Core Components

1. **Enhanced Combat Parser** (`enhanced_combat_parser_production_ENHANCED.py`)
   - Main production system processing 2,480+ matches
   - Implements smart arena boundary detection
   - Extracts 14 combat metrics per match (casts, interrupts, purges, etc.)
   - Uses multi-strategy timestamp matching with death correlation verification

2. **Timestamp Matching System**
   - Correlates video recordings with combat log events
   - Three reliability levels: High (JSON start field ±30s), Medium (combat log parsing ±2min), Low (filename estimation ±5min)
   - Handles timezone conversions and format variations

3. **Arena Boundary Detection**
   - Smart algorithm to find correct arena start/end events
   - Validates both bracket type (2v2/3v3/Solo Shuffle) and map name
   - Prevents cross-match contamination from adjacent games

4. **Pet Combat Tracking**
   - Separates player actions from pet actions
   - Tracks pet dispels (Devour Magic) as `purges_own`
   - Maintains spell cast and purge lists for analysis

5. **Computer Vision System** (NEW)
   - OpenCV 4.12.0 for video frame extraction and analysis
   - Tesseract OCR 5.5.0 for spell name and UI text recognition
   - Supports 3440x1440 ultrawide resolution with 60fps video
   - Analyzes cast bars, player frames, and combat text regions

### Data Flow

1. **Video Archive**: 11,355+ matches dating back to 2023
2. **Combat Logs**: Available from January 2025 onwards (`/Logs/` directory)
3. **Enhanced Index**: `master_index_enhanced.csv` with precise timestamp matching
4. **Feature Extraction**: Combat events parsed into structured metrics
5. **Output**: `match_features_enhanced_VERIFIED.csv` ready for AI training

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

## File Organization

### Core Production Files
- `enhanced_combat_parser_production_ENHANCED.py` - Main parser with pet index integration
- `run_enhanced_parser_selective.py` - Menu-driven runner with selective processing
- `master_index_enhanced.csv` - Video index with precise timestamps
- `match_features_enhanced_VERIFIED.csv` - Parser output with combat metrics

### Essential Utilities
- `build_index.py` - Builds master index from JSON files
- `pet_index_builder.py` - Builds comprehensive pet index for detection
- `debug_enhanced_parser_with_detailed_logging.py` - Single-match detailed debugging

### Testing & Validation
- `validate_production_parser_ROBUST.py` - Comprehensive validation suite
- `test_enhanced_parser_specific.py` - Targeted functionality testing
- `test_timestamp_matching.py` - Timestamp matching accuracy validation
- `pet_index_validation_test.py` - Pet index validation on problematic matches
- `focused_pet_validation_test.py` - Focused pet testing on specific match window

### Computer Vision Tools
- `validate_cv_setup.py` - CV dependencies validation (OpenCV, Tesseract, NumPy, etc.)
- `test_frame_extraction.py` - Video frame extraction and WoW UI region detection
- `test_wow_ocr.py` - OCR testing on WoW UI elements and spell names

### Legacy Reference
- `parse_logs_fast.py` - Original parser implementation (reference only)

### Data Files
- `/2023-05/`, `/2023-06/` - Monthly video archive directories
- `/Logs/` - Combat log files (WoWCombatLog-*.txt format)
- `arena.db` - SQLite database for match storage
- `player_pet_index.json` - Pet name mappings for dispel tracking
- `/test_frames/` - Extracted video frames for computer vision analysis

## Development Notes

### Current Status
- Enhanced parser successfully deployed and processing 2,480 matches
- ~100/2,480 matches complete (~4%) as of last update
- Death correlation verification working correctly
- Data quality verified through spot checks
- **Computer vision system operational**: OpenCV + Tesseract OCR ready for video analysis

### Key Algorithms
1. **Smart Arena Boundary Detection**: Multi-strategy search (backward/forward) with validation
2. **Death Correlation**: Cross-verify deaths between combat logs and video metadata
3. **Enhanced Tiebreaking**: Differentiate back-to-back matches on same map/bracket
4. **Multi-format Timestamp Parsing**: Handle various combat log timestamp formats

### Performance Metrics Tracked
- `cast_success_own`: Player spells cast successfully  
- `interrupt_success_own`: Interrupts performed
- `times_interrupted`: Times player was interrupted
- `precog_gained_own/enemy`: Precognition buffs gained
- `purges_own`: Pet dispels performed
- `spells_cast/spells_purged`: Detailed spell tracking lists

### Expected Dataset Output
- ~2,480 matches with verified unique features
- 14-field feature schema per match
- Processing rate >95% for matches with available combat logs
- <5% zero-value matches target
- Ready for AI model training pipeline

## Testing

No formal test framework configured. Testing done through:
- Manual validation scripts (`validate_production_parser_*.py`)
- Debug output comparison between versions
- Spot-checking high-activity matches for accuracy
- Death correlation verification against video metadata