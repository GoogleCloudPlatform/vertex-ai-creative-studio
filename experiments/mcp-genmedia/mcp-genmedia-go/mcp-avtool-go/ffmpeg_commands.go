// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"fmt"
	"log"
	"os/exec"
	"strings"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// runFFmpegCommand executes an FFMpeg command with the given arguments.
// It logs the command being executed and captures the combined stdout and stderr.
// If the command fails, it logs the error and the output, then returns an error.
// Otherwise, it logs the last few lines of the output for brevity and returns the full output.
func runFFmpegCommand(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	log.Printf("Running FFMpeg command: ffmpeg %s", strings.Join(args, " "))

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("FFMpeg command failed. Error: %v\nFFMpeg Output:\n%s", err, string(output))
		return string(output), fmt.Errorf("ffmpeg command failed: %w. Output: %s", err, string(output))
	}
	log.Printf("FFMpeg command successful. Output (last few lines):\n%s", common.GetTail(string(output), 5)) // getTail from file_utils.go
	return string(output), nil
}

// Note: Specific ffmpeg command functions (like convertAudioToMP3, createGIF etc.) will be added here later.
// For now, this file only contains the generic runFFmpegCommand.
// The handlers in mcp_handlers.go will still call runFFmpegCommand directly in this phase.
// In a subsequent refactoring step, we would create specific functions here, e.g.:
// func executeConvertAudioToMP3(ctx context.Context, localInputAudio, tempOutputFile string) (string, error) {
// 	 return runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-acodec", "libmp3lame", tempOutputFile)
// }
