// Package common provides shared utilities for the MCP Genmedia servers.

package common

import (
	"context"
	"log"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

// InitTracerProvider initializes and configures the OpenTelemetry tracer provider.
// It sets up a GRPC exporter to send trace data and configures the tracer with
// service name and version attributes. This is crucial for observability, allowing
// for distributed tracing of requests as they flow through the system.
func InitTracerProvider(serviceName, serviceVersion string) (*sdktrace.TracerProvider, error) {
	if os.Getenv("OTEL_ENABLED") != "true" {
		log.Println("OpenTelemetry tracing is disabled. Set OTEL_ENABLED=true to enable.")
		return nil, nil // Return nil to indicate that tracing is disabled.
	}
	ctx := context.Background()

	// --- Recommended Configuration Logic ---

	// Define the OTLP endpoint, which can also be set via environment variables.
	// Example: OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:4317" // Default to localhost if not set.
	}

	// Default to a secure connection.
	opts := []otlptracegrpc.Option{
		otlptracegrpc.WithEndpoint(endpoint),
	}

	// Check for the standard environment variable to enable insecure mode.
	if os.Getenv("OTEL_EXPORTER_OTLP_INSECURE") == "true" {
		log.Println("WARNING: Using insecure connection for OTLP exporter")
		opts = append(opts, otlptracegrpc.WithInsecure())
	}
	// --- End of Recommended Logic ---

	exporter, err := otlptracegrpc.New(ctx, opts...)
	if err != nil {
		log.Fatalf("failed to create OTLP trace exporter: %v", err)
	}

	// Create a new tracer provider.
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(serviceName),
			semconv.ServiceVersionKey.String(serviceVersion),
		)),
	)

	// Register the tracer provider as the global provider.
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))

	log.Printf("Tracer provider initialized for service: %s, version: %s", serviceName, serviceVersion)

	return tp, nil
}
