// Package common provides shared utilities for the MCP Genmedia servers.

package common

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
)

// DownloadFromGCS downloads a file from a GCS bucket to a local path.
// It parses the GCS URI, creates a GCS client, and then reads the object's contents,
// writing them to a new local file. It also creates the destination directory if it doesn't exist.
func DownloadFromGCS(ctx context.Context, gcsURI, localDestPath string) error {
	bucketName, objectName, err := ParseGCSPath(gcsURI)
	if err != nil {
		return err
	}

	client, err := storage.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer client.Close()

	gcsOpCtx, cancel := context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()
	rc, err := client.Bucket(bucketName).Object(objectName).NewReader(gcsOpCtx)
	if err != nil {
		return fmt.Errorf("Object(%q).NewReader: %w", objectName, err)
	}
	defer rc.Close()

	destDir := filepath.Dir(localDestPath)
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return fmt.Errorf("os.MkdirAll for directory %s: %w", destDir, err)
	}

	f, err := os.Create(localDestPath)
	if err != nil {
		return fmt.Errorf("os.Create: %w", err)
	}
	defer f.Close()

	if _, err := io.Copy(f, rc); err != nil {
		return fmt.Errorf("io.Copy: %w", err)
	}
	log.Printf("Successfully downloaded %s to %s", gcsURI, localDestPath)
	return nil
}

func DownloadFromGCSAsBytes(ctx context.Context, gcsURI string) ([]byte, error) {
	bucketName, objectName, err := ParseGCSPath(gcsURI)
	if err != nil {
		return nil, err
	}

	client, err := storage.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("storage.NewClient: %w", err)
	}
	defer client.Close()

	var rc *storage.Reader
	var lastErr error
	// Retry loop to handle eventual consistency of GCS.
	for i := 0; i < 5; i++ {
		gcsOpCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
		rc, lastErr = client.Bucket(bucketName).Object(objectName).NewReader(gcsOpCtx)
		if lastErr == nil {
			cancel()
			break // Success
		}
		cancel()
		if !errors.Is(lastErr, storage.ErrObjectNotExist) {
			return nil, fmt.Errorf("Object(%q).NewReader: %w", objectName, lastErr) // Return non-transient errors immediately
		}
		log.Printf("Object %s not found, retrying in 3 seconds... (attempt %d/5)", gcsURI, i+1)
		time.Sleep(3 * time.Second)
	}

	if lastErr != nil {
		return nil, fmt.Errorf("Object(%q).NewReader timed out after retries: %w", objectName, lastErr)
	}
	defer rc.Close()

	data, err := io.ReadAll(rc)
	if err != nil {
		return nil, fmt.Errorf("io.ReadAll: %w", err)
	}
	return data, nil
}

// UploadToGCS uploads data to a specified GCS bucket and object.
// It takes the data as a byte slice and infers the content type from the object name's extension
// if it's not explicitly provided. This is useful for ensuring that GCS objects have the correct
// metadata, which is important for serving them correctly.
func UploadToGCS(ctx context.Context, bucketName, objectName, contentType string, data []byte) error {
	client, err := storage.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer client.Close()

	obj := client.Bucket(bucketName).Object(objectName)
	wc := obj.NewWriter(ctx)

	finalContentType := contentType
	if finalContentType == "" {
		ext := strings.ToLower(filepath.Ext(objectName))
		switch ext {
		case ".mp3":
			finalContentType = "audio/mpeg"
		case ".wav":
			finalContentType = "audio/wav"
		case ".mp4":
			finalContentType = "video/mp4"
		case ".mov":
			finalContentType = "video/quicktime"
		case ".mkv":
			finalContentType = "video/x-matroska"
		case ".webm":
			finalContentType = "video/webm"
		case ".png":
			finalContentType = "image/png"
		case ".jpg", ".jpeg":
			finalContentType = "image/jpeg"
		case ".gif":
			finalContentType = "image/gif"
		default:
			log.Printf("uploadToGCS: Could not infer ContentType for extension '%s' of object '%s'. Uploading without explicit ContentType.", ext, objectName)
		}
	}

	if finalContentType != "" {
		wc.ContentType = finalContentType
		log.Printf("uploadToGCS: Setting ContentType to '%s' for object '%s'", finalContentType, objectName)
	}

	if _, err := wc.Write(data); err != nil {
		wc.Close()
		return fmt.Errorf("Writer.Write: %w", err)
	}
	if err := wc.Close(); err != nil {
		return fmt.Errorf("Writer.Close: %w", err)
	}
	return nil
}

// ParseGCSPath extracts the bucket and object names from a GCS URI.
// It validates that the URI has the correct format (gs://bucket/object)
// and returns the two components. This is a helper function to make working
// with GCS paths easier and more reliable.
func ParseGCSPath(gcsURI string) (bucketName, objectName string, err error) {
	if !strings.HasPrefix(gcsURI, "gs://") {
		return "", "", fmt.Errorf("invalid GCS URI: must start with 'gs://', got %s", gcsURI)
	}
	trimmedURI := strings.TrimPrefix(gcsURI, "gs://")
	parts := strings.SplitN(trimmedURI, "/", 2)
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("invalid GCS URI format: %s. Expected gs://bucket/object", gcsURI)
	}
	return parts[0], parts[1], nil
}

// EnsureGCSPathPrefix ensures that a given path starts with "gs://".
// If the path does not start with "gs://", it prepends it.
// This is useful for normalizing GCS paths provided by users.
func EnsureGCSPathPrefix(path string) string {
	if !strings.HasPrefix(path, "gs://") {
		return "gs://" + path
	}
	return path
}
