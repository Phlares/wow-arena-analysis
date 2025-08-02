"""
Memory-efficient monthly frame sampling for WoW UI evolution analysis.
Samples 1-2 frames per month to avoid memory issues (22GB limit).
"""

import cv2
import os
import numpy as np
from pathlib import Path
import gc

def get_monthly_videos():
    """Get one representative video from each available month."""
    monthly_videos = {}
    
    # Scan directories for videos by month
    base_dir = Path('.')
    for month_dir in base_dir.glob('2023-*'):
        if month_dir.is_dir():
            videos = list(month_dir.glob('*.mp4'))
            if videos:
                # Pick first video from each month
                monthly_videos[month_dir.name] = videos[0]
    
    return monthly_videos

def extract_single_frame(video_path, frame_time=30):
    """Extract single frame at specified time (seconds) with memory cleanup."""
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
    
    print(f"Video: {width}x{height}, {fps}fps, {total_frames} frames")
    
    # Jump to specific time
    target_frame = min(int(frame_time * fps), total_frames - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    
    ret, frame = cap.read()
    cap.release()  # Immediate cleanup
    
    if not ret:
        print(f"ERROR: Could not read frame at {frame_time}s")
        return None
    
    return frame, width, height

def analyze_ui_regions(frame, month, width, height):
    """Analyze key UI regions without storing large arrays."""
    print(f"\nAnalyzing UI regions for {month}:")
    
    # Define UI regions as percentages (resolution independent)
    ui_regions = {
        "player_frame": (int(width*0.02), int(height*0.05), int(width*0.25), int(height*0.25)),
        "target_frame": (int(width*0.75), int(height*0.05), int(width*0.98), int(height*0.25)),
        "party1_frame": (int(width*0.02), int(height*0.25), int(width*0.20), int(height*0.35)),
        "party2_frame": (int(width*0.02), int(height*0.35), int(width*0.20), int(height*0.45)),
        "arena123_frames": (int(width*0.75), int(height*0.25), int(width*0.98), int(height*0.55)),
        "cast_bar": (int(width*0.3), int(height*0.8), int(width*0.7), int(height*0.9)),
        "minimap": (int(width*0.85), int(height*0.05), int(width*0.98), int(height*0.18))
    }
    
    results = {}
    
    for region_name, (x1, y1, x2, y2) in ui_regions.items():
        # Extract small region
        region = frame[y1:y2, x1:x2]
        
        if region.size == 0:
            continue
            
        # Quick color analysis
        mean_color = np.mean(region, axis=(0,1))
        
        # Check for common UI colors
        green_pixels = np.sum((region[:,:,1] > 100) & (region[:,:,0] < 80) & (region[:,:,2] < 80))
        blue_pixels = np.sum((region[:,:,0] > 100) & (region[:,:,1] < 80) & (region[:,:,2] < 80))
        red_pixels = np.sum((region[:,:,2] > 100) & (region[:,:,0] < 80) & (region[:,:,1] < 80))
        
        total_pixels = region.shape[0] * region.shape[1]
        
        results[region_name] = {
            'mean_bgr': mean_color.tolist(),
            'green_pct': (green_pixels / total_pixels) * 100,
            'blue_pct': (blue_pixels / total_pixels) * 100,
            'red_pct': (red_pixels / total_pixels) * 100,
            'size': f"{x2-x1}x{y2-y1}"
        }
        
        print(f"  {region_name}: {results[region_name]['size']}, "
              f"G:{results[region_name]['green_pct']:.1f}% "
              f"B:{results[region_name]['blue_pct']:.1f}% "
              f"R:{results[region_name]['red_pct']:.1f}%")
    
    # Force garbage collection
    del region
    gc.collect()
    
    return results

def save_sample_frame(frame, month, output_dir="ui_samples"):
    """Save a small sample frame for reference."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Resize to save space (keep aspect ratio)
    height, width = frame.shape[:2]
    scale = min(800/width, 600/height)  # Max 800x600
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    resized = cv2.resize(frame, (new_width, new_height))
    
    output_path = f"{output_dir}/{month}_sample.jpg"
    cv2.imwrite(output_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"Saved sample: {output_path}")
    
    del resized
    gc.collect()

def main():
    """Main execution with memory management."""
    print("Memory-efficient monthly UI sampling starting...")
    print("Maximum 1-2 frames per month to stay under 22GB limit")
    
    monthly_videos = get_monthly_videos()
    print(f"\nFound videos from {len(monthly_videos)} months")
    
    all_results = {}
    
    for month, video_path in sorted(monthly_videos.items()):
        print(f"\n{'='*50}")
        print(f"MONTH: {month}")
        print(f"{'='*50}")
        
        # Extract single frame
        result = extract_single_frame(video_path, frame_time=30)
        if result is None:
            continue
            
        frame, width, height = result
        
        # Analyze UI regions
        ui_analysis = analyze_ui_regions(frame, month, width, height)
        all_results[month] = ui_analysis
        
        # Save small sample
        save_sample_frame(frame, month)
        
        # Force cleanup
        del frame
        gc.collect()
        
        print(f"Month {month} complete. Memory cleaned.")
    
    print(f"\n{'='*50}")
    print("SUMMARY: UI Evolution Analysis")
    print(f"{'='*50}")
    
    # Print summary of changes across months
    if len(all_results) > 1:
        first_month = list(all_results.keys())[0]
        print(f"Baseline: {first_month}")
        
        for month in sorted(all_results.keys())[1:]:
            print(f"\n{month} vs {first_month}:")
            for region in all_results[month]:
                if region in all_results[first_month]:
                    old_green = all_results[first_month][region]['green_pct']
                    new_green = all_results[month][region]['green_pct']
                    if abs(new_green - old_green) > 2.0:  # Significant change
                        print(f"  {region}: Health bars {old_green:.1f}% -> {new_green:.1f}%")
    
    print(f"\nAnalysis complete. Check /ui_samples/ for reference frames.")

if __name__ == "__main__":
    main()