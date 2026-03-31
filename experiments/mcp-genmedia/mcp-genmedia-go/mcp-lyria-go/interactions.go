package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

// generateAudioWithInteractions uses the experimental Interactions API to generate audio
// for newer Lyria models like lyria-3-pro-preview and lyria-3-clip-preview.
func generateAudioWithInteractions(ctx context.Context, modelID string, prompt string) ([]byte, string, error) {
	log.Printf("Using Interactions API for model: %s", modelID)

	creds, err := google.FindDefaultCredentials(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, "", fmt.Errorf("failed to get default credentials: %w", err)
	}
	oauthClient := oauth2.NewClient(ctx, creds.TokenSource)

	endpoint := "aiplatform.googleapis.com"
	if appConfig.ApiEndpoint != "" {
		endpoint = appConfig.ApiEndpoint
	}

	// Lyria 3 preview models via the Interactions API currently only support the global location ("Cardolan").
	// We hardcode "global" here instead of using appConfig.Location (which defaults to "us-central1").
	url := fmt.Sprintf("https://%s/v1beta1/projects/%s/locations/global/interactions",
		endpoint, appConfig.ProjectID)

	payload := map[string]interface{}{
		"model": modelID,
		"input": []map[string]string{
			{
				"type": "text",
				"text": prompt,
			},
		},
		"store": false,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, "", fmt.Errorf("failed to marshal payload: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(body))
	if err != nil {
		return nil, "", fmt.Errorf("failed to create http request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-goog-user-project", appConfig.ProjectID)

	// Inject auth header manually if optional header capture is enabled
	if appConfig.EnableOptionalHeaderCapture {
		token, tokenErr := creds.TokenSource.Token()
		if tokenErr == nil {
			httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token.AccessToken))
		}
	}

	resp, err := oauthClient.Do(httpReq)
	if err != nil {
		return nil, "", fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	var sherlogLink string
	if appConfig.EnableOptionalHeaderCapture {
		sherlogLink = resp.Header.Get("x-goog-sherlog-link")
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, "", fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, "", fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(respBody))
	}

	var raw map[string]interface{}
	if err := json.Unmarshal(respBody, &raw); err != nil {
		return nil, "", fmt.Errorf("failed to parse JSON response: %w", err)
	}

	outputs, ok := raw["outputs"].([]interface{})
	if !ok {
		return nil, "", fmt.Errorf("no \"outputs\" array found in response")
	}

	for _, out := range outputs {
		outMap, ok := out.(map[string]interface{})
		if !ok {
			continue
		}
		if outMap["type"] == "audio" {
			data, ok := outMap["data"].(string)
			if !ok {
				continue
			}
			// Decode the base64 string directly
			decodedBytes, err := base64.StdEncoding.DecodeString(data)
			if err != nil {
				return nil, "", fmt.Errorf("failed to decode base64 audio data: %w", err)
			}
			return decodedBytes, sherlogLink, nil
		}
	}

	return nil, "", fmt.Errorf("no audio output found in response")
}
