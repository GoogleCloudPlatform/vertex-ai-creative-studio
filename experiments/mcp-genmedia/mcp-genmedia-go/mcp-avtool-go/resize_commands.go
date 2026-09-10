// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"fmt"
	"math"
	"strconv"
	"strings"
)

// Reframe modes decide how an aspect-ratio mismatch between the source and the
// requested target frame is reconciled.
//
// "pad" is the default: the whole source is scaled to fit inside the target frame
// and the leftover space is filled with bars (letterbox/pillarbox). It is chosen as
// the default because it never discards picture content — every pixel of the input
// is preserved in the output, which is the safe, non-destructive behaviour a caller
// expects unless they explicitly ask to fill the frame.
//
// "crop" scales the source to cover the target frame and trims the overflow, which
// fills the frame edge-to-edge at the cost of cutting off the parts of the picture
// that fall outside the target aspect ratio.
const (
	reframeModePad  = "pad"
	reframeModeCrop = "crop"

	defaultReframeMode = reframeModePad
	defaultPadColor    = "black"
)

// reframeTarget captures the fully-resolved output geometry for a resize/reframe
// run: the exact (even) target dimensions, how to reconcile an aspect mismatch, and
// the fill colour used when padding.
type reframeTarget struct {
	Width    int
	Height   int
	Mode     string
	PadColor string
}

// parseAspectRatio parses an aspect-ratio shorthand of the form "W:H" (e.g. "16:9",
// "9:16", "1:1") into a numeric width/height ratio. Both components must be positive
// numbers; anything else is reported as an error so a malformed target is rejected
// before it reaches ffmpeg.
func parseAspectRatio(s string) (float64, error) {
	parts := strings.Split(strings.TrimSpace(s), ":")
	if len(parts) != 2 {
		return 0, fmt.Errorf("aspect ratio %q must be in W:H form (e.g. 16:9)", s)
	}
	w, err := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
	if err != nil || w <= 0 {
		return 0, fmt.Errorf("aspect ratio %q has an invalid width component", s)
	}
	h, err := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
	if err != nil || h <= 0 {
		return 0, fmt.Errorf("aspect ratio %q has an invalid height component", s)
	}
	return w / h, nil
}

// roundToEvenDim rounds a computed pixel dimension to the nearest positive even
// integer (with a floor of 2). Even dimensions are required by common 4:2:0 video
// codecs (e.g. H.264 with yuv420p), so rounding here rather than letting ffmpeg fail
// on an odd width/height keeps the output encodable. An odd value is rounded up to
// the next even number.
func roundToEvenDim(v float64) int {
	n := int(math.Round(v))
	if n < 2 {
		return 2
	}
	if n%2 != 0 {
		n++
	}
	return n
}

// resolveTargetDimensions derives the final, even target width and height from the
// caller's request and the input's own dimensions. The precedence is:
//
//  1. width AND height both given -> use them verbatim (any aspect_ratio is ignored;
//     the caller has stated the exact frame).
//  2. aspect_ratio given -> size the frame to that ratio, using an explicit width or
//     height as the anchor when one is supplied, otherwise anchoring on the input's
//     width.
//  3. only width (or only height) given -> a plain proportional resize that keeps the
//     input's aspect ratio.
//
// reqWidth/reqHeight of 0 mean "not supplied"; aspect of 0 means "not supplied".
// inWidth/inHeight are the input's pixel dimensions and are only consulted when the
// request cannot be satisfied from explicit values alone.
func resolveTargetDimensions(reqWidth, reqHeight int, aspect float64, inWidth, inHeight int) (int, int, error) {
	switch {
	case reqWidth > 0 && reqHeight > 0:
		return roundToEvenDim(float64(reqWidth)), roundToEvenDim(float64(reqHeight)), nil

	case aspect > 0:
		switch {
		case reqWidth > 0:
			return roundToEvenDim(float64(reqWidth)), roundToEvenDim(float64(reqWidth) / aspect), nil
		case reqHeight > 0:
			return roundToEvenDim(float64(reqHeight) * aspect), roundToEvenDim(float64(reqHeight)), nil
		default:
			if inWidth <= 0 || inHeight <= 0 {
				return 0, 0, fmt.Errorf("cannot derive target dimensions from aspect ratio alone: the input's dimensions are unknown; provide a width or height")
			}
			return roundToEvenDim(float64(inWidth)), roundToEvenDim(float64(inWidth) / aspect), nil
		}

	case reqWidth > 0:
		if inWidth <= 0 || inHeight <= 0 {
			return 0, 0, fmt.Errorf("cannot compute a proportional height: the input's dimensions are unknown; provide both width and height")
		}
		return roundToEvenDim(float64(reqWidth)), roundToEvenDim(float64(reqWidth) * float64(inHeight) / float64(inWidth)), nil

	case reqHeight > 0:
		if inWidth <= 0 || inHeight <= 0 {
			return 0, 0, fmt.Errorf("cannot compute a proportional width: the input's dimensions are unknown; provide both width and height")
		}
		return roundToEvenDim(float64(reqHeight) * float64(inWidth) / float64(inHeight)), roundToEvenDim(float64(reqHeight)), nil

	default:
		return 0, 0, fmt.Errorf("no target specified: provide width, height, and/or aspect_ratio")
	}
}

// buildReframeFilter constructs the ffmpeg -vf filtergraph for the requested target.
//
// Both modes first scale the source and then reconcile any aspect mismatch:
//   - pad:  scale to fit *inside* the target (force_original_aspect_ratio=decrease),
//     then pad the remainder with the fill colour, centring the picture.
//   - crop: scale to *cover* the target (force_original_aspect_ratio=increase), then
//     crop the overflow, centring the picture.
//
// force_divisible_by=2 keeps the intermediate scaled dimensions even so the codec
// never sees an odd size, and setsar=1 normalises the sample aspect ratio so the
// stored pixel dimensions display as intended (guards against anamorphic inputs).
// When the source and target already share an aspect ratio, both graphs reduce to a
// plain scale with no bars added or pixels cut.
func buildReframeFilter(t reframeTarget) string {
	switch t.Mode {
	case reframeModeCrop:
		return fmt.Sprintf(
			"scale=%d:%d:force_original_aspect_ratio=increase:force_divisible_by=2,crop=%d:%d,setsar=1",
			t.Width, t.Height, t.Width, t.Height,
		)
	default: // reframeModePad
		return fmt.Sprintf(
			"scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=%s,setsar=1",
			t.Width, t.Height, t.Width, t.Height, t.PadColor,
		)
	}
}

// buildResizeArgs assembles the full ffmpeg argument list. The video (or single
// image frame) is filtered to the target geometry; when the input also carries an
// audio stream it is stream-copied so a video resize does not needlessly re-encode
// or drop the audio.
func buildResizeArgs(input, output string, t reframeTarget, hasAudio bool) []string {
	args := []string{"-y", "-hide_banner", "-i", input, "-vf", buildReframeFilter(t)}
	if hasAudio {
		args = append(args, "-c:a", "copy")
	}
	args = append(args, output)
	return args
}

// executeResizeReframe runs the resize/reframe operation for the resolved target.
func executeResizeReframe(ctx context.Context, input, output string, t reframeTarget, hasAudio bool) error {
	_, err := runFFmpegCommand(ctx, buildResizeArgs(input, output, t, hasAudio)...)
	return err
}

// isValidPadColor restricts the caller-supplied pad colour to characters that appear
// in ffmpeg colour specifications (named colours like "black", hex forms like
// "0xRRGGBB" or "#RRGGBB", and an optional "@alpha" suffix). Rejecting anything else
// prevents a crafted value from injecting extra filtergraph tokens (commas, colons,
// quotes) into the -vf string.
func isValidPadColor(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z':
		case r >= 'A' && r <= 'Z':
		case r >= '0' && r <= '9':
		case r == '#' || r == '@' || r == '.':
		default:
			return false
		}
	}
	return true
}
