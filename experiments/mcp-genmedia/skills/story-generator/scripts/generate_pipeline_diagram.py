import subprocess
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate Graphviz flowcharts for the double-engine pipeline.")
    parser.add_argument("--project_dir", type=str, default="/Users/ghchinoy/genmedia/bunny_science_story/story-generator", help="Path to project directory")
    args = parser.parse_args()
    
    report_dir = os.path.join(args.project_dir, "report")
    os.makedirs(report_dir, exist_ok=True)
    
    dot_path = os.path.join(report_dir, "pipeline_diagram.dot")
    webp_path = os.path.join(report_dir, "pipeline_diagram.webp")
    
    print(f"Creating Graphviz DOT file: {dot_path}...")
    
    dot_content = """digraph G {
    fontname="Inter,Helvetica,Arial,sans-serif";
    bgcolor="#121212";
    rankdir=LR;
    nodesep=0.5;
    ranksep=0.7;
    pad=0.4;
    
    // Node styles
    node [
        fontname="Inter,Helvetica,Arial,sans-serif",
        fontsize=11,
        color="#707070",
        fontcolor="#e0e0e0",
        style="filled,rounded",
        fillcolor="#1e1e1e",
        shape=box,
        height=0.35
    ];
    
    // Edge styles
    edge [
        fontname="Inter,Helvetica,Arial,sans-serif",
        fontsize=9,
        color="#00ff88",
        fontcolor="#bbbbbb",
        arrowsize=0.7
    ];

    // Clusters
    subgraph cluster_co_creation {
        label="STAGE 1: CO-CREATION";
        fontcolor="#00ff88";
        color="#00ff88";
        style="dashed,rounded";
        
        User [label="User Co-Director", fillcolor="#311b92", color="#8e24aa", fontcolor="#ffffff"];
        Showrunner [label="Showrunner Persona", fillcolor="#1a237e", color="#039be5", fontcolor="#ffffff"];
        Bible [label="Story Bible (scenes.json)", fillcolor="#004d40", color="#00b0ff", fontcolor="#ffffff"];
        
        User -> Showrunner [label="Topic & Tone"];
        Showrunner -> User [label="Creative Suggestions"];
        User -> Bible [label="Approved Script"];
    }

    subgraph cluster_generation {
        label="STAGE 2: SCENE COMPOSITING";
        fontcolor="#ffab40";
        color="#ffab40";
        style="dashed,rounded";
        
        GenScene [label="generate_scene.py", fillcolor="#212121", color="#ff9100", fontcolor="#ffffff"];
        AudioCheck [label="ffprobe Duration Check", fillcolor="#263238"];
        SpeedFit [label="atempo Speed-Fitting Filter", fillcolor="#3e2723", color="#ff5722"];
        MuxCheck [label="ffprobe Ambient Audio Check", fillcolor="#263238"];
        Mixer [label="amix Multi-Track Volume Ducking", fillcolor="#006064", color="#00e5ff"];
        MixedClip [label="mixed/scene_x_final.mp4", fillcolor="#0d533a", color="#00ff88"];
        
        Bible -> GenScene [label="Scenes Metadata"];
        GenScene -> AudioCheck [label="Parse Runtimes"];
        AudioCheck -> SpeedFit [label="If Voice > Video (1.0x - 2.0x)"];
        SpeedFit -> MuxCheck;
        GenScene -> MuxCheck [label="Find Ambient Track"];
        MuxCheck -> Mixer [label="Mix & Duck 3 Tracks"];
        Mixer -> MixedClip [label="Copy-Mux Video"];
    }

    subgraph cluster_assembly {
        label="STAGE 3: STANDARD MERGING";
        fontcolor="#00b0ff";
        color="#00b0ff";
        style="dashed,rounded";
        
        AssembleScript [label="assemble_story.py", fillcolor="#212121", color="#0091ea", fontcolor="#ffffff"];
        NormProbe [label="ffprobe Audio Check", fillcolor="#263238"];
        SilentInject [label="anullsrc Silent Mono Injection", fillcolor="#3e2723", color="#ff5722"];
        StdReencode [label="Standardize Video (libx264/aac/44.100Hz)", fillcolor="#0d533a"];
        ConcatList [label="concat_list.txt", fillcolor="#37474f"];
        ConcatDemux [label="ffmpeg concat (copy)", fillcolor="#006064", color="#00ff88"];
        FinalStory [label="final_story.mp4", fillcolor="#1b5e20", color="#00e676", fontcolor="#ffffff"];
        
        MixedClip -> AssembleScript;
        AssembleScript -> NormProbe [label="Scan Scenes"];
        NormProbe -> SilentInject [label="If Silent Clip"];
        NormProbe -> StdReencode [label="If Mixed Clip"];
        SilentInject -> StdReencode [label="Mux Mono"];
        StdReencode -> ConcatList [label="Write Abs Paths"];
        ConcatList -> ConcatDemux [label="Instantly Stitch"];
        ConcatDemux -> FinalStory [label="Perfect A/V Sync"];
    }

    subgraph cluster_quality {
        label="STAGE 4: EDITOR'S QUALITY QC ROOM";
        fontcolor="#ea00ff";
        color="#ea00ff";
        style="dashed,rounded";
        
        QC_Room [label="editors_quality_room.py", fillcolor="#212121", color="#d500f9", fontcolor="#ffffff"];
        ParamAudit [label="Codec, Rate & Res Audit", fillcolor="#263238"];
        WordWarning [label="Narrator Speech Tempo Check", fillcolor="#3e2723", color="#ff1744"];
        ReportFiles [label="quality_report.json / .md", fillcolor="#4a148c", color="#e040fb"];
        
        FinalStory -> QC_Room [label="Audit Master"];
        MixedClip -> QC_Room [label="Audit Scenes"];
        QC_Room -> ParamAudit;
        ParamAudit -> WordWarning [label="If Tempo > 1.5x"];
        WordWarning -> ReportFiles [label="Actionable Editorial Notes"];
    }
}"""
    
    with open(dot_path, "w") as f:
        f.write(dot_content)
        
    print(f"DOT file successfully written to: {dot_path}")
    
    # Try to compile with Graphviz dot
    print("Attempting to compile DOT to WEBP...")
    try:
        cmd = f'dot -Twebp "{dot_path}" -o "{webp_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"SUCCESS! Rendered Graphviz pipeline diagram to WEBP: {webp_path}")
            print(f"File size: {os.path.getsize(webp_path)} bytes")
        else:
            print("Graphviz compilation failed. Error output:", result.stderr)
            print("Fallback: Please verify if Graphviz is installed on this system.")
    except Exception as e:
        print("Could not invoke 'dot' compiler. Error:", e)
        print("Fallback: Graphviz binary might be missing from path. The .dot file was saved for offline rendering.")

if __name__ == "__main__":
    main()
