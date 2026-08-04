#!/usr/bin/env bash
#
# grant-access.sh
#
# Grant (or revoke) access to a deployed GenMedia Creative Studio instance.
#
# Two grants are always needed per person, which is the part people get wrong:
#   1. IAP  — roles/iap.httpsResourceAccessor, to reach the app at all.
#   2. GCS  — roles/storage.objectViewer on the assets bucket. The app serves
#             media via authenticated GCS URLs, so without this users sign in
#             successfully but every image and video is broken.
#
# The correct IAP surface depends on how the app was deployed (HTTPS load
# balancer vs. IAP-for-Cloud-Run); this script detects it rather than asking.
#
# Usage:
#   ./grant-access.sh --project-id PROJECT alice@example.com bob@example.com
#   ./grant-access.sh --project-id PROJECT --group team@example.com
#   ./grant-access.sh --project-id PROJECT --revoke alice@example.com
#   ./grant-access.sh --project-id PROJECT --list
#   ./grant-access.sh --project-id PROJECT --from-file emails.txt
#
set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"
readonly SERVICE_NAME="creative-studio"
readonly IAP_ROLE="roles/iap.httpsResourceAccessor"
readonly GCS_ROLE="roles/storage.objectViewer"

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
BUCKET="${BUCKET:-}"
MEMBERS=()
KIND="user"          # user | group | serviceAccount | domain
REVOKE=0
LIST=0
DRY_RUN=0
ASSUME_YES=0
FROM_FILE=""

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  C_RESET=$'\033[0m'; C_RED=$'\033[31m'; C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
else
  C_RESET=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_BOLD=""
fi

log()  { printf '%s[%s]%s %s\n' "$C_BLUE" "$(date +%H:%M:%S)" "$C_RESET" "$*"; }
ok()   { printf '%s  ✓%s %s\n' "$C_GREEN"  "$C_RESET" "$*"; }
warn() { printf '%s  !%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
err()  { printf '%s  ✗%s %s\n' "$C_RED"    "$C_RESET" "$*" >&2; }
die()  { err "$*"; exit 1; }
step() { printf '\n%s==> %s%s\n' "$C_BOLD" "$*" "$C_RESET"; }

run() {
  printf '%s    $ %s%s\n' "$C_BLUE" "$*" "$C_RESET"
  (( DRY_RUN )) && return 0
  "$@"
}

usage() {
  cat <<EOF
${C_BOLD}$SCRIPT_NAME${C_RESET} — manage who can use GenMedia Creative Studio.

${C_BOLD}USAGE${C_RESET}
  $SCRIPT_NAME --project-id PROJECT [options] EMAIL [EMAIL...]

${C_BOLD}WHAT IT GRANTS${C_RESET}
  Each person receives two roles, both of which are required:
    $IAP_ROLE   (reach the app)
    $GCS_ROLE          (see the generated media)
  Granting only the first is the usual cause of "I can log in but every
  image is broken".

${C_BOLD}OPTIONS${C_RESET}
  --project-id ID    Google Cloud project      (env PROJECT_ID)   [required]
  --region REGION    Deployment region (default: us-central1, env REGION)
  --bucket NAME      Assets bucket. Default: auto-detected from Terraform
                     state, else creative-studio-<project>-assets
  --group            Treat the arguments as Google Groups, not users
  --service-account  Treat the arguments as service accounts
  --domain           Treat the arguments as whole domains (e.g. example.com)
  --from-file PATH   Read addresses from a file, one per line (# = comment)
  --revoke           Remove access instead of granting it
  --list             Show who currently has access, then exit
  -y, --yes          Do not prompt for confirmation
  --dry-run          Print the commands without running them
  -h, --help         This help

${C_BOLD}EXAMPLES${C_RESET}
  # Grant two people
  $SCRIPT_NAME --project-id my-proj alice@example.com bob@example.com

  # Grant a whole Google Group (best for teams — one grant, managed centrally)
  $SCRIPT_NAME --project-id my-proj --group creative-team@example.com

  # Bulk grant from a file
  $SCRIPT_NAME --project-id my-proj --from-file new-hires.txt

  # Who has access today?
  $SCRIPT_NAME --project-id my-proj --list

  # Off-boarding
  $SCRIPT_NAME --project-id my-proj --revoke alice@example.com

${C_BOLD}NOTE${C_RESET}
  New grants take a few minutes to propagate. If someone still sees
  "You don't have access" afterwards, have them retry in a private window —
  IAP caches the denial in a session cookie.
EOF
}

parse_args() {
  while (( $# )); do
    case "$1" in
      --project-id)      PROJECT_ID="${2:?--project-id needs a value}"; shift 2 ;;
      --region)          REGION="${2:?--region needs a value}"; shift 2 ;;
      --bucket)          BUCKET="${2:?--bucket needs a value}"; shift 2 ;;
      --from-file)       FROM_FILE="${2:?--from-file needs a value}"; shift 2 ;;
      --group)           KIND="group"; shift ;;
      --service-account) KIND="serviceAccount"; shift ;;
      --domain)          KIND="domain"; shift ;;
      --revoke)          REVOKE=1; shift ;;
      --list)            LIST=1; shift ;;
      -y|--yes)          ASSUME_YES=1; shift ;;
      --dry-run)         DRY_RUN=1; shift ;;
      -h|--help)         usage; exit 0 ;;
      -*)                usage >&2; die "Unknown option: $1" ;;
      *)                 MEMBERS+=("$1"); shift ;;
    esac
  done

  if [[ -n "$FROM_FILE" ]]; then
    [[ -r "$FROM_FILE" ]] || die "Cannot read $FROM_FILE"
    local line
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%%#*}"                      # strip comments
      line="$(tr -d '[:space:]' <<<"$line")"  # strip whitespace
      [[ -n "$line" ]] && MEMBERS+=("$line")
    done < "$FROM_FILE"
  fi
}

confirm() {
  local prompt="$1" reply
  (( ASSUME_YES )) && return 0
  if [[ ! -t 0 ]] && [[ ! -r /dev/tty ]]; then
    die "Needs confirmation but there is no terminal. Re-run with --yes."
  fi
  read -r -p "$prompt [y/N] " reply < /dev/tty || true
  [[ "$reply" =~ ^[Yy]$ ]]
}

# A domain grant is "example.com"; everything else must look like an address.
validate_member() {
  local m="$1"
  if [[ "$KIND" == "domain" ]]; then
    [[ "$m" == *.* && "$m" != *@* ]] || die "--domain expects a bare domain, got: $m"
  else
    [[ "$m" == *@*.* ]] || die "Not a valid email address: $m  (need --domain or --group?)"
  fi
}

preflight() {
  command -v gcloud >/dev/null 2>&1 \
    || die "gcloud not found — https://cloud.google.com/sdk/docs/install"
  [[ -n "$PROJECT_ID" ]] || die "--project-id (or PROJECT_ID) is required."

  gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1 \
    || die "Cannot read project '$PROJECT_ID'. Check the ID and your permissions."

  # Which IAP surface is in play? A Cloud Run service with iap_enabled uses the
  # per-service resource; a load-balancer deployment uses the project-wide one.
  local iap_enabled
  iap_enabled="$(gcloud run services describe "$SERVICE_NAME" \
      --region="$REGION" --project="$PROJECT_ID" \
      --format='value(metadata.annotations."run.googleapis.com/iap-enabled")' 2>/dev/null || true)"

  if [[ "$iap_enabled" == "true" ]]; then
    IAP_SURFACE="cloud-run"
  elif gcloud run services describe "$SERVICE_NAME" --region="$REGION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
    IAP_SURFACE="iap_web"     # service exists but IAP is on the load balancer
  else
    die "No '$SERVICE_NAME' service in $PROJECT_ID/$REGION. Wrong --project-id or --region?"
  fi

  if [[ -z "$BUCKET" ]]; then
    BUCKET="creative-studio-${PROJECT_ID}-assets"
    gcloud storage buckets describe "gs://$BUCKET" --project="$PROJECT_ID" >/dev/null 2>&1 \
      || warn "Bucket gs://$BUCKET not found — pass --bucket if it differs."
  fi
}

iap_binding() {   # $1 = add|remove, $2 = member string
  local action="$1" member="$2"
  if [[ "$IAP_SURFACE" == "cloud-run" ]]; then
    run gcloud beta iap web "${action}-iam-policy-binding" \
      --project="$PROJECT_ID" --region="$REGION" \
      --resource-type=cloud-run --service="$SERVICE_NAME" \
      --member="$member" --role="$IAP_ROLE"
  else
    run gcloud iap web "${action}-iam-policy-binding" \
      --project="$PROJECT_ID" \
      --resource-type=iap_web \
      --member="$member" --role="$IAP_ROLE"
  fi
}

bucket_binding() { # $1 = add|remove, $2 = member string
  local action="$1" member="$2"
  run gcloud storage buckets "${action}-iam-policy-binding" "gs://$BUCKET" \
    --project="$PROJECT_ID" --member="$member" --role="$GCS_ROLE"
}

list_access() {
  step "Who can access $SERVICE_NAME in $PROJECT_ID"

  # --flatten turns the members array into one row each, so no list-repr leaks
  # through. Project-level roles (projectOwner/Editor/Viewer) are inherited
  # rather than granted by this tool, so they are filtered out of the bucket
  # listing to keep the answer to "who did we add?" readable.
  printf '\n  %sIAP (%s) — %s%s\n' "$C_BOLD" "$IAP_SURFACE" "$IAP_ROLE" "$C_RESET"
  if [[ "$IAP_SURFACE" == "cloud-run" ]]; then
    gcloud beta iap web get-iam-policy --resource-type=cloud-run \
      --service="$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" \
      --flatten='bindings[].members' --format='value(bindings.members)' 2>/dev/null \
      | sort -u | sed 's/^/    /'
  else
    gcloud iap web get-iam-policy --resource-type=iap_web --project="$PROJECT_ID" \
      --flatten='bindings[].members' --format='value(bindings.members)' 2>/dev/null \
      | sort -u | sed 's/^/    /'
  fi

  # 'gcloud storage buckets get-iam-policy' has no --filter, so select with awk.
  # objectAdmin and objectUser also confer read, so listing objectViewer alone
  # would under-report who can actually see the media.
  printf '\n  %sAssets bucket (gs://%s) — can read media%s\n' "$C_BOLD" "$BUCKET" "$C_RESET"
  gcloud storage buckets get-iam-policy "gs://$BUCKET" --project="$PROJECT_ID" \
    --flatten='bindings[].members' \
    --format='value(bindings.role,bindings.members)' 2>/dev/null \
    | awk -F'\t' '$1 ~ /objectViewer|objectAdmin|objectUser/ && $2 !~ /^project(Owner|Editor|Viewer):/ {
        printf "    %s  (%s)\n", $2, $1
      }' | sort -u
  printf '    %s(project owners/editors/viewers inherit access and are not listed)%s\n' \
    "$C_BLUE" "$C_RESET"
  echo
  printf '  %sNote%s: someone with IAP but not the bucket role can sign in but sees no media.\n' \
    "$C_YELLOW" "$C_RESET"
}

main() {
  parse_args "$@"
  preflight

  if (( LIST )); then
    list_access
    exit 0
  fi

  (( ${#MEMBERS[@]} )) || { usage >&2; die "No email addresses given."; }

  local m
  for m in "${MEMBERS[@]}"; do validate_member "$m"; done

  local verb action
  if (( REVOKE )); then verb="Revoking"; action="remove"; else verb="Granting"; action="add"; fi

  step "$verb access — ${#MEMBERS[@]} member(s)"
  printf '  Project : %s\n' "$PROJECT_ID"
  printf '  Service : %s (%s)\n' "$SERVICE_NAME" "$REGION"
  printf '  IAP     : %s\n' "$IAP_SURFACE"
  printf '  Bucket  : gs://%s\n' "$BUCKET"
  printf '  Members :\n'
  for m in "${MEMBERS[@]}"; do printf '    %s:%s\n' "$KIND" "$m"; done
  echo
  confirm "Proceed?" || die "Aborted."

  local failed=0
  for m in "${MEMBERS[@]}"; do
    step "$verb ${KIND}:${m}"
    if iap_binding "$action" "${KIND}:${m}"; then
      ok "IAP ($IAP_ROLE)"
    else
      err "IAP grant failed for $m"; failed=$(( failed + 1 )); continue
    fi
    if bucket_binding "$action" "${KIND}:${m}"; then
      ok "Bucket ($GCS_ROLE)"
    else
      err "Bucket grant failed for $m — they will sign in but see no media."
      failed=$(( failed + 1 ))
    fi
  done

  echo
  if (( failed )); then
    die "$failed operation(s) failed. See the errors above."
  fi

  if (( REVOKE )); then
    ok "Access revoked for ${#MEMBERS[@]} member(s)."
  else
    ok "Access granted to ${#MEMBERS[@]} member(s)."
    printf '\n  %sTell them:%s\n' "$C_BOLD" "$C_RESET"
    local url
    url="$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" \
            --project="$PROJECT_ID" --format='value(status.url)' 2>/dev/null || true)"
    printf '    URL: %s\n' "${url:-<see creative-studio-url.txt>}"
    printf '    Grants take a few minutes to propagate. If they see\n'
    printf '    "You don'"'"'t have access", retry in a private window —\n'
    printf '    IAP caches the denial in a session cookie.\n'
  fi
}

main "$@"
