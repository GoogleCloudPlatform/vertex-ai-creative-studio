package main

import (
	"strings"
	"testing"
)

// TestParseAspectRatio covers the valid W:H forms and the malformed inputs that must
// be rejected before reaching ffmpeg.
func TestParseAspectRatio(t *testing.T) {
	t.Run("valid ratios", func(t *testing.T) {
		cases := map[string]float64{
			"16:9": 16.0 / 9.0,
			"9:16": 9.0 / 16.0,
			"1:1":  1.0,
			"4:3":  4.0 / 3.0,
			" 21 : 9 ": 21.0 / 9.0,
		}
		for in, want := range cases {
			got, err := parseAspectRatio(in)
			if err != nil {
				t.Errorf("parseAspectRatio(%q) unexpected error: %v", in, err)
				continue
			}
			if got != want {
				t.Errorf("parseAspectRatio(%q) = %v, want %v", in, got, want)
			}
		}
	})

	t.Run("malformed ratios error", func(t *testing.T) {
		bad := []string{"", "16", "16:9:1", "16:", ":9", "a:b", "0:9", "16:0", "-16:9", "16x9"}
		for _, in := range bad {
			if _, err := parseAspectRatio(in); err == nil {
				t.Errorf("parseAspectRatio(%q) expected error, got nil", in)
			}
		}
	})
}

// TestRoundToEvenDim ensures computed dimensions are rounded to positive even
// integers, which codecs like H.264/yuv420p require.
func TestRoundToEvenDim(t *testing.T) {
	cases := map[float64]int{
		1080:   1080,
		1081:   1082, // odd rounds up to even
		1919.4: 1920, // rounds to nearest int (1919), then up to even
		1920.6: 1922, // rounds to 1921, then up to even
		0:      2,    // floor of 2
		1:      2,
		-5:     2,
		607:    608,
	}
	for in, want := range cases {
		if got := roundToEvenDim(in); got != want {
			t.Errorf("roundToEvenDim(%v) = %d, want %d", in, got, want)
		}
	}
}

// TestResolveTargetDimensions exercises the precedence rules for turning the
// requested width/height/aspect plus the input dimensions into an even target frame.
func TestResolveTargetDimensions(t *testing.T) {
	type args struct {
		reqW, reqH   int
		aspect       float64
		inW, inH     int
	}
	cases := []struct {
		name       string
		in         args
		wantW      int
		wantH      int
		wantErr    bool
	}{
		{"explicit width and height", args{reqW: 1280, reqH: 720, inW: 1920, inH: 1080}, 1280, 720, false},
		{"explicit dims ignore aspect", args{reqW: 1000, reqH: 1000, aspect: 16.0 / 9.0, inW: 1920, inH: 1080}, 1000, 1000, false},
		{"aspect with width anchor (9:16)", args{reqW: 1080, aspect: 9.0 / 16.0, inW: 1920, inH: 1080}, 1080, 1920, false},
		{"aspect with height anchor (16:9)", args{reqH: 1080, aspect: 16.0 / 9.0, inW: 640, inH: 480}, 1920, 1080, false},
		{"aspect alone keeps input width (1:1)", args{aspect: 1.0, inW: 1920, inH: 1080}, 1920, 1920, false},
		{"width alone keeps input aspect", args{reqW: 960, inW: 1920, inH: 1080}, 960, 540, false},
		{"height alone keeps input aspect", args{reqH: 540, inW: 1920, inH: 1080}, 960, 540, false},
		{"odd computed dim rounds even", args{reqW: 641, aspect: 1.0, inW: 100, inH: 100}, 642, 642, false},
		{"aspect alone without input dims errors", args{aspect: 1.0}, 0, 0, true},
		{"width alone without input dims errors", args{reqW: 640}, 0, 0, true},
		{"nothing specified errors", args{inW: 1920, inH: 1080}, 0, 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			gotW, gotH, err := resolveTargetDimensions(tc.in.reqW, tc.in.reqH, tc.in.aspect, tc.in.inW, tc.in.inH)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got %dx%d", gotW, gotH)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if gotW != tc.wantW || gotH != tc.wantH {
				t.Errorf("resolveTargetDimensions = %dx%d, want %dx%d", gotW, gotH, tc.wantW, tc.wantH)
			}
			if gotW%2 != 0 || gotH%2 != 0 {
				t.Errorf("resolveTargetDimensions produced odd dimensions %dx%d", gotW, gotH)
			}
		})
	}
}

// TestBuildReframeFilter verifies the pad and crop filtergraphs are constructed with
// the correct scale strategy, even-dimension enforcement and SAR normalisation.
func TestBuildReframeFilter(t *testing.T) {
	t.Run("pad mode fits and letterboxes", func(t *testing.T) {
		got := buildReframeFilter(reframeTarget{Width: 1080, Height: 1920, Mode: reframeModePad, PadColor: "black"})
		want := "scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
		if got != want {
			t.Errorf("pad filter = %q, want %q", got, want)
		}
	})

	t.Run("crop mode covers and trims", func(t *testing.T) {
		got := buildReframeFilter(reframeTarget{Width: 1080, Height: 1080, Mode: reframeModeCrop})
		want := "scale=1080:1080:force_original_aspect_ratio=increase:force_divisible_by=2,crop=1080:1080,setsar=1"
		if got != want {
			t.Errorf("crop filter = %q, want %q", got, want)
		}
	})

	t.Run("unknown mode defaults to pad", func(t *testing.T) {
		got := buildReframeFilter(reframeTarget{Width: 640, Height: 480, Mode: "bogus", PadColor: "white"})
		if !strings.Contains(got, "pad=640:480") || !strings.Contains(got, "color=white") {
			t.Errorf("unexpected default filter: %q", got)
		}
	})
}

// TestBuildResizeArgs verifies the ffmpeg argument list, including audio stream-copy
// only when audio is present and output as the final argument.
func TestBuildResizeArgs(t *testing.T) {
	target := reframeTarget{Width: 1280, Height: 720, Mode: reframeModePad, PadColor: "black"}

	t.Run("video with audio copies audio", func(t *testing.T) {
		got := buildResizeArgs("in.mp4", "out.mp4", target, true)
		joined := strings.Join(got, " ")
		if !strings.Contains(joined, "-c:a copy") {
			t.Errorf("expected audio stream copy: %s", joined)
		}
		if got[len(got)-1] != "out.mp4" {
			t.Errorf("output must be last arg, got %q", got[len(got)-1])
		}
		if !strings.Contains(joined, "-vf scale=1280:720") {
			t.Errorf("expected scale filter for target: %s", joined)
		}
	})

	t.Run("image without audio omits audio copy", func(t *testing.T) {
		got := buildResizeArgs("in.png", "out.png", target, false)
		if strings.Contains(strings.Join(got, " "), "-c:a copy") {
			t.Errorf("image resize should not stream-copy audio: %v", got)
		}
	})
}

// TestIsValidPadColor guards the -vf injection defense on the pad colour parameter.
func TestIsValidPadColor(t *testing.T) {
	valid := []string{"black", "white", "#000000", "0xFFFFFF", "red@0.5", "Gray"}
	for _, c := range valid {
		if !isValidPadColor(c) {
			t.Errorf("isValidPadColor(%q) = false, want true", c)
		}
	}
	invalid := []string{"", "black,crop=1:1", "black:0", "red green", "co'lor", "a\"b", "x;y"}
	for _, c := range invalid {
		if isValidPadColor(c) {
			t.Errorf("isValidPadColor(%q) = true, want false", c)
		}
	}
}
