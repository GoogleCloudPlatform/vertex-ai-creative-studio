package common

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestParseGCSPath(t *testing.T) {
	testCases := []struct {
		gcsURI       string
		expectedBucket string
		expectedObject string
		expectError  bool
	}{
		{"gs://bucket/object", "bucket", "object", false},
		{"gs://bucket/object/with/slashes", "bucket", "object/with/slashes", false},
		{"invalid-uri", "", "", true},
		{"gs://", "", "", true},
		{"gs://bucket", "", "", true},
	}

	for _, tc := range testCases {
		t.Run(tc.gcsURI, func(t *testing.T) {
			bucket, object, err := ParseGCSPath(tc.gcsURI)
			if (err != nil) != tc.expectError {
				t.Errorf("expected error: %v, but got: %v", tc.expectError, err)
			}
			if bucket != tc.expectedBucket {
				t.Errorf("expected bucket '%s', but got '%s'", tc.expectedBucket, bucket)
			}
			if object != tc.expectedObject {
				t.Errorf("expected object '%s', but got '%s'", tc.expectedObject, object)
			}
		})
	}
}

func TestDownloadFromGCS(t *testing.T) {
	// This is a basic integration test that requires a running GCS emulator.
	// You can start one with: gcloud beta emulators gcs start --project=test-project
	if os.Getenv("GCS_EMULATOR_HOST") == "" {
		t.Skip("Skipping GCS integration tests, GCS_EMULATOR_HOST not set")
	}

	// Create a temporary file to upload
	tempFile, err := os.CreateTemp("", "gcs_test_*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.Remove(tempFile.Name())

	// Write some content to the file
	content := []byte("hello world")
	if _, err := tempFile.Write(content); err != nil {
		t.Fatal(err)
	}
	tempFile.Close()

	// Upload the file to the emulator
	bucket := "test-bucket"
	object := "test-object"
	gcsURI := fmt.Sprintf("gs://%s/%s", bucket, object)

	ctx := context.Background()
	if err := UploadToGCS(ctx, bucket, object, "text/plain", content); err != nil {
		t.Fatalf("failed to upload to GCS: %v", err)
	}

	// Download the file
	tempDir, err := os.MkdirTemp("", "gcs_test_download_*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempDir)

	localPath := filepath.Join(tempDir, "downloaded_file")
	if err := DownloadFromGCS(ctx, gcsURI, localPath); err != nil {
		t.Fatalf("failed to download from GCS: %v", err)
	}

	// Verify the content
	downloadedContent, err := os.ReadFile(localPath)
	if err != nil {
		t.Fatal(err)
	}

	if string(downloadedContent) != string(content) {
		t.Errorf("expected downloaded content to be '%s', but got '%s'", string(content), string(downloadedContent))
	}
}
