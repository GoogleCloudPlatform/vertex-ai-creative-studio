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

package common

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// TestResolveConfinedOutputDir is the prove-it test for the directory half of the
// CWE-22 path-traversal fix. Before the fix there was no confinement helper at all;
// after it, absolute caller directories and ".." traversal are rejected and valid
// relative directories resolve under the configured output root.
func TestResolveConfinedOutputDir(t *testing.T) {
	base := t.TempDir()
	t.Setenv(OutputRootEnvVar, base)
	// EvalSymlinks the base for comparison (macOS /var -> /private/var, etc.).
	resolvedBase, err := filepath.EvalSymlinks(base)
	if err != nil {
		resolvedBase = base
	}

	t.Run("rejects absolute path", func(t *testing.T) {
		abs := filepath.Join(t.TempDir(), "escape") // absolute, outside base
		if _, err := ResolveConfinedOutputDir(abs); err == nil {
			t.Fatalf("expected error for absolute output dir %q, got nil", abs)
		}
	})

	t.Run("rejects dot-dot traversal", func(t *testing.T) {
		for _, in := range []string{"..", "../escape", "a/../../escape", "sub/../../.."} {
			if _, err := ResolveConfinedOutputDir(in); err == nil {
				t.Fatalf("expected error for traversal output dir %q, got nil", in)
			}
		}
	})

	t.Run("accepts confined relative path", func(t *testing.T) {
		got, err := ResolveConfinedOutputDir("nested/out")
		if err != nil {
			t.Fatalf("unexpected error for confined relative dir: %v", err)
		}
		want := filepath.Join(resolvedBase, "nested", "out")
		if got != want {
			t.Fatalf("got %q, want %q", got, want)
		}
		// The resolved path must stay under the base.
		rel, relErr := filepath.Rel(resolvedBase, got)
		if relErr != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			t.Fatalf("resolved dir %q escapes base %q (rel=%q, err=%v)", got, resolvedBase, rel, relErr)
		}
	})

	t.Run("empty resolves to base", func(t *testing.T) {
		got, err := ResolveConfinedOutputDir("   ")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != resolvedBase {
			t.Fatalf("got %q, want base %q", got, resolvedBase)
		}
	})

	t.Run("rejects backslash traversal", func(t *testing.T) {
		if runtime.GOOS != "windows" {
			// On non-Windows hosts backslashes are normalized so the ".." segment
			// check still catches Windows-style traversal.
			if _, err := ResolveConfinedOutputDir("..\\escape"); err == nil {
				t.Fatalf("expected error for backslash traversal, got nil")
			}
		}
	})
}

// TestOutputRootDefaultsToWorkingDir confirms the root defaults to the process
// working directory when MCP_OUTPUT_ROOT is unset.
func TestOutputRootDefaultsToWorkingDir(t *testing.T) {
	t.Setenv(OutputRootEnvVar, "")
	os.Unsetenv(OutputRootEnvVar)

	root, err := OutputRoot()
	if err != nil {
		t.Fatalf("OutputRoot: %v", err)
	}
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd: %v", err)
	}
	if resolved, err := filepath.EvalSymlinks(wd); err == nil {
		wd = resolved
	}
	if root != wd {
		t.Fatalf("default output root = %q, want working dir %q", root, wd)
	}
}
