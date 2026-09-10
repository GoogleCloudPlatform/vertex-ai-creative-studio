# AVTool Compositing Recipes

This document describes the `ffmpeg` and `ffprobe` commands used by the `mcp-avtool-go` service.

## `ffprobe` Commands

### Get Media Info

This command is used to get information about a media file.

```
ffprobe -v quiet -print_format json -show_format -show_streams <input_media_uri>
```

## `ffmpeg` Commands

### Convert WAV to MP3

This command is used to convert a WAV audio file to MP3 format.

```
ffmpeg -y -i <input_audio_uri> -acodec libmp3lame <output_file_name>.mp3
```

### Create GIF

This command is used to create a GIF from a video file. This is a two-pass process.

**Pass 1: Generate Palette**

```
ffmpeg -y -i <input_video_uri> -vf "fps=<fps>,scale=iw*<scale_width_factor>:-1:flags=lanczos+accurate_rnd+full_chroma_inp,palettegen" <palette_path>
```

**Pass 2: Create GIF**

```
ffmpeg -y -i <input_video_uri> -i <palette_path> -lavfi "fps=<fps>,scale=iw*<scale_width_factor>:-1:flags=lanczos+accurate_rnd+full_chroma_inp [x]; [x][1:v] paletteuse" <output_file_name>.gif
```

### Combine Audio and Video

This command is used to combine a video file and an audio file into a single video file.

```
ffmpeg -y -i <input_video_uri> -i <input_audio_uri> -map 0 -map 1:a -c:v copy -shortest <output_file_name>.mp4
```

### Overlay Image on Video

This command is used to overlay an image on a video.

```
ffmpeg -y -i <input_video_uri> -i <input_image_uri> -filter_complex "[0:v][1:v]overlay=<x_coordinate>:<y_coordinate>" <output_file_name>.mp4
```

### Concatenate Media Files

This command is used to concatenate multiple media files. This is a two-pass process for non-WAV files.

**Pass 1: Standardize Files**

```
ffmpeg -y -i <input_media_uri> -vf "scale=<common_width>:<common_height>:force_original_aspect_ratio=decrease,pad=<common_width>:<common_height>:0:0,fps=<common_fps>" -c:v libx264 -preset medium -crf 23 -c:a aac -ar <common_sample_rate> -ac <common_channels> -b:a 192k <standardized_output_path>
```

**Pass 2: Concatenate Files**

```
ffmpeg -y -f concat -safe 0 -i <concat_list_path> -c copy <output_file_name>.mp4
```

### Adjust Volume

This command is used to adjust the volume of an audio file.

```
ffmpeg -y -i <input_audio_uri> -af "volume=<volume_db_change>dB" <output_file_name>.mp3
```

### Layer Audio Files

This command is used to layer multiple audio files together.

```
ffmpeg -y -i <input_audio_uri_1> -i <input_audio_uri_2> ... -filter_complex "amix=inputs=<number_of_inputs>:duration=longest" <output_file_name>.mp3
```

### Trim Media

This command extracts a single segment from an audio or video file, keeping only the
portion beginning at `<start_time>` (in seconds) and lasting `<duration>` seconds. The
same recipe works for both audio and video because `-ss`/`-t` operate on any stream
type.

Fast, lossless stream copy (default). Seeking to a keyframe means the cut may not be
exactly frame-accurate; `-avoid_negative_ts make_zero` normalizes the copied
timestamps to start at zero:

```
ffmpeg -y -ss <start_time> -i <input_media_uri> -t <duration> -c copy -avoid_negative_ts make_zero <output_file_name>
```

Frame-accurate re-encode (used when `re_encode` is requested, or automatically as a
fallback when a stream copy is not possible for the chosen output container):

```
ffmpeg -y -ss <start_time> -i <input_media_uri> -t <duration> <output_file_name>
```
