// Package main implements an MCP server for Google's Chirp3 text-to-speech models.

package main

import (
	"context"
	"encoding/base64" // For encoding audio data
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	texttospeech "cloud.google.com/go/texttospeech/apiv1"
	"cloud.google.com/go/texttospeech/apiv1/texttospeechpb"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

var (
	ttsClient           *texttospeech.Client // Global Text-to-Speech client
	availableVoices     []*texttospeechpb.Voice
	transport           string
	port                string
	version             = "0.1.1" // Disable OTel by default
)

const (
	serviceName             = "mcp-chirp3-go"
	timeFormatForFilename = "20060102-150405"
	defaultChirpVoiceName = "en-US-Chirp3-HD-Zephyr"
)

// LanguageNameToCodeMap maps descriptive language names (lowercase) to BCP-47 codes (canonical casing).
var LanguageNameToCodeMap = map[string]string{
	"german (germany)":         "de-DE",
	"english (australia)":      "en-AU",
	"english (united kingdom)": "en-GB",
	"english (india)":          "en-IN",
	"english (united states)":  "en-US",
	"spanish (united states)":  "es-US",
	"french (france)":          "fr-FR",
	"hindi (india)":            "hi-IN",
	"portuguese (brazil)":      "pt-BR",
	"arabic (generic)":         "ar-XA",
	"spanish (spain)":          "es-ES",
	"french (canada)":          "fr-CA",
	"indonesian (indonesia)":   "id-ID",
	"italian (italy)":          "it-IT",
	"japanese (japan)":         "ja-JP",
	"turkish (turkey)":         "tr-TR",
	"vietnamese (vietnam)":     "vi-VN",
	"bengali (india)":          "bn-IN",
	"gujarati (india)":         "gu-IN",
	"kannada (india)":          "kn-IN",
	"malayalam (india)":        "ml-IN",
	"marathi (india)":          "mr-IN",
	"tamil (india)":            "ta-IN",
	"telugu (india)":           "te-IN",
	"dutch (netherlands)":      "nl-NL",
	"korean (south korea)":     "ko-KR",
	"mandarin chinese (china)": "cmn-CN",
	"polish (poland)":          "pl-PL",
	"russian (russia)":         "ru-RU",
	"thai (thailand)":          "th-TH",
}

// OriginalLanguageNames is used to get the original casing for display in disambiguation messages.
var OriginalLanguageNames = make(map[string]string) // map[lowercase_name]Original_Cased_Name

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&port, "p", "8080", "Port for SSE server if transport is sse") // This port is for SSE, HTTP will use its own.
	flag.Parse()

	titleCaser := cases.Title(language.Und)
	for k := range LanguageNameToCodeMap {
		OriginalLanguageNames[k] = titleCaser.String(k)
	}
}

// listAndCacheChirpHDVoices fetches the list of available voices from the
// Google Cloud Text-to-Speech API and caches those that are identified as
// Chirp3-HD voices. This cached list is used by other functions to validate
// voice selections and provide voice options.
func listAndCacheChirpHDVoices(ctx context.Context) error {
	log.Println("Fetching available Chirp3-HD voices...")
	tempClient, err := texttospeech.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("texttospeech.NewClient for voice listing: %w", err)
	}
	defer tempClient.Close()

	resp, err := tempClient.ListVoices(ctx, &texttospeechpb.ListVoicesRequest{})
	if err != nil {
		return fmt.Errorf("ListVoices: %w", err)
	}

	var foundVoices []*texttospeechpb.Voice
	for _, voice := range resp.Voices {
		if strings.Contains(voice.Name, "Chirp3-HD") {
			foundVoices = append(foundVoices, voice)
		}
	}
	availableVoices = foundVoices

	if len(availableVoices) == 0 {
		log.Println("Warning: No Chirp3-HD voices found. TTS functionality might be limited.")
	} else {
		log.Printf("Found and cached %d Chirp3-HD voices.", len(availableVoices))
	}
	return nil
}

// parseMcpPronunciations processes custom pronunciation parameters provided in an MCP request.
// It takes the raw `pronunciations` parameter (expected as an array of strings)
// and an encoding string ('ipa' or 'xsampa'). Each string in the array should be in
// the format 'phrase:phonetic_form'. The function validates the inputs and converts
// them into the appropriate protobuf message structure required by the Text-to-Speech API.
func parseMcpPronunciations(pronunciationsParam interface{}, encodingStr string) (*texttospeechpb.CustomPronunciations, error) {
	if pronunciationsParam == nil {
		return nil, nil // No pronunciations provided
	}

	pronunciationItems, ok := pronunciationsParam.([]interface{})
	if !ok {
		return nil, fmt.Errorf("pronunciations parameter is not a valid array, got %T", pronunciationsParam)
	}

	if len(pronunciationItems) == 0 {
		return nil, nil
	}

	var encodingType texttospeechpb.CustomPronunciationParams_PhoneticEncoding
	switch strings.ToLower(encodingStr) {
	case "ipa":
		encodingType = texttospeechpb.CustomPronunciationParams_PHONETIC_ENCODING_IPA
	case "xsampa", "x-sampa": // Allow for x-sampa as well
		encodingType = texttospeechpb.CustomPronunciationParams_PHONETIC_ENCODING_X_SAMPA
	default:
		return nil, fmt.Errorf("unsupported pronunciation_encoding: %s. Must be 'ipa' or 'xsampa'", encodingStr)
	}

	var parsedParams []*texttospeechpb.CustomPronunciationParams
	for i, item := range pronunciationItems {
		entryStr, ok := item.(string)
		if !ok {
			return nil, fmt.Errorf("pronunciation item at index %d is not a string, got %T", i, item)
		}

		trimmedEntry := strings.TrimSpace(entryStr)
		if trimmedEntry == "" {
			continue
		}
		parts := strings.SplitN(trimmedEntry, ":", 2)
		if len(parts) != 2 {
			return nil, fmt.Errorf("malformed pronunciation entry at index %d: %q. Expected format 'phrase:pronunciation'", i, trimmedEntry)
		}
		phrase := strings.TrimSpace(parts[0])
		pronunciation := strings.TrimSpace(parts[1])

		if phrase == "" || pronunciation == "" {
			return nil, fmt.Errorf("empty phrase or pronunciation in entry at index %d: %q", i, trimmedEntry)
		}

		params := &texttospeechpb.CustomPronunciationParams{
			Phrase:           &phrase,
			Pronunciation:    &pronunciation,
			PhoneticEncoding: &encodingType,
		}
		parsedParams = append(parsedParams, params)
	}

	if len(parsedParams) == 0 {
		return nil, nil
	}

	return &texttospeechpb.CustomPronunciations{
		Pronunciations: parsedParams,
	}, nil
}

// main is the entry point for the mcp-chirp3-go service.
// It initializes the OpenTelemetry provider, the Google Cloud Text-to-Speech client,
// and caches the available Chirp3-HD voices. It then sets up an MCP server, registers
// the 'chirp_tts' and 'list_chirp_voices' tools, and starts listening for requests
// on the configured transport (stdio, sse, or http).
func main() {
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

	log.Printf("Initializing global Text-to-Speech client...")
	startupCtx, startupCancel := context.WithTimeout(context.Background(), 1*time.Minute)
	defer startupCancel()

	ttsClient, err = texttospeech.NewClient(startupCtx)
	if err != nil {
		log.Fatalf("Error creating global Text-to-Speech client: %v", err)
	}
	log.Printf("Global Text-to-Speech client initialized successfully.")

	err = listAndCacheChirpHDVoices(startupCtx)
	if err != nil {
		log.Printf("Warning: Could not fetch Chirp3-HD voices at startup: %v. Voice-dependent tools may not function correctly.", err)
	}

	s := server.NewMCPServer(
		serviceName, // Standardized name
		version,
	)

	chirpTool := mcp.NewTool("chirp_tts",
		mcp.WithDescription("Synthesizes speech from text using Google Cloud TTS with Chirp3-HD voices. Returns audio data and optionally saves it locally."),
		mcp.WithString("text",
			mcp.Required(),
			mcp.Description("The text to synthesize into speech."),
		),
		mcp.WithString("voice_name",
			mcp.Description(fmt.Sprintf("Optional. The specific Chirp3-HD voice name to use (e.g., '%s'). If not provided, defaults to '%s' if available, otherwise the first available Chirp3-HD voice.", defaultChirpVoiceName, defaultChirpVoiceName)),
		),
		mcp.WithString("output_filename_prefix",
			mcp.DefaultString("chirp_audio"),
			mcp.Description("Optional. A prefix for the output WAV filename if saving locally. A timestamp and .wav extension will be appended."),
		),
		mcp.WithString("output_directory",
			mcp.Description("Optional. If provided, specifies a local directory to save the generated audio file to. Filenames will be generated automatically using the prefix. If not provided, audio data is returned in the response."),
		),
		mcp.WithArray("pronunciations", // New array parameter for pronunciations
			mcp.Description("Optional. An array of custom pronunciations. Each item should be a string in the format 'phrase:phonetic_representation' (e.g., 'tomato:təˈmeɪtoʊ'). All items must use the same encoding specified by 'pronunciation_encoding'."),
			mcp.Items(map[string]any{"type": "string"}), // Specify that array items are strings
		),
		mcp.WithString("pronunciation_encoding", // New string parameter for encoding type
			mcp.DefaultString("ipa"), // Default to IPA
			mcp.Description("Optional. The phonetic encoding used for the 'pronunciations' array. Can be 'ipa' or 'xsampa'. Defaults to 'ipa'."),
			mcp.Enum("ipa", "xsampa"), // Specify allowed values
		),
	)
	s.AddTool(chirpTool, func(toolCtx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return chirpTTSHandler(ttsClient, toolCtx, request)
	})

	listVoicesTool := mcp.NewTool("list_chirp_voices",
		mcp.WithDescription("Lists Chirp3-HD voices, filtered by the provided language (either descriptive name or BCP-47 code)."),
		mcp.WithString("language",
			mcp.Required(),
			mcp.Description("The language to filter voices by. Can be a descriptive name (e.g., 'English (United States)') or a BCP-47 code (e.g., 'en-US')."),
		),
	)
	s.AddTool(listVoicesTool, listChirpVoicesHandler)

	// Add the new list-voices prompt
	s.AddPrompt(mcp.NewPrompt("list-voices",
		mcp.WithPromptDescription("Lists available Chirp3-HD voices, with an option to filter by language."),
		mcp.WithArgument("language",
			mcp.ArgumentDescription("Optional. The language to filter voices by (e.g., 'English (United States)', 'en-US')."),
		),
	), func(ctx context.Context, request mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		languageParam, langProvided := request.Params.Arguments["language"]
		if !langProvided || strings.TrimSpace(languageParam) == "" {
			// If no language is provided, ask the user to specify one.
			return mcp.NewGetPromptResult(
				"Specify Language",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(
						mcp.RoleAssistant,
						mcp.NewTextContent("What language would you like to list the voices for? You can see available languages by using the resource 'chirp://language_codes'"),
					),
				},
			), nil
		}

		summary, jsonData, err := getFilteredVoices(languageParam)
		if err != nil {
			return mcp.NewGetPromptResult(
				"Error",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(
						mcp.RoleAssistant,
						mcp.NewTextContent(err.Error()),
					),
				},
			), nil
		}

		return mcp.NewGetPromptResult(
			"Voice List",
			[]mcp.PromptMessage{
				mcp.NewPromptMessage(
					mcp.RoleAssistant,
					mcp.NewTextContent(summary+"\n"+jsonData),
				),
			},
		), nil
	})

	// Add the language codes resource
	s.AddResource(mcp.NewResource(
		"chirp://language_codes",
		"Chirp Language Codes",
		mcp.WithResourceDescription("A list of supported languages and their BCP-47 codes."),
		mcp.WithMIMEType("application/json"),
	), func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		jsonData, err := json.MarshalIndent(LanguageNameToCodeMap, "", "  ")
		if err != nil {
			return nil, fmt.Errorf("failed to marshal language codes: %w", err)
		}
		return []mcp.ResourceContents{
			mcp.TextResourceContents{
				URI:      "chirp://language_codes",
				MIMEType: "application/json",
				Text:     string(jsonData),
			},
		}, nil
	})

	userSetPort := false
	flag.Visit(func(f *flag.Flag) {
		if f.Name == "p" {
			userSetPort = true
		}
	})

	if userSetPort && transport == "stdio" {
		log.Printf("Port -p specified (%s), overriding transport to sse.", port)
		transport = "sse"
	}

	log.Printf("Starting %s MCP Server (Version: %s, Transport: %s)", serviceName, version, transport)

	if transport == "sse" {
		if port == "" {
			port = "8081" // Default SSE port to 8081 if not specified, to avoid conflict with HTTP default 8080
			log.Printf("Transport is SSE but no port specified, defaulting to %s", port)
		}
		sseServer := server.NewSSEServer(s, server.WithBaseURL(fmt.Sprintf("http://localhost:%s", port)))
		log.Printf("%s MCP Server listening on SSE at :%s with tools: chirp_tts, list_chirp_voices", serviceName, port)
		if err := sseServer.Start(fmt.Sprintf(":%s", port)); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else if transport == "http" {
		mcpHTTPHandler := server.NewStreamableHTTPServer(s) // Base path /mcp

		// Configure CORS
		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"}, // Consider making this configurable via env var for production
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300, // In seconds
			// Debug: true, // Uncomment for debugging CORS issues
		})

		// Wrap the MCP handler with the CORS middleware
		handlerWithCORS := c.Handler(mcpHTTPHandler)

		httpPort := common.GetEnv("PORT", "8080")
		listenAddr := fmt.Sprintf(":%s", httpPort)
		log.Printf("%s MCP Server listening on HTTP at %s/mcp with tools: chirp_tts, list_chirp_voices and CORS enabled", serviceName, listenAddr)
		// Start the server using the wrapped handler
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	} else { // Default to stdio
		if transport != "stdio" && transport != "" {
			log.Printf("Unsupported transport type '%s' specified, defaulting to stdio.", transport)
		}
		log.Printf("%s MCP Server listening on STDIO with tools: chirp_tts, list_chirp_voices", serviceName)
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}

	log.Printf("%s Server has stopped.", serviceName)
	if ttsClient != nil {
		ttsClient.Close() // Ensure client is closed on server stop, regardless of transport
	}
}

// chirpTTSHandler is the core logic for the 'chirp_tts' tool.
// It handles requests to synthesize speech from text. The function extracts parameters
// from the request, selects an appropriate voice, and calls the Text-to-Speech API.
// It can save the resulting audio to a local file or return it directly in the
// response as base64-encoded data.
func chirpTTSHandler(client *texttospeech.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	var contentItems []mcp.Content

	if err := ctx.Err(); err != nil {
		log.Printf("chirpTTSHandler: Incoming context (ctx) is already canceled or has an error upon entry: %v. Will attempt to proceed with TTS using a background context.", err)
	} else {
		log.Printf("chirpTTSHandler: Incoming context (ctx) is active upon entry.")
	}

	log.Printf("Handling chirp_tts request with arguments: %v", request.GetArguments())

	text, ok := request.GetArguments()["text"].(string)
	if !ok || strings.TrimSpace(text) == "" {
		errMsg := "text parameter must be a non-empty string and is required"
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMsg})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	// Handle custom pronunciations
	pronunciationsParam := request.GetArguments()["pronunciations"] // This will be []interface{} or nil
	pronunciationEncodingStr, _ := request.GetArguments()["pronunciation_encoding"].(string)
	if pronunciationEncodingStr == "" { // Apply default if not provided
		pronunciationEncodingStr = "ipa"
	}

	customPronos, err := parseMcpPronunciations(pronunciationsParam, pronunciationEncodingStr)
	if err != nil {
		errMsg := fmt.Sprintf("Error parsing custom pronunciations: %v", err)
		log.Print(errMsg)
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMsg})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}
	if customPronos != nil {
		log.Printf("Applying %d custom pronunciations with %s encoding.", len(customPronos.Pronunciations), pronunciationEncodingStr)
	}

	var selectedVoice *texttospeechpb.Voice
	voiceNameParam, voiceNameProvided := request.GetArguments()["voice_name"].(string)

	if voiceNameProvided && strings.TrimSpace(voiceNameParam) != "" {
		voiceNameParam = strings.TrimSpace(voiceNameParam)
		found := false
		for _, v := range availableVoices {
			if v.Name == voiceNameParam {
				selectedVoice = v
				found = true
				break
			}
		}
		if !found {
			log.Printf("Requested voice_name '%s' not found among available Chirp3-HD voices. Attempting default.", voiceNameParam)
		} else {
			log.Printf("Using requested voice: %s", selectedVoice.Name)
		}
	}

	if selectedVoice == nil {
		for _, v := range availableVoices {
			if v.Name == defaultChirpVoiceName {
				selectedVoice = v
				log.Printf("Voice_name not provided or invalid/not found. Defaulting to preferred voice: %s", selectedVoice.Name)
				break
			}
		}
		if selectedVoice == nil && len(availableVoices) > 0 {
			selectedVoice = availableVoices[0]
			log.Printf("Preferred default voice '%s' not found. Defaulting to first available Chirp3-HD voice: %s", defaultChirpVoiceName, selectedVoice.Name)
		} else if selectedVoice == nil {
			errMsg := "No Chirp3-HD voices available for synthesis. Please check server logs for voice fetching issues at startup."
			log.Println("Error: " + errMsg)
			contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMsg})
			return &mcp.CallToolResult{Content: contentItems}, nil
		}
	}

	filenamePrefix, _ := request.GetArguments()["output_filename_prefix"].(string)
	if strings.TrimSpace(filenamePrefix) == "" {
		filenamePrefix = "chirp_audio"
	}

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}
	attemptLocalSave := outputDir != ""
	log.Printf("Output directory: '%s', Attempt local save: %t", outputDir, attemptLocalSave)

	synthesisAPICallCtx, synthesisAPICallCancel := context.WithTimeout(ctx, 30*time.Second)
	defer synthesisAPICallCancel()

	log.Printf("Synthesizing speech for text: \"%s\" with voice: %s. API call using independent context with timeout: 30s", text, selectedVoice.Name)
	// Pass customPronos to synthesizeWithVoice
	audioContentBytes, err := synthesizeWithVoice(synthesisAPICallCtx, client, selectedVoice, text, customPronos)

	if err != nil {
		errMsg := fmt.Sprintf("Error synthesizing speech: %v", err)
		log.Print(errMsg)
		if errors.Is(err, context.DeadlineExceeded) && synthesisAPICallCtx.Err() == context.DeadlineExceeded {
			errMsg = "Speech synthesis API call timed out."
			log.Printf("SynthesizeSpeech call timed out after 30 seconds (independent synthesisAPICallCtx).")
		} else if errors.Is(err, context.Canceled) && synthesisAPICallCtx.Err() == context.Canceled {
			errMsg = "Speech synthesis API call was canceled."
			log.Printf("SynthesizeSpeech call canceled (independent synthesisAPICallCtx).")
		}
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMsg})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	if len(audioContentBytes) == 0 {
		errMsg := fmt.Sprintf("Synthesized audio is empty for voice %s.", selectedVoice.Name)
		log.Print(errMsg)
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMsg})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	var fileSaveMessage string
	var savedFilename string

	if attemptLocalSave {
		if err := os.MkdirAll(outputDir, 0755); err != nil {
			fileSaveMessage = fmt.Sprintf("Error creating directory %s: %v. Audio data will be returned in response instead.", outputDir, err)
			log.Print(fileSaveMessage)
			base64AudioData := base64.StdEncoding.EncodeToString(audioContentBytes)
			audioItem := mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"}
			contentItems = append(contentItems, audioItem)
		} else {
			safeVoiceName := strings.ReplaceAll(selectedVoice.Name, "/", "_")
			safeVoiceName = strings.ReplaceAll(safeVoiceName, ":", "_")
			genFilename := fmt.Sprintf("%s-%s-%s.wav", filenamePrefix, safeVoiceName, time.Now().Format(timeFormatForFilename))
			savedFilename = filepath.Join(outputDir, genFilename)
			savedFilename = filepath.Clean(savedFilename)

			err = os.WriteFile(savedFilename, audioContentBytes, 0644)
			if err != nil {
				fileSaveMessage = fmt.Sprintf("Error writing audio file %s: %v. Audio data will be returned in response instead.", savedFilename, err)
				log.Print(fileSaveMessage)
				base64AudioData := base64.StdEncoding.EncodeToString(audioContentBytes)
				audioItem := mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"}
				contentItems = append(contentItems, audioItem)
				savedFilename = ""
			} else {
				fileSaveMessage = fmt.Sprintf("Audio saved to: %s (%d bytes).", savedFilename, len(audioContentBytes))
				log.Printf("Audio content (%d bytes) written to file: %s", len(audioContentBytes), savedFilename)
			}
		}
	} else {
		base64AudioData := base64.StdEncoding.EncodeToString(audioContentBytes)
		audioItem := mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: "audio/wav"}
		contentItems = append(contentItems, audioItem)
		fileSaveMessage = "Audio data is included in the response."
	}

	resultText := fmt.Sprintf("Speech synthesized successfully with voice %s. %s",
		selectedVoice.Name,
		fileSaveMessage,
	)
	textItem := mcp.TextContent{Type: "text", Text: strings.TrimSpace(resultText)}

	finalContentItems := []mcp.Content{textItem}
	// Only append audio to finalContentItems if it's meant to be returned in the response
	if !attemptLocalSave || (attemptLocalSave && savedFilename == "") {
		// Find the audioItem in contentItems (it should be the only one if it exists)
		for _, item := range contentItems {
			if _, ok := item.(mcp.AudioContent); ok {
				finalContentItems = append(finalContentItems, item)
				break
			}
		}
	}

	return &mcp.CallToolResult{Content: finalContentItems}, nil
}

// synthesizeWithVoice encapsulates the call to the Google Cloud Text-to-Speech API.
// It constructs the synthesis request with the specified voice, text, and custom pronunciations,
// sends it to the API, and returns the raw audio content as a byte slice.
func synthesizeWithVoice(ctx context.Context, client *texttospeech.Client, voice *texttospeechpb.Voice, textToSynthesize string, customPronos *texttospeechpb.CustomPronunciations) ([]byte, error) {
	req := texttospeechpb.SynthesizeSpeechRequest{
		Input: &texttospeechpb.SynthesisInput{
			InputSource:          &texttospeechpb.SynthesisInput_Text{Text: textToSynthesize},
			CustomPronunciations: customPronos, // Set custom pronunciations here
		},
		Voice: &texttospeechpb.VoiceSelectionParams{
			LanguageCode: voice.GetLanguageCodes()[0],
			Name:         voice.GetName(),
		},
		AudioConfig: &texttospeechpb.AudioConfig{
			AudioEncoding: texttospeechpb.AudioEncoding_LINEAR16, // WAV format
		},
	}

	resp, err := client.SynthesizeSpeech(ctx, &req)
	if err != nil {
		return nil, fmt.Errorf("SynthesizeSpeech: %w", err)
	}
	return resp.AudioContent, nil
}

type VoiceInfo struct {
	Name         string `json:"name"`
	LanguageCode string `json:"language_code"`
	Gender       string `json:"gender"`
}

func getFilteredVoices(languageQuery string) (string, string, error) {
	if strings.TrimSpace(languageQuery) == "" {
		return "", "", errors.New("language query must not be empty")
	}

	normalizedInput := strings.ToLower(strings.TrimSpace(languageQuery))
	var targetLangCode string
	var directlyResolved bool

	bcp47Code, isNameMatch := LanguageNameToCodeMap[normalizedInput]
	if isNameMatch {
		targetLangCode = bcp47Code
		directlyResolved = true
	} else {
		for _, codeInMap := range LanguageNameToCodeMap {
			if strings.ToLower(codeInMap) == normalizedInput {
				targetLangCode = codeInMap
				directlyResolved = true
				break
			}
		}
	}

	if !directlyResolved {
		potentialMatches := make(map[string]bool)
		for lcNameKey, originalCasedName := range OriginalLanguageNames {
			bcp47ForThisName := LanguageNameToCodeMap[lcNameKey]
			if strings.Contains(lcNameKey, normalizedInput) || strings.Contains(strings.ToLower(bcp47ForThisName), normalizedInput) {
				potentialMatches[originalCasedName] = true
			}
		}

		if len(potentialMatches) == 0 {
			return "", "", fmt.Errorf("unsupported language query: '%s'. No matching language names or BCP-47 codes found", languageQuery)
		}

		if len(potentialMatches) > 1 {
			var displayNames []string
			for name := range potentialMatches {
				displayNames = append(displayNames, name)
			}
			sort.Strings(displayNames)
			return "", "", fmt.Errorf("your language query '%s' is ambiguous. Please be more specific by choosing one of the following: %s", languageQuery, strings.Join(displayNames, ", "))
		}

		for name := range potentialMatches {
			targetLangCode = LanguageNameToCodeMap[strings.ToLower(name)]
		}
	}

	if len(availableVoices) == 0 {
		return "", "", errors.New("no Chirp3-HD voices are currently available or cached")
	}

	var filteredVoiceInfos []VoiceInfo
	var voiceNameSuffixes []string
	filterLangCodeNormalized := strings.ToLower(targetLangCode)

	for _, v := range availableVoices {
		voiceMatches := false
		for _, lc := range v.GetLanguageCodes() {
			if strings.ToLower(lc) == filterLangCodeNormalized {
				voiceMatches = true
				break
			}
		}
		if voiceMatches {
			var primaryLangCode string
			if len(v.GetLanguageCodes()) > 0 {
				primaryLangCode = v.GetLanguageCodes()[0]
			}
			info := VoiceInfo{
				Name:         v.GetName(),
				LanguageCode: primaryLangCode,
				Gender:       v.GetSsmlGender().String(),
			}
			filteredVoiceInfos = append(filteredVoiceInfos, info)

			nameSuffix := v.GetName()
			if primaryLangCode != "" {
				expectedPrefix := strings.ToLower(primaryLangCode) + "-chirp3-hd-"
				if strings.HasPrefix(strings.ToLower(v.GetName()), expectedPrefix) {
					potentialSuffix := v.GetName()[len(expectedPrefix):]
					if potentialSuffix != "" {
						nameSuffix = potentialSuffix
					}
				}
			}
			voiceNameSuffixes = append(voiceNameSuffixes, nameSuffix)
		}
	}

	if len(filteredVoiceInfos) == 0 {
		return "", "", fmt.Errorf("no Chirp3-HD voices found for the specified language filter: '%s' (resolved to %s)", languageQuery, targetLangCode)
	}

	sort.Strings(voiceNameSuffixes)

	summaryText := fmt.Sprintf("I've resolved your request for '%s' to the language code '%s'. Found %d voice(s): %s",
		languageQuery,
		targetLangCode,
		len(filteredVoiceInfos),
		strings.Join(voiceNameSuffixes, ", "),
	)

	jsonData, err := json.MarshalIndent(filteredVoiceInfos, "", "  ")
	if err != nil {
		return "", "", fmt.Errorf("error marshalling filtered voice list to JSON: %w", err)
	}

	return summaryText, string(jsonData), nil
}

func listChirpVoicesHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if err := ctx.Err(); err != nil {
		log.Printf("listChirpVoicesHandler: Incoming context (ctx) is already canceled or has an error upon entry: %v. Attempting to proceed with listing.", err)
	} else {
		log.Printf("listChirpVoicesHandler: Incoming context (ctx) is active upon entry.")
	}
	log.Println("Handling list_chirp_voices request.")

	languageParam, langProvided := request.GetArguments()["language"].(string)
	if !langProvided || strings.TrimSpace(languageParam) == "" {
		return mcp.NewToolResultError("'language' parameter must be provided and non-empty."), nil
	}

	summary, jsonData, err := getFilteredVoices(languageParam)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: summary,
			},
			mcp.TextContent{
				Type: "text",
				Text: jsonData,
			},
		},
	}, nil
}