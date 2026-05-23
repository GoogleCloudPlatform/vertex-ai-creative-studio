import argparse
import os
import shutil
import subprocess
import glob

def main():
    parser = argparse.ArgumentParser(description="Package the HTML report and assets into a standalone zip file.")
    parser.add_argument("--project_dir", type=str, required=True, help="Path to the project directory")
    parser.add_argument("--zip_name", type=str, default="story_report.zip", help="Name of the output zip file")
    args = parser.parse_args()

    src_dir = args.project_dir
    stage_dir = f"{src_dir}/report_standalone"
    zip_file = f"{src_dir}/{args.zip_name}"

    print("Creating staging directory...")
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(stage_dir, exist_ok=True)

    print("Copying report files...")
    html_src = f"{src_dir}/report/index.html"
    if not os.path.exists(html_src):
        print(f"Error: Report directory or index.html not found at: {html_src}")
        return

    shutil.copy(html_src, f"{stage_dir}/index.html")
    if os.path.exists(f"{src_dir}/report/index.css"):
        shutil.copy(f"{src_dir}/report/index.css", f"{stage_dir}/index.css")
    if os.path.exists(f"{src_dir}/report/fonts"):
        shutil.copytree(f"{src_dir}/report/fonts", f"{stage_dir}/fonts", dirs_exist_ok=True)
    if os.path.exists(f"{src_dir}/walkthrough.md"):
        shutil.copy(f"{src_dir}/walkthrough.md", f"{stage_dir}/walkthrough.md")
    if os.path.exists(f"{src_dir}/storyline.md"):
        shutil.copy(f"{src_dir}/storyline.md", f"{stage_dir}/storyline.md")
    if os.path.exists(f"{src_dir}/scenes.json"):
        shutil.copy(f"{src_dir}/scenes.json", f"{stage_dir}/scenes.json")

    print("Copying media assets...")
    # 1. Handle classic structure (images/ and mixed/ folders)
    has_classic_images = os.path.exists(f"{src_dir}/images")
    has_classic_mixed = os.path.exists(f"{src_dir}/mixed")
    
    if has_classic_images:
        print("  Detected classic 'images' directory structure...")
        shutil.copytree(f"{src_dir}/images", f"{stage_dir}/images", dirs_exist_ok=True)
        
    if has_classic_mixed:
        print("  Detected classic 'mixed' video directory structure...")
        shutil.copytree(f"{src_dir}/mixed", f"{stage_dir}/mixed", dirs_exist_ok=True)

    # 2. Handle modern parallel direct MCP test structure (scene_{id}/ folders and scene_{id}_mixed.mp4)
    has_modern_scenes = any(os.path.exists(f"{src_dir}/scene_{i}") for i in range(1, 10))
    if has_modern_scenes:
        print("  Detected parallel direct scene structure. Copying scene directories and mixed files...")
        for i in range(1, 10):
            scene_dir_src = f"{src_dir}/scene_{i}"
            if os.path.exists(scene_dir_src):
                scene_dir_dest = f"{stage_dir}/scene_{i}"
                os.makedirs(scene_dir_dest, exist_ok=True)
                # Copy images under scene_i
                png_files = glob.glob(f"{scene_dir_src}/*.png")
                for png in png_files:
                    shutil.copy(png, f"{scene_dir_dest}/{os.path.basename(png)}")
            
            # Copy individual mixed scene videos from root
            mixed_scene_src = f"{src_dir}/scene_{i}_mixed.mp4"
            if os.path.exists(mixed_scene_src):
                shutil.copy(mixed_scene_src, f"{stage_dir}/scene_{i}_mixed.mp4")

    # 3. Find the final concatenated video
    final_video = None
    for file in os.listdir(src_dir):
        if file.endswith("final.mp4") or file == "final_story.mp4":
            final_video = file
            break
            
    if final_video:
        print(f"  Copying final stitched video: {final_video}")
        shutil.copy(f"{src_dir}/{final_video}", f"{stage_dir}/{final_video}")

    print("Updating path references in HTML for standalone viewing...")
    with open(f"{stage_dir}/index.html", 'r') as f:
        html = f.read()

    # Normalize relative links: replace "../" with relative to standalone root
    html = html.replace('../', '')

    with open(f"{stage_dir}/index.html", 'w') as f:
        f.write(html)

    print("Creating zip archive...")
    if os.path.exists(zip_file):
        os.remove(zip_file)
    subprocess.run(["zip", "-r", zip_file, "."], cwd=stage_dir, check=True)

    print("Cleaning up staging directory...")
    shutil.rmtree(stage_dir)

    print(f"Zip created successfully at: {zip_file}")

if __name__ == "__main__":
    main()
