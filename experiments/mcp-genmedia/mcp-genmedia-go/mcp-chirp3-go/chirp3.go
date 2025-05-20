package main

import (
	"context"
	"encoding/base64" // For encoding audio data
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	texttospeech "cloud.google.com/go/texttospeech/apiv1"
	"cloud.google.com/go/texttospeech/apiv1/texttospeechpb"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

var (
	projectID, location string
	ttsClient           *texttospeech.Client // Global Text-to-Speech client
	availableVoices     []*texttospeechpb.Voice
	transport           string
	port                string
)

const version = "1.3.4" // Version increment for breaking changes

const (
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

// envCheck checks for an environment variable, otherwise returns default
func envCheck(environmentVariable, defaultVar string) string {
	if envar, ok := os.LookupEnv(environmentVariable); !ok {
		return defaultVar
	} else if envar == "" {
		return defaultVar
	} else {
		return envar
	}
}

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio or sse)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio or sse)")
	flag.StringVar(&port, "p", "8080", "Port for SSE server if transport is sse")
	flag.Parse()

	titleCaser := cases.Title(language.Und)
	for k := range LanguageNameToCodeMap {
		OriginalLanguageNames[k] = titleCaser.String(k)
	}
}

// listAndCacheChirpHDVoices fetches and stores all voices containing "Chirp3-HD".
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

// parseMcpPronunciations parses the custom pronunciations from MCP parameters.
// pronunciationsParam is expected to be []interface{}, where each item is a string "phrase:phonetic_form".
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

func main() {
	projectID = envCheck("PROJECT_ID", "")
	if projectID == "" {
		log.Fatal("PROJECT_ID environment variable not set. Please set it, e.g., export PROJECT_ID=$(gcloud config get project)")
	}
	location = envCheck("LOCATION", "us-central1")
	log.Printf("Using Project ID: %s, Location: %s", projectID, location)

	log.Printf("Initializing global Text-to-Speech client...")
	startupCtx, startupCancel := context.WithTimeout(context.Background(), 1*time.Minute)
	defer startupCancel()

	var err error
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
		"Google Cloud TTS with Chirp",
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

	if transport == "sse" {
		if port == "" {
			port = "8080"
			log.Printf("Transport is SSE but no port specified, defaulting to %s", port)
		}
		sseServer := server.NewSSEServer(s, server.WithBaseURL(fmt.Sprintf("http://localhost:%s", port)))
		log.Printf("SSE server listening on :%s with tools: chirp_tts, list_chirp_voices", port)
		if err := sseServer.Start(fmt.Sprintf(":%s", port)); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
		log.Println("SSE Server has stopped.")
		if ttsClient != nil {
			ttsClient.Close()
		}
	} else {
		log.Printf("STDIO server listening with tools: chirp_tts, list_chirp_voices")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
		if ttsClient != nil {
			ttsClient.Close()
		}
	}
}

// chirpTTSHandler handles requests for the chirp_tts tool.
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
	pronunciationsParam, _ := request.GetArguments()["pronunciations"] // This will be []interface{} or nil
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

	synthesisAPICallCtx, synthesisAPICallCancel := context.WithTimeout(context.Background(), 30*time.Second)
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

// synthesizeWithVoice now accepts customPronos
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

	trimmedLangParam := strings.TrimSpace(languageParam)
	normalizedInput := strings.ToLower(trimmedLangParam)
	var targetLangCode string
	var directlyResolved bool

	bcp47Code, isNameMatch := LanguageNameToCodeMap[normalizedInput]
	if isNameMatch {
		targetLangCode = bcp47Code
		directlyResolved = true
		log.Printf("Input '%s' directly matched language name. Resolved to BCP-47 code: '%s'", trimmedLangParam, targetLangCode)
	} else {
		for _, codeInMap := range LanguageNameToCodeMap {
			if strings.ToLower(codeInMap) == normalizedInput {
				targetLangCode = codeInMap
				directlyResolved = true
				log.Printf("Input '%s' directly matched BCP-47 code: '%s'", trimmedLangParam, targetLangCode)
				break
			}
		}
	}

	if !directlyResolved {
		log.Printf("Input '%s' not a direct match. Performing broader search for disambiguation.", trimmedLangParam)
		potentialMatches := make(map[string]bool)

		for lcNameKey, originalCasedName := range OriginalLanguageNames {
			bcp47ForThisName := LanguageNameToCodeMap[lcNameKey]
			if strings.Contains(lcNameKey, normalizedInput) || strings.Contains(strings.ToLower(bcp47ForThisName), normalizedInput) {
				potentialMatches[originalCasedName] = true
			}
		}

		if len(potentialMatches) == 0 {
			return mcp.NewToolResultError(fmt.Sprintf("Unsupported language query: '%s'. No matching language names or BCP-47 codes found.", trimmedLangParam)), nil
		}

		if len(potentialMatches) == 1 {
			var singleMatchFullName string
			for name := range potentialMatches {
				singleMatchFullName = name
				break
			}
			targetLangCode = LanguageNameToCodeMap[strings.ToLower(singleMatchFullName)]
			log.Printf("Broad search yielded one match: '%s'. Resolved to BCP-47 code: '%s'", singleMatchFullName, targetLangCode)
		} else {
			var displayNames []string
			for name := range potentialMatches {
				displayNames = append(displayNames, name)
			}
			sort.Strings(displayNames)
			disambiguationMsg := fmt.Sprintf("Your language query '%s' is ambiguous. Please be more specific by choosing one of the following: %s",
				trimmedLangParam, strings.Join(displayNames, ", "))
			log.Println(disambiguationMsg)
			return mcp.NewToolResultText(disambiguationMsg), nil
		}
	}

	if len(availableVoices) == 0 {
		log.Println("No Chirp3-HD voices cached to list.")
		return mcp.NewToolResultText("No Chirp3-HD voices are currently available or cached. Check server logs for details."), nil
	}

	var filteredVoiceInfos []VoiceInfo
	var voiceNameSuffixes []string

	filterLangCodeNormalized := strings.ToLower(targetLangCode)
	log.Printf("Using fully resolved and lowercased targetLangCode for matching: '%s'", filterLangCodeNormalized)

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
		return mcp.NewToolResultText(fmt.Sprintf("No Chirp3-HD voices found for the specified language filter: '%s' (resolved to %s)", trimmedLangParam, targetLangCode)), nil
	}

	sort.Strings(voiceNameSuffixes)

	summaryText := fmt.Sprintf("I've resolved your request for '%s' to the language code '%s'. Found %d voice(s): %s",
		trimmedLangParam,
		targetLangCode,
		len(filteredVoiceInfos),
		strings.Join(voiceNameSuffixes, ", "),
	)

	jsonData, err := json.MarshalIndent(filteredVoiceInfos, "", "  ")
	if err != nil {
		log.Printf("Error marshaling filtered voice list to JSON: %v", err)
		return mcp.NewToolResultError(fmt.Sprintf("Error preparing filtered voice list: %v", err)), nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: summaryText,
			},
			mcp.TextContent{
				Type: "text",
				Text: string(jsonData),
			},
		},
	}, nil
}
