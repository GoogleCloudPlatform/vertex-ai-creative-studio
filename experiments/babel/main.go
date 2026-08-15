// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"cloud.google.com/go/storage"
	texttospeech "cloud.google.com/go/texttospeech/apiv1"
	"cloud.google.com/go/texttospeech/apiv1/texttospeechpb"
	"cloud.google.com/go/vertexai/genai"
	"google.golang.org/api/option"

	"github.com/schollz/progressbar/v3"
)

var (
	projectID   string
	location    string
	service     string
	babelbucket string
	babelpath   string
	voices      []*texttospeechpb.Voice
)

var languageDescriptions = map[string]string{
	"es-US": "Mexican Spanish",
}

const timeformat = "20060102.030405.06"

func init() {
	flag.StringVar(&service, "service", "false", "start as service")
	flag.Parse()
}

func main() {
	// project setup
	// Get Google Cloud Project ID from environment variable
	projectID = envCheck("PROJECT_ID", "") // no default
	if projectID == "" {
		log.Fatalf("please set env var PROJECT_ID with google cloud project, e.g. export PROJECT_ID=$(gcloud config get project)")
	}
	// Get Google Cloud Region from environment variable
	location = envCheck("REGION", "us-central1") // default is us-central1

	// get all Chirp-HD voices
	var err error
	voices, err = listChirpHDVoices()
	if err != nil {
		log.Fatalf("cannot listChirpHDVoices: %v", err)
	}
	log.Printf("%d Chirp-HD voices", len(voices))

	// run as service, env var precedence
	service = envCheck("SERVICE", service)

	if service != "false" {
		port := os.Getenv("PORT")
		if port == "" {
			port = "8080"
		}
		babelbucket = envCheck("BABEL_BUCKET", fmt.Sprintf("%s-fabulae", projectID))
		babelpath = envCheck("BABEL_PATH", "babel")
		log.Printf("using gs://%s/%s", babelbucket, babelpath)
		http.HandleFunc("POST /babel", handleSynthesis)
		http.HandleFunc("GET /voices", handleListVoices)
		http.ListenAndServe(fmt.Sprintf(":%s", port), nil)
	}

	// statement ingestion
	statement := strings.Join(flag.Args(), " ")
	log.Printf("original statement: %s", statement)

	// get all languages
	languages := getAllLanguages()

	// translate to each language
	translateSpinner := progressbar.NewOptions(
		-1,
		progressbar.OptionSetDescription("translating statement ..."),
		progressbar.OptionSetWidth(15),
	)
	translateSpinner.Add(1)
	translations := translate(statement, languages)
	translateSpinner.Finish()
	fmt.Println()

	// tts and write to file
	audioGenerationSpinner := progressbar.NewOptions(
		-1,
		progressbar.OptionSetDescription("generating audio ..."),
		progressbar.OptionSetWidth(15),
	)
	audioGenerationSpinner.Add(1)
	outputfiles := generateSpeech(voices, translations)
	audioGenerationSpinner.Finish()
	fmt.Println()
	log.Printf("complete. wrote %d files", len(outputfiles))

}

// BabelOutput represents the metatdata for the translated audio generated
type BabelOutput struct {
	VoiceName    string `json:"voice_name"`
	LanguageCode string `json:"language_code"`
	Text         string `json:"text"`
	AudioPath    string `json:"audio_path"`
	Gender       string `json:"gender"`
	Error        string `json:"-"`
	Length       int    `json:"bytes"`
}

// BabelRequest represents the request to the service
type BabelRequest struct {
	// Statement is the primary statement to voice
	Statement string `json:"statement"`
	// Modifiers are the tone modifiers for Gemini voices
	// these could be "happy", "sad", "angry", "professional", etc.
	Modifiers []string `json:"modifiers"`
	// Instructions is the voicing instruction for Gemini voices
	// typically something like "say the following: "
	Instructions string `json:"instructions"`
	// VoiceName is for a single Gemini Voice generation
	VoiceName string `json:"voiceName"`
}

// BabelResponse represents the response from the service
type BabelResponse struct {
	AudioMetadata []BabelOutput `json:"audio_metadata"`
}

// VoiceMetadata is a minimal set of tts voice metadata
type VoiceMetadata struct {
	Name          string   `json:"name"`
	Gender        string   `json:"gender"`
	LanguageCodes []string `json:"language_codes"`
}

// handleSynthesis generates audio with all Journey voices
func handleSynthesis(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "unable to process body", http.StatusInternalServerError)
		return
	}
	if len(body) == 0 {
		http.Error(w, "no content provided", http.StatusBadRequest)
		return
	}
	log.Printf("%s", body)

	var babelRequest BabelRequest
	err = json.NewDecoder(bytes.NewReader(body)).Decode(&babelRequest)
	if err != nil {
		http.Error(w, "error decoding Fabulae Request", http.StatusInternalServerError)
		return
	}

	log.Print("synthesizing... ")

	// core babel functionality
	// languages
	languages := getAllLanguages()
	// translations
	translations := translate(babelRequest.Statement, languages)
	// generate speech
	outputmetadata := generateSpeech(voices, translations)

	// service additional functionality
	// move to storage bucket
	outputfiles := []string{}
	for _, translation := range outputmetadata {
		outputfiles = append(outputfiles, translation.AudioPath)
	}
	err = moveFilesToAudioBucket(outputfiles)
	if err != nil {
		http.Error(w, "error writing to Storage", http.StatusInternalServerError)
		return
	}
	log.Printf("%d files written to gs://%s/%s", len(outputfiles), babelbucket, babelpath)

	revisedOutput := []BabelOutput{}
	for _, o := range outputmetadata {
		if o.Length > 0 {
			revisedOutput = append(revisedOutput, o)
		}
	}

	response := BabelResponse{}
	response.AudioMetadata = revisedOutput

	w.Header().Set("Content-Type", "application/json")
	//fmt.Fprintf(w, "%s", body)

	err = json.NewEncoder(w).Encode(response)
	if err != nil {
		log.Print(err)
	}
}

// handleListVoices lists all Journey voices
func handleListVoices(w http.ResponseWriter, r *http.Request) {
	voiceMetadata := []VoiceMetadata{}
	for _, v := range voices {
		voiceMetadata = append(voiceMetadata, VoiceMetadata{
			Name:          v.GetName(),
			Gender:        v.GetSsmlGender().String(),
			LanguageCodes: v.GetLanguageCodes(),
		})
	}
	err := json.NewEncoder(w).Encode(voiceMetadata)
	if err != nil {
		log.Print(err)
	}
	w.Header().Set("Content-Type", "application/json")
}

// moveFilesToAudioBucket moves a list of files to the bucket/path provided
func moveFilesToAudioBucket(outputfiles []string) error {
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	parts := strings.Split(fmt.Sprintf("%s/%s", babelbucket, babelpath), "/")
	bucketName := parts[0]
	storagePath := strings.Join(parts[1:], "/")

	for _, audiofile := range outputfiles {
		objectName := fmt.Sprintf("%s/%s", storagePath, audiofile)
		// Check if the file exists locally
		if _, err := os.Stat(audiofile); os.IsNotExist(err) {
			log.Printf("file %s does not exist, skipping", audiofile)
			continue // Skip to the next file
		}

		f, err := os.Open(audiofile)
		if err != nil {
			log.Printf("unable to open file %s: %v", audiofile, err)
			//return err
			continue
		}
		defer f.Close()

		//log.Printf("writing to %s %s", bucketName, objectName)
		o := client.Bucket(bucketName).Object(objectName)

		o = o.If(storage.Conditions{DoesNotExist: true})

		wc := o.NewWriter(ctx)
		if _, err = io.Copy(wc, f); err != nil {
			return fmt.Errorf("io.Copy: %w", err)
		}
		if err := wc.Close(); err != nil {
			return fmt.Errorf("Writer.Close: %w", err)
		}

		err = os.Remove(audiofile)
		if err != nil {
			return fmt.Errorf("os.Remove: %w", err)
		}
	}

	return nil
}

// getAllLanguages returns a list of all unique language codes
func getAllLanguages() []string {
	langsmap := make(map[string]string)
	for _, v := range voices {
		language := v.LanguageCodes[0]
		langsmap[language] = language
	}
	var languages []string
	for lang := range langsmap {
		languages = append(languages, lang)
	}
	return languages
}

// listChirpHDVoices returns all voices with "Chirp-HD" in the name
func listChirpHDVoices() ([]*texttospeechpb.Voice, error) {
	voices := []*texttospeechpb.Voice{}
	ctx := context.Background()

	client, err := texttospeech.NewClient(ctx)
	if err != nil {
		return voices, err
	}

	resp, err := client.ListVoices(ctx, &texttospeechpb.ListVoicesRequest{})
	if err != nil {
		return voices, err
	}

	for _, voice := range resp.Voices {
		/*
			if strings.Contains(voice.Name, "Chirp-HD") {
				voices = append(voices, voice)
			}
		*/

		if strings.Contains(voice.Name, "Chirp3-HD") {
			voices = append(voices, voice)
		}

	}

	return voices, nil
}

// translate takes a primary statement and a list of languages
// and returns the translation of the statement into each of those languages
// this looks like a list of [en-us]"translated statement"
func translate(statement string, languages []string) map[string]string {
	var wg sync.WaitGroup
	results := make(map[string]string)
	resultChan := make(chan map[string]string, len(languages))

	ctx := context.Background()

	for _, language := range languages {
		wg.Add(1)
		go func(ctx context.Context, statement, language string) {
			defer wg.Done()
			// obtain language description, if there is one
			languageDescription := language
			if value, ok := languageDescriptions[language]; ok == true {
				languageDescription = value
			}
			// translation prompt
			prompt := fmt.Sprintf(`
translate this into appropriate vernacular in language %s \"%s\" output only the statement mimicing the level of formality, do not explain why.
translation: `, languageDescription, statement)
			prompt = strings.ReplaceAll(prompt, "\n", "")
			translation, err := generateContent(ctx, prompt)
			if err != nil {
				translation = fmt.Sprintf("couldn't translate to %s: %v", language, err)
			}
			langtrans := make(map[string]string)
			langtrans[language] = translation
			resultChan <- langtrans
		}(ctx, statement, language)
	}

	go func() {
		wg.Wait()
		close(resultChan)
	}()

	for r := range resultChan {
		for k, v := range r {
			results[k] = v
		}
	}

	return results
}

// generateContent calls Gemini using the provided prompt
func generateContent(ctx context.Context, prompt string) (string, error) {
	client, err := genai.NewClient(ctx, projectID, location)
	if err != nil {
		return "", fmt.Errorf("error creating a client: %v", err)
	}
	defer client.Close()

	gemini := client.GenerativeModel("gemini-3.5-flash")
	gemini.SafetySettings = []*genai.SafetySetting{
		{
			Category:  genai.HarmCategoryHarassment,
			Threshold: genai.HarmBlockNone,
		},
		{
			Category:  genai.HarmCategoryDangerousContent,
			Threshold: genai.HarmBlockNone,
		},
	}

	parts := []genai.Part{genai.Text(prompt)}
	resp, err := gemini.GenerateContent(ctx, parts...)
	if err != nil {
		return "", fmt.Errorf("error generating content: %v", err)
	}
	var all []string
	for _, v := range resp.Candidates[0].Content.Parts {
		all = append(all, fmt.Sprintf("%s", v))
	}
	return strings.Join(all, " "), nil
}

// create audio output for each voice given the statement per language
func generateSpeech(voices []*texttospeechpb.Voice, translations map[string]string) []BabelOutput {
	ctx := context.Background()

	var wg sync.WaitGroup
	//results := []string{}
	results := []BabelOutput{}
	resultChan := make(chan BabelOutput, len(voices))

	timestamp := time.Now().Format(timeformat)

	for _, voice := range voices {
		wg.Add(1)
		lang := voice.GetLanguageCodes()[0]
		text := translations[lang]
		//log.Printf("%s %s %s: %s", voice.GetName(), lang, voice.GetSsmlGender(), text)

		go func(voice *texttospeechpb.Voice, text, timestamp string) {
			defer wg.Done()
			outputmetadata := BabelOutput{
				VoiceName:    voice.GetName(),
				LanguageCode: voice.GetLanguageCodes()[0],
				Text:         text,
				Gender:       voice.GetSsmlGender().String(),
			}
			audiobytes, err := synthesizeWithVoice(ctx, voice, text)
			if err != nil {
				outputmetadata.Error = fmt.Sprintf("error goroutine: text %s; voice: %s", text, voice.GetName())
				resultChan <- outputmetadata
				//resultChan <- fmt.Sprintf("error goroutine: text %s; voice: %s", text, voice.GetName())
			}
			filename := fmt.Sprintf("%s-%s-%s-%s.wav", timestamp, voice.GetName(), voice.GetLanguageCodes()[0], voice.GetSsmlGender())
			outputmetadata.AudioPath = filename
			outputmetadata.Length = len(audiobytes)
			if len(audiobytes) == 0 {
				//log.Printf("%s is zero bytes", filename)
				outputmetadata.Error = fmt.Sprintf("%s voice generated 0 bytes", voice.GetName())
				resultChan <- outputmetadata
			} else {
				err = os.WriteFile(filename, audiobytes, 0644)
				if err != nil {
					//resultChan <- fmt.Sprintf("unable to write to %s: %v", filename, err)
					outputmetadata.Error = fmt.Sprintf("unable to write to %s: %v", filename, err)
				}
			}
			/* log.Printf(" %s Audio content (%7d bytes) written to file: %v",
				voice.GetName(),
				len(audiobytes),
				filename,
			) */
			//resultChan <- filename
			resultChan <- outputmetadata
		}(voice, text, timestamp)

	}
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	for r := range resultChan {
		results = append(results, r)
	}

	return results
}

// synthesizeWithVoice takes a string and a voice and returns audio bytes using GCP TTS
func synthesizeWithVoice(ctx context.Context, voice *texttospeechpb.Voice, turn string) ([]byte, error) {

	opts := []option.ClientOption{}
	client, err := texttospeech.NewClient(ctx, opts...)
	if err != nil {
		return []byte{}, err
	}
	defer client.Close()

	voiceParams := &texttospeechpb.VoiceSelectionParams{
		LanguageCode: voice.GetLanguageCodes()[0],
		Name:         voice.GetName(),
		SsmlGender:   voice.GetSsmlGender(),
	}

	//log.Printf("Using: %s", jsonify(voice))
	req := texttospeechpb.SynthesizeSpeechRequest{
		Input: &texttospeechpb.SynthesisInput{
			InputSource: &texttospeechpb.SynthesisInput_Text{Text: turn},
		},
		Voice: voiceParams,
		AudioConfig: &texttospeechpb.AudioConfig{
			AudioEncoding: texttospeechpb.AudioEncoding_LINEAR16,
		},
	}
	resp, err := client.SynthesizeSpeech(ctx, &req)
	if err != nil {
		return []byte{}, err
	}
	return resp.AudioContent, nil
}

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
