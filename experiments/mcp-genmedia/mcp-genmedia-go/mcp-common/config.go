// Package common provides shared utilities for the MCP Genmedia servers.

package common

import (
	"log"
	"os"
	"strings"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	ProjectID         string
	Location          string
	GenmediaBucket    string
	ApiEndpoint       string // New field
	AllowUnsafeModels bool
}

func LoadConfig(serviceName string) *Config {
	// Load .env file
	err := godotenv.Load()
	if err != nil {
		log.Println("Error loading .env file, using environment variables only")
	}

	var projectID string

	// Attempt to load server-specific override first
	if serviceName != "" {
		// e.g. "mcp-veo-go" -> "VEO"
		prefix := strings.ToUpper(strings.TrimSuffix(strings.TrimPrefix(serviceName, "mcp-"), "-go"))
		overrideKey := prefix + "_PROJECT_ID"
		projectID = os.Getenv(overrideKey)
		if projectID != "" {
			log.Printf("Using server-specific project override %s: %s", overrideKey, projectID)
		}
	}

	// Fallback to primary GOOGLE_CLOUD_PROJECT
	if projectID == "" {
		projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
	}

	// Fallback to legacy PROJECT_ID
	if projectID == "" {
		projectID = os.Getenv("PROJECT_ID")
		if projectID != "" {
			log.Printf("GOOGLE_CLOUD_PROJECT not set, using PROJECT_ID fallback: %s", projectID)
		}
	}

	if projectID == "" {
		log.Fatal("GOOGLE_CLOUD_PROJECT (or PROJECT_ID) environment variable not set. Please set the env variable, e.g. export GOOGLE_CLOUD_PROJECT=$(gcloud config get project)")
	}
	log.Printf("Project ID set to: %s", projectID)

	genmediaBucket := GetEnv("GENMEDIA_BUCKET", "")
	if genmediaBucket != "" {
		log.Printf("GENMEDIA_BUCKET set to: %s", genmediaBucket)
		genmediaBucket = strings.TrimPrefix(genmediaBucket, "gs://")
	} else {
		log.Println("GENMEDIA_BUCKET is not set.")
	}

	allowUnsafe := false
	if strings.ToLower(os.Getenv("ALLOW_UNSAFE_MODELS")) == "true" {
		allowUnsafe = true
		log.Printf("Warning: ALLOW_UNSAFE_MODELS is enabled. Strict model validation will be bypassed.")
	}

	return &Config{
		ProjectID:         projectID,
		Location:          GetEnv("LOCATION", "us-central1"),
		GenmediaBucket:    genmediaBucket,
		ApiEndpoint:       os.Getenv("VERTEX_API_ENDPOINT"), // Use os.Getenv for optional value
		AllowUnsafeModels: allowUnsafe,
	}
}

// GetGCSDownloadTimeout returns the timeout duration for GCS download operations.
// It reads from the GCS_DOWNLOAD_TIMEOUT environment variable, which accepts
// Go duration strings (e.g. "30s", "5m", "2m30s"). If the variable is not set
// or contains an invalid value, it defaults to 5 minutes.
func GetGCSDownloadTimeout() time.Duration {
	if v := os.Getenv("GCS_DOWNLOAD_TIMEOUT"); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
		log.Printf("Invalid GCS_DOWNLOAD_TIMEOUT value %q, using default of 5m", v)
	}
	return 5 * time.Minute
}

// GetEnv retrieves an environment variable by its key.
// If the variable is not set or is empty, it returns a fallback value.
// This function is useful for providing default values for optional configurations.
func GetEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists && value != "" {
		return value
	}
	if fallback != "" {
		log.Printf("Environment variable %s not set or empty, using fallback: %s", key, fallback)
	} else {
		log.Printf("Environment variable %s not set or empty, using empty fallback.", key)
	}
	return fallback
}
