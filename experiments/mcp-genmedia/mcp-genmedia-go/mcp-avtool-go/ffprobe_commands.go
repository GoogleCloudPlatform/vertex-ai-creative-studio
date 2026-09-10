// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

// runFFprobeCommand executes an FFprobe command and returns its combined output.
func runFFprobeCommand(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "ffprobe", args...)
	if customPath := os.Getenv("MCP_CUSTOM_PATH"); customPath != "" {
		cmd.Env = append(os.Environ(), "PATH="+customPath)
	}
	log.Printf("Running FFprobe command: ffprobe %s", strings.Join(args, " "))

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("FFprobe command execution failed. Error: %v\nFFprobe Output:\n%s", err, string(output))
		return string(output), fmt.Errorf("ffprobe command execution failed: %w. Output: %s", err, string(output))
	}
	var js json.RawMessage
	if json.Unmarshal(output, &js) != nil && strings.TrimSpace(string(output)) != "" {
		log.Printf("FFprobe output was not valid JSON, though command execution reported no error. Output:\n%s", string(output))
	}

	log.Printf("FFprobe command successful.")
	return string(output), nil
}

// executeGetMediaInfo uses ffprobe to extract detailed media information from a given file.
// It specifically requests format and stream information in JSON format.
// The function assembles the required command-line arguments for this task and
// calls runFFprobeCommand to execute the command, returning the resulting JSON string.
func executeGetMediaInfo(ctx context.Context, localInputMedia string) (string, error) {
	ffprobeArgs := []string{
		"-v", "quiet",
		"-print_format", "json",
		"-show_format",
		"-show_streams",
		localInputMedia,
	}
	return runFFprobeCommand(ctx, ffprobeArgs...)
}

// mediaStreamInfo summarizes the stream layout of a media file: whether it carries
// audio and/or video, the first audio stream's sample rate (empty when unknown), and
// the first video (or image) stream's pixel dimensions (zero when there is none).
type mediaStreamInfo struct {
	HasAudio   bool
	HasVideo   bool
	SampleRate string
	Width      int
	Height     int
}

// probeMediaStreamInfo inspects a media file with ffprobe and reports which stream
// types it contains, the audio sample rate, and the first visual stream's pixel
// dimensions. Callers use it to reject inputs that have no audio stream, to preserve
// the source sample rate through filters that would otherwise resample, and to size a
// resize/reframe against the input's own dimensions — all from a single ffprobe call.
func probeMediaStreamInfo(ctx context.Context, localInputMedia string) (mediaStreamInfo, error) {
	var result mediaStreamInfo

	infoJSON, err := executeGetMediaInfo(ctx, localInputMedia)
	if err != nil {
		return result, fmt.Errorf("failed to probe media info: %w", err)
	}

	var info struct {
		Streams []struct {
			CodecType  string `json:"codec_type"`
			SampleRate string `json:"sample_rate"`
			Width      int    `json:"width"`
			Height     int    `json:"height"`
		} `json:"streams"`
	}
	if err := json.Unmarshal([]byte(infoJSON), &info); err != nil {
		return result, fmt.Errorf("failed to parse media info: %w", err)
	}

	for _, stream := range info.Streams {
		switch stream.CodecType {
		case "audio":
			result.HasAudio = true
			if result.SampleRate == "" {
				result.SampleRate = strings.TrimSpace(stream.SampleRate)
			}
		case "video":
			result.HasVideo = true
			if result.Width == 0 && stream.Width > 0 && stream.Height > 0 {
				result.Width = stream.Width
				result.Height = stream.Height
			}
		}
	}

	return result, nil
}

// probeMediaDurationSeconds returns the total duration of a media file in seconds,
// parsed from the container's format metadata. It is used to validate trim ranges
// against the actual length of the input. A non-nil error indicates the duration
// could not be determined (e.g. a stream without a known duration), in which case
// callers should skip range validation rather than reject the request.
func probeMediaDurationSeconds(ctx context.Context, localInputMedia string) (float64, error) {
	infoJSON, err := executeGetMediaInfo(ctx, localInputMedia)
	if err != nil {
		return 0, fmt.Errorf("failed to probe media info: %w", err)
	}
	var info struct {
		Format struct {
			Duration string `json:"duration"`
		} `json:"format"`
	}
	if err := json.Unmarshal([]byte(infoJSON), &info); err != nil {
		return 0, fmt.Errorf("failed to parse media info: %w", err)
	}
	if strings.TrimSpace(info.Format.Duration) == "" {
		return 0, fmt.Errorf("media info did not report a container duration")
	}
	seconds, err := strconv.ParseFloat(info.Format.Duration, 64)
	if err != nil {
		return 0, fmt.Errorf("failed to parse duration %q: %w", info.Format.Duration, err)
	}
	return seconds, nil
}
