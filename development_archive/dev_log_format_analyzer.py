#!/usr/bin/env python3
"""
Combat Log Format Analyzer

Analyzes the actual format of combat log lines to understand why position 
data extraction is failing on real logs vs. the test example.
"""

from pathlib import Path
import re
from collections import defaultdict

def analyze_log_format():
    """Analyze the format of actual combat log lines."""
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print("COMBAT LOG FORMAT ANALYSIS")
    print("=" * 80)
    print(f"Analyzing: {log_file.name}")
    print()
    
    # Track different line formats
    format_examples = defaultdict(list)
    event_counts = defaultdict(int)
    parameter_counts = defaultdict(int)
    
    with open(log_file, 'r', encoding='utf-8') as f:
        line_count = 0
        
        for line in f:
            line_count += 1
            if line_count > 5000:  # Analyze first 5000 lines
                break
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Split timestamp from event data
            parts = line.strip().split('  ', 1)
            if len(parts) != 2:
                continue
            
            timestamp_str, event_data = parts
            params = [p.strip() for p in event_data.split(',')]
            
            if len(params) < 1:
                continue
            
            event_type = params[0]
            param_count = len(params)
            
            event_counts[event_type] += 1
            parameter_counts[param_count] += 1
            
            # Collect examples of different event types with their parameter counts
            key = f"{event_type}_{param_count}"
            if len(format_examples[key]) < 2:  # Keep up to 2 examples per format
                format_examples[key].append({
                    'line_number': line_count,
                    'timestamp': timestamp_str,
                    'params': params[:15],  # First 15 params for analysis
                    'total_params': param_count,
                    'raw_line': line.strip()[:200] + "..." if len(line.strip()) > 200 else line.strip()
                })
    
    # Show event type frequency
    print("EVENT TYPE FREQUENCY:")
    print("-" * 50)
    top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    for event_type, count in top_events:
        print(f"{event_type:25s}: {count:4d}")
    
    print(f"\nPARAMETER COUNT DISTRIBUTION:")
    print("-" * 50)
    param_dist = sorted(parameter_counts.items())
    for param_count, count in param_dist:
        print(f"{param_count:2d} parameters: {count:4d} lines")
    
    # Show examples of position-relevant events
    position_events = ['SPELL_CAST_SUCCESS', 'SPELL_DAMAGE', 'SPELL_HEAL']
    
    print(f"\n{'='*80}")
    print("POSITION EVENT ANALYSIS")
    print("=" * 80)
    
    for event_type in position_events:
        print(f"\n{event_type} EXAMPLES:")
        print("-" * 60)
        
        # Find examples of this event type
        event_examples = []
        for key, examples in format_examples.items():
            if key.startswith(event_type):
                event_examples.extend(examples)
        
        if not event_examples:
            print("  No examples found")
            continue
        
        # Show different parameter count variations
        param_variations = defaultdict(list)
        for example in event_examples:
            param_variations[example['total_params']].append(example)
        
        for param_count in sorted(param_variations.keys()):
            examples = param_variations[param_count][:2]  # Show up to 2 examples
            
            print(f"\n  {param_count} Parameter Format ({len(param_variations[param_count])} occurrences):")
            
            for i, example in enumerate(examples):
                print(f"    Example {i+1} (Line {example['line_number']}):")
                print(f"      Timestamp: {example['timestamp']}")
                print(f"      Parameters 0-14: {example['params']}")
                print(f"      Raw: {example['raw_line']}")
                
                # Check if this might have advanced logging
                if param_count >= 25:  # Potentially enough for advanced logging
                    print(f"      -> Potentially has advanced logging data")
                    
                    # Try to find position-like data in last 10 parameters
                    full_params = example['raw_line'].split(',')
                    if len(full_params) >= param_count:
                        last_10 = full_params[-10:]
                        position_candidates = []
                        
                        for j, param in enumerate(last_10[:-1]):
                            try:
                                x = float(param.strip())
                                y = float(last_10[j+1].strip())
                                if abs(x) > 10 or abs(y) > 10:  # Non-trivial coordinates
                                    position_candidates.append((j-10+len(last_10), x, y))
                            except (ValueError, IndexError):
                                pass
                        
                        if position_candidates:
                            print(f"      -> Position candidates: {position_candidates}")
                        else:
                            print(f"      -> No clear position coordinates found")
                else:
                    print(f"      -> Insufficient parameters for advanced logging")
                print()

def find_arena_time_examples():
    """Find examples during known arena times."""
    log_file = Path("./Logs/WoWCombatLog-050625_182406.txt")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print(f"\n{'='*80}")
    print("ARENA TIME EXAMPLES")
    print("=" * 80)
    
    # Look for lines during arena match times (around 19:04)
    arena_pattern = r"5/6/2025 19:04:[23456][0-9]"
    position_events = ['SPELL_CAST_SUCCESS', 'SPELL_DAMAGE', 'SPELL_HEAL']
    
    arena_examples = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if re.search(arena_pattern, line):
                # Check if it's a position event
                for event_type in position_events:
                    if event_type in line:
                        parts = line.strip().split('  ', 1)
                        if len(parts) == 2:
                            params = parts[1].split(',')
                            arena_examples.append({
                                'line_number': line_num,
                                'event_type': event_type,
                                'param_count': len(params),
                                'raw_line': line.strip()
                            })
                            
                            if len(arena_examples) >= 5:  # Get first 5
                                break
                if len(arena_examples) >= 5:
                    break
    
    print(f"Found {len(arena_examples)} arena-time position events:")
    print()
    
    for i, example in enumerate(arena_examples):
        print(f"Arena Example {i+1} (Line {example['line_number']}):")
        print(f"  Event: {example['event_type']}")
        print(f"  Parameters: {example['param_count']}")
        print(f"  Line: {example['raw_line']}")
        
        # Try to parse this line with our parser
        print(f"  Analysis: ", end="")
        if example['param_count'] >= 25:
            print("Sufficient parameters for advanced logging")
        else:
            print("Insufficient parameters - likely no advanced logging")
        print()

if __name__ == "__main__":
    analyze_log_format()
    find_arena_time_examples()