// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Package main contains the sample code for the GenerateContent API.
package main

/*
# For Vertex AI API
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT={YOUR_PROJECT_ID}
export GOOGLE_CLOUD_LOCATION={YOUR_LOCATION}

# For Gemini AI API
export GOOGLE_GENAI_USE_VERTEXAI=false
export GOOGLE_API_KEY={YOUR_API_KEY}

go run samples/generate_audio.go --model=gemini-3.5-flash
*/

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"math/rand"

	genai "google.golang.org/genai"
)

var (
	model        string
	prompt       string
	outputfile   string
	voiceName    string
	allVoices    bool
	geminiVoices = []string{"Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede"}
)

func init() {
	flag.StringVar(&model, "model", "gemini-3.5-flash", "the model name, e.g. gemini-3.5-flash")
	flag.StringVar(&outputfile, "output", "", "the filename for output")
	flag.StringVar(&voiceName, "voice", "", "the voice to use, e.g. Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede")
	flag.BoolVar(&allVoices, "all", false, "generate audio for all voices")
	flag.Parse()
}

func getGeminiVoicesMetadata() []VoiceMetadata {
	geminiVoicesMetadata := []VoiceMetadata{}
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Zephyr",
		Gender: "Female",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Puck",
		Gender: "Male",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Charon",
		Gender: "Male",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Kore",
		Gender: "Female",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Leda",
		Gender: "Female",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Fenrir",
		Gender: "Male",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Orus",
		Gender: "Male",
	})
	geminiVoicesMetadata = append(geminiVoicesMetadata, VoiceMetadata{
		Name:   "Aoede",
		Gender: "Female",
	})
	return geminiVoicesMetadata
}

// generateAllAudio uses all the voices
func generateAllAudio(ctx context.Context) {
	// Create a Gemini client.
	client := createGeminiClient(ctx, projectID)
	// Obtain the prompt.
	prompt = strings.Join(flag.Args(), " ")
	if prompt == "" {
		prompt = "say something nice to me"
	}
	fmt.Println("Voicing:", prompt)
	// Generate and save audio for all voices.
	for _, voiceName := range geminiVoices {
		log.Printf("Voice: %s", voiceName)
		_, err := generateAudio(ctx, client, voiceName, prompt, false)
		if err != nil {
			log.Printf("unable to generated audio: %v", err)
		}
	}
}

// generateSingleAudio uses a single voice
func generateSingleAudio(ctx context.Context) {
	// Create a Gemini client.
	client := createGeminiClient(ctx, projectID)
	// Obtain the prompt.
	prompt = strings.Join(flag.Args(), " ")
	if prompt == "" {
		prompt = "say something nice to me"
	}
	// Determine the voice to use.
	fmt.Println("Voicing:", prompt)
	if voiceName == "" {
		voiceName = randomVoice()
		fmt.Println("Using random voice:", voiceName)
	}
	// Generate and save audio.
	_, err := generateAudio(ctx, client, voiceName, prompt, true)
	if err != nil {
		log.Printf("unable to generated audio: %v", err)
	}
}

func geminiSynthesis(ctx context.Context, prompt string, voiceName string, projectID string) []BabelOutput {
	// Create a Gemini client.
	client := createGeminiClient(ctx, projectID)

	voiceList := []string{}
	outputmetadata := []BabelOutput{}

	// use the single voice if provided
	if voiceName != "" {
		log.Printf("Single voice: %s", voiceName)
		voiceList = []string{voiceName}
	} else {
		voiceList = geminiVoices
		log.Printf("Voicing multiple: %d", len(voiceList))
	}

	for _, voiceName := range voiceList {
		log.Printf("Voicing (%s): %s", voiceName, prompt)
		// Generate and save audio.
		fn, err := generateAudio(ctx, client, voiceName, prompt, true)
		if err != nil {
			log.Printf("unable to generate audio: %v", err)
		}
		metadata := BabelOutput{
			VoiceName: voiceName,
			//LanguageCode: "",
			Text:      prompt,
			AudioPath: fn,
			//Gender:       "",
			//Error:        "",
		}
		if err != nil {
			metadata.Error = fmt.Sprintf("unable to generate audio: %v", err)
		}
		outputmetadata = append(outputmetadata, metadata)
	}

	return outputmetadata
}

// projects temporary list of allowlisted prjects
// var projects = []string{"cloud-llm-preview1", "cloud-llm-preview2", "cloud-llm-preview3", "cloud-llm-preview4"}
// var projects = []string{"genai-blackbelt-fishfooding"}
var projects = []string{projectID}

// createGeminiClient creates a gemini client with either AI Dev or Vertex AI credentials
func createGeminiClient(ctx context.Context, projectID string) *genai.Client {
	// TEMP: random choice from hardcoded projects
	//randomIndex := rand.Intn(len(projects)) // Generate a random index
	//projectID := projects[randomIndex]      // Get the element at the random index
	log.Printf("using project: %s", projectID)

	cc := genai.ClientConfig{
		Project:  projectID,
		Location: location,
	}
	client, err := genai.NewClient(ctx, &cc)
	//client.ClientConfig.Project = projectID
	if err != nil {
		log.Fatal(err)
	}
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		log.Printf("Calling VertexAI.GenerateContent API with project %s ...", client.ClientConfig().Project)
	} else {
		log.Println("Calling GeminiAI.GenerateContent API ...")
	}
	return client
}

// generateAudio is the core method to generate an audio output
func generateAudio(ctx context.Context, client *genai.Client, chosenVoice string, prompt string, prettyprint bool) (string, error) {
	config := &genai.GenerateContentConfig{}
	config.ResponseModalities = []string{"AUDIO"}
	config.SpeechConfig = &genai.SpeechConfig{
		VoiceConfig: &genai.VoiceConfig{
			PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{
				VoiceName: chosenVoice,
			},
		},
	}

	/*
		result, err := client.Models.GenerateContent(ctx, model, genai.Text(prompt), config)
		if err != nil {
			log.Fatal(err)
		}
	*/

	var result *genai.GenerateContentResponse
	var err error

	maxRetries := 4
	retryCount := 0
	duration := 3 * time.Second    // Initial backoff duration
	maxDuration := 1 * time.Minute // Maximum backoff duration

	for retryCount < maxRetries {
		result, err = client.Models.GenerateContent(ctx, model, genai.Text(prompt), config)
		if err == nil {
			break // Success!
		}
		// TODO add break on 403, permission denied
		log.Print(err.Error())

		// retry logic
		retryCount++
		log.Printf("Error: %v, retrying in %v (attempt %d/%d)", err, duration, retryCount, maxRetries)
		time.Sleep(duration) // Wait for the backoff duration
		// Exponential backoff with jitter
		duration *= 2
		duration += time.Duration(rand.Int63n(int64(duration / 2))) // Add jitter
		if duration > maxDuration {
			duration = maxDuration
		}
		// TEMP try again with a random client
		client = createGeminiClient(ctx, projectID)
	}

	if err != nil {
		return "", fmt.Errorf("Failed after %d retries: %v", maxRetries, err)
	}

	if prettyprint {
		prettyPrintJSON(result)
	}

	if result.Candidates[0].FinishReason == "STOP" {
		timestamp := time.Now().Format(timeformat)
		mimeType := result.Candidates[0].Content.Parts[0].InlineData.MIMEType
		ext := getFileExtensionFromMimeType(mimeType)
		var filename string
		if outputfile == "" {
			filename = fmt.Sprintf("%s-%s%s", timestamp, chosenVoice, ext)
		} else {
			filename = outputfile
		}
		audiobytes := result.Candidates[0].Content.Parts[0].InlineData.Data
		err = os.WriteFile(filename, audiobytes, 0644)
		if err != nil {
			log.Println(err)
		}
		log.Printf("Written to %s", filename)
		return filename, nil
	} else {
		log.Printf("Finish reason: %s", result.Candidates[0].FinishReason)
	}

	return "", fmt.Errorf("finish reason: %s", result.Candidates[0].FinishReason)
}

// getFileExtensionFromMimeType extracts the mime type and returns a file extension
func getFileExtensionFromMimeType(mimeType string) string {
	// Split the MIME type string by semicolon
	parts := strings.Split(mimeType, ";")
	// Extract the codec
	var codec string
	for _, part := range parts {
		if strings.HasPrefix(part, "codec=") {
			codec = strings.TrimPrefix(part, "codec=")
			break
		}
	}
	// Determine the file extension based on the codec
	var fileExtension string
	switch codec {
	case "pcm":
		fileExtension = ".wav"
	default:
		fileExtension = fmt.Sprintf(".%s", codec)
	}
	//log.Println("File extension:", fileExtension)
	return fileExtension
}

// randomVoice chooses a random voice
func randomVoice() string {
	source := rand.NewSource(time.Now().UnixNano())
	r := rand.New(source)
	randomIndex := r.Intn(len(geminiVoices))
	chosenVoice := geminiVoices[randomIndex]

	return chosenVoice
}

// prettyPrintJSON redacts long bytes and returns a copy of the response
func prettyPrintJSON(result *genai.GenerateContentResponse) {
	// copy the result so as not to effect the reference
	newResult := &genai.GenerateContentResponse{}
	resultJSON, err := json.Marshal(result)
	if err != nil {
		log.Fatal(err)
	}
	err = json.Unmarshal(resultJSON, newResult)
	if err != nil {
		log.Fatal(err)
	}
	// truncate the data part, if it exists
	if len(newResult.Candidates) > 0 && newResult.Candidates[0].Content != nil {
		if len(newResult.Candidates[0].Content.Parts) > 0 {
			data := newResult.Candidates[0].Content.Parts[0].InlineData.Data
			if len(data) > 40 {
				newResult.Candidates[0].Content.Parts[0].InlineData.Data = append(append(data[:20], []byte("...")...), data[len(data)-20:]...)
			}
		}
	}

	response, err := json.MarshalIndent(newResult, "", "  ")
	if err != nil {
		log.Fatal(err)
	}
	// Log the output.
	fmt.Println(string(response))
}

/*
func main() {
	ctx := context.Background()
	flag.Parse()
	if allVoices {
		log.Print("Generating audio for all voices...")
		generateAllAudio(ctx)

	} else {
		generateSingleAudio(ctx)
	}
}
*/
