package common

import (
	"fmt"
	"testing"
)

func TestFormatBytes(t *testing.T) {
	testCases := []struct {
		bytes    int64
		expected string
	}{
		{1023, "1023 B"},
		{1024, "1.0 KB"},
		{1536, "1.5 KB"},
		{1048576, "1.0 MB"},
		{1073741824, "1.0 GB"},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("%d bytes", tc.bytes), func(t *testing.T) {
			actual := FormatBytes(tc.bytes)
			if actual != tc.expected {
				t.Errorf("expected '%s', but got '%s'", tc.expected, actual)
			}
		})
	}
}

func TestGetTail(t *testing.T) {
	testCases := []struct {
		s        string
		n        int
		expected string
	}{
		{"a\nb\nc", 2, "b\nc"},
		{"a\nb\nc", 3, "a\nb\nc"},
		{"a\nb\nc", 4, "a\nb\nc"},
		{"a", 1, "a"},
		{"", 1, ""},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("n=%d", tc.n), func(t *testing.T) {
			actual := GetTail(tc.s, tc.n)
			if actual != tc.expected {
				t.Errorf("expected '%s', but got '%s'", tc.expected, actual)
			}
		})
	}
}

func TestNormalizeImageMIMEType(t *testing.T) {
	testCases := []struct {
		mimeType string
		expected string
	}{
		{"", "image/png"},
		{" IMAGE/WEBP ", "image/webp"},
		{"image/jpeg", "image/jpeg"},
	}

	for _, tc := range testCases {
		t.Run(tc.mimeType, func(t *testing.T) {
			actual := NormalizeImageMIMEType(tc.mimeType)
			if actual != tc.expected {
				t.Errorf("expected '%s', but got '%s'", tc.expected, actual)
			}
		})
	}
}

func TestImageExtensionForMIMEType(t *testing.T) {
	testCases := []struct {
		mimeType string
		expected string
	}{
		{"", ".png"},
		{"image/png", ".png"},
		{"image/jpeg", ".jpg"},
		{"image/webp", ".webp"},
		{"image/gif", ".gif"},
		{"application/octet-stream", ".png"},
	}

	for _, tc := range testCases {
		t.Run(tc.mimeType, func(t *testing.T) {
			actual := ImageExtensionForMIMEType(tc.mimeType)
			if actual != tc.expected {
				t.Errorf("expected '%s', but got '%s'", tc.expected, actual)
			}
		})
	}
}
