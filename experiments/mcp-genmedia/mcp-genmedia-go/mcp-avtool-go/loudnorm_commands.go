// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strconv"
	"strings"
)

// Default EBU R128 loudness targets. -16 LUFS integrated is the common target for
// streaming/web/podcast playback (Spotify, Apple Podcasts, YouTube all sit at or
// near it), which matches this server's role of levelling generated speech and
// media for downstream playback. A -1.5 dBTP true-peak ceiling leaves headroom for
// lossy-codec inter-sample overshoot, and an 11 LU loudness range is the widely used
// default for the loudnorm filter. Callers can override any of these per request.
const (
	defaultTargetLoudnessLUFS   = -16.0
	defaultTargetTruePeakDBTP   = -1.5
	defaultTargetLoudnessRangeLU = 11.0
)

// loudnormTarget holds the desired EBU R128 output targets for a normalization run.
type loudnormTarget struct {
	IntegratedLUFS float64 // I: target integrated loudness in LUFS
	TruePeakDBTP   float64 // TP: maximum true peak in dBTP
	LoudnessRangeLU float64 // LRA: target loudness range in LU
}

// loudnormMeasurements captures the values the first (analysis) pass of the
// loudnorm filter prints as JSON. They are kept as strings because they are fed
// straight back into the second pass's filter string; parsing them to floats would
// only risk reformatting drift.
type loudnormMeasurements struct {
	InputI       string `json:"input_i"`
	InputTP      string `json:"input_tp"`
	InputLRA     string `json:"input_lra"`
	InputThresh  string `json:"input_thresh"`
	TargetOffset string `json:"target_offset"`
}

// formatLoudnormValue renders a target parameter as a plain decimal string for the
// ffmpeg filter (e.g. -16 -> "-16", -1.5 -> "-1.5"), avoiding scientific notation
// and trailing zeros.
func formatLoudnormValue(v float64) string {
	return strconv.FormatFloat(v, 'f', -1, 64)
}

// buildLoudnormMeasureArgs builds the first-pass ffmpeg arguments. This pass does
// not write a media file: it runs the loudnorm filter in analysis mode against the
// requested targets and asks it to print the measured integrated loudness, true
// peak, loudness range and threshold as JSON (to stderr). The decode is discarded
// via the null muxer. Only audio is analyzed, so -vn disables the video stream to
// avoid decoding it — a meaningful saving on large video inputs.
func buildLoudnormMeasureArgs(input string, target loudnormTarget) []string {
	filter := fmt.Sprintf("loudnorm=I=%s:TP=%s:LRA=%s:print_format=json",
		formatLoudnormValue(target.IntegratedLUFS),
		formatLoudnormValue(target.TruePeakDBTP),
		formatLoudnormValue(target.LoudnessRangeLU),
	)
	return []string{"-hide_banner", "-i", input, "-af", filter, "-vn", "-f", "null", "-"}
}

// buildLoudnormApplyArgs builds the second-pass ffmpeg arguments. It applies the
// loudnorm filter using the measured values from the first pass, which lets the
// filter perform an accurate linear correction toward the target instead of the
// less precise single-pass dynamic mode. linear=true requests linear normalization;
// ffmpeg automatically falls back to dynamic if a linear gain would breach the
// true-peak ceiling.
//
// When the input carries a video stream the video is stream-copied so only the audio
// is re-encoded. When a source sample rate is known it is re-applied, because the
// loudnorm filter internally resamples to 192 kHz and would otherwise emit audio at
// that rate.
func buildLoudnormApplyArgs(input, output string, target loudnormTarget, m loudnormMeasurements, hasVideo bool, sampleRate string) []string {
	filter := fmt.Sprintf(
		"loudnorm=I=%s:TP=%s:LRA=%s:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true:print_format=summary",
		formatLoudnormValue(target.IntegratedLUFS),
		formatLoudnormValue(target.TruePeakDBTP),
		formatLoudnormValue(target.LoudnessRangeLU),
		m.InputI, m.InputTP, m.InputLRA, m.InputThresh, m.TargetOffset,
	)
	args := []string{"-y", "-hide_banner", "-i", input, "-af", filter}
	if hasVideo {
		args = append(args, "-c:v", "copy")
	}
	if strings.TrimSpace(sampleRate) != "" {
		args = append(args, "-ar", sampleRate)
	}
	args = append(args, output)
	return args
}

// parseLoudnormStats extracts the loudnorm analysis JSON from ffmpeg's combined
// output. The filter prints a single JSON object at the end of the run, so the last
// brace-delimited block is located and decoded. All five fields the second pass
// depends on must be present and non-empty; a missing field (or a non-finite
// measurement such as "-inf" from pure silence) is reported as an error so the
// caller does not attempt an invalid correction pass.
func parseLoudnormStats(output string) (loudnormMeasurements, error) {
	var m loudnormMeasurements

	start := strings.LastIndex(output, "{")
	end := strings.LastIndex(output, "}")
	if start == -1 || end == -1 || end < start {
		return m, fmt.Errorf("could not locate loudnorm JSON stats in ffmpeg output")
	}

	if err := json.Unmarshal([]byte(output[start:end+1]), &m); err != nil {
		return m, fmt.Errorf("failed to parse loudnorm JSON stats: %w", err)
	}

	for name, value := range map[string]string{
		"input_i":       m.InputI,
		"input_tp":      m.InputTP,
		"input_lra":     m.InputLRA,
		"input_thresh":  m.InputThresh,
		"target_offset": m.TargetOffset,
	} {
		if strings.TrimSpace(value) == "" {
			return m, fmt.Errorf("loudnorm stats missing %q value", name)
		}
		parsed, err := strconv.ParseFloat(value, 64)
		if err != nil || math.IsInf(parsed, 0) || math.IsNaN(parsed) {
			return m, fmt.Errorf("loudnorm stats %q is not a finite number (%q); the input may be silent or have no measurable loudness", name, value)
		}
	}

	return m, nil
}

// executeNormalizeLoudness runs the full two-pass EBU R128 normalization: it first
// measures the input against the requested targets, parses the reported statistics,
// then applies the correction using those measurements. The parsed measurements are
// returned so the caller can report the input's original loudness.
func executeNormalizeLoudness(ctx context.Context, input, output string, target loudnormTarget, hasVideo bool, sampleRate string) (loudnormMeasurements, error) {
	measureOutput, err := runFFmpegCommand(ctx, buildLoudnormMeasureArgs(input, target)...)
	if err != nil {
		return loudnormMeasurements{}, fmt.Errorf("loudness measurement pass failed: %w", err)
	}

	measurements, err := parseLoudnormStats(measureOutput)
	if err != nil {
		return loudnormMeasurements{}, err
	}

	if _, err := runFFmpegCommand(ctx, buildLoudnormApplyArgs(input, output, target, measurements, hasVideo, sampleRate)...); err != nil {
		return loudnormMeasurements{}, fmt.Errorf("loudness correction pass failed: %w", err)
	}

	return measurements, nil
}
