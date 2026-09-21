package main

import (
	"context"
	"testing"

	"github.com/GoogleCloudPlatform/genmedia-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
)

func TestFfmpegGetMediaInfoHandler(t *testing.T) {
	// Create a dummy request
	args := map[string]interface{}{
		"input_media_uri": "test.mp3",
	}
	req := mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}

	// Create a dummy config
	cfg := &common.Config{}

	// Call the handler
	_, err := ffmpegGetMediaInfoHandler(context.Background(), req, cfg)
	if err != nil {
		t.Errorf("expected no error, but got: %v", err)
	}
}
