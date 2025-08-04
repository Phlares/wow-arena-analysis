#!/usr/bin/env python3
"""
Combat Event Sampler

Shows exactly what combat events we're tracking for movement data and pulls
real examples from combat logs with position information extracted.
"""

from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict

class CombatEventSampler:
    """Samples combat events and shows position data extraction."""
    
    # These are the combat events we track for movement data
    SUPPORTED_EVENTS = {
        'SPELL_DAMAGE', 'SPELL_PERIODIC_DAMAGE', 'SPELL_HEAL', 'SPELL_PERIODIC_HEAL',
        'SPELL_ENERGIZE', 'SPELL_PERIODIC_ENERGIZE', 'RANGE_DAMAGE', 'SWING_DAMAGE',
        'SWING_DAMAGE_LANDED', 'SPELL_CAST_SUCCESS', 'SPELL_CAST_START'
    }
    
    def sample_combat_events(self, log_file: Path, max_samples_per_type: int = 2):
        """Sample combat events from log file and show position data extraction."""
        
        print(f"COMBAT EVENT TYPE ANALYSIS")
        print(f"Log File: {log_file.name}")
        print(f"="*80)
        
        event_samples = defaultdict(list)
        total_lines = 0
        matched_lines = 0
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                
                # Skip if we have enough samples for all event types
                if all(len(samples) >= max_samples_per_type for samples in event_samples.values() if len(samples) > 0):
                    break
                
                # Parse line to get event type
                parts = line.strip().split('  ', 1)
                if len(parts) != 2:
                    continue
                
                timestamp_str, event_data = parts
                event_params = [p.strip() for p in event_data.split(',')]
                
                if len(event_params) < 1:
                    continue
                
                event_type = event_params[0]
                
                # Check if this is a supported event type
                if event_type in self.SUPPORTED_EVENTS:
                    # Only collect if we need more samples of this type
                    if len(event_samples[event_type]) < max_samples_per_type:
                        
                        # Try to extract position data
                        position_data = self._extract_position_from_line(line)
                        
                        # Only store if it has position data
                        if position_data['has_position']:
                            event_samples[event_type].append({
                                'raw_line': line.strip(),
                                'event_type': event_type,
                                'timestamp': timestamp_str,
                                'position_x': position_data['x'],
                                'position_y': position_data['y'],
                                'source_name': position_data['source_name'],
                                'source_guid': position_data['source_guid'],
                                'coordinate_system': position_data['coordinate_system']
                            })
                            matched_lines += 1
                
                # Progress indicator
                if total_lines % 10000 == 0:
                    print(f"  Processed {total_lines:,} lines, found {matched_lines} with position data...")
        
        print(f"\nProcessing complete:")
        print(f"  Total lines processed: {total_lines:,}")
        print(f"  Lines with position data: {matched_lines}")
        print(f"  Event types found: {len(event_samples)}")
        
        # Display samples for each event type
        self._display_event_samples(event_samples)
        
        return event_samples
    
    def _extract_position_from_line(self, line: str) -> dict:
        """Extract position data from a combat log line."""
        result = {
            'has_position': False,
            'x': 0.0,
            'y': 0.0,
            'source_name': '',
            'source_guid': '',
            'coordinate_system': 'unknown'
        }
        
        # Split into components
        parts = line.strip().split('  ', 1)
        if len(parts) != 2:
            return result
        
        timestamp_str, event_data = parts
        params = [p.strip() for p in event_data.split(',')]
        
        if len(params) < 20:  # Need enough parameters for advanced logging
            return result
        
        # Extract source information
        if len(params) > 1:
            result['source_guid'] = params[1]
        
        if len(params) > 2:
            name_match = re.search(r'"([^"]+)"', params[2])
            if name_match:
                result['source_name'] = name_match.group(1)
        
        # Look for position coordinates in the last ~10 parameters
        for i in range(max(0, len(params) - 10), len(params) - 1):
            try:
                x = float(params[i])
                y = float(params[i + 1])
                
                # Basic sanity check: reasonable coordinate ranges
                if abs(x) < 10000 and abs(y) < 10000 and (abs(x) > 0.1 or abs(y) > 0.1):
                    result['x'] = x
                    result['y'] = y
                    result['has_position'] = True
                    
                    # Classify coordinate system
                    if abs(x) < 100 and abs(y) < 100:
                        result['coordinate_system'] = 'local_small'
                    elif abs(x) < 1000 and abs(y) < 1000:
                        result['coordinate_system'] = 'local_medium'
                    elif x < -1000:
                        result['coordinate_system'] = 'world_negative'
                    elif x > 1000:
                        result['coordinate_system'] = 'world_positive'
                    else:
                        result['coordinate_system'] = 'mixed'
                    
                    break
            except (ValueError, IndexError):
                continue
        
        return result
    
    def _display_event_samples(self, event_samples: dict):
        """Display samples for each event type with position analysis."""
        
        print(f"\n{'='*80}")
        print(f"COMBAT EVENT SAMPLES WITH POSITION DATA")
        print(f"{'='*80}")
        
        for event_type in sorted(self.SUPPORTED_EVENTS):
            samples = event_samples.get(event_type, [])
            
            print(f"\n{'-'*60}")
            print(f"EVENT TYPE: {event_type}")
            print(f"Samples found: {len(samples)}")
            print(f"{'-'*60}")
            
            if not samples:
                print("  No samples with position data found")
                continue
            
            for i, sample in enumerate(samples):
                print(f"\nSample {i+1}:")
                print(f"  Timestamp: {sample['timestamp']}")
                print(f"  Source: {sample['source_name']} ({sample['source_guid']})")
                print(f"  Position: ({sample['position_x']:.2f}, {sample['position_y']:.2f})")
                print(f"  Coordinate System: {sample['coordinate_system']}")
                print(f"  Raw Line:")
                
                # Format raw line for readability - break at commas but keep reasonable line length
                raw_line = sample['raw_line']
                if len(raw_line) > 120:
                    # Find a good break point around comma after ~80 chars
                    break_point = raw_line.find(',', 80)
                    if break_point > 0:
                        print(f"    {raw_line[:break_point]},")
                        print(f"    {raw_line[break_point+1:]}")
                    else:
                        print(f"    {raw_line}")
                else:
                    print(f"    {raw_line}")
        
        # Summary statistics
        print(f"\n{'='*80}")
        print(f"SUMMARY STATISTICS")
        print(f"{'='*80}")
        
        total_samples = sum(len(samples) for samples in event_samples.values())
        print(f"Total event samples with position data: {total_samples}")
        
        # Coordinate system distribution
        coord_systems = defaultdict(int)
        for samples in event_samples.values():
            for sample in samples:
                coord_systems[sample['coordinate_system']] += 1
        
        print(f"\nCoordinate System Distribution:")
        for system, count in sorted(coord_systems.items()):
            percentage = (count / total_samples) * 100 if total_samples > 0 else 0
            print(f"  {system}: {count} samples ({percentage:.1f}%)")
        
        # Event type frequency
        print(f"\nEvent Type Frequency (with position data):")
        for event_type in sorted(event_samples.keys()):
            count = len(event_samples[event_type])
            print(f"  {event_type}: {count} samples")

def main():
    """Sample combat events from a known log file."""
    
    # Use the same log file we analyzed before
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        print("Available log files:")
        logs_dir = Path("./Logs")
        if logs_dir.exists():
            for log in logs_dir.glob("*.txt"):
                print(f"  {log.name}")
        return
    
    # Sample combat events
    sampler = CombatEventSampler()
    samples = sampler.sample_combat_events(log_file, max_samples_per_type=2)
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"This shows the exact combat events we track for movement data.")
    print(f"Each event type includes the source entity's position at the time of the event.")
    print(f"Position data comes from WoW's advanced combat logging at the end of each line.")

if __name__ == "__main__":
    main()