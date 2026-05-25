import argparse
import os
import re
import glob
import subprocess
import shutil

def has_audio(file_path):
    cmd = f"ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 {file_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return len(result.stdout.strip()) > 0

def scene_sort_key(file_path):
    basename = os.path.basename(file_path)
    match = re.search(r"scene(\d+)", basename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 999

def main():
    parser = argparse.ArgumentParser(description="Assemble multiple scene clips into a single unified storybook.")
    parser.add_argument("--project_dir", type=str, required=True, help="Directory containing the story scenes (e.g. /mixed/)")
    parser.add_argument("--output_name", type=str, default="final_story.mp4", help="Name of the final compiled video")
    
    args = parser.parse_args()
    project_dir = args.project_dir
    mixed_dir = f"{project_dir}/mixed"
    
    if not os.path.exists(mixed_dir):
        print(f"Error: Mixed directory {mixed_dir} does not exist.")
        return

    # Find and numerically sort all mixed final videos
    pattern = os.path.join(mixed_dir, "scene*_final.mp4")
    mixed_videos = glob.glob(pattern)
    if not mixed_videos:
        print(f"No mixed videos found matching pattern: {pattern}")
        # Fallback to check raw video segments if no mixed clips exist
        videos_dir = f"{project_dir}/videos"
        if os.path.exists(videos_dir):
            pattern = os.path.join(videos_dir, "*.mp4")
            mixed_videos = glob.glob(pattern)
            print(f"Fallback check: found {len(mixed_videos)} raw video files in /videos/.")
    
    mixed_videos.sort(key=scene_sort_key)
    if not mixed_videos:
        print("Error: No video clips found to assemble.")
        return

    print(f"Found {len(mixed_videos)} scene video(s) for assembly in order:")
    for v in mixed_videos:
        print(f" - {os.path.basename(v)}")

    # Create temporary normalization directory
    norm_dir = os.path.join(project_dir, "temp_normalization")
    os.makedirs(norm_dir, exist_ok=True)

    normalized_files = []
    
    try:
        # Pre-flight Normalization Pass
        for i, video_path in enumerate(mixed_videos):
            base_name = os.path.basename(video_path)
            norm_path = os.path.join(norm_dir, f"norm_{i}_{base_name}")
            print(f"\nNormalizing Clip {i+1}/{len(mixed_videos)}: {base_name}...")
            
            has_track = has_audio(video_path)
            print(f" - Native audio track exists: {has_track}")

            if has_track:
                # Re-encode to standard format (H.264, AAC audio, 44100Hz)
                cmd = (
                    f'ffmpeg -y -i "{video_path}" '
                    f'-c:v libx264 -preset fast -pix_fmt yuv420p '
                    f'-c:a aac -ar 44100 '
                    f'"{norm_path}"'
                )
            else:
                # Force-inject silent mono audio track and re-encode to identical format
                print(" - Action: Injecting silent mono audio track for seamless concatenation.")
                cmd = (
                    f'ffmpeg -y -i "{video_path}" -f lavfi -i "anullsrc=cl=mono:r=44100" '
                    f'-map 0:v -map 1:a -c:v libx264 -preset fast -pix_fmt yuv420p '
                    f'-c:a aac -shortest '
                    f'"{norm_path}"'
                )
            
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            normalized_files.append(norm_path)
            print(f" - Standardized copy saved to: {os.path.basename(norm_path)}")

        # Create concat text file
        list_file_path = os.path.join(norm_dir, "concat_list.txt")
        with open(list_file_path, "w") as f:
            for n_file in normalized_files:
                # FFmpeg's concat demuxer needs single quotes escaped if present, 
                # but standard project paths won't have them. Use absolute paths.
                abs_path = os.path.abspath(n_file)
                f.write(f"file '{abs_path}'\n")
        
        # Assemble using concat demuxer (lossless and rapid because streams are identical)
        output_path = os.path.join(project_dir, args.output_name)
        print(f"\nStitching all standardized clips together...")
        concat_cmd = (
            f'ffmpeg -y -f concat -safe 0 -i "{list_file_path}" '
            f'-c copy "{output_path}"'
        )
        
        subprocess.run(concat_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"\nSUCCESS! Unified storybook compiled successfully: {output_path}")
        print(f"Final assembled file size: {os.path.getsize(output_path)} bytes")

    except Exception as e:
        print("\nAssembly compilation failed with error:", e)
    finally:
        # Cleanup temporary normalization assets
        print("\nCleaning up temporary normalization assets...")
        shutil.rmtree(norm_dir, ignore_errors=True)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
