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
RUN_ID="$(date +%Y%m%d-%H%M%S)"   # unique per invocation, for GCS prefixes
GCS_BASE=""                        # set in check_prereqs when in GCS mode
HAVE_FFMPEG=0                      # set in check_prereqs; gates avtool

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
    # Normalise to a gs:// base with no trailing slash, so per-server prefixes
    # can be composed uniformly.
    GCS_BASE="${GENMEDIA_BUCKET#gs://}"
    GCS_BASE="gs://${GCS_BASE%/}"
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

  # ffmpeg is a hard runtime dependency of avtool only. Its absence must not
  # abort the run or false-FAIL avtool — instead avtool is SKIPped (see
  # smoke_avtool). Detect it here so the disposition is decided up front.
  if command -v ffmpeg >/dev/null 2>&1; then
    HAVE_FFMPEG=1
  else
    HAVE_FFMPEG=0
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
# Verify a produced artifact. Echoes the verified reference on success.
#
#   verify_local <dir>          -> non-empty regular file in dir (ignoring our
#                                  own response.json log)
#   verify_gcs_prefix <prefix>  -> any object under the GCS prefix we wrote to.
#                                  This is deliberately independent of the tool
#                                  response body: some servers (e.g. veo)
#                                  return a `resource_link` content type that
#                                  the mcptools CLI cannot render, so parsing
#                                  the response is unreliable. We instead list
#                                  the exact destination we asked the tool for.
#   verify_gcs_response <json>  -> any gs:// URI mentioned in the response that
#                                  actually exists (last-resort fallback).
# ---------------------------------------------------------------------------
verify_local() {
  local dir="$1"
  local f
  f="$(find "$dir" -type f -size +0c ! -name 'response.json' 2>/dev/null | head -n 1)"
  if [[ -n "$f" ]]; then
    echo "$f"
    return 0
  fi
  return 1
}

verify_gcs_prefix() {
  local prefix="$1" uri
  # Require a real object of size > 0 (mirrors verify_local's -size +0c), so a
  # 0-byte object under the prefix cannot report a false PASS. `ls -l` lines are
  # "<size> <timestamp> <gs://uri>"; directory placeholders have no size / end
  # in '/', and the trailing "TOTAL:" line is ignored by the numeric guard.
  uri="$(gcloud storage ls -l -r "${prefix}**" 2>/dev/null \
         | awk '$1 ~ /^[0-9]+$/ && ($1+0)>0 && $NF ~ /^gs:\/\// && $NF !~ /\/$/ {print $NF; exit}')"
  if [[ -n "$uri" ]]; then
    echo "$uri"
    return 0
  fi
  return 1
}

verify_gcs_response() {
  local json="$1" uri
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
#   run_case <server> <tool> <params_json> <local_verify_dir> <gcs_prefix>
# `gcs_prefix` is the exact GCS prefix passed to the tool (empty for tools that
# only write locally, e.g. chirp/avtool).
# ---------------------------------------------------------------------------
run_case() {
  local server="$1" tool="$2" params="$3" verify_dir="$4" gcs_prefix="$5"

  info "${server} :: ${tool}"

  local bin
  bin="$(build_server "$server")" || {
    RESULTS+=("${server}|${tool}|BUILD-FAIL|go build failed (see /tmp/${server}.build.log)")
    OVERALL_RC=1
    return
  }

  # Ensure local verification can only ever reflect the CURRENT run — a leftover
  # artifact from a previous run would otherwise report a false PASS for a
  # now-broken server. Rather than silently deleting, warn and move any
  # non-empty prior dir aside (nothing is discarded; the operator can inspect
  # or remove it). These live under the gitignored smoke_output/.
  if [[ -d "$verify_dir" && -n "$(ls -A "$verify_dir" 2>/dev/null)" ]]; then
    local stale="${verify_dir}.stale-${RUN_ID}"
    log "  ${C_YELLOW}WARN${C_RESET} ${verify_dir} is non-empty from a previous run;" \
        "moving it aside to ${stale} so this run's verification is not fooled by stale output."
    mv "$verify_dir" "$stale"
  fi
  mkdir -p "$verify_dir"

  local raw rc
  raw="$(cd "$(dirname "$bin")" && timeout "$CALL_TIMEOUT" \
        mcptools call "$tool" --format json --params "$params" "./${server}" 2>&1)"
  rc=$?

  # Persist the raw response for debugging.
  printf '%s\n' "$raw" > "${verify_dir}/response.json" 2>/dev/null || true

  if [[ "$rc" -eq 124 ]]; then
    _record "$server" "$tool" "call timed out after ${CALL_TIMEOUT}s"
    return
  fi

  # Verify the artifact is real. In GCS mode, primarily list the exact
  # destination prefix we asked for (robust to unrenderable responses).
  local artifact=""
  if [[ "$MODE" == "gcs" && -n "$gcs_prefix" ]]; then
    artifact="$(verify_gcs_prefix "$gcs_prefix")" || true
  fi
  # Fall back to the local dir. Several tools always honour output_directory
  # even when a bucket is configured (e.g. chirp is local-only).
  if [[ -z "$artifact" ]]; then
    artifact="$(verify_local "$verify_dir")" || true
  fi
  # Last resort: any existing gs:// URI mentioned in the response body.
  if [[ -z "$artifact" && "$MODE" == "gcs" ]]; then
    artifact="$(verify_gcs_response "$raw")" || true
  fi

  if [[ -n "$artifact" ]]; then
    RESULTS+=("${server}|${tool}|PASS|${artifact}")
    log "  ${C_GREEN}PASS${C_RESET} -> ${artifact}"
  else
    local snippet
    snippet="$(printf '%s' "$raw" | tr '\n' ' ' | cut -c1-200)"
    _record "$server" "$tool" "no artifact; response: ${snippet}"
  fi
}

# Record a FAIL outcome.
_record() {
  local server="$1" tool="$2" detail="$3"
  RESULTS+=("${server}|${tool}|FAIL|${detail}")
  log "  ${C_RED}FAIL${C_RESET} (${detail})"
  OVERALL_RC=1
}

# Record a skip.
skip_case() {
  local server="$1" tool="$2" reason="$3"
  RESULTS+=("${server}|${tool}|SKIP|${reason}")
  log "  ${C_YELLOW}SKIP${C_RESET} ${server} :: ${tool} (${reason})"
}

# ---------------------------------------------------------------------------
# Per-server drivers. Each builds a params payload appropriate to MODE and
# calls run_case. Local dir is always created so servers that ignore the
# bucket (chirp) are still verifiable.
# ---------------------------------------------------------------------------

# Compose the unique GCS prefix for a server (only meaningful in GCS mode).
gcs_prefix_for() { printf '%s/smoke_%s/%s/' "$GCS_BASE" "$RUN_ID" "$1"; }

smoke_gemini() {
  local server="mcp-gemini-go" dir="${OUTPUT_DIR}/mcp-gemini-go" prefix params
  if [[ "$MODE" == "gcs" ]]; then
    prefix="$(gcs_prefix_for "$server")"
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg b "$prefix" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_gemini.png"}')"
  else
    prefix=""
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_gemini.png"}')"
  fi
  run_case "$server" "gemini_image_generation" "$params" "$dir" "$prefix"
}

smoke_nanobanana() {
  local server="mcp-nanobanana-go" dir="${OUTPUT_DIR}/mcp-nanobanana-go" prefix params
  if [[ "$MODE" == "gcs" ]]; then
    prefix="$(gcs_prefix_for "$server")"
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg b "$prefix" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_nanobanana.png"}')"
  else
    prefix=""
    params="$(jq -nc --arg p "$IMG_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_nanobanana.png"}')"
  fi
  run_case "$server" "nanobanana_image_generation" "$params" "$dir" "$prefix"
}

# NOTE: mcp-imagen-go is intentionally NOT covered. Imagen models were shut down
# across Google (incl. Vertex AI) on 2026-08-17 and return HTTP 404, so there is
# no value in smoke-testing them going forward.

smoke_veo() {
  # An explicit model is required: with no model the server falls back to
  # veo-2.0-generate-001, which rejects the default generate_audio=true.
  local server="mcp-veo-go" dir="${OUTPUT_DIR}/mcp-veo-go" prefix params
  local model="veo-3.1-fast-generate-001"
  if [[ "$MODE" == "gcs" ]]; then
    # veo uses `bucket` (not gcs_bucket_uri) for GCS output.
    prefix="$(gcs_prefix_for "$server")"
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg b "$prefix" --arg m "$model" \
      '{prompt:$p, bucket:$b, model:$m, output_filename:"smoke_veo.mp4"}')"
  else
    prefix=""
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg d "$dir" --arg m "$model" \
      '{prompt:$p, output_directory:$d, model:$m, output_filename:"smoke_veo.mp4"}')"
  fi
  run_case "$server" "veo_t2v" "$params" "$dir" "$prefix"
}

smoke_lyria() {
  local server="mcp-lyria-go" dir="${OUTPUT_DIR}/mcp-lyria-go" prefix params
  if [[ "$MODE" == "gcs" ]]; then
    # lyria uses `output_gcs_bucket` + `file_name`.
    prefix="$(gcs_prefix_for "$server")"
    params="$(jq -nc --arg p "$MUSIC_PROMPT" --arg b "$prefix" \
      '{prompt:$p, output_gcs_bucket:$b, file_name:"smoke_lyria.wav"}')"
  else
    # lyria uses `local_path` for local output.
    prefix=""
    params="$(jq -nc --arg p "$MUSIC_PROMPT" --arg d "$dir" \
      '{prompt:$p, local_path:$d, file_name:"smoke_lyria.wav"}')"
  fi
  run_case "$server" "lyria_generate_music" "$params" "$dir" "$prefix"
}

smoke_chirp() {
  # chirp only writes locally (output_directory); no GCS output param exists.
  local server="mcp-chirp3-go" dir="${OUTPUT_DIR}/mcp-chirp3-go" params
  params="$(jq -nc --arg t "$TTS_TEXT" --arg d "$dir" \
    '{text:$t, output_directory:$d, output_filename:"smoke_chirp.wav"}')"
  run_case "$server" "chirp_tts" "$params" "$dir" ""
}

smoke_omni() {
  local server="mcp-omni-go" dir="${OUTPUT_DIR}/mcp-omni-go" prefix params
  if [[ "$MODE" == "gcs" ]]; then
    prefix="$(gcs_prefix_for "$server")"
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg b "$prefix" \
      '{prompt:$p, gcs_bucket_uri:$b, output_filename:"smoke_omni.mp4"}')"
  else
    prefix=""
    params="$(jq -nc --arg p "$VIDEO_PROMPT" --arg d "$dir" \
      '{prompt:$p, output_directory:$d, output_filename:"smoke_omni.mp4"}')"
  fi
  run_case "$server" "omni_video_generation" "$params" "$dir" "$prefix"
}

smoke_avtool() {
  # avtool transforms EXISTING media rather than generating from a prompt, so
  # it needs an input file. We chain it off the chirp output: take the .wav
  # chirp produced and convert it to mp3, then verify the mp3. If chirp did not
  # produce a local wav, we skip avtool with a clear reason.
  local dir="${OUTPUT_DIR}/mcp-avtool-go"
  local chirp_dir="${OUTPUT_DIR}/mcp-chirp3-go"

  # ffmpeg is a hard runtime dependency of this tool. Without it the call can
  # only ever fail for reasons unrelated to the server, so SKIP rather than
  # false-FAIL the whole suite.
  if [[ "$HAVE_FFMPEG" -ne 1 ]]; then
    skip_case "mcp-avtool-go" "ffmpeg_convert_audio_wav_to_mp3" \
      "ffmpeg not found on PATH (required by avtool)"
    return
  fi

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
  # avtool always writes locally here, so no GCS prefix.
  run_case "mcp-avtool-go" "ffmpeg_convert_audio_wav_to_mp3" "$params" "$dir" ""
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
    echo "${C_GREEN}All servers produced verified media.${C_RESET}"
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
  local -a order=(gemini nanobanana veo lyria chirp omni avtool)
  local -a requested=("$@")
  [[ ${#requested[@]} -eq 0 ]] && requested=("${order[@]}")

  local name
  for name in "${requested[@]}"; do
    case "$name" in
      gemini)     smoke_gemini ;;
      nanobanana) smoke_nanobanana ;;
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
