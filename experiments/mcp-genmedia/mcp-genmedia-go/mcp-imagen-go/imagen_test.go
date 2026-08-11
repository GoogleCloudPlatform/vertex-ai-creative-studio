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

// TestImagenOutputNames locks the output_filename → per-image name mapping,
// including the num_images=4 case, extension forcing, and the unset back-compat
// path (nil → handler keeps its default naming scheme).
func TestImagenOutputNames(t *testing.T) {
	tests := []struct {
		name       string
		outputName string
		count      int
		mimeType   string
		want       []string
	}{
		{"unset returns nil (back-compat default naming)", "", 4, "image/png", nil},
		{"whitespace-only returns nil", "   ", 2, "image/png", nil},
		{"single image, no suffix", "hero.png", 1, "image/png", []string{"hero.png"}},
		{"four images, 1-based suffix", "hero.png", 4, "image/png", []string{"hero_1.png", "hero_2.png", "hero_3.png", "hero_4.png"}},
		{"extension forced to true MIME", "hero.jpeg", 1, "image/png", []string{"hero.png"}},
		{"jpeg output", "shot", 2, "image/jpeg", []string{"shot_1.jpg", "shot_2.jpg"}},
		{"path traversal sanitized", "../../etc/passwd", 1, "image/png", []string{"passwd.png"}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := imagenOutputNames(tc.outputName, tc.count, tc.mimeType)
			if !reflect.DeepEqual(got, tc.want) {
				t.Errorf("imagenOutputNames(%q, %d, %q) = %v, want %v", tc.outputName, tc.count, tc.mimeType, got, tc.want)
			}
		})
	}
}

// TestBuildImagenRenamePlan verifies the Path-C plan that maps the API-written
// sample_k objects to the client-desired names: num_images=4 + gcs +
// output_filename="hero.png" ⇒ sample_0..3 → hero_1..4.png under the same prefix,
// same bucket, with correct gs:// URIs. Feeding the returned renames to
// common.RenameGCSObjects (unit-tested in mcp-common) removes the originals.
func TestBuildImagenRenamePlan(t *testing.T) {
	gcsOutputURI := "gs://mybucket/imagen_outputs/"
	srcURIs := []string{
		"gs://mybucket/imagen_outputs/sample_0.png",
		"gs://mybucket/imagen_outputs/sample_1.png",
		"gs://mybucket/imagen_outputs/sample_2.png",
		"gs://mybucket/imagen_outputs/sample_3.png",
	}
	names := imagenOutputNames("hero.png", 4, "image/png")

	bucket, renames, planSrcURIs, dstURIs := buildImagenRenamePlan(gcsOutputURI, srcURIs, names)

	if bucket != "mybucket" {
		t.Errorf("bucket = %q, want mybucket", bucket)
	}
	// planSrcURIs is aligned 1:1 with renames/dstURIs and echoes the source URIs so
	// the caller can pair renamed URIs back by identity, not slice position.
	if !reflect.DeepEqual(planSrcURIs, srcURIs) {
		t.Errorf("planSrcURIs = %v, want %v", planSrcURIs, srcURIs)
	}
	wantRenames := []common.Rename{
		{Src: "imagen_outputs/sample_0.png", Dst: "imagen_outputs/hero_1.png"},
		{Src: "imagen_outputs/sample_1.png", Dst: "imagen_outputs/hero_2.png"},
		{Src: "imagen_outputs/sample_2.png", Dst: "imagen_outputs/hero_3.png"},
		{Src: "imagen_outputs/sample_3.png", Dst: "imagen_outputs/hero_4.png"},
	}
	if !reflect.DeepEqual(renames, wantRenames) {
		t.Errorf("renames = %v, want %v", renames, wantRenames)
	}
	wantURIs := []string{
		"gs://mybucket/imagen_outputs/hero_1.png",
		"gs://mybucket/imagen_outputs/hero_2.png",
		"gs://mybucket/imagen_outputs/hero_3.png",
		"gs://mybucket/imagen_outputs/hero_4.png",
	}
	if !reflect.DeepEqual(dstURIs, wantURIs) {
		t.Errorf("dstURIs = %v, want %v", dstURIs, wantURIs)
	}
}

// TestBuildImagenRenamePlanSingle: n==1 ⇒ no suffix (hero.png), bucket-root prefix.
func TestBuildImagenRenamePlanSingle(t *testing.T) {
	names := imagenOutputNames("hero.png", 1, "image/png")
	bucket, renames, _, dstURIs := buildImagenRenamePlan("gs://mybucket/", []string{"gs://mybucket/sample_0.png"}, names)
	if bucket != "mybucket" {
		t.Errorf("bucket = %q, want mybucket", bucket)
	}
	if len(renames) != 1 || renames[0] != (common.Rename{Src: "sample_0.png", Dst: "hero.png"}) {
		t.Errorf("renames = %v, want [{sample_0.png hero.png}]", renames)
	}
	if len(dstURIs) != 1 || dstURIs[0] != "gs://mybucket/hero.png" {
		t.Errorf("dstURIs = %v, want [gs://mybucket/hero.png]", dstURIs)
	}
}

// TestBuildImagenRenamePlanBackCompat: no output_filename ⇒ nil plan, so the
// handler leaves the API-written object names untouched (byte-for-byte legacy).
func TestBuildImagenRenamePlanBackCompat(t *testing.T) {
	names := imagenOutputNames("", 4, "image/png") // nil
	bucket, renames, planSrcURIs, dstURIs := buildImagenRenamePlan("gs://mybucket/imagen_outputs/", []string{"gs://mybucket/imagen_outputs/sample_0.png"}, names)
	if bucket != "" || renames != nil || planSrcURIs != nil || dstURIs != nil {
		t.Errorf("expected empty plan for unset output_filename, got bucket=%q renames=%v planSrcURIs=%v dstURIs=%v", bucket, renames, planSrcURIs, dstURIs)
	}
}

// TestApplyRenamedURIsIdentityPairing proves the URI writeback pairs each rename
// result to its artifact by identity (source URI), not by slice position (nit
// p3b-1). It constructs a reordered/partial rename result set over a src list with a
// middle unparseable URI (skipped by the plan) and asserts the renamed URIs land on
// the correct artifacts — a positional writeback would drift them.
func TestApplyRenamedURIsIdentityPairing(t *testing.T) {
	// The middle artifact's URI is unparseable, so the plan skips it. names[i]
	// belongs to artifact i, so artifact 2 must be renamed to hero_3.png.
	gcsSavedURIs := []string{
		"gs://mybucket/imagen_outputs/sample_0.png",
		"not-a-gcs-uri", // unparseable → skipped by the plan
		"gs://mybucket/imagen_outputs/sample_2.png",
	}
	names := imagenOutputNames("hero.png", 3, "image/png") // hero_1.png, hero_2.png, hero_3.png

	_, renames, planSrcURIs, dstURIs := buildImagenRenamePlan("gs://mybucket/imagen_outputs/", gcsSavedURIs, names)
	if len(renames) != 2 {
		t.Fatalf("expected 2 renames (middle skipped), got %d", len(renames))
	}

	t.Run("full success renames both parseable artifacts to the right names", func(t *testing.T) {
		saved := append([]string(nil), gcsSavedURIs...)
		applyRenamedURIs(saved, planSrcURIs, dstURIs, len(renames)) // renamedCount = 2
		want := []string{
			"gs://mybucket/imagen_outputs/hero_1.png",
			"not-a-gcs-uri", // untouched
			"gs://mybucket/imagen_outputs/hero_3.png",
		}
		if !reflect.DeepEqual(saved, want) {
			t.Errorf("identity writeback = %v, want %v", saved, want)
		}
	})

	t.Run("partial failure only writes back the renamed prefix, still by identity", func(t *testing.T) {
		saved := append([]string(nil), gcsSavedURIs...)
		applyRenamedURIs(saved, planSrcURIs, dstURIs, 1) // only the first rename succeeded
		want := []string{
			"gs://mybucket/imagen_outputs/hero_1.png",
			"not-a-gcs-uri",
			"gs://mybucket/imagen_outputs/sample_2.png", // NOT drifted onto by hero_3
		}
		if !reflect.DeepEqual(saved, want) {
			t.Errorf("partial identity writeback = %v, want %v", saved, want)
		}
	})
}
