#!/usr/bin/env bash
#
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ---------------------------------------------------------------------------
# Consolidated generate-and-verify smoke test for the mcp-genmedia-go servers.
#
# For each media-generation MCP server this script fires ONE realistic
# `tools/call` via the external `mcptools` CLI and then VERIFIES that a real
# media artifact was produced (a non-empty local file, or an object that
# `gcloud storage ls` can see in GCS). This is deliberately stronger than the
# per-server `verify.sh`, which only does a build + `tools/list` liveness check
# and never produces media.
#
# Output routing:
#   * If $GENMEDIA_BUCKET is set, generated media is written to that bucket and
#     verified with `gcloud storage ls`.
#   * Otherwise, media is written locally under ./smoke_output/<server>/ and
#     verified with a non-empty-file check. (smoke_output/ is gitignored.)
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT=your-project        # required
#   export GENMEDIA_BUCKET=gs://your-bucket/prefix  # optional (GCS mode)
#   ./smoke_generate_and_verify.sh                  # run all servers
#   ./smoke_generate_and_verify.sh veo lyria        # run a subset
#
# Requirements: mcptools (https://github.com/f/mcptools), go, jq, and (for GCS
# mode) gcloud with application-default credentials.
# ---------------------------------------------------------------------------

set -uo pipefail

# --- Resolve paths ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVERS_DIR="$(cd "${SCRIPT_DIR}/../mcp-genmedia/mcp-genmedia-go" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/smoke_output"

# Per-call wall-clock budget (seconds). Video models (veo/omni) can take a
# while as the server polls the long-running operation to completion.
CALL_TIMEOUT="${SMOKE_CALL_TIMEOUT:-600}"

# --- Prompts / inputs ------------------------------------------------------
IMG_PROMPT="a photorealistic red panda sitting in a bamboo forest, golden hour lighting"
VIDEO_PROMPT="a slow cinematic pan across a calm mountain lake at sunrise"
MUSIC_PROMPT="a gentle upbeat acoustic guitar melody, warm and optimistic"
TTS_TEXT="Hello from the consolidated MCP generate and verify smoke test."

# --- Result accumulation ---------------------------------------------------
declare -a RESULTS   # "server|tool|status|detail"
OVERALL_RC=0

# --- Colours (only when attached to a terminal) ----------------------------
if [[ -t 1 ]]; then
  C_GREEN=$'\033[0;32m'; C_RED=$'\033[0;31m'; C_YELLOW=$'\033[0;33m'
  C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_GREEN=""; C_RED=""; C_YELLOW=""; C_BOLD=""; C_RESET=""
fi

log()  { printf '%s\n' "$*" >&2; }
info() { log "${C_BOLD}==>${C_RESET} $*"; }

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
check_prereqs() {
  local missing=0

  if ! command -v mcptools >/dev/null 2>&1; then
    log "${C_RED}ERROR:${C_RESET} 'mcptools' CLI not found on PATH."
    log "  Install it with:"
    log "    go install github.com/f/mcptools/cmd/mcptools@latest"
    log "  and ensure \$(go env GOPATH)/bin is on your PATH."
    log "  See https://github.com/f/mcptools for details."
    missing=1
  fi
  if ! command -v go >/dev/null 2>&1; then
    log "${C_RED}ERROR:${C_RESET} 'go' toolchain not found (needed to build the servers)."
    missing=1
  fi
  if ! command -v jq >/dev/null 2>&1; then
    log "${C_RED}ERROR:${C_RESET} 'jq' not found (needed to parse tool responses)."
    missing=1
  fi

  if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
    log "${C_RED}ERROR:${C_RESET} GOOGLE_CLOUD_PROJECT is not set (required by every server)."
    missing=1
  fi

  if [[ -n "${GENMEDIA_BUCKET:-}" ]]; then
    MODE="gcs"
    if ! command -v gcloud >/dev/null 2>&1; then
      log "${C_RED}ERROR:${C_RESET} GENMEDIA_BUCKET is set (GCS mode) but 'gcloud' is not on PATH."
      missing=1
    fi
  else
    MODE="local"
  fi

  if [[ "$missing" -ne 0 ]]; then
    log "Prerequisites missing; aborting before any calls."
    exit 2
  fi

  info "Mode: ${C_BOLD}${MODE}${C_RESET} (GENMEDIA_BUCKET=${GENMEDIA_BUCKET:-<unset>})"
  info "Project: ${GOOGLE_CLOUD_PROJECT}"
  info "Servers dir: ${SERVERS_DIR}"
}

# ---------------------------------------------------------------------------
# Build a server binary.  Echoes the binary path on success; returns non-zero
# on build failure.
# ---------------------------------------------------------------------------
build_server() {
  local server="$1"
  local dir="${SERVERS_DIR}/${server}"
  if [[ ! -d "$dir" ]]; then
    log "${C_RED}ERROR:${C_RESET} server directory not found: ${dir}"
    return 1
  fi
  ( cd "$dir" && go build -o "$server" . ) >/tmp/${server}.build.log 2>&1 || {
    log "${C_RED}Build failed${C_RESET} for ${server}:"
    sed 's/^/    /' "/tmp/${server}.build.log" >&2
    return 1
  }
  echo "${dir}/${server}"
}

# ---------------------------------------------------------------------------
# Verify a produced artifact.
#   verify_local <dir>   -> success if dir contains a non-empty regular file
#   verify_gcs <json>    -> success if any gs:// URI in the JSON exists
# Echoes the verified artifact reference on success.
# ---------------------------------------------------------------------------
verify_local() {
  local dir="$1"
  local f
  f="$(find "$dir" -type f -size +0c 2>/dev/null | head -n 1)"
  if [[ -n "$f" ]]; then
    echo "$f"
    return 0
  fi
  return 1
}

verify_gcs() {
  local json="$1"
  local uri
  # Extract candidate gs:// URIs from the raw tool response.
  while IFS= read -r uri; do
    [[ -z "$uri" ]] && continue
    if gcloud storage ls "$uri" >/dev/null 2>&1; then
      echo "$uri"
      return 0
    fi
  done < <(printf '%s' "$json" | grep -oE 'gs://[a-zA-Z0-9._/\-]+' | sort -u)
  return 1
}

# ---------------------------------------------------------------------------
# Core: run one tool call and verify its output.
#   run_case <server> <tool> <params_json> <local_verify_dir> [expected]
# `expected` may be "expected-dead" for servers whose backend is known-dead
# (Imagen); a failure there is reported as EXPECTED-FAIL, not FAIL.
# ---------------------------------------------------------------------------
run_case() {
  local server="$1" tool="$2" params="$3" verify_dir="$4" expected="${5:-}"

  info "${server} :: ${tool}"

  local bin
  bin="$(build_server "$server")" || {
    RESULTS+=("${server}|${tool}|BUILD-FAIL|go build failed (see /tmp/${server}.build.log)")
    OVERALL_RC=1
    return
  }

  mkdir -p "$verify_dir"

  local raw rc
  raw="$(cd "$(dirname "$bin")" && timeout "$CALL_TIMEOUT" \
        mcptools --json call "$tool" --params "$params" "./${server}" 2>&1)"
  rc=$?

  # Persist the raw response for debugging.
  printf '%s\n' "$raw" > "${verify_dir}/response.json" 2>/dev/null || true

  if [[ "$rc" -eq 124 ]]; then
    _record "$server" "$tool" "$expected" "call timed out after ${CALL_TIMEOUT}s"
    return
  fi

  # Verify the artifact is real.
  local artifact=""
  if [[ "$MODE" == "gcs" ]]; then
    artifact="$(verify_gcs "$raw")" || true
  fi
  # Fall back to (or primarily use) the local dir. Several servers always
  # honour output_directory even when a bucket is configured (e.g. chirp).
  if [[ -z "$artifact" ]]; then
    artifact="$(verify_local "$verify_dir")" || true
  fi

  if [[ -n "$artifact" ]]; then
    RESULTS+=("${server}|${tool}|PASS|${artifact}")
    log "  ${C_GREEN}PASS${C_RESET} -> ${artifact}"
  else
    local snippet
    snippet="$(printf '%s' "$raw" | tr '\n' ' ' | cut -c1-200)"
    _record "$server" "$tool" "$expected" "no artifact; response: ${snippet}"
  fi
}

# Record a non-passing outcome, honouring the "expected-dead" disposition.
_record() {
  local server="$1" tool="$2" expected="$3" detail="$4"
  if [[ "$expected" == "expected-dead" ]]; then
    RESULTS+=("${server}|${tool}|EXPECTED-FAIL|${detail}")
    log "  ${C_YELLOW}EXPECTED-FAIL${C_RESET} (${detail})"
  else
    RESULTS+=("${server}|${tool}|FAIL|${detail}")
    log "  ${C_RED}FAIL${C_RESET} (${detail})"
    OVERALL_RC=1
  fi
}

# Record a skip.
skip_case() {
  local server="$1" tool="$2" reason="$3"
  RESULTS+=("${server}|${tool}|SKIP|${reason}")
  log "  ${C_YELLOW}SKIP${C_RESET} ${server} :: ${tool} (${reason})"
}

# JSON-string helper (escapes a value for embedding in a params payload).
jstr() { printf '%s' "$1" | jq -Rs .; }

# ---------------------------------------------------------------------------
# Per-server drivers. Each builds a params payload appropriate to MODE and
# calls run_case. Local dir is always created so servers that ignore the
# bucket (chirp) are still verifiable.
# ---------------------------------------------------------------------------

smoke_gemini() {
  local dir="${OUTPUT_DIR}/mcp-gemini-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_gemini.png"}')"
  else
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_gemini.png"}')"
  fi
  run_case "mcp-gemini-go" "gemini_image_generation" "$params" "$dir"
}

smoke_nanobanana() {
  local dir="${OUTPUT_DIR}/mcp-nanobanana-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_nanobanana.png"}')"
  else
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_nanobanana.png"}')"
  fi
  run_case "mcp-nanobanana-go" "nanobanana_image_generation" "$params" "$dir"
}

smoke_imagen() {
  # Imagen models were shut down across Google (incl. Vertex AI) on 2026-08-17.
  # This call is EXPECTED to fail; we include it so its status is reported.
  local dir="${OUTPUT_DIR}/mcp-imagen-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_imagen.png"}')"
  else
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_imagen.png"}')"
  fi
  run_case "mcp-imagen-go" "imagen_t2i" "$params" "$dir" "expected-dead"
}

smoke_veo() {
  local dir="${OUTPUT_DIR}/mcp-veo-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    # veo uses `bucket` (not gcs_bucket_uri) for GCS output.
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, bucket:$b, output_filename:"smoke_veo.mp4"}')"
  else
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_veo.mp4"}')"
  fi
  run_case "mcp-veo-go" "veo_t2v" "$params" "$dir"
}

smoke_lyria() {
  local dir="${OUTPUT_DIR}/mcp-lyria-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    # lyria uses `output_gcs_bucket` + `file_name`.
    params="$(jq -nc --arg p "$MUSIC_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, output_gcs_bucket:$b, file_name:"smoke_lyria.wav"}')"
  else
    # lyria uses `local_path` for local output.
    params="$(jq -nc --arg p "$MUSIC_PROMPT" --arg d "$dir" \
      '{prompt:$p, local_path:$d, file_name:"smoke_lyria.wav"}')"
  fi
  run_case "mcp-lyria-go" "lyria_generate_music" "$params" "$dir"
}

smoke_chirp() {
  # chirp only writes locally (output_directory); no GCS output param exists.
  local dir="${OUTPUT_DIR}/mcp-chirp3-go"
  local params
  params="$(jq -nc --arg t "$TTS_TEXT" --arg d "$dir" \
    '{text:$t, output_directory:$d, output_filename:"smoke_chirp.wav"}')"
  run_case "mcp-chirp3-go" "chirp_tts" "$params" "$dir"
}

smoke_omni() {
  local dir="${OUTPUT_DIR}/mcp-omni-go"
  local params
  if [[ "$MODE" == "gcs" ]]; then
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg b "$GENMEDIA_BUCKET" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_omni.mp4"}')"
  else
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_omni.mp4"}')"
  fi
  run_case "mcp-omni-go" "omni_video_generation" "$params" "$dir"
}

smoke_avtool() {
  # avtool transforms EXISTING media rather than generating from a prompt, so
  # it needs an input file. We chain it off the chirp output: take the .wav
  # chirp produced and convert it to mp3, then verify the mp3. If chirp did not
  # produce a local wav, we skip avtool with a clear reason.
  local dir="${OUTPUT_DIR}/mcp-avtool-go"
  local chirp_dir="${OUTPUT_DIR}/mcp-chirp3-go"
  local input
  input="$(find "$chirp_dir" -type f -name '*.wav' -size +0c 2>/dev/null | head -n 1)"
  if [[ -z "$input" ]]; then
    skip_case "mcp-avtool-go" "ffmpeg_convert_audio_wav_to_mp3" \
      "no chirp .wav input available (chirp must PASS in local mode to feed avtool)"
    return
  fi
  mkdir -p "$dir"
  local params
  params="$(jq -nc --arg i "$input" --arg d "$dir" \
    '{input_audio_uri:$i, output_local_dir:$d, output_filename:"smoke_avtool.mp3"}')"
  run_case "mcp-avtool-go" "ffmpeg_convert_audio_wav_to_mp3" "$params" "$dir"
}

# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
print_report() {
  echo
  echo "${C_BOLD}================ mcp-genmedia smoke report ================${C_RESET}"
  printf '%-20s %-32s %-14s %s\n' "SERVER" "TOOL" "RESULT" "ARTIFACT / DETAIL"
  printf '%-20s %-32s %-14s %s\n' "------" "----" "------" "-----------------"
  local row server tool status detail colour
  for row in "${RESULTS[@]}"; do
    IFS='|' read -r server tool status detail <<< "$row"
    case "$status" in
      PASS)          colour="$C_GREEN" ;;
      FAIL|BUILD-FAIL) colour="$C_RED" ;;
      *)             colour="$C_YELLOW" ;;
    esac
    printf '%-20s %-32s %b%-14s%b %s\n' \
      "$server" "$tool" "$colour" "$status" "$C_RESET" "$detail"
  done
  echo "${C_BOLD}==========================================================${C_RESET}"
  if [[ "$OVERALL_RC" -eq 0 ]]; then
    echo "${C_GREEN}All non-expected servers produced verified media.${C_RESET}"
  else
    echo "${C_RED}One or more servers failed (see FAIL rows above).${C_RESET}"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  check_prereqs
  mkdir -p "$OUTPUT_DIR"

  # Map friendly names -> driver functions. avtool runs after chirp so it can
  # consume chirp's output.
  local -a order=(gemini nanobanana imagen veo lyria chirp omni avtool)
  local -a requested=("$@")
  [[ ${#requested[@]} -eq 0 ]] && requested=("${order[@]}")

  local name
  for name in "${requested[@]}"; do
    case "$name" in
      gemini)     smoke_gemini ;;
      nanobanana) smoke_nanobanana ;;
      imagen)     smoke_imagen ;;
      veo)        smoke_veo ;;
      lyria)      smoke_lyria ;;
      chirp|chirp3) smoke_chirp ;;
      omni)       smoke_omni ;;
      avtool)     smoke_avtool ;;
      *) log "${C_YELLOW}Unknown server '${name}' — skipping.${C_RESET}" ;;
    esac
  done

  print_report
  exit "$OVERALL_RC"
}

main "$@"
