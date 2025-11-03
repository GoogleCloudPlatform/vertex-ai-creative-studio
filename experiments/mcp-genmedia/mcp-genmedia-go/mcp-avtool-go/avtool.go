// Package main implements an MCP server for audio and video processing.

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
)

const (
	serviceName = "mcp-avtool-go"
	version     = "2.1.1" // Disable OTel by default
)

var transport = flag.String("transport", "stdio", "Transport type (stdio, sse, or http)")

// init handles command-line flags and initial logging setup.
// It configures the log package to include standard flags and the short file name
// of the caller in log messages, which is useful for debugging.
func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
}

// main is the entry point of the application. It initializes the configuration,
// sets up OpenTelemetry for tracing, creates a new MCP server, registers all the
// available AV (Audio/Video) tools, and starts the server based on the specified
// transport mechanism (stdio, sse, or http).
func main() {
	flag.Parse() // Ensure flags are parsed before use

	cfg := common.LoadConfig()

	// Initialize OpenTelemetry
	tp, err := common.InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}
	if tp != nil {
		defer func() {
			if err := tp.Shutdown(context.Background()); err != nil {
				log.Printf("Error shutting down tracer provider: %v", err)
			}
		}()
	}

	s := server.NewMCPServer(
		"AV Compositing Tool", // More general name
		version,
	)

	// Register tools - these functions are now in mcp_handlers.go
	// and now require the config to be passed.
	addConvertAudioTool(s, cfg)
	addCombineAudioVideoTool(s, cfg)
	addOverlayImageOnVideoTool(s, cfg)
	addConcatenateMediaTool(s, cfg)
	addAdjustVolumeTool(s, cfg)
	addLayerAudioTool(s, cfg)
	addCreateGifTool(s, cfg)
	addGetMediaInfoTool(s, cfg)

	log.Printf("Starting AV Compositing Tool (avtool) MCP Server (Version: %s, Transport: %s)", version, *transport)

	if *transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8081"))
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on SSE at :8081")
		if err := sseServer.Start(":8081"); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else if *transport == "http" {
		mcpHTTPHandler := server.NewStreamableHTTPServer(s) // Base path /mcp

		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"}, // Consider making this configurable
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300,
		})

		handlerWithCORS := c.Handler(mcpHTTPHandler)

		httpPort := common.GetEnv("PORT", "8080")
		listenAddr := fmt.Sprintf(":%s", httpPort)
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on HTTP at %s/mcp and CORS enabled", listenAddr)
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	} else { // Default to stdio
		if *transport != "stdio" && *transport != "" {
			log.Printf("Unsupported transport type '%s' specified, defaulting to stdio.", *transport)
		}
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on STDIO")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}
	log.Println("AV Compositing Tool (avtool) Server has stopped.")
}