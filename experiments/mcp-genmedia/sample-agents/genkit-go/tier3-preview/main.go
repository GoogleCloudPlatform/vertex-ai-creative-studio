// Copyright 2026 Google LLC
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

// ============================================================================
// PREVIEW — Tier 3 uses EXPERIMENTAL Genkit `.../exp` packages behind
// genkit.WithExperimental(). The API is NOT stable, is pinned to
// github.com/firebase/genkit/go v1.13.1, and MAY BREAK on upgrade. This tier is
// additive and self-contained: NOTHING in Tiers 0-2 depends on it. It is a
// flourish, not the series' foundation.
// ============================================================================
//
// Command tier3-preview is the PREVIEW capstone of the Genkit Go genmedia
// series: an "agentic producer". Where Tier 2 sequenced four servers in a fixed
// Go order (the CODE picks the order, the MODEL picks each tool), Tier 3 hands
// the sequencing to an ORCHESTRATOR agent that DELEGATES to specialist
// sub-agents, and PAUSES for human approval (a tool interrupt) before the
// expensive Veo render.
//
// The distinctively-Genkit shape this tier shows in the Dev-UI trace:
//
//	orchestrator (agent, Agents middleware)
//	  ├─ delegate_to_image   -> image-agent : nanobanana still  + verify_by_listing
//	  ├─ approve_video_render -> INTERRUPT: pause for human approve/reject
//	  ├─ delegate_to_video   -> video-agent : veo_render (GATED) + verify_by_listing
//	  ├─ delegate_to_music   -> music-agent : lyria score       + verify_by_listing
//	  └─ delegate_to_av      -> av-agent    : avtool mux         + verify_by_listing
//
// TWO EXPERIMENTAL-API CORRECTIONS vs the design (verified against the real
// v1.13.1 source; see tier3-dev-notes.md for the full list):
//
//  1. FileSessionStore is constructed with
//     localstore.NewFileSessionStore[State](dir) from
//     github.com/firebase/genkit/go/ai/exp/localstore, not a bare
//     `FileSessionStore{}`.
//  2. INTERACTIVE SUB-AGENT INTERRUPTS ARE NOT SUPPORTED in v1.13.1. The Agents
//     middleware turns a sub-agent's interrupt into a plain tool response to the
//     orchestrator ("interactive sub-agent interaction is a future feature" —
//     plugins/middleware/exp/agents.go). So the human-in-the-loop interrupt
//     CANNOT live inside the video sub-agent. It lives on the ORCHESTRATOR as an
//     interruptible tool (approve_video_render), which is where interrupts DO
//     surface to the client. The Veo render is then made impossible-without-
//     approval by a process-level gate the approval flips (see renderGate): the
//     video-agent's veo_render tool refuses until the gate is open. This is the
//     bulletproof, honest adaptation of "an interrupt on the video step".
//
// Run it with the Dev UI to watch the delegation + the interrupt pause/resume:
//
//	export GOOGLE_CLOUD_PROJECT=your-project
//	export GENMEDIA_BUCKET=gs://your-bare-bucket   # bare bucket, NO path
//	export GOOGLE_CLOUD_LOCATION=us-central1
//	genkit start -- go run ./tier3-preview            # then open localhost:4000
//
// Or headless (this program drives the approve/reject resume programmatically,
// because the genkit CLI/Dev-UI is not required to run it):
//
//	go run ./tier3-preview            # approve path: renders the video
//	go run ./tier3-preview -reject    # reject path: halts before the render
//
// See README.md for the full walkthrough and the PREVIEW banner.
package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/ai/exp/localstore"
	"github.com/firebase/genkit/go/ai/exp/tool"
	"github.com/firebase/genkit/go/genkit"
	genkitx "github.com/firebase/genkit/go/genkit/exp"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	middlewarex "github.com/firebase/genkit/go/plugins/middleware/exp"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/sample-agents/genkit-go/internal/genmedia"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/sample-agents/genkit-go/internal/verify"
)

// modelName orchestrates delegation and drives each specialist. Single-sourced
// here; matches Tiers 0-2 ("vertexai/..." is the googlegenai plugin's Vertex
// provider). Overridable via TIER3_MODEL for experimentation.
const defaultModel = "vertexai/gemini-2.5-flash"

// Load-bearing genmedia model ids (same footguns as Tier 2, distributed into the
// specialists). veo with no model falls back to veo-2.0 which rejects
// generate_audio=true; lyria's clip-preview routes through the global
// Interactions API so it runs alongside the us-central1 image/video steps.
const (
	veoModel   = "veo-3.1-fast-generate-001"
	lyriaModel = "lyria-3-clip-preview"
)

// producerServers are the four genmedia servers, partitioned across sub-agents.
var producerServers = []string{"nanobanana", "veo", "lyria", "avtool"}

// requiredTools are the exact namespaced tool names each specialist depends on.
// mcp.NewMCPHost logs-and-continues on a failed connect, so we PROVE every
// server is present before defining any agent (same guard as Tier 2).
var requiredTools = []string{
	"nanobanana_nanobanana_image_generation",
	"veo_veo_i2v",
	"lyria_lyria_generate_music",
	"avtool_ffmpeg_combine_audio_and_video",
}

// renderGate is the process-level approval gate that makes the Veo render
// impossible without human approval. The orchestrator's approve_video_render
// interrupt flips it open; the video-agent's veo_render tool refuses until it
// is. This compensates for the v1.13.1 limitation that a sub-agent cannot itself
// hold an interactive interrupt (see the package banner, correction #2).
type renderGate struct {
	mu       sync.Mutex
	approved bool
}

func (g *renderGate) open()        { g.mu.Lock(); g.approved = true; g.mu.Unlock() }
func (g *renderGate) isOpen() bool { g.mu.Lock(); defer g.mu.Unlock(); return g.approved }

// RenderApproval is the typed payload the approval interrupt hands the client so
// a human knows what they are approving before the expensive render.
type RenderApproval struct {
	ImageURI    string `json:"imageUri"`
	VideoPrompt string `json:"videoPrompt"`
	VideoDest   string `json:"videoDest"`
	Model       string `json:"model"`
}

// ApprovalDecision is the resume payload the client sends back into the
// approve_video_render tool when it resolves the interrupt.
type ApprovalDecision struct {
	Approved bool `json:"approved"`
}

// ApproveInput / ApproveOutput are the approval tool's model-facing contract.
type ApproveInput struct {
	ImageURI    string `json:"imageUri" jsonschema_description:"The confirmed gs:// URI of the still to animate"`
	VideoPrompt string `json:"videoPrompt" jsonschema_description:"The motion/camera description for the clip"`
	VideoDest   string `json:"videoDest" jsonschema_description:"The gs:// destination the clip will be written to"`
}
type ApproveOutput struct {
	Decision string `json:"decision"`
	Detail   string `json:"detail"`
}

// RenderInput / RenderOutput are the video-agent's veo_render tool contract.
type RenderInput struct {
	ImageURI string `json:"imageUri" jsonschema_description:"The confirmed gs:// URI of the still to animate"`
	Motion   string `json:"motion" jsonschema_description:"The motion/camera description for the clip"`
	Dest     string `json:"dest" jsonschema_description:"The gs:// destination (bucket+prefix) to write the clip to"`
}
type RenderOutput struct {
	VideoURI string `json:"videoUri"`
}

// VerifyInput / VerifyOutput are the shared verify_by_listing tool contract. It
// is the heart of the series' discipline: prove an artifact by LISTING its
// destination, never by trusting a tool's resource_link.
type VerifyInput struct {
	Dest       string `json:"dest" jsonschema_description:"The gs:// destination or prefix to list"`
	WantSuffix string `json:"wantSuffix,omitempty" jsonschema_description:"Optional: return the leaf ending with this suffix (e.g. \".mp4\")"`
}
type VerifyOutput struct {
	Found   bool     `json:"found"`
	URI     string   `json:"uri,omitempty"`
	Entries []string `json:"entries,omitempty"`
}

func main() {
	reject := flag.Bool("reject", false, "resolve the video-render interrupt by REJECTING it (demonstrates the halt-before-render path)")
	flag.Parse()

	subject := ""
	if args := flag.Args(); len(args) > 0 {
		subject = strings.Join(args, " ")
	}

	if err := run(context.Background(), *reject, subject); err != nil {
		log.Fatalf("tier3-preview: %v", err)
	}
}

func run(ctx context.Context, reject bool, subject string) error {
	project := firstEnv("GOOGLE_CLOUD_PROJECT", "PROJECT_ID")
	if project == "" {
		return fmt.Errorf("set GOOGLE_CLOUD_PROJECT (or PROJECT_ID) to your Google Cloud project")
	}
	location := firstEnv("GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_REGION")
	if location == "" {
		location = "us-central1"
	}
	base := os.Getenv("GENMEDIA_BUCKET")
	if base == "" {
		return fmt.Errorf("set GENMEDIA_BUCKET to a gs:// bucket for the generated artifacts")
	}
	// Same bare-bucket footgun as Tier 2: lyria and avtool take a bucket NAME
	// only (they strip gs:// and write at the root), while nanobanana/veo accept
	// a bucket+prefix. Standardize on a bare bucket and add per-run structure.
	bucket, err := bareBucket(base)
	if err != nil {
		return err
	}
	modelName := firstEnv("TIER3_MODEL")
	if modelName == "" {
		modelName = defaultModel
	}

	// Per-run destinations. The CODE owns these so it can prove every artifact by
	// listing at the end, independent of what the LLM reports. The orchestrator
	// is TOLD these destinations and passes them to each specialist.
	id := runID()
	imageDest := gcsJoin(base, id, "image")           // nanobanana: gcs_bucket_uri (bucket+prefix OK)
	videoDest := gcsJoin(base, id, "video")           // veo: bucket (bucket+prefix OK; writes <jobid>/ under it)
	musicName := id + "-score"                        // lyria: output_filename base (ext forced by server)
	musicPrefix := "gs://" + bucket + "/" + musicName // where lyria writes
	finalName := id + "-final.mp4"                    // avtool: output_filename
	finalURI := "gs://" + bucket + "/" + finalName    // where avtool writes

	// EXPERIMENTAL: genkit.WithExperimental() is REQUIRED for the exp agent APIs
	// (genkitx.DefineAgent / DefineInterruptibleTool, the Agents/Artifacts
	// middleware). Registering the middleware plugin makes the middleware
	// resolvable by name in the Dev UI; using them via ai.WithUse does not
	// require it, but it keeps `genkit start` reflection tidy.
	g := genkit.Init(ctx,
		genkit.WithPlugins(
			&googlegenai.VertexAI{ProjectID: project, Location: location},
			&middlewarex.Middleware{},
		),
		genkit.WithExperimental(),
	)

	// Connect to all four genmedia servers through the shared multi-server host
	// (reused from Tier 2), then confirm every required tool is present.
	host, err := genmedia.NewHost(ctx, g, producerServers...)
	if err != nil {
		return fmt.Errorf("creating multi-server genmedia host: %w", err)
	}
	for _, s := range producerServers {
		defer host.Disconnect(ctx, s)
	}
	tools, err := host.GetActiveTools(ctx, g)
	if err != nil {
		return fmt.Errorf("listing multi-server tools: %w", err)
	}
	if err := requireTools(tools, requiredTools); err != nil {
		return err
	}
	log.Printf("connected: %d server(s), %d tool(s) total", len(producerServers), len(tools))

	veoTool := findTool(tools, "veo_veo_i2v")
	if veoTool == nil {
		return fmt.Errorf("veo_veo_i2v tool not found after requireTools passed (should be impossible)")
	}

	gate := &renderGate{}

	// ------------------------------------------------------------------ tools
	// verify_by_listing: the shared verify-by-listing tool. Every specialist
	// calls it to CONFIRM its output exists and get the exact leaf gs:// URI to
	// report upward — never trusting the media tool's resource_link.
	verifyTool := genkitx.DefineTool(g, "verify_by_listing",
		"Confirm a generated artifact by LISTING its Google Cloud Storage destination and return its exact gs:// leaf URI. "+
			"ALWAYS call this after generating media; a tool's resource_link is NOT proof of success.",
		func(ctx context.Context, in VerifyInput) (VerifyOutput, error) {
			res, err := verify.VerifyRecursive(ctx, in.Dest)
			if err != nil {
				return VerifyOutput{}, fmt.Errorf("verify_by_listing %s: %w", in.Dest, err)
			}
			log.Printf("verify_by_listing: %s", res)
			for _, e := range res.Entries {
				log.Printf("  - %s", e)
			}
			if !res.Exists || len(res.Entries) == 0 {
				return VerifyOutput{Found: false}, nil
			}
			uri := res.Entries[0]
			if in.WantSuffix != "" {
				uri = ""
				for _, e := range res.Entries {
					if strings.HasSuffix(e, in.WantSuffix) {
						uri = e
						break
					}
				}
				if uri == "" {
					return VerifyOutput{Found: false, Entries: res.Entries}, nil
				}
			}
			return VerifyOutput{Found: true, URI: uri, Entries: res.Entries}, nil
		})

	// veo_render: the GATED Veo render. It refuses until a human has approved via
	// approve_video_render (the gate). This is what guarantees "the Veo render
	// only runs post-approval" even though the interrupt itself cannot live in
	// this sub-agent (v1.13.1 limitation). Params are hand-set (verified against
	// the veo server source: image_uri/prompt/model/bucket/num_videos/
	// generate_audio) so the render is deterministic, then verified by listing.
	renderTool := genkitx.DefineTool(g, "veo_render",
		"Render a short video clip from an input still using Veo 3. REQUIRES prior human approval; "+
			"it will refuse if the render has not been approved. Returns the confirmed gs:// URI of the clip.",
		func(ctx context.Context, in RenderInput) (RenderOutput, error) {
			if !gate.isOpen() {
				return RenderOutput{}, fmt.Errorf("veo_render refused: the human has not approved this render. " +
					"The orchestrator must call approve_video_render and receive approval first")
			}
			log.Printf("veo_render: APPROVED — calling veo_veo_i2v (image=%s dest=%s)", in.ImageURI, in.Dest)
			args := map[string]any{
				"image_uri":      in.ImageURI,
				"prompt":         in.Motion,
				"model":          veoModel,
				"bucket":         in.Dest,
				"num_videos":     1,
				"generate_audio": true,
			}
			if _, err := veoTool.RunRaw(ctx, args); err != nil {
				return RenderOutput{}, fmt.Errorf("veo render failed: %w", err)
			}
			// veo writes into a server-assigned <jobid>/ subfolder; list recursively
			// for the .mp4 leaf.
			res, err := verify.VerifyRecursive(ctx, in.Dest)
			if err != nil {
				return RenderOutput{}, fmt.Errorf("verifying veo output: %w", err)
			}
			log.Printf("veo_render verify: %s", res)
			for _, e := range res.Entries {
				log.Printf("  - %s", e)
			}
			for _, e := range res.Entries {
				if strings.HasSuffix(e, ".mp4") {
					return RenderOutput{VideoURI: e}, nil
				}
			}
			return RenderOutput{}, fmt.Errorf("no .mp4 found under %s after veo render", in.Dest)
		})

	// approve_video_render: the ORCHESTRATOR's interruptible tool. On the first
	// call (res==nil) it PAUSES with a typed RenderApproval payload; the client
	// resolves the interrupt with an ApprovalDecision. On approval it OPENS the
	// gate; on rejection it leaves it shut. This is the human-in-the-loop step,
	// and it lives on the orchestrator because that is where interrupts surface.
	approveTool := genkitx.DefineInterruptibleTool(g, "approve_video_render",
		"Ask a human to approve the expensive Veo video render before it runs. Call this AFTER the still "+
			"is ready and BEFORE delegating to the video agent. Pass the still URI and the motion prompt.",
		func(ctx context.Context, in ApproveInput, res *ApprovalDecision) (ApproveOutput, error) {
			if res == nil {
				log.Printf("approve_video_render: PAUSING for human approval (image=%s dest=%s)", in.ImageURI, in.VideoDest)
				return ApproveOutput{}, tool.Interrupt(RenderApproval{
					ImageURI:    in.ImageURI,
					VideoPrompt: in.VideoPrompt,
					VideoDest:   in.VideoDest,
					Model:       veoModel,
				})
			}
			if res.Approved {
				gate.open()
				log.Printf("approve_video_render: APPROVED by human — render gate opened")
				return ApproveOutput{Decision: "approved", Detail: "The human APPROVED the render. You may now delegate_to_video."}, nil
			}
			log.Printf("approve_video_render: REJECTED by human — render gate stays shut")
			return ApproveOutput{Decision: "rejected", Detail: "The human REJECTED the render. Do NOT delegate_to_video; stop and report that the render was declined."}, nil
		})

	// ------------------------------------------------------------ sub-agents
	// Each specialist gets the shared quirks fragment (the footguns the LLM can't
	// see), its own server's tool(s), the shared verify_by_listing tool, and the
	// Artifacts middleware so its output can be merged into the orchestrator's
	// session (ArtifactStrategySession). Sub-agents have NO session store: each
	// delegation runs them one-shot (client-managed), which is what lets the
	// orchestrator forward recent history to them (Agents.HistoryLength).
	imageAgent := genkitx.DefineAgent(g, "image-agent",
		aix.InlinePrompt{
			ai.WithModelName(modelName),
			ai.WithSystem(genmedia.QuirksPrompt + "\n\nYOU ARE THE IMAGE SPECIALIST. Generate ONE still image with the tool " +
				"nanobanana_nanobanana_image_generation, writing it to Google Cloud Storage via gcs_bucket_uri set to the " +
				"destination in your task. Then call verify_by_listing on that same destination to confirm it and get the exact " +
				"gs:// URI. Report that URI on its own line as: IMAGE_URI=<uri>. Be brief."),
			ai.WithTools(append(refsWithPrefix(tools, "nanobanana_"), verifyTool)...),
			ai.WithToolChoice(ai.ToolChoiceAuto),
			ai.WithMaxTurns(8),
			ai.WithUse(&middlewarex.Artifacts{}),
		},
		aix.WithDescription[any]("Generates a still image with nanobanana and confirms it by listing."),
	)

	videoAgent := genkitx.DefineAgent(g, "video-agent",
		aix.InlinePrompt{
			ai.WithModelName(modelName),
			ai.WithSystem(genmedia.QuirksPrompt + "\n\nYOU ARE THE VIDEO SPECIALIST. Render ONE clip from the input still using the " +
				"tool veo_render. Pass imageUri, motion, and dest exactly as given in your task. veo_render is human-gated and will " +
				"refuse if the render was not approved; if it refuses, report the refusal and stop. On success it returns the confirmed " +
				"clip URI — report it on its own line as: VIDEO_URI=<uri>. Be brief."),
			ai.WithTools(renderTool),
			ai.WithToolChoice(ai.ToolChoiceAuto),
			ai.WithMaxTurns(6),
			ai.WithUse(&middlewarex.Artifacts{}),
		},
		aix.WithDescription[any]("Renders a video clip from a still with Veo — human-gated before the render."),
	)

	musicAgent := genkitx.DefineAgent(g, "music-agent",
		aix.InlinePrompt{
			ai.WithModelName(modelName),
			ai.WithSystem(genmedia.QuirksPrompt + "\n\nYOU ARE THE MUSIC SPECIALIST. Compose ONE short score with the tool " +
				"lyria_lyria_generate_music, using model_id " + lyriaModel + ", output_gcs_bucket set to the BARE bucket name in your " +
				"task, and output_filename set to the base name in your task. Then call verify_by_listing on the gs:// prefix in your " +
				"task to confirm it and get the exact gs:// URI (lyria forces the extension, so list by prefix). Report it on its own " +
				"line as: MUSIC_URI=<uri>. Be brief."),
			ai.WithTools(append(refsWithPrefix(tools, "lyria_"), verifyTool)...),
			ai.WithToolChoice(ai.ToolChoiceAuto),
			ai.WithMaxTurns(8),
			ai.WithUse(&middlewarex.Artifacts{}),
		},
		aix.WithDescription[any]("Composes a music score with lyria and confirms it by listing."),
	)

	avAgent := genkitx.DefineAgent(g, "av-agent",
		aix.InlinePrompt{
			ai.WithModelName(modelName),
			ai.WithSystem(genmedia.QuirksPrompt + "\n\nYOU ARE THE AUDIO/VIDEO SPECIALIST. Mux the given clip and score into one scored " +
				"video with the tool avtool_ffmpeg_combine_audio_and_video: set input_video_uri and input_audio_uri to the URIs in your " +
				"task, output_gcs_bucket to the BARE bucket name, and output_filename to the name in your task. Then call verify_by_listing " +
				"on the output gs:// URI to confirm it. Report it on its own line as: FINAL_URI=<uri>. Be brief."),
			ai.WithTools(append(refsWithPrefix(tools, "avtool_"), verifyTool)...),
			ai.WithToolChoice(ai.ToolChoiceAuto),
			ai.WithMaxTurns(8),
			ai.WithUse(&middlewarex.Artifacts{}),
		},
		aix.WithDescription[any]("Muxes a clip and a score into one scored video with avtool and confirms it by listing."),
	)

	// ---------------------------------------------------------- orchestrator
	// The orchestrator uses the Agents middleware (auto-injects delegate_to_<name>
	// tools + lists the sub-agents in its system prompt) with ArtifactStrategySession
	// (merge sub-agent artifacts into this session), plus the Artifacts middleware
	// read-only (so it can review merged artifacts) and the approve_video_render
	// interrupt. A FileSessionStore persists the conversation so the Dev UI can
	// resume it. The system prompt hard-codes this run's destinations so the
	// orchestrator threads exact gs:// URIs between specialists.
	store, err := localstore.NewFileSessionStore[any]("./.genkit/snapshots/producer")
	if err != nil {
		return fmt.Errorf("creating session store: %w", err)
	}

	orchestratorSystem := fmt.Sprintf(`You are an agentic video PRODUCER. You do not call media tools yourself; you
DELEGATE to specialist sub-agents (image, video, music, av) via their
delegate_to_<name> tools, and you PAUSE for human approval before the expensive
video render.

This run's fixed destinations (pass them verbatim in each delegation task):
- IMAGE  -> gcs_bucket_uri = %q
- VIDEO  -> dest           = %q
- MUSIC  -> output_gcs_bucket = %q  (BARE bucket) ; output_filename = %q
- FINAL  -> output_gcs_bucket = %q  (BARE bucket) ; output_filename = %q

Follow these steps IN ORDER, one tool call per turn, and copy each returned
gs:// URI VERBATIM into the next step:

1. delegate_to_image: ask it to generate the still (subject in the user's
   request) at the IMAGE destination and report IMAGE_URI.
2. approve_video_render: pass imageUri=<the IMAGE_URI>, the motion/camera
   videoPrompt, and videoDest=<the VIDEO dest>. This PAUSES for a human.
   - If the result decision is "approved": continue to step 3.
   - If the result decision is "rejected": STOP. Do not delegate_to_video.
     Give a brief final answer saying the render was declined and list the
     still you did produce.
3. delegate_to_video: pass imageUri=<the IMAGE_URI>, the motion, and
   dest=<the VIDEO dest>. It returns VIDEO_URI.
4. delegate_to_music: ask it to compose a score (mood in the user's request)
   to the MUSIC destination and report MUSIC_URI.
5. delegate_to_av: pass input_video_uri=<VIDEO_URI>, input_audio_uri=<MUSIC_URI>,
   and the FINAL destination. It returns FINAL_URI.
6. Give a brief final answer listing IMAGE_URI, VIDEO_URI, MUSIC_URI, FINAL_URI.

Before each delegation or the approval call, send one short sentence saying what
you are about to do. Never skip the approval step, and never delegate to the
video agent before approval.`,
		imageDest, videoDest, bucket, musicName, bucket, finalName)

	orchestrator := genkitx.DefineAgent(g, "producer",
		aix.InlinePrompt{
			ai.WithModelName(modelName),
			ai.WithSystem(orchestratorSystem),
			ai.WithTools(approveTool),
			ai.WithToolChoice(ai.ToolChoiceAuto),
			ai.WithMaxTurns(24),
			ai.WithUse(
				&middlewarex.Agents{
					Agents:           []aix.AgentRef{imageAgent.Ref(), videoAgent.Ref(), musicAgent.Ref(), avAgent.Ref()},
					MaxDelegations:   10,
					HistoryLength:    12,
					ArtifactStrategy: middlewarex.ArtifactStrategySession,
				},
				&middlewarex.Artifacts{Readonly: true},
			),
		},
		aix.WithSessionStore(store),
		aix.WithDescription[any]("Agentic producer: delegates to image/video/music/av specialists and gates the Veo render on human approval."),
	)

	// ------------------------------------------------------------------ drive
	if subject == "" {
		subject = "a photorealistic red panda sitting on a moss-covered rock in a misty forest at dawn"
	}
	userTask := fmt.Sprintf("Produce a short scored video. Subject for the still: %s. "+
		"Motion for the clip: a slow, gentle camera push-in with drifting mist and subtle movement. "+
		"Mood for the score: a calm, warm ambient piece — soft piano and airy strings, unhurried and gently hopeful.", subject)

	approve := !reject
	log.Printf("run %s: driving orchestrator (interrupt will be %s); image=%s video=%s music=%s final=%s",
		id, decisionWord(approve), imageDest, videoDest, musicPrefix, finalURI)

	out, err := driveOrchestrator(ctx, orchestrator, approveTool, userTask, approve)
	if err != nil {
		return err
	}
	log.Printf("orchestrator finished: reason=%s snapshot=%s", out.FinishReason, out.SnapshotID)
	if out.Error != nil {
		log.Printf("orchestrator error: %s: %s", out.Error.Status, out.Error.Message)
	}
	if out.Message != nil {
		if txt := strings.TrimSpace(out.Message.Text()); txt != "" {
			log.Printf("orchestrator final answer:\n%s", txt)
		}
	}

	// -------------------------------------------------- authoritative evidence
	// Prove artifacts by LISTING the destinations the code owns — independent of
	// the LLM's textual report. This is the success gate, same discipline as
	// Tiers 0-2.
	log.Printf("==== VERIFY-BY-LISTING (authoritative) ====")
	imageURI, imgErr := reportLeaf(ctx, "image", imageDest, "")
	if !approve {
		// Reject path: the video, and therefore the mux, must NOT exist.
		videoRes, _ := verify.VerifyRecursive(ctx, videoDest)
		if videoRes.Exists {
			return fmt.Errorf("REJECT PATH VIOLATED: a video artifact exists at %s despite rejection: %v", videoDest, videoRes.Entries)
		}
		log.Printf("reject path OK: no video at %s (the gate held; the Veo render never ran)", videoDest)
		if imgErr != nil {
			log.Printf("note: image not confirmed on reject path (%v) — acceptable if the orchestrator stopped early", imgErr)
		} else {
			log.Printf("reject path produced only the still: %s", imageURI)
		}
		if gate.isOpen() {
			return fmt.Errorf("REJECT PATH VIOLATED: render gate is open after a rejection")
		}
		return nil
	}

	// Approve path: every artifact must exist.
	videoURI, err := reportLeaf(ctx, "video", videoDest, ".mp4")
	if err != nil {
		return err
	}
	musicURI, err := reportLeaf(ctx, "music", musicPrefix, "")
	if err != nil {
		return err
	}
	finalConfirmed, err := reportLeaf(ctx, "final", finalURI, "")
	if err != nil {
		return err
	}
	if imgErr != nil {
		return imgErr
	}
	log.Printf("==== DONE (approve path) ====")
	log.Printf("image=%s", imageURI)
	log.Printf("video=%s", videoURI)
	log.Printf("music=%s", musicURI)
	log.Printf("final=%s", finalConfirmed)
	return nil
}

// driveOrchestrator opens a connection to the orchestrator, sends the task, and
// consumes the stream — logging delegation/tool calls and, when the
// approve_video_render tool interrupts, resolving it programmatically with the
// approve/reject decision (the stand-in for a human at the Dev UI). It loops
// because a resumed turn can interrupt again. This mirrors what the Dev UI does
// interactively; here it is headless so the live run needs no CLI installed.
func driveOrchestrator(ctx context.Context, a *aix.Agent[any], approveTool *aix.InterruptibleTool[ApproveInput, ApproveOutput, ApprovalDecision], task string, approve bool) (*aix.AgentOutput[any], error) {
	conn, err := a.Connect(ctx)
	if err != nil {
		return nil, fmt.Errorf("connecting to orchestrator: %w", err)
	}
	defer conn.Close()

	if err := conn.SendText(task); err != nil {
		return nil, fmt.Errorf("sending task: %w", err)
	}

	for {
		var interrupts []*ai.Part
		var ended bool
		for chunk, rerr := range conn.Receive() {
			if rerr != nil {
				return nil, fmt.Errorf("receiving from orchestrator: %w", rerr)
			}
			if mc := chunk.ModelChunk; mc != nil {
				if t := strings.TrimSpace(mc.Text()); t != "" {
					log.Printf("[producer] %s", t)
				}
				for _, p := range mc.Content {
					switch {
					case p.IsInterrupt():
						interrupts = append(interrupts, p)
					case p.IsToolRequest() && !p.ToolRequest.Partial:
						log.Printf("[producer] -> tool %s %s", p.ToolRequest.Name, compactJSON(p.ToolRequest.Input))
					}
				}
			}
			if chunk.Artifact != nil {
				log.Printf("[producer] artifact: %s", chunk.Artifact.Name)
			}
			if chunk.TurnEnd != nil {
				ended = true
				break
			}
		}
		if len(interrupts) == 0 {
			if ended {
				break
			}
			break
		}
		// Resolve every interrupt with the approve/reject decision.
		resume := &aix.ToolResume{}
		for _, ip := range interrupts {
			if meta, ok := tool.InterruptAs[RenderApproval](ip); ok {
				log.Printf("[human] approval requested: render %s -> %s (%s); deciding: %s",
					meta.ImageURI, meta.VideoDest, meta.Model, decisionWord(approve))
			}
			part, perr := approveTool.Resume(ip, ApprovalDecision{Approved: approve})
			if perr != nil {
				return nil, fmt.Errorf("building resume part: %w", perr)
			}
			resume.Restart = append(resume.Restart, part)
		}
		if err := conn.SendResume(resume); err != nil {
			return nil, fmt.Errorf("sending resume: %w", err)
		}
		// Loop to consume the resumed continuation.
	}

	return conn.Output()
}

// reportLeaf lists dest and returns the chosen leaf URI (by suffix, else first),
// logging what it found. It is the authoritative, code-owned verify-by-listing.
func reportLeaf(ctx context.Context, label, dest, wantSuffix string) (string, error) {
	res, err := verify.VerifyRecursive(ctx, dest)
	if err != nil {
		return "", fmt.Errorf("verify %s at %s: %w", label, dest, err)
	}
	log.Printf("verify %s: %s", label, res)
	for _, e := range res.Entries {
		log.Printf("  - %s", e)
	}
	if !res.Exists || len(res.Entries) == 0 {
		return "", fmt.Errorf("no %s artifact found at %s", label, dest)
	}
	if wantSuffix != "" {
		for _, e := range res.Entries {
			if strings.HasSuffix(e, wantSuffix) {
				return e, nil
			}
		}
		return "", fmt.Errorf("no %s%s artifact found under %s", label, wantSuffix, dest)
	}
	return res.Entries[0], nil
}

// findTool returns the aggregated tool with the exact namespaced name, or nil.
func findTool(tools []ai.Tool, name string) ai.Tool {
	for _, t := range tools {
		if t.Name() == name {
			return t
		}
	}
	return nil
}

// refsWithPrefix returns the tools whose namespaced name starts with prefix, as
// []ai.ToolRef ready for ai.WithTools.
func refsWithPrefix(tools []ai.Tool, prefix string) []ai.ToolRef {
	var refs []ai.ToolRef
	for _, t := range tools {
		if strings.HasPrefix(t.Name(), prefix) {
			refs = append(refs, t)
		}
	}
	return refs
}

// requireTools confirms every required namespaced tool name is present.
func requireTools(tools []ai.Tool, required []string) error {
	present := make(map[string]bool, len(tools))
	for _, t := range tools {
		present[t.Name()] = true
	}
	var missing []string
	for _, name := range required {
		if !present[name] {
			missing = append(missing, name)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("required genmedia tool(s) not available (a server failed to connect?): %s",
			strings.Join(missing, ", "))
	}
	return nil
}

// bareBucket validates base is a gs:// URI naming a bucket with NO path and
// returns the bare bucket name (lyria/avtool take a bucket name only).
func bareBucket(base string) (string, error) {
	if !verify.IsGCS(base) {
		return "", fmt.Errorf("GENMEDIA_BUCKET must be a gs:// URI (got %q)", base)
	}
	name := strings.Trim(strings.TrimPrefix(base, "gs://"), "/")
	if name == "" {
		return "", fmt.Errorf("GENMEDIA_BUCKET must name a bucket (got %q)", base)
	}
	if strings.Contains(name, "/") {
		return "", fmt.Errorf("GENMEDIA_BUCKET must be a BARE bucket with no path: "+
			"lyria and avtool take a bucket name only and write at the root (got %q)", base)
	}
	return name, nil
}

// gcsJoin appends per-run segments to a gs:// base, normalizing the slash.
func gcsJoin(base string, segments ...string) string {
	return strings.TrimRight(base, "/") + "/" + strings.Join(segments, "/")
}

// runID returns a per-run segment: a UTC timestamp plus a short random suffix.
func runID() string {
	ts := time.Now().UTC().Format("20060102-150405")
	var b [2]byte
	if _, err := rand.Read(b[:]); err != nil {
		return ts
	}
	return ts + "-" + hex.EncodeToString(b[:])
}

// firstEnv returns the value of the first set (non-empty) environment variable.
func firstEnv(keys ...string) string {
	for _, k := range keys {
		if v := os.Getenv(k); v != "" {
			return v
		}
	}
	return ""
}

func decisionWord(approve bool) string {
	if approve {
		return "APPROVED"
	}
	return "REJECTED"
}

// compactJSON renders a tool input as compact single-line text for logs.
func compactJSON(v any) string {
	if v == nil {
		return "{}"
	}
	s := fmt.Sprintf("%v", v)
	const max = 200
	if r := []rune(s); len(r) > max {
		return string(r[:max]) + "…"
	}
	return s
}
