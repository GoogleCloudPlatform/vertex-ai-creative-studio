// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os/exec"
	"strings"
)

// runFFprobeCommand executes an FFprobe command and returns its combined output.
func runFFprobeCommand(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "ffprobe", args...)
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
