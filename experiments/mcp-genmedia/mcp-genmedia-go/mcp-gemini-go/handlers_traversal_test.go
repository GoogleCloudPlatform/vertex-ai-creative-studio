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
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestProcessGeminiImageResponseRejectsTraversal is the per-server prove-it test
// for the gemini image sink (CWE-22 output-directory traversal). It asserts that a
// caller-supplied output_directory that is absolute or contains a dot-dot segment
// is rejected before any bytes are written, and that a confined relative directory
// still writes normally under the configured MCP_OUTPUT_ROOT. The write seam is a
// recorder so a leak would be observable as a path outside the root.
//
// Before the fix (outputDir used verbatim), the absolute and dot-dot cases would
// write outside the root; after the fix they return an error result and write
// nothing.
func TestProcessGeminiImageResponseRejectsTraversal(t *testing.T) {
	root := t.TempDir()
	t.Setenv("MCP_OUTPUT_ROOT", root)
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		resolvedRoot = root
	}

	origWrite := writeFileFn
	t.Cleanup(func() { writeFileFn = origWrite })
	var written []string
	writeFileFn = func(path string, _ []byte, _ os.FileMode) error {
		written = append(written, path)
		return nil
	}

	// An absolute directory outside the root that the attacker would target.
	outsideAbs := t.TempDir()

	cases := []struct {
		name       string
		outputDir  string
		wantReject bool
	}{
		{"absolute path rejected", outsideAbs, true},
		{"absolute etc rejected", "/etc/cron.d", true},
		{"dot-dot escape rejected", "../../../../../../tmp/evil", true},
		{"dot-dot nested rejected", "sub/../../escape", true},
		{"confined relative accepted", "safe/out", false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			written = nil
			resp := imageResponse(imagePart("image/png", []byte("payload")))
			res, err := processGeminiImageResponse(
				context.Background(), resp,
				map[string]any{"output_filename": "shot.png"},
				tc.outputDir, "", "", "",
			)
			if err != nil {
				t.Fatalf("unexpected transport error: %v", err)
			}

			if tc.wantReject {
				if res == nil || !res.IsError {
					t.Fatalf("expected an error result for %q, got %+v", tc.outputDir, res)
				}
				if len(written) != 0 {
					t.Fatalf("traversal wrote files outside confinement: %v", written)
				}
				return
			}

			// Confined case: a file must be written, and strictly under the root.
			if len(written) != 1 {
				t.Fatalf("expected exactly 1 write for confined dir, got %v", written)
			}
			got := written[0]
			if !strings.HasPrefix(got, resolvedRoot+string(os.PathSeparator)) {
				t.Fatalf("write %q escaped confinement root %q", got, resolvedRoot)
			}
		})
	}
}
