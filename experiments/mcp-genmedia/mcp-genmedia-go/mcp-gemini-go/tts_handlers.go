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
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

const (
	geminiTTSAPIEndpoint         = "https://texttospeech.googleapis.com/v1/text:synthesize"
	defaultGeminiTTSModel        = "gemini-2.5-flash-preview-tts"
	defaultGeminiTTSVoice        = "Callirrhoe"
	timeFormatForTTSFilename     = "20060102-150405"
)

// hardcoded list of voices based on documentation
var availableGeminiVoices = []string{
	"Achernar",
	"Achird",
	"Algenib",
	"Algieba",
	"Alnilam",
	"Aoede",
	"Autonoe",
	"Callirrhoe",
	"Charon",
	"Despina",
	"Enceladus",
	"Erinome",
	"Fenrir",
	"Gacrux",
	"Iapetus",
	"Kore",
	"Laomedeia",
	"Leda",
	"Orus",
	"Pulcherrima",
	"Puck",
	"Rasalgethi",
	"Sadachbia",
	"Sadaltager",
	"Schedar",
	"Sulafat",
	"Umbriel",
	"Vindemiatrix",
	"Zephyr",
	"Zubenelgenubi",
}

// geminiLanguageCodeMap holds the supported languages.
var geminiLanguageCodeMap = map[string]string{
	"english (united states)": "en-US",
}

// --- Resource Handler ---

func geminiLanguageCodesHandler(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
	jsonData, err := json.MarshalIndent(geminiLanguageCodeMap, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("failed to marshal language codes: %w", err)
	}
	return []mcp.ResourceContents{
		mcp.TextResourceContents{
			URI:      "gemini://language_codes",
			MIMEType: "application/json",
			Text:     string(jsonData),
		},
	}, nil
}

// --- API Request and Response Structs ---

type geminiTTSRequest struct {
	Input       geminiTTSInput       `json:"input"`
	Voice       geminiTTSVoiceParams `json:"voice"`
	AudioConfig geminiTTSAudioConfig `json:"audioConfig"`
}

type geminiTTSInput struct {
	Text   string `json:"text"`
	Prompt string `json:"prompt,omitempty"`
}

type geminiTTSVoiceParams struct {
	LanguageCode string `json:"languageCode"`
	Name         string `json:"name"`
	ModelName    string `json:"model_name"`
}

type geminiTTSAudioConfig struct {
	AudioEncoding string `json:"audioEncoding"`
}

type geminiTTSResponse struct {
	AudioContent string `json:"audioContent"`
}

// --- Tool Handlers ---

// listGeminiVoicesHandler handles the 'list_gemini_voices' tool request.
// It returns a hardcoded list of available Gemini TTS voices.
func listGeminiVoicesHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	log.Println("Handling list_gemini_voices request.")

	voiceListJSON, err := json.MarshalIndent(availableGeminiVoices, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("failed to marshal voice list: %v", err)), nil
	}

	summary := fmt.Sprintf("Found %d available Gemini TTS voices.", len(availableGeminiVoices))

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{Type: "text", Text: summary},
			mcp.TextContent{Type: "text", Text: string(voiceListJSON)},
		},
	}, nil
}

// geminiAudioTTSHandler handles the 'gemini_audio_tts' tool request.
func geminiAudioTTSHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	log.Printf("Handling gemini_audio_tts request with arguments: %v", request.GetArguments())

	// --- 1. Parse and Validate Arguments ---
	text, ok := request.GetArguments()["text"].(string)
	if !ok || strings.TrimSpace(text) == "" {
		return mcp.NewToolResultError("text parameter must be a non-empty string and is required"), nil
	}
	if len(text) > 800 {
		return mcp.NewToolResultError("text parameter cannot exceed 800 characters"), nil
	}

	prompt, _ := request.GetArguments()["prompt"].(string)

	modelName, _ := request.GetArguments()["model_name"].(string)
	if modelName == "" {
		modelName = defaultGeminiTTSModel
	}

	voiceName, _ := request.GetArguments()["voice_name"].(string)
	if voiceName == "" {
		voiceName = defaultGeminiTTSVoice
	}
	// Validate voice
	validVoice := false
	for _, v := range availableGeminiVoices {
		if v == voiceName {
			validVoice = true
			break
		}
	}
	if !validVoice {
		return mcp.NewToolResultError(fmt.Sprintf("invalid voice_name '%s'. Use 'list_gemini_voices' to see available voices", voiceName)), nil
	}

	outputDir, _ := request.GetArguments()["output_directory"].(string)
	filenamePrefix, _ := request.GetArguments()["output_filename_prefix"].(string)
	if filenamePrefix == "" {
		filenamePrefix = "gemini_tts_audio"
	}

	// --- 2. Call the TTS API ---
	audioBytes, err := callGeminiTTSAPI(ctx, text, prompt, voiceName, modelName)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("error calling Gemini TTS API: %v", err)), nil
	}

	// --- 3. Process the Audio Response ---
	var contentItems []mcp.Content
	var fileSaveMessage string

	if outputDir != "" {
		if err := os.MkdirAll(outputDir, 0755); err != nil {
			fileSaveMessage = fmt.Sprintf("Error creating directory %s: %v. Audio data will be returned in response instead.", outputDir, err)
			log.Print(fileSaveMessage)
			// Fallback to returning data in response
			base64AudioData := base64.StdEncoding.EncodeToString(audioBytes)
			contentItems = append(contentItems, mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"})
		} else {
			filename := fmt.Sprintf("%s-%s-%s.wav", filenamePrefix, voiceName, time.Now().Format(timeFormatForTTSFilename))
			savedFilename := filepath.Join(outputDir, filename)
			if err := os.WriteFile(savedFilename, audioBytes, 0644); err != nil {
				fileSaveMessage = fmt.Sprintf("Error writing audio file %s: %v. Audio data will be returned in response instead.", savedFilename, err)
				log.Print(fileSaveMessage)
				base64AudioData := base64.StdEncoding.EncodeToString(audioBytes)
				contentItems = append(contentItems, mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"})
			} else {
				fileSaveMessage = fmt.Sprintf("Audio saved to: %s (%d bytes).", savedFilename, len(audioBytes))
				log.Printf(fileSaveMessage)
			}
		}
	} else {
		base64AudioData := base64.StdEncoding.EncodeToString(audioBytes)
		contentItems = append(contentItems, mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"})
		fileSaveMessage = "Audio data is included in the response."
	}

	resultText := fmt.Sprintf("Speech synthesized successfully with voice %s. %s", voiceName, fileSaveMessage)
	contentItems = append([]mcp.Content{mcp.TextContent{Type: "text", Text: resultText}}, contentItems...)

	return &mcp.CallToolResult{Content: contentItems}, nil
}

// --- API Helper Function ---

func callGeminiTTSAPI(ctx context.Context, text, prompt, voiceName, modelName string) ([]byte, error) {
	// --- 1. Get Project ID from environment ---
	projectID := os.Getenv("PROJECT_ID")
	if projectID == "" {
		return nil, fmt.Errorf("PROJECT_ID environment variable must be set")
	}

	// --- 2. Create Authenticated HTTP Client ---
	// The context passed in here is used for the token source.
	tokenSource, err := google.DefaultTokenSource(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, fmt.Errorf("failed to create token source: %w", err)
	}
	client := &http.Client{
		Transport: &oauth2.Transport{
			Source: tokenSource,
		},
		Timeout: 30 * time.Second,
	}

	// --- 3. Construct the Request Body ---
	reqBody := geminiTTSRequest{
		Input: geminiTTSInput{
			Text:   text,
			Prompt: prompt,
		},
		Voice: geminiTTSVoiceParams{
			LanguageCode: "en-US", // Currently only en-US is supported
			Name:         voiceName,
			ModelName:    modelName,
		},
		AudioConfig: geminiTTSAudioConfig{
			AudioEncoding: "LINEAR16", // WAV format
		},
	}

	reqBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	// --- 4. Create and Send the HTTP Request ---
	// Use a new context for the HTTP request itself to respect the client's timeout.
	httpCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	httpReq, err := http.NewRequestWithContext(httpCtx, "POST", geminiTTSAPIEndpoint, bytes.NewBuffer(reqBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create HTTP request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-goog-user-project", projectID)

	log.Printf("Sending Gemini TTS request to %s with model %s and voice %s", geminiTTSAPIEndpoint, modelName, voiceName)

	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send HTTP request: %w", err)
	}
	defer resp.Body.Close()

	// --- 5. Process the Response ---
	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %s: %s", resp.Status, string(bodyBytes))
	}

	var ttsResp geminiTTSResponse
	if err := json.NewDecoder(resp.Body).Decode(&ttsResp); err != nil {
		return nil, fmt.Errorf("failed to decode response body: %w", err)
	}

	if ttsResp.AudioContent == "" {
		return nil, fmt.Errorf("API response did not contain audio content")
	}

	audioBytes, err := base64.StdEncoding.DecodeString(ttsResp.AudioContent)
	if err != nil {
		return nil, fmt.Errorf("failed to decode base64 audio content: %w", err)
	}

	return audioBytes, nil
}
