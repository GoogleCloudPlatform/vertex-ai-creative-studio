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

package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
)

func inferMimeType(uri string) string {
	ext := strings.ToLower(filepath.Ext(uri))
	switch ext {
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".webp":
		return "image/webp"
	case ".mp4":
		return "video/mp4"
	case ".mov":
		return "video/quicktime"
	default:
		return "application/octet-stream"
	}
}

func readOrDownloadFile(ctx context.Context, pathOrURI string) ([]byte, string, error) {
	mimeType := inferMimeType(pathOrURI)
	if strings.HasPrefix(pathOrURI, "gs://") {
		client, err := storage.NewClient(ctx)
		if err != nil {
			return nil, "", fmt.Errorf("failed to create GCS client: %w", err)
		}
		defer client.Close()

		trimmed := strings.TrimPrefix(pathOrURI, "gs://")
		parts := strings.SplitN(trimmed, "/", 2)
		if len(parts) < 2 {
			return nil, "", fmt.Errorf("invalid GCS URI: %s", pathOrURI)
		}
		bucketName, objectName := parts[0], parts[1]

		rc, err := client.Bucket(bucketName).Object(objectName).NewReader(ctx)
		if err != nil {
			return nil, "", fmt.Errorf("failed to read from GCS %s: %w", pathOrURI, err)
		}
		defer rc.Close()

		data, err := io.ReadAll(rc)
		if err != nil {
			return nil, "", fmt.Errorf("failed to read data from GCS %s: %w", pathOrURI, err)
		}
		return data, mimeType, nil
	}

	data, err := os.ReadFile(pathOrURI)
	if err != nil {
		return nil, "", fmt.Errorf("failed to read local file %s: %w", pathOrURI, err)
	}
	return data, mimeType, nil
}

func saveVideoToGCS(ctx context.Context, gcsPrefix string, videoData []byte) (string, error) {
	client, err := storage.NewClient(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to create GCS client: %w", err)
	}
	defer client.Close()

	trimmed := strings.TrimPrefix(gcsPrefix, "gs://")
	parts := strings.SplitN(trimmed, "/", 2)
	bucketName := parts[0]
	prefix := ""
	if len(parts) > 1 {
		prefix = strings.TrimSuffix(parts[1], "/")
	}

	filename := fmt.Sprintf("omni_%d.mp4", time.Now().UnixNano())
	objectName := filename
	if prefix != "" {
		objectName = prefix + "/" + filename
	}

	wc := client.Bucket(bucketName).Object(objectName).NewWriter(ctx)
	wc.ContentType = "video/mp4"
	if _, err := wc.Write(videoData); err != nil {
		wc.Close()
		return "", fmt.Errorf("failed to write video to GCS: %w", err)
	}
	if err := wc.Close(); err != nil {
		return "", fmt.Errorf("failed to close GCS writer: %w", err)
	}

	return fmt.Sprintf("gs://%s/%s", bucketName, objectName), nil
}

func saveVideoLocally(outputDir string, videoData []byte) (string, error) {
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create output directory %s: %w", outputDir, err)
	}
	filename := fmt.Sprintf("omni_%d.mp4", time.Now().UnixNano())
	fullPath := filepath.Join(outputDir, filename)
	if err := os.WriteFile(fullPath, videoData, 0644); err != nil {
		return "", fmt.Errorf("failed to write file %s: %w", fullPath, err)
	}
	log.Printf("Saved video to local file: %s", fullPath)
	return fullPath, nil
}
