// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestParseMediaRefsGCSURI verifies gs:// entries are passed through by URI (no
// file read) with a MIME type inferred from the extension.
func TestParseMediaRefsGCSURI(t *testing.T) {
	refs, err := parseMediaRefs([]interface{}{"gs://bucket/cat.png"}, "image")
	if err != nil {
		t.Fatalf("parseMediaRefs returned error: %v", err)
	}
	if len(refs) != 1 {
		t.Fatalf("len(refs) = %d, want 1", len(refs))
	}
	if refs[0].URI != "gs://bucket/cat.png" {
		t.Errorf("URI = %q, want gs://bucket/cat.png", refs[0].URI)
	}
	if len(refs[0].Data) != 0 {
		t.Errorf("gs:// ref should carry no inline data, got %d bytes", len(refs[0].Data))
	}
	if refs[0].MimeType != "image/png" {
		t.Errorf("MimeType = %q, want image/png", refs[0].MimeType)
	}
}

// TestParseMediaRefsLocalFile verifies a local path is read into inline bytes.
func TestParseMediaRefsLocalFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "clip.mp4")
	want := []byte("fake-mp4-bytes")
	if err := os.WriteFile(path, want, 0o600); err != nil {
		t.Fatalf("failed to write temp file: %v", err)
	}

	refs, err := parseMediaRefs([]interface{}{path}, "video")
	if err != nil {
		t.Fatalf("parseMediaRefs returned error: %v", err)
	}
	if len(refs) != 1 {
		t.Fatalf("len(refs) = %d, want 1", len(refs))
	}
	if string(refs[0].Data) != string(want) {
		t.Errorf("Data = %q, want %q", refs[0].Data, want)
	}
	if refs[0].URI != "" {
		t.Errorf("local ref should carry no URI, got %q", refs[0].URI)
	}
	if refs[0].MimeType != "video/mp4" {
		t.Errorf("MimeType = %q, want video/mp4", refs[0].MimeType)
	}
}

func TestParseMediaRefsErrors(t *testing.T) {
	if _, err := parseMediaRefs("not-an-array", "image"); err == nil {
		t.Error("expected error for a non-array argument")
	}
	if _, err := parseMediaRefs([]interface{}{""}, "image"); err == nil {
		t.Error("expected error for an empty-string entry")
	}
	if _, err := parseMediaRefs([]interface{}{123}, "image"); err == nil {
		t.Error("expected error for a non-string entry")
	}
	if _, err := parseMediaRefs([]interface{}{"/no/such/file.png"}, "image"); err == nil {
		t.Error("expected error for an unreadable local file")
	}
}

// TestParseMediaRefsNilYieldsNil confirms an absent argument produces no refs.
func TestParseMediaRefsNilYieldsNil(t *testing.T) {
	refs, err := parseMediaRefs(nil, "image")
	if err != nil {
		t.Fatalf("parseMediaRefs(nil) returned error: %v", err)
	}
	if refs != nil {
		t.Errorf("parseMediaRefs(nil) = %v, want nil", refs)
	}
}

func TestInferMediaMimeType(t *testing.T) {
	cases := map[string]string{
		"a.png":       "image/png",
		"a.JPG":       "image/jpeg",
		"a.jpeg":      "image/jpeg",
		"a.webp":      "image/webp",
		"clip.mp4":    "video/mp4",
		"clip.mov":    "video/quicktime",
		"clip.webm":   "video/webm",
		"unknown.bin": "application/octet-stream",
	}
	for name, want := range cases {
		if got := inferMediaMimeType(name); got != want {
			t.Errorf("inferMediaMimeType(%q) = %q, want %q", name, got, want)
		}
	}
}

func TestToInt(t *testing.T) {
	if n, err := toInt(float64(3)); err != nil || n != 3 {
		t.Errorf("toInt(3.0) = %d, %v; want 3, nil", n, err)
	}
	if n, err := toInt(2); err != nil || n != 2 {
		t.Errorf("toInt(2) = %d, %v; want 2, nil", n, err)
	}
	if _, err := toInt(float64(2.5)); err == nil {
		t.Error("expected error for a non-integer float")
	}
	if _, err := toInt("nope"); err == nil {
		t.Error("expected error for a string argument")
	}
}

func TestParseOptionalFloatInRange(t *testing.T) {
	args := map[string]interface{}{
		"temperature": float64(1.5),
		"too_high":    float64(9),
		"not_number":  "x",
	}

	// Absent key -> nil, no error.
	v, err := parseOptionalFloatInRange(args, "missing", 0, 2)
	if err != nil || v != nil {
		t.Errorf("absent key: got %v, %v; want nil, nil", v, err)
	}

	// In-range value.
	v, err = parseOptionalFloatInRange(args, "temperature", 0, 2)
	if err != nil || v == nil || *v != 1.5 {
		t.Errorf("in-range: got %v, %v; want 1.5, nil", v, err)
	}

	// Out-of-range value.
	if _, err := parseOptionalFloatInRange(args, "too_high", 0, 2); err == nil {
		t.Error("expected error for an out-of-range value")
	}

	// Wrong type.
	if _, err := parseOptionalFloatInRange(args, "not_number", 0, 2); err == nil {
		t.Error("expected error for a non-numeric value")
	}
}

// TestParseOptionalFloatInRangeIntegers guards BOT-1: integer JSON numbers (which
// may surface as float64, int, or int64) must be accepted for temperature/top_p,
// not rejected as "must be a number".
func TestParseOptionalFloatInRangeIntegers(t *testing.T) {
	cases := map[string]interface{}{
		"float64_int": float64(1), // JSON "1" decoded to float64
		"int":         1,
		"int64":       int64(1),
	}
	for name, raw := range cases {
		t.Run(name, func(t *testing.T) {
			// temperature range [0,2]
			v, err := parseOptionalFloatInRange(map[string]interface{}{"temperature": raw}, "temperature", 0, 2)
			if err != nil {
				t.Fatalf("integer temperature %v (%T) rejected: %v", raw, raw, err)
			}
			if v == nil || *v != 1 {
				t.Fatalf("temperature = %v, want 1", v)
			}
			// top_p range [0,1]
			p, err := parseOptionalFloatInRange(map[string]interface{}{"top_p": raw}, "top_p", 0, 1)
			if err != nil {
				t.Fatalf("integer top_p %v (%T) rejected: %v", raw, raw, err)
			}
			if p == nil || *p != 1 {
				t.Fatalf("top_p = %v, want 1", p)
			}
		})
	}
}

// TestParseMediaRefsOversized guards BOT-3: a local file above the inline cap is
// rejected with a hint to use a gs:// URI, and is not read fully into memory.
func TestParseMediaRefsOversized(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "big.mp4")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	// Sparse file just over the cap (no large allocation).
	if err := f.Truncate(maxInlineMediaBytes + 1); err != nil {
		t.Fatalf("truncate: %v", err)
	}
	f.Close()

	_, err = parseMediaRefs([]interface{}{path}, "video")
	if err == nil {
		t.Fatal("expected an error for an oversized local file")
	}
	if !strings.Contains(err.Error(), "gs://") {
		t.Errorf("error should suggest a gs:// URI, got: %v", err)
	}
}
