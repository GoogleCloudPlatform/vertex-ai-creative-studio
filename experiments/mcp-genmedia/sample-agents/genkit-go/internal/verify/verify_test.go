// Copyright 2026 Google LLC
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

package verify

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

// TestIsGCSNotFound is the load-bearing distinction of the shared success gate:
// a non-zero `gcloud storage ls` exit whose diagnostic is the "nothing is there"
// signature is a legitimate empty destination (Exists=false, nil error), while
// any other non-zero exit (auth/ADC expiry, permission denied, network) is a
// real failure that must be surfaced so a caller never misreads "listing failed"
// as "the generation produced nothing." This table pins both sides.
func TestIsGCSNotFound(t *testing.T) {
	cases := []struct {
		name   string
		output string
		want   bool
	}{
		// --- not-found signatures: destination is empty/absent ---
		{
			name:   "current gcloud phrasing",
			output: "ERROR: (gcloud.storage.ls) One or more URLs matched no objects.",
			want:   true,
		},
		{
			name:   "older tooling phrasing",
			output: "CommandException: One or more URLs matched no objects.",
			want:   true,
		},
		{
			name:   "no url ... matched split phrasing",
			output: "ERROR: (gcloud.storage.ls) The following URL did not match any objects: gs://b/p",
			want:   false, // "did not match any objects" is not our signature; be conservative
		},
		{
			name:   "no URL matched wording",
			output: "ERROR: No URL matched the provided prefix.",
			want:   true,
		},
		{
			name:   "case insensitivity",
			output: "one or more urls MATCHED NO OBJECTS.",
			want:   true,
		},

		// --- real errors: must NOT be swallowed as not-found ---
		{
			name:   "auth / ADC expiry",
			output: "ERROR: (gcloud.storage.ls) Your credentials are invalid. Reauthenticate with `gcloud auth login`.",
			want:   false,
		},
		{
			name:   "permission denied",
			output: "ERROR: (gcloud.storage.ls) HTTPError 403: does not have storage.objects.list access to the bucket.",
			want:   false,
		},
		{
			name:   "bucket does not exist (403/404 style, not our signature)",
			output: "ERROR: (gcloud.storage.ls) HTTPError 404: The specified bucket does not exist.",
			want:   false,
		},
		{
			name:   "network failure",
			output: "ERROR: (gcloud.storage.ls) Could not reach the server. Check your network connection.",
			want:   false,
		},
		{
			name:   "empty output",
			output: "",
			want:   false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := isGCSNotFound([]byte(tc.output)); got != tc.want {
				t.Errorf("isGCSNotFound(%q) = %v, want %v", tc.output, got, tc.want)
			}
		})
	}
}

// TestParseGCSListing pins the success-path parsing of `gcloud storage ls`
// stdout: non-empty trimmed lines become entries, blank lines and surrounding
// whitespace are dropped, and empty output yields no entries.
func TestParseGCSListing(t *testing.T) {
	cases := []struct {
		name   string
		stdout string
		want   []string
	}{
		{
			name:   "single object",
			stdout: "gs://b/p/img.png\n",
			want:   []string{"gs://b/p/img.png"},
		},
		{
			name:   "multiple objects and a subfolder prefix",
			stdout: "gs://b/p/a.png\ngs://b/p/vid/\ngs://b/p/b.png\n",
			want:   []string{"gs://b/p/a.png", "gs://b/p/vid/", "gs://b/p/b.png"},
		},
		{
			name:   "blank lines and stray whitespace are dropped",
			stdout: "\n  gs://b/p/a.png  \n\n\tgs://b/p/b.png\n \n",
			want:   []string{"gs://b/p/a.png", "gs://b/p/b.png"},
		},
		{
			name:   "empty output yields no entries",
			stdout: "",
			want:   nil,
		},
		{
			name:   "whitespace-only output yields no entries",
			stdout: "   \n\t\n",
			want:   nil,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := parseGCSListing([]byte(tc.stdout))
			if !reflect.DeepEqual(got, tc.want) {
				t.Errorf("parseGCSListing(%q) = %#v, want %#v", tc.stdout, got, tc.want)
			}
		})
	}
}

// TestVerifyRecursiveLocal pins the recursive local walk that Tier 2 relies on:
// it returns every file at any depth (never directories), reports a missing path
// as not-found with a nil error, and a single file as itself.
func TestVerifyRecursiveLocal(t *testing.T) {
	ctx := context.Background()

	t.Run("nested files are returned as leaves", func(t *testing.T) {
		root := t.TempDir()
		want := []string{
			filepath.Join(root, "a.mp3"),
			filepath.Join(root, "sub", "b.mp4"),
			filepath.Join(root, "sub", "deep", "c.wav"),
		}
		for _, f := range want {
			if err := os.MkdirAll(filepath.Dir(f), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(f, []byte("x"), 0o644); err != nil {
				t.Fatal(err)
			}
		}
		res, err := VerifyRecursive(ctx, root)
		if err != nil {
			t.Fatalf("VerifyRecursive(%q) error: %v", root, err)
		}
		if !res.Exists {
			t.Fatalf("VerifyRecursive(%q).Exists = false, want true", root)
		}
		got := append([]string(nil), res.Entries...)
		sort.Strings(got)
		sort.Strings(want)
		if !reflect.DeepEqual(got, want) {
			t.Errorf("VerifyRecursive(%q).Entries = %#v, want %#v", root, got, want)
		}
	})

	t.Run("missing path is not-found with nil error", func(t *testing.T) {
		missing := filepath.Join(t.TempDir(), "does-not-exist")
		res, err := VerifyRecursive(ctx, missing)
		if err != nil {
			t.Fatalf("VerifyRecursive(%q) error: %v", missing, err)
		}
		if res.Exists || len(res.Entries) != 0 {
			t.Errorf("VerifyRecursive(%q) = %+v, want empty not-found", missing, res)
		}
	})

	t.Run("single file returns itself", func(t *testing.T) {
		f := filepath.Join(t.TempDir(), "only.mp4")
		if err := os.WriteFile(f, []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
		res, err := VerifyRecursive(ctx, f)
		if err != nil {
			t.Fatalf("VerifyRecursive(%q) error: %v", f, err)
		}
		if !res.Exists || !reflect.DeepEqual(res.Entries, []string{f}) {
			t.Errorf("VerifyRecursive(%q) = %+v, want single entry %q", f, res, f)
		}
	})
}
