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

package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"path/filepath"
	"strings"

	"cloud.google.com/go/storage"
	"github.com/google/uuid"
)

type UploadResponse struct {
	URI       string `json:"uri"`       // gs:// URI
	SignedURI string `json:"signedUri"` // HTTPS URL for preview
}

const MaxUploadSize = 50 << 20 // 50 MB

func (h *Handler) HandleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// limit size
	r.Body = http.MaxBytesReader(w, r.Body, MaxUploadSize)
	if err := r.ParseMultipartForm(MaxUploadSize); err != nil {
		http.Error(w, "File too large", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Validate content type
	contentType := header.Header.Get("Content-Type")
	if strings.HasPrefix(contentType, "video/") && contentType != "video/mp4" {
		http.Error(w, "Only video/mp4 is supported", http.StatusBadRequest)
		return
	}
	if !strings.HasPrefix(contentType, "image/") && contentType != "video/mp4" {
		http.Error(w, "Only images and MP4 videos are supported", http.StatusBadRequest)
		return
	}

	// Generate path
	ext := filepath.Ext(header.Filename)
	if ext == "" {
		ext = ".png" // default
	}
	filename := fmt.Sprintf("uploads/%s%s", uuid.New().String(), ext)
	
	ctx := r.Context()
	bucketName := h.Config.VeoBucket
	
	slog.Info("Uploading file", "filename", filename, "bucket", bucketName)

	client, err := storage.NewClient(ctx)
	if err != nil {
		slog.Error("Failed to create storage client", "error", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer client.Close()

	wc := client.Bucket(bucketName).Object(filename).NewWriter(ctx)
	wc.ContentType = contentType
	
	if _, err := io.Copy(wc, file); err != nil {
		slog.Error("Failed to write file to GCS", "error", err)
		http.Error(w, "Upload failed", http.StatusInternalServerError)
		return
	}
	if err := wc.Close(); err != nil {
		slog.Error("Failed to close GCS writer", "error", err)
		http.Error(w, "Upload failed", http.StatusInternalServerError)
		return
	}

	gcsURI := fmt.Sprintf("gs://%s/%s", bucketName, filename)
	
	// Generate signed URL for preview
	signedURI, err := h.signURL(ctx, gcsURI)
	if err != nil {
		slog.Warn("Failed to sign uploaded file URL", "error", err)
		signedURI = "" // proceed without preview if signing fails
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(UploadResponse{
		URI:       gcsURI,
		SignedURI: signedURI,
	})
}
