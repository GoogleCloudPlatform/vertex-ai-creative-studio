import argparse
import json
import subprocess
import os
import re
import glob

def run_mcp(command, tool_name, arguments):
    env = os.environ.copy()
    env["GOOGLE_CLOUD_PROJECT"] = "genai-blackbelt-fishfooding"
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    out, err = p.communicate(json.dumps(req) + "\n")
    return out, err

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return float(result.stdout.strip())

def main():
    parser = argparse.ArgumentParser(description="Generate a single media scene.")
    parser.add_argument("--scene_id", type=int, required=True)
    parser.add_argument("--narrator", type=str, required=True)
    parser.add_argument("--voice", type=str, default="Callirrhoe")
    parser.add_argument("--voice_prompt", type=str, default="soothing female voice")
    parser.add_argument("--music", type=str, required=True)
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--out_dir", type=str, required=True)
    
    args = parser.parse_args()
    
    out_dir = args.out_dir
    bucket = "genai-blackbelt-fishfooding-assets"
    
    os.makedirs(f"{out_dir}/audio", exist_ok=True)
    os.makedirs(f"{out_dir}/images", exist_ok=True)
    os.makedirs(f"{out_dir}/videos", exist_ok=True)
    os.makedirs(f"{out_dir}/mixed", exist_ok=True)
    
    s_id = args.scene_id
    print(f"=== Processing Scene {s_id} ===")
    
    # 1. TTS
    print(f"Generating TTS for scene {s_id}...")
    out, err = run_mcp(["mcp-gemini-go", "-t", "stdio"], "gemini_audio_tts", {
        "text": args.narrator,
        "voice_name": args.voice,
        "prompt": args.voice_prompt,
        "output_directory": f"{out_dir}/audio",
        "output_filename_prefix": f"scene{s_id}_voice"
    })
    
    try:
        res = json.loads(out)
        text = res['result']['content'][0]['text']
        match = re.search(r"Audio saved to: (.*\.wav)", text)
        voice_file = match.group(1)
        print("Voice file:", voice_file)
    except Exception as e:
        print("Error parsing TTS:", e, out)
        return

    # 2. Music
    print(f"Generating Music for scene {s_id}...")
    music_file = f"{out_dir}/audio/scene{s_id}_music.wav"
    out, err = run_mcp(["mcp-lyria-go", "-t", "stdio"], "lyria_generate_music", {
        "prompt": args.music,
        "output_gcs_bucket": bucket,
        "local_path": f"{out_dir}/audio",
        "file_name": f"scene{s_id}_music.wav"
    })
    print("Music generation complete.")

    # 3. Image locally then upload (Nano Banana direct to GCS is sometimes flaky)
    print(f"Generating Image locally for scene {s_id}...")
    out, err = run_mcp(["mcp-nanobanana-go", "-t", "stdio"], "nanobanana_image_generation", {
        "prompt": args.image,
        "output_directory": f"{out_dir}/images",
        "aspect_ratio": "16:9"
    })
    try:
        res = json.loads(out)
        text = res['result']['content'][0]['text']
        match = re.search(r"Generated and saved 1 image\(s\): (.*\.png)", text)
        image_file = match.group(1)
        print("Image file:", image_file)
    except Exception as e:
        print("Error parsing image:", e, out, err)
        return

    # Upload to GCS
    print("Uploading image to GCS...")
    gcs_uri = f"gs://{bucket}/story_generator/scene{s_id}_image_{os.path.basename(image_file)}"
    subprocess.run(f"gcloud storage cp {image_file} {gcs_uri}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 4. Video (i2v)
    print(f"Generating Video for scene {s_id}...")
    out, err = run_mcp(["mcp-veo-go", "-t", "stdio"], "veo_i2v", {
        "image_uri": gcs_uri,
        "prompt": args.video,
        "model": "veo-3.1-lite-generate-001",
        "bucket": bucket,
        "output_directory": f"{out_dir}/videos",
        "duration": 6,
        "aspect_ratio": "16:9",
        "generate_audio": False
    })
    try:
        res = json.loads(out)
        text = res['result']['content'][0]['text']
        match = re.search(r"Successfully downloaded locally to '.*': (.*\.mp4)", text)
        video_file = match.group(1)
        print("Video file:", video_file)
    except Exception as e:
        print("Error parsing Video:", e, out, err)
        return

    # 5. Mix
    print(f"Mixing Scene {s_id}...")
    try:
        voice_duration = get_duration(voice_file)
        mix_duration = voice_duration + 1.0
        out_mix = f"{out_dir}/mixed/scene{s_id}_final.mp4"
        cmd = (
            f'ffmpeg -y -stream_loop -1 -i "{video_file}" -i "{voice_file}" -i "{music_file}" '
            f'-filter_complex "[2:a]volume=0.15[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]" '
            f'-map 0:v -map "[aout]" -t {mix_duration} -c:v libx264 -c:a aac -pix_fmt yuv420p "{out_mix}"'
        )
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Scene {s_id} complete! Mixed file: {out_mix}")
    except Exception as e:
        print("Error mixing:", e)

if __name__ == "__main__":
    main()
