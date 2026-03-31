package common

import (
	"context"
	"fmt"
	"net/http"

	"golang.org/x/oauth2/google"
	"google.golang.org/genai"
)

// InjectCaptureHeaders updates the provided genai.ClientConfig to include
// a manually fetched Bearer token if the EnableOptionalHeaderCapture flag is true.
// This is necessary because the Go GenAI SDK requires manual auth injection to 
// preserve certain custom upstream routing behaviors.
func InjectCaptureHeaders(ctx context.Context, config *Config, clientConfig *genai.ClientConfig) error {
	if !config.EnableOptionalHeaderCapture {
		return nil
	}

	creds, err := google.FindDefaultCredentials(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to get default credentials for optional header capture: %w", err)
	}

	token, err := creds.TokenSource.Token()
	if err != nil {
		return fmt.Errorf("failed to retrieve token for optional header capture: %w", err)
	}

	if clientConfig.HTTPOptions.Headers == nil {
		clientConfig.HTTPOptions.Headers = make(http.Header)
	}

	// Manually inject the Authorization header
	clientConfig.HTTPOptions.Headers.Set("Authorization", fmt.Sprintf("Bearer %s", token.AccessToken))

	return nil
}
