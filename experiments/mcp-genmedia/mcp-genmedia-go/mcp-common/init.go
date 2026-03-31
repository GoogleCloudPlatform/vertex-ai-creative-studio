package common

import (
	"context"
	"log"
)

// Init loads the configuration and initializes OpenTelemetry.
// It returns the loaded config and a cleanup function that should be deferred in main().
func Init(serviceName, version string) (*Config, func()) {
	cfg := LoadConfig(serviceName)

	tp, err := InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}

	cleanup := func() {
		if tp != nil {
			if err := tp.Shutdown(context.Background()); err != nil {
				log.Printf("Error shutting down tracer provider: %v", err)
			}
		}
	}

	return cfg, cleanup
}
