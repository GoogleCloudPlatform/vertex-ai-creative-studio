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

// Package verify implements the genmedia "verify-by-listing" workaround, shared
// across every tier of the Genkit Go genmedia series.
//
// The genmedia GCS-writing tools (nanobanana/gemini image, veo, lyria, omni)
// return a resource_link content item pointing at a gs:// URI, NOT the generated
// bytes. A resource_link is therefore NOT proof of success. The only honest
// confirmation is to LIST the destination: `gcloud storage ls` for a gs:// URI,
// or a filesystem stat for local output. Every tier calls this instead of
// trusting the raw tool result.
package verify

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Result reports what listing the destination found.
type Result struct {
	// Destination is the gs:// URI/prefix or local path that was checked.
	Destination string
	// Exists is true if at least one object/file was found at Destination.
	Exists bool
	// Entries are the listed object URIs or file paths (best effort).
	Entries []string
}

// String renders a human-readable one-line summary.
func (r Result) String() string {
	if !r.Exists {
		return fmt.Sprintf("NOT FOUND at %s", r.Destination)
	}
	return fmt.Sprintf("found %d entr%s at %s", len(r.Entries),
		plural(len(r.Entries)), r.Destination)
}

func plural(n int) string {
	if n == 1 {
		return "y"
	}
	return "ies"
}

// IsGCS reports whether dest is a Google Cloud Storage URI.
func IsGCS(dest string) bool {
	return strings.HasPrefix(dest, "gs://")
}

// Verify confirms an artifact exists at dest by listing/statting it — never by
// trusting a tool result. dest is a gs:// URI/prefix (verified with
// `gcloud storage ls`) or a local path (verified with the filesystem).
//
// A non-nil error means the check could not be performed (e.g. gcloud missing,
// listing command failed); Result.Exists == false with a nil error means the
// check ran and the destination is empty/absent.
func Verify(ctx context.Context, dest string) (Result, error) {
	if IsGCS(dest) {
		return verifyGCS(ctx, dest)
	}
	return verifyLocal(dest)
}

// VerifyAll runs Verify for each destination and returns the results in order.
// It does not short-circuit: every destination is checked so a tier can report
// each GCS-writing step. The returned error is the first check that could not be
// performed, if any.
func VerifyAll(ctx context.Context, dests ...string) ([]Result, error) {
	results := make([]Result, 0, len(dests))
	var firstErr error
	for _, d := range dests {
		r, err := Verify(ctx, d)
		if err != nil && firstErr == nil {
			firstErr = err
		}
		results = append(results, r)
	}
	return results, firstErr
}

// verifyGCS lists a gs:// destination with `gcloud storage ls`.
func verifyGCS(ctx context.Context, uri string) (Result, error) {
	res := Result{Destination: uri}

	if _, err := exec.LookPath("gcloud"); err != nil {
		return res, fmt.Errorf("verify: gcloud not found on PATH (needed to list %s): %w", uri, err)
	}

	cmd := exec.CommandContext(ctx, "gcloud", "storage", "ls", uri)
	// Keep stdout (the object listing) and stderr (diagnostics) in separate
	// buffers: on success we parse stdout for the found objects without stderr
	// noise polluting the listing; on failure we inspect stderr for gcloud's
	// not-found signature to tell "nothing there" apart from a real failure
	// (auth/ADC expiry, permission denied, network).
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) && isGCSNotFound(stderr.Bytes()) {
			// A non-zero exit whose diagnostic is gcloud's "no objects matched"
			// signature is a legitimate "not found", not a tooling failure.
			return res, nil
		}
		// Anything else (auth/permission/network, or a non-exec error) is a real
		// failure: surface it so the caller does not misread it as "no output".
		return res, fmt.Errorf("verify: gcloud storage ls %s failed: %w: %s",
			uri, err, strings.TrimSpace(stderr.String()))
	}

	res.Entries = parseGCSListing(stdout.Bytes())
	res.Exists = len(res.Entries) > 0
	return res, nil
}

// parseGCSListing turns `gcloud storage ls` stdout into the non-empty, trimmed
// object/prefix lines it reported. Factored out as a pure function so the
// success-path parsing is unit-testable without shelling to gcloud.
func parseGCSListing(stdout []byte) []string {
	var entries []string
	for _, line := range strings.Split(strings.TrimSpace(string(stdout)), "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			entries = append(entries, line)
		}
	}
	return entries
}

// isGCSNotFound reports whether gcloud's diagnostic output is its
// "the prefix/URL matched nothing" signature, as opposed to an auth, permission,
// or network failure. `gcloud storage ls` on a missing prefix exits non-zero
// with "One or more URLs matched no objects." (older tooling: "matched no objects").
func isGCSNotFound(output []byte) bool {
	msg := strings.ToLower(string(output))
	return strings.Contains(msg, "matched no objects") ||
		(strings.Contains(msg, "no url") && strings.Contains(msg, "matched"))
}

// verifyLocal stats a local path. If it is a directory, its entries are listed.
func verifyLocal(path string) (Result, error) {
	res := Result{Destination: path}

	info, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return res, nil
		}
		return res, fmt.Errorf("verify: stat %s failed: %w", path, err)
	}

	if info.IsDir() {
		entries, err := os.ReadDir(path)
		if err != nil {
			return res, fmt.Errorf("verify: read dir %s failed: %w", path, err)
		}
		for _, e := range entries {
			res.Entries = append(res.Entries, filepath.Join(path, e.Name()))
		}
		res.Exists = len(res.Entries) > 0
		return res, nil
	}

	res.Entries = []string{path}
	res.Exists = true
	return res, nil
}
