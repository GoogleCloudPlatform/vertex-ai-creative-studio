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
)

// TestIntegrationImagenRenameNamingEndToEnd is an end-to-end (Path-C:
// API-controls-GCS) integration test for the imagen naming pipeline. imagen lets
// Vertex write and name the objects (sample_k) under the output prefix, then
// renames them to the client-desired names. This test composes the whole
// server-side chain the handler runs —
//
//	imagenOutputNames → buildImagenRenamePlan → (RenameGCSObjects) → applyRenamedURIs
//
// — and asserts the gs:// URIs handed back to the client are the renamed ones. The
// GCS copy/delete step itself is simulated here by reporting how many plan entries
// "renamed" (RenameGCSObjects returns a prefix of the plan, truncated at the first
// failure); the real copy-rename against a bucket is exercised network-free via
// the fakeGCS seam and, gated behind GENMEDIA_BUCKET, live in mcp-common. This
// keeps the test network-free while covering deterministic suffixing, extension
// forcing, single-image (no suffix), partial-failure writeback, and the unset
// back-compat path.
func TestIntegrationImagenRenameNamingEndToEnd(t *testing.T) {
	const gcsOutputURI = "gs://mybucket/imagen_outputs/"

	// srcURIs are the API-written objects (Vertex names them sample_k).
	srcURIs := func(n int) []string {
		out := make([]string, n)
		for i := 0; i < n; i++ {
			out[i] = "gs://mybucket/imagen_outputs/sample_" + itoa(i) + ".png"
		}
		return out
	}

	// run drives the full chain and returns the gs:// URIs as the client would see
	// them. renamedCount simulates how many leading plan entries RenameGCSObjects
	// reported as renamed (== len(plan) on full success).
	run := func(outputFilename string, count int, renamedCount int) []string {
		saved := srcURIs(count)
		names := imagenOutputNames(outputFilename, count, "image/png")
		_, renames, planSrcURIs, dstURIs := buildImagenRenamePlan(gcsOutputURI, saved, names)
		if renamedCount < 0 {
			renamedCount = len(renames) // full success
		}
		applyRenamedURIs(saved, planSrcURIs, dstURIs, renamedCount)
		return saved
	}

	t.Run("multiple images -> 1-based suffix, extension forced, writeback by identity", func(t *testing.T) {
		got := run("hero.jpg", 3, -1) // wrong ext forced to .png; full success
		want := []string{
			"gs://mybucket/imagen_outputs/hero_1.png",
			"gs://mybucket/imagen_outputs/hero_2.png",
			"gs://mybucket/imagen_outputs/hero_3.png",
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("client URIs = %v, want %v", got, want)
		}
	})

	t.Run("single image -> no suffix", func(t *testing.T) {
		got := run("hero", 1, -1)
		want := []string{"gs://mybucket/imagen_outputs/hero.png"}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("client URIs = %v, want %v", got, want)
		}
	})

	t.Run("partial rename failure -> only renamed URIs rewritten, rest keep API names", func(t *testing.T) {
		// Only the first of three copies succeeded before RenameGCSObjects failed.
		got := run("hero", 3, 1)
		want := []string{
			"gs://mybucket/imagen_outputs/hero_1.png",
			"gs://mybucket/imagen_outputs/sample_1.png",
			"gs://mybucket/imagen_outputs/sample_2.png",
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("client URIs = %v, want %v", got, want)
		}
	})

	t.Run("unset output_filename -> no rename plan, API names kept (back-compat)", func(t *testing.T) {
		got := run("", 2, -1)
		want := []string{
			"gs://mybucket/imagen_outputs/sample_0.png",
			"gs://mybucket/imagen_outputs/sample_1.png",
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("client URIs = %v, want %v (unset must keep default API names)", got, want)
		}
	})
}

// itoa is a tiny dependency-free int->string for building sample_k URIs (k < 10
// in these tests).
func itoa(i int) string {
	return string(rune('0' + i))
}
