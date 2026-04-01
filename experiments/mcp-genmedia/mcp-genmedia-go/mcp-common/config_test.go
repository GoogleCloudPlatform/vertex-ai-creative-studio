package common

import (
	"os"
	"testing"
	"time"
)

func TestLoadConfig(t *testing.T) {
	t.Run("with all env vars set (using GOOGLE_CLOUD_PROJECT)", func(t *testing.T) {
		_ = os.Setenv("GOOGLE_CLOUD_PROJECT", "test-project")
		_ = os.Unsetenv("PROJECT_ID")
		_ = os.Setenv("LOCATION", "test-location")
		_ = os.Setenv("GENMEDIA_BUCKET", "test-bucket")

		cfg := LoadConfig("test-server")

		if cfg.ProjectID != "test-project" {
			t.Errorf("expected ProjectID to be 'test-project', but got '%s'", cfg.ProjectID)
		}
		if cfg.Location != "test-location" {
			t.Errorf("expected Location to be 'test-location', but got '%s'", cfg.Location)
		}
		if cfg.GenmediaBucket != "test-bucket" {
			t.Errorf("expected GenmediaBucket to be 'test-bucket', but got '%s'", cfg.GenmediaBucket)
		}

	})

	t.Run("with PROJECT_ID fallback", func(t *testing.T) {
		_ = os.Unsetenv("GOOGLE_CLOUD_PROJECT")
		_ = os.Setenv("PROJECT_ID", "test-project-fallback")
		_ = os.Setenv("LOCATION", "test-location")
		_ = os.Setenv("GENMEDIA_BUCKET", "test-bucket")

		cfg := LoadConfig("test-server")

		if cfg.ProjectID != "test-project-fallback" {
			t.Errorf("expected ProjectID to be 'test-project-fallback', but got '%s'", cfg.ProjectID)
		}
	})

	t.Run("with server specific project override", func(t *testing.T) {
		_ = os.Setenv("VEO_PROJECT_ID", "test-veo-project")
		_ = os.Setenv("GOOGLE_CLOUD_PROJECT", "test-global-project")

		cfg := LoadConfig("mcp-veo-go")

		if cfg.ProjectID != "test-veo-project" {
			t.Errorf("expected ProjectID to be 'test-veo-project', but got '%s'", cfg.ProjectID)
		}
		_ = os.Unsetenv("VEO_PROJECT_ID")
	})

	t.Run("with server specific location override", func(t *testing.T) {
		_ = os.Setenv("GOOGLE_CLOUD_PROJECT", "test-project")
		_ = os.Setenv("VEO_LOCATION", "test-veo-location")
		_ = os.Setenv("LOCATION", "test-global-location")

		cfg := LoadConfig("mcp-veo-go")

		if cfg.Location != "test-veo-location" {
			t.Errorf("expected Location to be 'test-veo-location', but got '%s'", cfg.Location)
		}
		_ = os.Unsetenv("VEO_LOCATION")
		_ = os.Unsetenv("LOCATION")
	})

	t.Run("with ALLOW_UNSAFE_MODELS enabled", func(t *testing.T) {
		_ = os.Setenv("GOOGLE_CLOUD_PROJECT", "test-project")
		_ = os.Setenv("ALLOW_UNSAFE_MODELS", "TrUe")

		cfg := LoadConfig("test-server")

		if !cfg.AllowUnsafeModels {
			t.Errorf("expected AllowUnsafeModels to be true")
		}
		_ = os.Unsetenv("ALLOW_UNSAFE_MODELS")
	})

	t.Run("with some env vars missing", func(t *testing.T) {
		_ = os.Unsetenv("LOCATION")
		_ = os.Unsetenv("GENMEDIA_BUCKET")

		cfg := LoadConfig("test-server")

		if cfg.Location != "us-central1" {
			t.Errorf("expected Location to be 'us-central1', but got '%s'", cfg.Location)
		}
		if cfg.GenmediaBucket != "" {
			t.Errorf("expected GenmediaBucket to be '', but got '%s'", cfg.GenmediaBucket)
		}

	})
}

func TestGetGCSDownloadTimeout(t *testing.T) {
	// Save original env var to restore it later
	originalValue, wasSet := os.LookupEnv("GCS_DOWNLOAD_TIMEOUT")
	defer func() {
		if wasSet {
			os.Setenv("GCS_DOWNLOAD_TIMEOUT", originalValue)
		} else {
			os.Unsetenv("GCS_DOWNLOAD_TIMEOUT")
		}
	}()

	tests := []struct {
		name     string
		envValue string
		expected time.Duration
	}{
		{"default_fallback", "", 5 * time.Minute},
		{"valid_seconds", "30s", 30 * time.Second},
		{"valid_minutes", "2m", 2 * time.Minute},
		{"valid_mixed", "2m30s", 2*time.Minute + 30*time.Second},
		{"invalid_fallback", "invalid_string", 5 * time.Minute},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.envValue == "" {
				os.Unsetenv("GCS_DOWNLOAD_TIMEOUT")
			} else {
				os.Setenv("GCS_DOWNLOAD_TIMEOUT", tt.envValue)
			}
			got := GetGCSDownloadTimeout()
			if got != tt.expected {
				t.Errorf("GetGCSDownloadTimeout() = %v, want %v (env: %q)", got, tt.expected, tt.envValue)
			}
		})
	}
}
