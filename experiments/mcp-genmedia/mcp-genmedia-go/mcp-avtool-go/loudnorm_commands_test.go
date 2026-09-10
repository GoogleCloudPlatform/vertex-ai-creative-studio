package main

import (
	"strings"
	"testing"
)

// TestFormatLoudnormValue ensures target parameters render as plain decimals
// suitable for the ffmpeg filter string.
func TestFormatLoudnormValue(t *testing.T) {
	cases := map[float64]string{
		-16:   "-16",
		-1.5:  "-1.5",
		11:    "11",
		-23:   "-23",
		-0.25: "-0.25",
	}
	for in, want := range cases {
		if got := formatLoudnormValue(in); got != want {
			t.Errorf("formatLoudnormValue(%v) = %q, want %q", in, want, got)
		}
	}
}

// TestBuildLoudnormMeasureArgs verifies the first-pass analysis command: it must
// request JSON stats and discard the decode via the null muxer, and must not write
// an output file.
func TestBuildLoudnormMeasureArgs(t *testing.T) {
	target := loudnormTarget{IntegratedLUFS: -16, TruePeakDBTP: -1.5, LoudnessRangeLU: 11}
	got := buildLoudnormMeasureArgs("in.wav", target)
	want := []string{"-hide_banner", "-i", "in.wav", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"}
	if strings.Join(got, " ") != strings.Join(want, " ") {
		t.Errorf("buildLoudnormMeasureArgs = %v, want %v", got, want)
	}
}

// TestBuildLoudnormApplyArgs verifies the second-pass command feeds the measured
// values back into the filter, requests linear normalization, copies video only when
// present and re-applies a known sample rate.
func TestBuildLoudnormApplyArgs(t *testing.T) {
	target := loudnormTarget{IntegratedLUFS: -16, TruePeakDBTP: -1.5, LoudnessRangeLU: 11}
	m := loudnormMeasurements{
		InputI: "-27.61", InputTP: "-10.75", InputLRA: "6.20", InputThresh: "-38.44", TargetOffset: "0.47",
	}

	t.Run("audio only preserves sample rate, no video copy", func(t *testing.T) {
		got := buildLoudnormApplyArgs("in.wav", "out.wav", target, m, false, "44100")
		joined := strings.Join(got, " ")
		wantFilter := "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-27.61:measured_TP=-10.75:measured_LRA=6.20:measured_thresh=-38.44:offset=0.47:linear=true:print_format=summary"
		if !strings.Contains(joined, wantFilter) {
			t.Errorf("apply args missing expected filter.\n got: %s\nwant substring: %s", joined, wantFilter)
		}
		if strings.Contains(joined, "-c:v copy") {
			t.Errorf("audio-only apply args should not stream-copy video: %s", joined)
		}
		if !strings.Contains(joined, "-ar 44100") {
			t.Errorf("apply args should re-apply the source sample rate: %s", joined)
		}
		if got[len(got)-1] != "out.wav" {
			t.Errorf("output path should be the last argument, got %q", got[len(got)-1])
		}
	})

	t.Run("video input copies video stream", func(t *testing.T) {
		got := buildLoudnormApplyArgs("in.mp4", "out.mp4", target, m, true, "48000")
		joined := strings.Join(got, " ")
		if !strings.Contains(joined, "-c:v copy") {
			t.Errorf("video apply args should stream-copy video: %s", joined)
		}
	})

	t.Run("unknown sample rate omits -ar", func(t *testing.T) {
		got := buildLoudnormApplyArgs("in.wav", "out.wav", target, m, false, "")
		if strings.Contains(strings.Join(got, " "), "-ar") {
			t.Errorf("apply args should omit -ar when sample rate unknown: %v", got)
		}
	})
}

// TestParseLoudnormStats covers extracting the JSON block from realistic ffmpeg
// output and the error paths for missing or non-finite measurements.
func TestParseLoudnormStats(t *testing.T) {
	t.Run("parses trailing JSON block", func(t *testing.T) {
		output := `[Parsed_loudnorm_0 @ 0x556]
Input Integrated:    -27.6 LUFS
{
	"input_i" : "-27.61",
	"input_tp" : "-10.75",
	"input_lra" : "6.20",
	"input_thresh" : "-38.44",
	"output_i" : "-16.00",
	"output_tp" : "-1.49",
	"output_lra" : "5.60",
	"output_thresh" : "-27.19",
	"normalization_type" : "dynamic",
	"target_offset" : "0.47"
}
`
		m, err := parseLoudnormStats(output)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if m.InputI != "-27.61" || m.InputTP != "-10.75" || m.InputLRA != "6.20" || m.InputThresh != "-38.44" || m.TargetOffset != "0.47" {
			t.Errorf("parsed measurements incorrect: %+v", m)
		}
	})

	t.Run("errors when no JSON present", func(t *testing.T) {
		if _, err := parseLoudnormStats("no json here"); err == nil {
			t.Error("expected error when no JSON block is present")
		}
	})

	t.Run("errors on non-finite measurement", func(t *testing.T) {
		output := `{
	"input_i" : "-inf",
	"input_tp" : "-120.00",
	"input_lra" : "0.00",
	"input_thresh" : "-inf",
	"target_offset" : "0.00"
}`
		if _, err := parseLoudnormStats(output); err == nil {
			t.Error("expected error for non-finite input_i (silent input)")
		}
	})

	t.Run("errors on missing field", func(t *testing.T) {
		output := `{
	"input_i" : "-23.0",
	"input_tp" : "-5.0",
	"input_lra" : "7.0"
}`
		if _, err := parseLoudnormStats(output); err == nil {
			t.Error("expected error when required fields are missing")
		}
	})
}
