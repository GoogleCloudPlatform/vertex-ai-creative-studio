import os
import subprocess
import tempfile
import numpy as np
import shutil
from pathlib import Path
import pyiqa
import torch

# Initialize PyTorch device and models globally to prevent OOM errors
# and avoid reloading heavy weights on every concurrent API request.
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_niqe_metric = pyiqa.create_metric("niqe", device=_device)

def extract_frames(video_path, output_dir, num_frames=5):
    """Extracts a fixed number of frames from a video using ffmpeg."""
    # Copy video to the local temporary directory to avoid FUSE random-access bottlenecks
    local_video_path = Path(output_dir) / "temp_video.mp4"
    try:
        shutil.copy2(video_path, local_video_path)
    except Exception as e:
        print(f"Failed to copy video to local tmpfs: {e}")
        return []

    # Get total duration
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(local_video_path)]
    try:
        duration = float(subprocess.check_output(cmd).decode().strip())
    except subprocess.CalledProcessError as e:
        print(f"ffprobe failed: {e}")
        return []
    except ValueError:
        print("ffprobe returned invalid duration")
        return []
    
    # Extract frames at regular intervals
    intervals = np.linspace(0, duration, num_frames + 2)[1:-1]
    
    for i, timestamp in enumerate(intervals):
        frame_path = Path(output_dir) / f"frame_{i:03d}.png"
        cmd = [
            "ffmpeg", "-ss", str(timestamp), "-i", str(local_video_path),
            "-frames:v", "1", "-q:v", "2", str(frame_path), "-y"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ffmpeg frame extraction failed for timestamp {timestamp}: {result.stderr}")
    
    # Return all PNGs extracted, but exclude the temporary video file we copied
    return list(Path(output_dir).glob("frame_*.png"))

def evaluate_technical_quality(video_path, metric_name="niqe"):
    """Calculates no-reference quality metrics using pyiqa."""
    
    # Use the globally initialized metric
    if metric_name != "niqe":
        # Fallback for dynamic metrics, though currently unused
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        iqa_metric = pyiqa.create_metric(metric_name, device=device)
    else:
        iqa_metric = _niqe_metric
    
    with tempfile.TemporaryDirectory() as tmpdir:
        frames = extract_frames(video_path, tmpdir)
        scores = []
        for frame in frames:
            score = iqa_metric(str(frame)).item()
            scores.append(score)
            
    if not scores:
        print(f"Warning: No frames extracted for {video_path}. Returning default 0.0 scores.")
        return {
            "metric": metric_name,
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "frame_scores": []
        }
            
    return {
        "metric": metric_name,
        "avg_score": float(np.mean(scores)),
        "min_score": float(np.min(scores)),
        "max_score": float(np.max(scores)),
        "frame_scores": [float(s) for s in scores]
    }