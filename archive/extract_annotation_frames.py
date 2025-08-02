"""
Extract frames for manual annotation from 3v3 and 2v2 videos.
Pulls 10 consecutive frames starting at 30s, each 0.5s apart.
Memory-efficient implementation staying under 22GB limit.
"""

import cv2
import os
import numpy as np
from pathlib import Path
import gc
import re

def get_monthly_videos():
    """Get first 3v3 and 2v2 video from each month."""
    monthly_videos = {}
    
    # Scan directories for videos by month (2023, 2024, 2025)
    base_dir = Path('.')
    for month_dir in sorted(list(base_dir.glob('2023-*')) + list(base_dir.glob('2024-*')) + list(base_dir.glob('2025-*'))):
        if month_dir.is_dir():
            videos = list(month_dir.glob('*.mp4'))
            
            # Find first 3v3 and 2v2 videos
            first_3v3 = None
            first_2v2 = None
            
            for video in sorted(videos):
                video_name = video.name.lower()
                
                # Look for 3v3 in filename
                if '3v3' in video_name and first_3v3 is None:
                    first_3v3 = video
                
                # Look for 2v2 in filename  
                if '2v2' in video_name and first_2v2 is None:
                    first_2v2 = video
                
                # Stop once we have both
                if first_3v3 and first_2v2:
                    break
            
            month_videos = {}
            if first_3v3:
                month_videos['3v3'] = first_3v3
            if first_2v2:
                month_videos['2v2'] = first_2v2
            
            if month_videos:  # Only add months that have videos
                monthly_videos[month_dir.name] = month_videos
    
    return monthly_videos

def extract_consecutive_frames(video_path, start_time=30, frame_interval=0.5, num_frames=10):
    """Extract consecutive frames starting at start_time with given interval."""
    print(f"Processing: {video_path}")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"ERROR: Cannot open {video_path}")
        return None
    
    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps
    
    print(f"Video: {width}x{height}, {fps}fps, {duration:.1f}s duration")
    
    # Check if video is long enough
    if duration < start_time + (num_frames * frame_interval):
        print(f"WARNING: Video too short ({duration:.1f}s). Adjusting extraction...")
        start_time = max(10, duration - (num_frames * frame_interval) - 5)
    
    frames = []
    frame_times = []
    
    for i in range(num_frames):
        # Calculate frame time and number
        current_time = start_time + (i * frame_interval)
        frame_number = int(current_time * fps)
        
        # Skip if beyond video length
        if frame_number >= total_frames:
            print(f"Frame {i+1} beyond video length, stopping at {len(frames)} frames")
            break
        
        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            frames.append(frame)
            frame_times.append(current_time)
            print(f"  Extracted frame {i+1}/{num_frames} at {current_time:.1f}s")
        else:
            print(f"  Failed to read frame {i+1} at {current_time:.1f}s")
    
    cap.release()
    
    if not frames:
        print("ERROR: No frames extracted")
        return None
    
    return frames, frame_times

def save_frames_for_annotation(frames, frame_times, output_dir, video_type, video_path):
    """Save frames with annotation-friendly naming."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract video basename for naming
    video_name = Path(video_path).stem
    
    saved_files = []
    
    for i, (frame, frame_time) in enumerate(zip(frames, frame_times)):
        # Create descriptive filename
        filename = f"{video_type}_{i+1:02d}_{frame_time:.1f}s_{video_name}.jpg"
        output_path = os.path.join(output_dir, filename)
        
        # Save with high quality for annotation
        cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        saved_files.append(filename)
        
        print(f"    Saved: {filename}")
    
    # Clean up frames from memory
    for frame in frames:
        del frame
    del frames
    gc.collect()
    
    return saved_files

def create_annotation_readme(output_dir, month, videos_processed):
    """Create README file with annotation instructions."""
    readme_path = os.path.join(output_dir, "README_ANNOTATION.txt")
    
    with open(readme_path, 'w') as f:
        f.write(f"ANNOTATION FRAMES - {month.upper()}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("FRAMES EXTRACTED:\n")
        for video_type, info in videos_processed.items():
            f.write(f"  {video_type.upper()}: {info['count']} frames from {info['video_name']}\n")
        f.write(f"  TOTAL: {sum(info['count'] for info in videos_processed.values())} frames\n\n")
        
        f.write("EXTRACTION DETAILS:\n")
        f.write("  - Start time: 30.0 seconds into video\n")
        f.write("  - Frame interval: 0.5 seconds apart\n")
        f.write("  - Frame sequence: 30.0s, 30.5s, 31.0s, 31.5s, 32.0s, 32.5s, 33.0s, 33.5s, 34.0s, 34.5s\n\n")
        
        f.write("ANNOTATION TARGETS:\n")
        f.write("  - Player health/mana bars and exact positions\n")
        f.write("  - Party member 1 & 2 health/resource bars\n")
        f.write("  - Target health/mana bars\n")
        f.write("  - Arena enemy 1, 2, 3 health bars\n")
        f.write("  - Cast bar location and spell text region\n")
        f.write("  - Combat log panel boundaries\n")
        f.write("  - Minimap position\n\n")
        
        f.write("NAMING CONVENTION:\n")
        f.write("  Format: {bracket}_{frame_num}_{time}_{video_name}.jpg\n")
        f.write("  Example: 3v3_01_30.0s_2023-05-10_17-37-00_-_3v3_Tiger's_Peak_(Win).jpg\n\n")
        
        f.write("ANNOTATION INSTRUCTIONS:\n")
        f.write("  1. Manually identify and mark exact pixel coordinates for each UI element\n")
        f.write("  2. Create coordinate mappings for consistent detection across all months\n")
        f.write("  3. Note any UI changes or variations between frames\n")
        f.write("  4. Focus on 1-2 representative frames per bracket type for detailed annotation\n")

def main():
    """Main execution with memory management."""
    print("Extracting frames for manual annotation...")
    print("Target: First 3v3 and 2v2 from each month (2023-2025), 10 frames each at 0.5s intervals")
    print("="*70)
    
    monthly_videos = get_monthly_videos()
    print(f"\nFound videos from {len(monthly_videos)} months")
    
    # Create base annotation directory
    base_annotation_dir = "annotation_frames"
    os.makedirs(base_annotation_dir, exist_ok=True)
    
    # Check which months are already processed
    existing_months = set()
    if os.path.exists(base_annotation_dir):
        existing_months = {d for d in os.listdir(base_annotation_dir) 
                          if os.path.isdir(os.path.join(base_annotation_dir, d)) and d.startswith(('2023-', '2024-', '2025-'))}
    
    print(f"Already processed months: {sorted(existing_months)}")
    
    total_frames_extracted = 0
    
    for month, videos in sorted(monthly_videos.items()):
        # Skip already processed months
        if month in existing_months:
            print(f"\nSKIPPING {month} (already processed)")
            continue
            
        print(f"\n{'='*50}")
        print(f"MONTH: {month}")
        print(f"{'='*50}")
        
        # Create month subdirectory
        month_dir = os.path.join(base_annotation_dir, month)
        os.makedirs(month_dir, exist_ok=True)
        
        videos_processed = {}
        
        for video_type, video_path in videos.items():
            print(f"\nProcessing {video_type.upper()} video:")
            
            # Extract frames
            result = extract_consecutive_frames(video_path, start_time=30, frame_interval=0.5, num_frames=10)
            
            if result is None:
                print(f"Failed to extract frames from {video_path}")
                continue
            
            frames, frame_times = result
            
            # Save frames for annotation
            saved_files = save_frames_for_annotation(frames, frame_times, month_dir, video_type, video_path)
            
            videos_processed[video_type] = {
                'count': len(saved_files),
                'video_name': video_path.name,
                'files': saved_files
            }
            
            total_frames_extracted += len(saved_files)
            
            print(f"  {video_type.upper()}: {len(saved_files)} frames extracted")
        
        # Create annotation README for this month
        if videos_processed:
            create_annotation_readme(month_dir, month, videos_processed)
            print(f"\nMonth {month}: {sum(info['count'] for info in videos_processed.values())} total frames")
        
        # Force cleanup between months
        gc.collect()
    
    print(f"\n{'='*70}")
    print("EXTRACTION COMPLETE!")
    print(f"{'='*70}")
    print(f"Total frames extracted: {total_frames_extracted}")
    print(f"Months processed: {len(monthly_videos)}")
    print(f"Output directory: {base_annotation_dir}/")
    print("\nEach month subdirectory contains:")
    print("  - Up to 20 frames (10 from 3v3, 10 from 2v2)")
    print("  - README_ANNOTATION.txt with details")
    print("  - High-quality JPEGs ready for manual annotation")
    print(f"\nFrames are extracted at 30s + (0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5) seconds")

if __name__ == "__main__":
    main()