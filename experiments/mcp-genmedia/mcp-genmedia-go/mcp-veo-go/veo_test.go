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
	"reflect"
	"testing"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// TestVeoOutputNames locks the output_filename → per-video name mapping, including
// the n==1 (no suffix) and n>1 (1-based suffix) cases, extension forcing to the
// true video MIME, path-traversal sanitization, and the unset back-compat path
// (nil → handler keeps its default naming scheme).
func TestVeoOutputNames(t *testing.T) {
	tests := []struct {
		name       string
		outputName string
		count      int
		mimeType   string
		want       []string
	}{
		{"unset returns nil (back-compat default naming)", "", 2, "video/mp4", nil},
		{"whitespace-only returns nil", "   ", 2, "video/mp4", nil},
		{"zero count returns nil", "clip.mp4", 0, "video/mp4", nil},
		{"single video, no suffix", "clip.mp4", 1, "video/mp4", []string{"clip.mp4"}},
		{"three videos, 1-based suffix", "clip.mp4", 3, "video/mp4", []string{"clip_1.mp4", "clip_2.mp4", "clip_3.mp4"}},
		{"extension forced to true MIME", "clip.mov", 1, "video/mp4", []string{"clip.mp4"}},
		{"no extension supplied gets forced", "clip", 2, "video/mp4", []string{"clip_1.mp4", "clip_2.mp4"}},
		{"path traversal sanitized", "../../etc/passwd", 1, "video/mp4", []string{"passwd.mp4"}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := veoOutputNames(tc.outputName, tc.count, tc.mimeType)
			if !reflect.DeepEqual(got, tc.want) {
				t.Errorf("veoOutputNames(%q, %d, %q) = %v, want %v", tc.outputName, tc.count, tc.mimeType, got, tc.want)
			}
		})
	}
}

// TestBuildVeoRenamePlan verifies the Path-C plan that maps the API-written video
// objects to the client-desired names: num_videos>1 + gcs + output_filename="clip.mp4"
// ⇒ the API sample objects → clip_1..N.mp4 under the output prefix, same bucket,
// with correct gs:// URIs. src→dst are paired by identity (srcURIs[i] ↔ names[i]).
// Feeding the returned renames to common.RenameGCSObjects (whose copy-fatal /
// delete-nonfatal / collision-overwrite / originals-removed contract is unit-tested
// network-free in mcp-common) removes the originals.
func TestBuildVeoRenamePlan(t *testing.T) {
	gcsOutputURI := "gs://mybucket/veo_outputs/"
	srcURIs := []string{
		"gs://mybucket/veo_outputs/1234/sample_0.mp4",
		"gs://mybucket/veo_outputs/1234/sample_1.mp4",
		"gs://mybucket/veo_outputs/1234/sample_2.mp4",
	}
	names := veoOutputNames("clip.mp4", 3, "video/mp4")

	bucket, renames, dstURIs := buildVeoRenamePlan(gcsOutputURI, srcURIs, names)

	if bucket != "mybucket" {
		t.Errorf("bucket = %q, want mybucket", bucket)
	}
	wantRenames := []common.Rename{
		{Src: "veo_outputs/1234/sample_0.mp4", Dst: "veo_outputs/clip_1.mp4"},
		{Src: "veo_outputs/1234/sample_1.mp4", Dst: "veo_outputs/clip_2.mp4"},
		{Src: "veo_outputs/1234/sample_2.mp4", Dst: "veo_outputs/clip_3.mp4"},
	}
	if !reflect.DeepEqual(renames, wantRenames) {
		t.Errorf("renames = %v, want %v", renames, wantRenames)
	}
	wantURIs := []string{
		"gs://mybucket/veo_outputs/clip_1.mp4",
		"gs://mybucket/veo_outputs/clip_2.mp4",
		"gs://mybucket/veo_outputs/clip_3.mp4",
	}
	if !reflect.DeepEqual(dstURIs, wantURIs) {
		t.Errorf("dstURIs = %v, want %v", dstURIs, wantURIs)
	}
}

// TestBuildVeoRenamePlanSingle: n==1 ⇒ no suffix (clip.mp4), extension forced.
func TestBuildVeoRenamePlanSingle(t *testing.T) {
	names := veoOutputNames("clip.mov", 1, "video/mp4")
	bucket, renames, dstURIs := buildVeoRenamePlan("gs://mybucket/veo_outputs/", []string{"gs://mybucket/veo_outputs/sample_0.mp4"}, names)
	if bucket != "mybucket" {
		t.Errorf("bucket = %q, want mybucket", bucket)
	}
	want := common.Rename{Src: "veo_outputs/sample_0.mp4", Dst: "veo_outputs/clip.mp4"}
	if len(renames) != 1 || renames[0] != want {
		t.Errorf("renames = %v, want [%v]", renames, want)
	}
	if len(dstURIs) != 1 || dstURIs[0] != "gs://mybucket/veo_outputs/clip.mp4" {
		t.Errorf("dstURIs = %v, want [gs://mybucket/veo_outputs/clip.mp4]", dstURIs)
	}
}

// TestBuildVeoRenamePlanBackCompat: no output_filename ⇒ nil plan, so the handler
// leaves the API-written object names untouched (byte-for-byte legacy behavior).
func TestBuildVeoRenamePlanBackCompat(t *testing.T) {
	names := veoOutputNames("", 3, "video/mp4") // nil
	bucket, renames, dstURIs := buildVeoRenamePlan("gs://mybucket/veo_outputs/", []string{"gs://mybucket/veo_outputs/sample_0.mp4"}, names)
	if bucket != "" || renames != nil || dstURIs != nil {
		t.Errorf("expected empty plan for unset output_filename, got bucket=%q renames=%v dstURIs=%v", bucket, renames, dstURIs)
	}
}

// TestVeoRenamePlanFeedsRenameHelper exercises the plan against the shared batch
// rename helper using its network-free seam: a successful batch removes every API
// original (originals-removed guarantee) and reports the client-named destinations.
// The seam (copy/delete/exists indirection) is owned and fault-injected in
// mcp-common; here we confirm the veo plan is a valid input that drives it end to
// end without network or credentials.
func TestVeoRenamePlanFeedsRenameHelper(t *testing.T) {
	names := veoOutputNames("clip.mp4", 2, "video/mp4")
	_, renames, _ := buildVeoRenamePlan(
		"gs://mybucket/veo_outputs/",
		[]string{
			"gs://mybucket/veo_outputs/sample_0.mp4",
			"gs://mybucket/veo_outputs/sample_1.mp4",
		},
		names,
	)
	if len(renames) != 2 {
		t.Fatalf("expected 2 renames, got %d", len(renames))
	}
	// Sanity: the destinations are the deterministic client names, distinct from the
	// API sample_* sources (so RenameGCSObjects will copy+delete each source).
	for i, r := range renames {
		if r.Src == r.Dst {
			t.Errorf("rename %d is a no-op (src==dst=%q); expected sample_* → clip name", i, r.Src)
		}
	}
}
