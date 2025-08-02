# WoW Arena Analysis System

A comprehensive gameplay analysis tool that processes 6TB+ of World of Warcraft Arena footage to extract performance metrics for AI model training and gameplay optimization.

## Overview

This system combines combat log parsing with computer vision analysis to create training datasets from thousands of WoW Arena matches. It extracts detailed combat metrics and UI information from video recordings for machine learning applications.

## Key Features

- **Combat Log Parsing**: Processes 2,480+ arena matches with smart boundary detection
- **Computer Vision**: Maps 73 UI zones with 83% accuracy on modern WoW interface
- **OCR Integration**: Tesseract-based text recognition for spell names and UI elements
- **Multi-Format Support**: Handles 2v2, 3v3, and Solo Shuffle arena formats
- **Timestamp Correlation**: Precise matching between video and combat log events
- **Pet Combat Tracking**: Separates player and pet actions for accurate analysis

## Quick Start

### Prerequisites
- Python 3.8+
- OpenCV 4.12.0+
- Tesseract OCR 5.5.0
- NumPy, Pandas for data processing

### Installation
1. Clone the repository
2. Install dependencies: `pip install opencv-python pytesseract pandas numpy`
3. Configure Tesseract path in scripts
4. Validate setup: `python system_validator.py --all`

### Basic Usage

```bash
# Validate system setup
python system_validator.py --all

# Extract UI zones from annotated SVG
python zone_extractor.py --extract --validate

# Test OCR on actual game footage
python ocr_analyzer.py --debug --video "match.mp4"

# Run production combat parser
python combat_parser.py --mode production

# Generate test frames for verification
python frame_generator.py --test-frames --type scaled
```

## Architecture

### Core Components (Consolidated)

1. **Combat Parser** (`combat_parser.py`)
   - Unified interface for all parsing operations
   - Supports production, debug, test, and validation modes
   - Processes combat logs with smart arena boundary detection

2. **Zone Extractor** (`zone_extractor.py`)
   - Maps 73 UI zones with proper scaling for 3440x1440 resolution
   - Validates zone positioning and coverage
   - Supports lookup and mismatch analysis

3. **OCR Analyzer** (`ocr_analyzer.py`)
   - Comprehensive OCR testing and debugging
   - Multi-preprocessing techniques for WoW UI elements
   - Detailed zone-by-zone analysis capabilities

4. **Frame Generator** (`frame_generator.py`)
   - Creates test frames with zone overlays
   - Extracts frames from video for analysis
   - Supports multiple output formats

5. **System Validator** (`system_validator.py`)
   - Validates all system components and dependencies
   - Tests OCR configuration and CV setup
   - Automated health checks

### Data Pipeline

1. **Video Archive**: 11,355+ matches from 2023-2025
2. **Combat Logs**: Detailed event logs from January 2025 onwards
3. **Zone Mapping**: 73 UI zones mapped with coordinate transformation
4. **Feature Extraction**: 14 combat metrics per match
5. **Output**: Training-ready datasets for AI models

## Computer Vision System

The system identifies 73 distinct UI zones across 9 categories:

- **Health/Resource Bars**: Player, target, and enemy status indicators
- **Character Names**: Player and NPC name displays
- **Spell Tracking**: Cast bars and ability cooldowns
- **Combat Information**: Text-based combat logs and notifications
- **Arena Status**: Match time, location, and scoring information
- **PvP Elements**: Trinket usage and crowd control tracking

**Zone Accuracy**: 83% correct positioning on 2025 WoW footage
**Coverage**: 99.3% width, 95.5% height of 3440x1440 resolution

## Performance Metrics

The system tracks comprehensive combat metrics:
- Spell casts and success rates
- Interrupt performance (given and received)
- Crowd control usage and effectiveness
- Resource management patterns
- Positioning and movement data
- Pet combat contributions

## File Structure

```
├── Core Scripts (6 total)
│   ├── combat_parser.py          # Unified parsing interface
│   ├── zone_extractor.py         # Zone mapping system
│   ├── ocr_analyzer.py           # OCR testing framework
│   ├── frame_generator.py        # Frame generation tools
│   ├── system_validator.py       # Validation suite
│   └── cleanup_outputs.py        # Project maintenance
├── Data Processing
│   ├── build_index.py            # Video index creation
│   ├── pet_index_builder.py      # Pet detection system
│   └── test_timestamp_matching.py # Correlation testing
├── Production Data
│   ├── scaled_zone_mapping.json   # 73 UI zones
│   ├── player_pet_index.json     # Pet classifications
│   ├── master_index_enhanced.csv  # Video catalog
│   └── match_features_enhanced_VERIFIED.csv # Training data
├── Legacy Scripts
│   └── archive/                   # 17 superseded scripts
└── Output Directories
    ├── archive_outputs/           # Old output files
    ├── debug_outputs/             # Debug information
    └── debug_ocr_output/          # Detailed OCR analysis
```

## Development Status

### Recently Completed
- **Major Refactoring**: Consolidated 29 scripts into 6 focused modules
- **Computer Vision**: Achieved 83% zone accuracy on modern WoW UI
- **OCR Integration**: Fully functional Tesseract setup with preprocessing
- **Project Organization**: Clean structure with archived legacy code
- **Documentation**: Updated guides and command references

### Production Ready
- Combat parser processing 2,480+ matches successfully
- Zone mapping system with proper coordinate transformation
- OCR framework with multiple preprocessing techniques
- Comprehensive validation and testing suite
- Organized output structure for training pipeline

## Contributing

This system is designed for AI training data extraction from WoW Arena recordings. The consolidated script structure makes it easy to:

- Add new combat metrics
- Enhance OCR preprocessing
- Extend zone mapping capabilities
- Integrate additional data sources
- Modify output formats

## Documentation

- **`CLAUDE.md`**: Detailed technical documentation and command reference
- **`Zone_Colour_Definitions.md`**: Computer vision zone specifications
- **Script Help**: All scripts include `--help` for command-line guidance

## Testing

Comprehensive testing available through:
```bash
python system_validator.py --all      # Complete system validation
python combat_parser.py --mode test   # Parser functionality tests
python ocr_analyzer.py --validate     # OCR system verification
```

## License

This project is for educational and research purposes, focused on AI training data extraction from gameplay recordings.

---

**Status**: Production Ready | **Version**: 2.0 (Consolidated) | **Last Updated**: August 2025