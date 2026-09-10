package main

import (
	"strings"
	"testing"
)

// TestBuildTrimArgs verifies the ffmpeg argument construction for both the
// stream-copy and re-encode paths, including decimal time formatting.
func TestBuildTrimArgs(t *testing.T) {
	t.Run("stream copy places -ss before -i, adds -c copy", func(t *testing.T) {
		got := buildTrimArgs("in.mp4", "out.mp4", 12.5, 10, true)
		want := []string{"-y", "-ss", "12.5", "-i", "in.mp4", "-t", "10", "-c", "copy", "-avoid_negative_ts", "make_zero", "out.mp4"}
		if strings.Join(got, " ") != strings.Join(want, " ") {
			t.Errorf("buildTrimArgs stream-copy = %v, want %v", got, want)
		}
	})

	t.Run("re-encode omits -c copy", func(t *testing.T) {
		got := buildTrimArgs("in.wav", "out.wav", 0, 3, false)
		want := []string{"-y", "-ss", "0", "-i", "in.wav", "-t", "3", "out.wav"}
		if strings.Join(got, " ") != strings.Join(want, " ") {
			t.Errorf("buildTrimArgs re-encode = %v, want %v", got, want)
		}
		if strings.Contains(strings.Join(got, " "), "-c copy") {
			t.Errorf("re-encode args should not contain -c copy: %v", got)
		}
	})
}

// TestFormatSeconds ensures times render as plain decimals without scientific
// notation or trailing zeros, which keeps the emitted ffmpeg command readable.
func TestFormatSeconds(t *testing.T) {
	cases := map[float64]string{
		0:      "0",
		3:      "3",
		12.5:   "12.5",
		0.25:   "0.25",
		90.125: "90.125",
		3600:   "3600",
	}
	for in, want := range cases {
		if got := formatSeconds(in); got != want {
			t.Errorf("formatSeconds(%v) = %q, want %q", in, got, want)
		}
	}
}
