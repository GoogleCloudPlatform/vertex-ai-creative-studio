# AVTool Enhancement Plan

## Overview

This document outlines a phased plan to enhance the `mcp-avtool-go` server by incorporating new, advanced `ffmpeg` capabilities. The new tools are based on the command "incantations" provided in the `incantations` directory, focusing on advanced audio manipulation and image processing.

Each phase represents a logical grouping of new tools and includes specific implementation tasks and validation steps.

---

## Phase 1: Advanced Audio Manipulation Tools

This phase focuses on adding tools critical for a professional audio production workflow, such as podcast creation.

### Task 1.1: New Tool `ffmpeg_get_volume_stats`

*   **Goal:** Create a tool that analyzes an audio file and returns its volume statistics, which is crucial for normalization.
*   **FFmpeg Command:** `ffmpeg -i <input> -af volumedetect -f null -`
*   **Implementation:**
    1.  Create a new `ffmpeg_get_volume_stats` handler in `mcp_handlers.go`.
    2.  The handler will call a new `executeGetVolumeStats` function in `ffmpeg_commands.go`.
    3.  This function will execute the `volumedetect` command and capture the `stderr` output.
    4.  The handler must parse the text output from `ffmpeg` to extract the `mean_volume`, `max_volume`, and other relevant statistics.
    5.  The parsed statistics should be returned as a structured JSON object in the tool's result.
*   **Validation:**
    *   Call the new tool with a sample `.wav` file.
    *   Verify that the output is a JSON object containing the expected keys (e.g., `mean_volume`) and numeric values.

### Task 1.2: New Tool `ffmpeg_apply_audio_fade`

*   **Goal:** Create a flexible tool to apply fade-in or fade-out effects to audio clips.
*   **FFmpeg Command:** `ffmpeg -i <input> -af "afade=t=<type>:st=<start>:d=<duration>" <output>`
*   **Implementation:**
    1.  Create a new `ffmpeg_apply_audio_fade` tool and handler.
    2.  Define parameters for `input_uri`, `output_uri`, `fade_type` (enum: "in", "out"), `start_time` (in seconds), and `fade_duration` (in seconds).
    3.  The corresponding function in `ffmpeg_commands.go` will dynamically construct the `-af "afade=..."` argument string based on the provided parameters.
*   **Validation:**
    *   Call the tool on a sample audio file with `fade_type: "out"`. Verify the audio fades out at the end.
    *   Call the tool with `fade_type: "in"`. Verify the audio fades in at the beginning.
    *   Use `ffmpeg_get_media_info` to confirm the output file duration is correct.

### Task 1.3: New Tool `ffmpeg_crossfade_audio`

*   **Goal:** Create a tool to blend two audio clips together smoothly.
*   **FFmpeg Command:** `ffmpeg -i in1.wav -i in2.wav -filter_complex "[0:a][1:a]acrossfade=d=2[out]" -map "[out]" out.wav`
*   **Implementation:**
    1.  Create a new `ffmpeg_crossfade_audio` tool and handler.
    2.  Define parameters for two input URIs, one output URI, and `crossfade_duration` in seconds.
    3.  The implementation will use the `-filter_complex` argument with the `acrossfade` filter.
*   **Validation:**
    *   Call the tool with two distinct audio files.
    *   Listen to the output file to confirm that the two clips are blended smoothly over the specified duration.

---

## Phase 2: Advanced Image Processing Tools

This phase introduces image manipulation capabilities, particularly for preparing images for video generation pipelines.

### Task 2.1: New Tool `ffmpeg_pad_image_to_ratio`

*   **Goal:** Create a tool to pad an image to a specific aspect ratio, like 16:9.
*   **FFmpeg Command:** `ffmpeg -i in.png -vf "pad=width=ceil(ih*16/9):height=ih:x=(ow-iw)/2:y=0:color=#f8f8f8" out.png`
*   **Implementation:**
    1.  Create a new `ffmpeg_pad_image_to_ratio` tool and handler.
    2.  Define parameters for `input_uri`, `output_uri`, `aspect_ratio` (string, e.g., "16:9"), and an optional `padding_color` (string, e.g., "black" or "#ffffff").
    3.  The implementation will parse the `aspect_ratio` string to dynamically construct the `pad` filter arguments.
*   **Validation:**
    *   Call the tool with a square image, an aspect ratio of "16:9", and a bright color like "red".
    *   Verify the output image has the correct dimensions and red padding bars on the sides.

### Task 2.2: New Tool `ffmpeg_get_image_corner_color`

*   **Goal:** Create a utility tool to detect the color of the top-left corner of an image.
*   **FFmpeg Command:** `ffmpeg -i in.png -vf "crop=10:10:0:0,scale=1:1" -f image2pipe -c:v ppm - | xxd -p | tail -c 7`
*   **Implementation:**
    1.  Create a new `ffmpeg_get_image_corner_color` tool and handler.
    2.  **Note:** This is significantly more complex than other tools. It requires executing a shell pipeline, not just a single `ffmpeg` command. The Go code will need to:
        a. Run the `ffmpeg` part of the command.
        b. Capture the binary `stdout` of the `ffmpeg` process.
        c. Process the binary PPM stream in Go to extract the color data, or pipe it to `xxd` and `tail` within a `bash -c "..."` sub-shell. The sub-shell approach is simpler to implement but creates a dependency on `xxd` and `tail`.
    3.  The handler should return the detected color as a hex string (e.g., `"#f8f8f8"`).
*   **Validation:**
    *   Create a test image with a solid, known color (e.g., blue, `#0000ff`).
    *   Call the tool on this image and verify that it returns the correct hex color code.

---

## Phase 3: Suggestions for Future Tools

After implementing the core "incantations," `mcp-avtool-go` could be further enhanced with these industry-standard media processing capabilities.

*   **Audio Normalization (`loudnorm`):**
    *   **Use Case:** Instead of simple volume adjustment, this provides standardized loudness normalization (EBU R128), which is essential for podcasts and broadcast media to ensure a consistent listening experience across platforms.
    *   **FFmpeg Command:** `ffmpeg -i input.wav -af loudnorm output.wav`

*   **Subtitle Burn-in (`subtitles`):**
    *   **Use Case:** Permanently render subtitles from a file (e.g., `.srt` or `.vtt`) onto a video stream. This is useful for creating accessible content or social media clips where audio may be off by default.
    *   **FFmpeg Command:** `ffmpeg -i input.mp4 -vf "subtitles=subs.srt" output.mp4`

*   **Video Scene Detection & Thumbnails (`thumbnail`, `select`):**
    *   **Use Case:** Automate the creation of video previews or chapter markers by detecting scene changes and extracting keyframes.
    *   **FFmpeg Command:** `ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)'" -vsync vfr thumbnails/thumb%03d.png`

*   **Audio Waveform Visualization (`showwavespic`):**
    *   **Use Case:** Generate a static image of an audio file's waveform. This is highly useful for social media posts, podcast episode art, or as a visual element in audiogram videos.
    *   **FFmpeg Command:** `ffmpeg -i input.mp3 -filter_complex "showwavespic=s=1280x240" -frames:v 1 waveform.png`

---

## Appendix: `ffmpeg-go` vs. Bespoke Wrapper Analysis

(This is a summary of the previous analysis provided).

### **Recommendation: Continue Expanding the Bespoke `mcp-avtool-go` Wrapper**

While `ffmpeg-go` is an excellent library for common use cases, it is recommended to **continue with the current bespoke wrapper.**

**Reasoning:**

1.  **Control is Paramount:** The planned "incantations" rely on complex, dynamic, and sometimes esoteric `ffmpeg` features (e.g., shell pipelines for color detection, dynamic `pad` expressions). A high-level fluent API is more likely to be a hindrance than a help in these scenarios. The current direct approach guarantees 100% control over the executed command.

2.  **Maintainability for Experts:** For a developer who understands `ffmpeg`, maintaining the argument slices in `mcp-avtool-go` is trivial and fast. The "source of truth" is the stable `ffmpeg` documentation itself, not a third-party library's API, which is a more robust long-term solution.

3.  **Avoiding Dependency Risk:** By not adding a third-party dependency, the project is not subject to its release cycles, bugs, or potential abandonment.

In short, `mcp-avtool-go` is a specialized tool for a specialized job. The verbosity of the current approach is a reasonable trade-off for the ultimate flexibility and control required for the advanced media processing tasks planned for this project.
