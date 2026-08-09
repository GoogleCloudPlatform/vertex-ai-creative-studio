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
	"testing"
	"time"
)

func TestParseGCSBucketAndPrefix(t *testing.T) {
	tests := []struct {
		name       string
		uri        string
		wantBucket string
		wantPrefix string
	}{
		{"bucket only", "my-bucket", "my-bucket", ""},
		{"bucket only with gs scheme", "gs://my-bucket", "my-bucket", ""},
		{"bucket with trailing slash", "gs://my-bucket/", "my-bucket", ""},
		{"bucket and prefix", "gs://my-bucket/prefix", "my-bucket", "prefix/"},
		{"bucket and prefix trailing slash preserved", "gs://my-bucket/prefix/", "my-bucket", "prefix/"},
		{"bucket and nested prefix", "gs://my-bucket/a/b/c", "my-bucket", "a/b/c/"},
		{"bucket and nested prefix trailing slash", "gs://my-bucket/a/b/c/", "my-bucket", "a/b/c/"},
		{"no gs scheme with prefix", "my-bucket/spike_a", "my-bucket", "spike_a/"},
		{"leading slash stripped", "/my-bucket/prefix", "my-bucket", "prefix/"},
		{"gs scheme leading slash", "gs:///my-bucket/prefix", "my-bucket", "prefix/"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			gotBucket, gotPrefix := parseGCSBucketAndPrefix(tc.uri)
			if gotBucket != tc.wantBucket {
				t.Errorf("parseGCSBucketAndPrefix(%q) bucket = %q, want %q", tc.uri, gotBucket, tc.wantBucket)
			}
			if gotPrefix != tc.wantPrefix {
				t.Errorf("parseGCSBucketAndPrefix(%q) prefix = %q, want %q", tc.uri, gotPrefix, tc.wantPrefix)
			}
		})
	}
}

func TestExtForMimeType(t *testing.T) {
	tests := []struct {
		mimeType string
		want     string
	}{
		{"image/jpeg", ".jpg"},
		{"image/webp", ".webp"},
		{"image/gif", ".gif"},
		{"image/png", ".png"},
		{"application/octet-stream", ".png"}, // unknown -> default png
		{"", ".png"},                         // empty -> default png
		{"image/JPEG", ".png"},               // case-sensitive: not matched -> default png
	}
	for _, tc := range tests {
		t.Run(tc.mimeType, func(t *testing.T) {
			if got := extForMimeType(tc.mimeType); got != tc.want {
				t.Errorf("extForMimeType(%q) = %q, want %q", tc.mimeType, got, tc.want)
			}
		})
	}
}

func TestSignedURLExpiry(t *testing.T) {
	const def = 24 * time.Hour  // default validity
	const max = 168 * time.Hour // V4 ceiling
	tests := []struct {
		name   string
		env    string // value to set; "" means unset/empty
		setEnv bool
		want   time.Duration
	}{
		{"unset defaults to 24h", "", false, def},
		{"empty defaults to 24h", "", true, def},
		{"explicit 24h", "24", true, 24 * time.Hour},
		{"1h", "1", true, 1 * time.Hour},
		{"exactly 168 stays 168", "168", true, max},
		{"over 168 clamps to 168", "200", true, max},
		{"way over clamps to 168", "100000", true, max},
		{"zero disables", "0", true, 0},
		{"negative -> default", "-5", true, def},
		{"non-numeric -> default", "notanumber", true, def},
		{"float -> default (Atoi fails)", "24.5", true, def},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if tc.setEnv {
				t.Setenv("NANOBANANA_SIGNED_URL_EXPIRY_HOURS", tc.env)
			} else {
				// Ensure it is unset for this case.
				t.Setenv("NANOBANANA_SIGNED_URL_EXPIRY_HOURS", "")
				// t.Setenv cannot truly unset; empty string is treated as unset by signedURLExpiry.
			}
			if got := signedURLExpiry(); got != tc.want {
				t.Errorf("signedURLExpiry() with env=%q = %v, want %v", tc.env, got, tc.want)
			}
		})
	}
}
