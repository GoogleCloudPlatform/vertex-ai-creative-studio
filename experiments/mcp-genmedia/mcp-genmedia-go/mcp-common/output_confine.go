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

// Package common provides shared utilities for the MCP Genmedia servers.

package common

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// OutputRootEnvVar is the environment variable that configures the allowed base
// root for all caller-supplied output directories. When unset, the confinement
// root defaults to the process working directory (see ResolveConfinedOutputDir).
const OutputRootEnvVar = "MCP_OUTPUT_ROOT"

// OutputRoot returns the absolute, symlink-resolved confinement root for local
// output writes. It is read from the MCP_OUTPUT_ROOT environment variable and
// defaults to the process working directory when that variable is unset or empty.
//
// The returned root is the boundary every caller-supplied output directory is
// confined to by ResolveConfinedOutputDir. filepath.EvalSymlinks is applied when
// the root exists on disk so that a symlinked root cannot be used to escape
// confinement; if the root does not yet exist, the cleaned absolute path is used.
func OutputRoot() (string, error) {
	root := strings.TrimSpace(os.Getenv(OutputRootEnvVar))
	if root == "" {
		wd, err := os.Getwd()
		if err != nil {
			return "", fmt.Errorf("cannot determine working directory for output root: %w", err)
		}
		root = wd
	}

	abs, err := filepath.Abs(root)
	if err != nil {
		return "", fmt.Errorf("cannot resolve absolute output root for %q: %w", root, err)
	}

	// Resolve symlinks when the root exists so a symlinked base cannot be used to
	// escape confinement. If the root does not exist yet, fall back to the cleaned
	// absolute path (EvalSymlinks errors on non-existent paths).
	if resolved, err := filepath.EvalSymlinks(abs); err == nil {
		return resolved, nil
	}
	return abs, nil
}

// ResolveConfinedOutputDir validates a caller-supplied output directory against
// the configured confinement root (see OutputRoot) and returns the safe absolute
// directory the caller must actually write into.
//
// The caller-supplied value is UNTRUSTED (it arrives directly from an MCP tool
// argument such as output_local_dir / output_directory). This helper is the single
// place that closes the directory half of the path-traversal / arbitrary-file-write
// vulnerability (CWE-22); the filename half is handled separately by
// SanitizeBaseFilename / BuildOutputFilenames, which are intentionally left as-is.
//
// It enforces, in order:
//   - the caller path must NOT be absolute (an absolute path would otherwise win
//     the filepath.Join and escape the root entirely);
//   - the caller path must NOT contain any ".." path segment;
//   - after filepath.Clean and joining under the root, the result must remain a
//     descendant of the root (prefix containment verified via filepath.Rel).
//
// An empty (or whitespace-only) userDir resolves to the root itself; callers that
// treat "no directory" as "do not write locally" should guard on that before
// calling this helper (all current callers do).
//
// BACKWARD-COMPATIBILITY NOTE (for reviewers): this TIGHTENS behavior. Callers that
// previously passed an ABSOLUTE output directory, or one containing "..", now
// receive an error instead of writing there. Relative directories continue to
// resolve under the process working directory by default (MCP_OUTPUT_ROOT unset),
// so the common relative-path case is unchanged; deployments needing a different
// root can set MCP_OUTPUT_ROOT.
func ResolveConfinedOutputDir(userDir string) (string, error) {
	base, err := OutputRoot()
	if err != nil {
		return "", err
	}

	trimmed := strings.TrimSpace(userDir)
	if trimmed == "" {
		return base, nil
	}

	// Reject absolute caller paths outright: filepath.Join(base, "/abs") == "/abs",
	// which would escape the root entirely.
	if filepath.IsAbs(trimmed) {
		return "", fmt.Errorf("output directory %q must be relative to the output root %q", userDir, base)
	}

	// Normalize Windows separators so the ".." segment check is reliable on all
	// hosts, then reject any parent-directory traversal up front.
	normalized := strings.ReplaceAll(trimmed, "\\", "/")
	cleaned := filepath.Clean(normalized)
	if hasDotDotSegment(cleaned) {
		return "", fmt.Errorf("output directory %q must not contain a %q path segment", userDir, "..")
	}

	joined := filepath.Join(base, cleaned)

	// Defense in depth: verify prefix containment. Even after the checks above, a
	// relative path must resolve to a descendant of (or equal to) the base.
	rel, err := filepath.Rel(base, joined)
	if err != nil {
		return "", fmt.Errorf("output directory %q could not be resolved under the output root %q: %w", userDir, base, err)
	}
	if rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("output directory %q escapes the output root %q", userDir, base)
	}

	return joined, nil
}

// hasDotDotSegment reports whether the (already forward-slash-normalized) path
// contains a ".." component. It matches whole path segments, so legitimate names
// such as "foo..bar" are not rejected.
func hasDotDotSegment(p string) bool {
	for _, seg := range strings.Split(filepath.ToSlash(p), "/") {
		if seg == ".." {
			return true
		}
	}
	return false
}
