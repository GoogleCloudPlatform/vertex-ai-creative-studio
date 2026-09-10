// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// runFFmpegCommand executes an FFMpeg command with the given arguments.
// It logs the command being executed and captures the combined stdout and stderr.
// If the command fails, it logs the error and the output, then returns an error.
// Otherwise, it logs the last few lines of the output for brevity and returns the full output.
func runFFmpegCommand(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	if customPath := os.Getenv("MCP_CUSTOM_PATH"); customPath != "" {
		cmd.Env = append(os.Environ(), "PATH="+customPath)
	}
	log.Printf("Running FFMpeg command: ffmpeg %s", strings.Join(args, " "))

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("FFMpeg command failed. Error: %v\nFFMpeg Output:\n%s", err, string(output))
		return string(output), fmt.Errorf("ffmpeg command failed: %w. Output: %s", err, string(output))
	}
	log.Printf("FFMpeg command successful. Output (last few lines):\n%s", common.GetTail(string(output), 5)) // getTail from file_utils.go
	return string(output), nil
}

// formatSeconds renders a number of seconds as a plain decimal string suitable for
// passing to ffmpeg's -ss/-t options (e.g. 12.5 -> "12.5", 3 -> "3"). It avoids
// scientific notation and trailing zeros so the emitted command is easy to read.
func formatSeconds(seconds float64) string {
	return strconv.FormatFloat(seconds, 'f', -1, 64)
}

// buildTrimArgs constructs the ffmpeg argument list for extracting a segment that
// begins at startSeconds and lasts durationSeconds.
//
// When streamCopy is true the segment is copied without re-encoding (-c copy). This
// is fast and lossless, but because ffmpeg can only start a stream copy on a
// keyframe, the actual cut point is the nearest keyframe at or before the requested
// start, so the result may not be frame-accurate. -avoid_negative_ts make_zero keeps
// the copied timestamps starting from zero so players don't stumble on the leading
// gap.
//
// When streamCopy is false the segment is re-encoded, which decodes from the nearest
// keyframe and writes exactly the requested range — frame-accurate at the cost of a
// slower, lossy pass.
func buildTrimArgs(localInput, tempOutput string, startSeconds, durationSeconds float64, streamCopy bool) []string {
	args := []string{"-y", "-ss", formatSeconds(startSeconds), "-i", localInput, "-t", formatSeconds(durationSeconds)}
	if streamCopy {
		args = append(args, "-c", "copy", "-avoid_negative_ts", "make_zero")
	}
	args = append(args, tempOutput)
	return args
}

// executeTrimMedia runs the trim operation. It first attempts the requested mode
// (stream copy unless reEncode is set). If a stream copy fails — some codec/container
// combinations cannot be copied into the chosen output container — it automatically
// retries with a re-encode so the caller still gets a usable clip. The boolean return
// reports whether the output was produced by re-encoding.
func executeTrimMedia(ctx context.Context, localInput, tempOutput string, startSeconds, durationSeconds float64, reEncode bool) (bool, error) {
	if !reEncode {
		_, err := runFFmpegCommand(ctx, buildTrimArgs(localInput, tempOutput, startSeconds, durationSeconds, true)...)
		if err == nil {
			return false, nil
		}
		log.Printf("Stream-copy trim failed (%v); retrying with a re-encode fallback.", err)
	}
	_, err := runFFmpegCommand(ctx, buildTrimArgs(localInput, tempOutput, startSeconds, durationSeconds, false)...)
	return true, err
}

// Note: Specific ffmpeg command functions (like convertAudioToMP3, createGIF etc.) will be added here later.
// For now, this file only contains the generic runFFmpegCommand.
// The handlers in mcp_handlers.go will still call runFFmpegCommand directly in this phase.
// In a subsequent refactoring step, we would create specific functions here, e.g.:
// func executeConvertAudioToMP3(ctx context.Context, localInputAudio, tempOutputFile string) (string, error) {
// 	 return runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-acodec", "libmp3lame", tempOutputFile)
// }
