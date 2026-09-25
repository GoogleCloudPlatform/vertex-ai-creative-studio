# GKE `IAP_JWT_AUDIENCE` — post-apply numeric-id lookup (two-stage)

This note documents how the GKE deploy root sets `IAP_JWT_AUDIENCE` for the
app-layer IAP-JWT verification introduced in Vuln #4, and how it avoids the
app's **FATAL-on-unset** boot path on a real deploy.

## The audience value

The app cryptographically verifies the IAP-signed `X-Goog-IAP-JWT-Assertion` and
checks its `aud` claim against `IAP_JWT_AUDIENCE`. For the **GKE
Ingress/BackendConfig** topology the audience uses the Compute/GKE load-balancer
form (confirmed from the IAP *signed-headers-howto* doc — see
`infra-modernization/iap-jwt-audience-facts.md` §A row 3):

```
/projects/<PROJECT_NUMBER>/global/backendServices/<NUMERIC_BACKEND_SERVICE_ID>
```

- `<PROJECT_NUMBER>` is derived from `data.google_project.project.number`
  (added to this root; the Cloud Run root already had it). **Never hardcoded.**
- `<NUMERIC_BACKEND_SERVICE_ID>` is the **server-assigned numeric id** of the
  backend service — **not** its name. This is the crux: the existing
  `var.iap_backend_service_name` (which feeds the IAP IAM binding) is the *name*,
  which is fine for IAM but **wrong for the aud**. The aud needs the numeric id of
  the same backend service.

## Why it is not knowable at apply

On GKE the backend service is **not** created by Terraform. The GKE Ingress/NEG
controller creates it **asynchronously, after apply**, from the
`Service` + `Ingress` + `BackendConfig`. Its numeric id therefore does not exist
at initial plan/apply time — a single-pass apply cannot know it. This mirrors how
the repo already treats the backend-service **name** as out-of-band
(`var.iap_backend_service_name`, supplied on a follow-up apply).

## Mechanism chosen: out-of-band numeric-id input on a second apply

A new root input `var.iap_backend_service_id` (numeric id, nullable, default
`null`) carries the id, exactly mirroring the existing out-of-band
`iap_backend_service_name` flow:

```hcl
iap_jwt_audience = var.iap_backend_service_id != null
  ? "/projects/${data.google_project.project.number}/global/backendServices/${var.iap_backend_service_id}"
  : null
# merged into local.creative_studio_env_vars only when non-null:
#   ... , local.iap_jwt_audience != null ? { IAP_JWT_AUDIENCE = local.iap_jwt_audience } : {}
```

When the id is unknown (first apply) the key is **omitted** from the env map —
never a hardcoded id and never an empty placeholder.

**Alternative considered:** a `data "google_compute_backend_service"` lookup by
the known name in the second apply, reading `.generated_id`. Equivalent once the
backend service exists, but it adds a live read/permission dependency and a data
source that returns nothing useful on the first apply. The out-of-band input
variable was chosen for parity with the existing `iap_backend_service_name` flow
and because it keeps the offline gates (`validate`) clean. Either is acceptable to
the owner.

## Owner's two-stage apply sequence

1. **Stage 1 — bring-up (no aud, app NOT in iap mode).** Apply the GKE root with
   `iap_backend_service_id = null` (aud omitted) and `APP_ENV` left at its
   local/unset value. This creates the cluster, workload, Service, Ingress and
   BackendConfig. The GKE Ingress/NEG controller then reconciles and
   **auto-creates the backend service**.
   - The pods in this stage run the pre-Vuln#4 image (or the S2 image, which will
     simply refuse to serve — see "fail-safe" below). **The app never enters iap
     mode here.**
2. **Discover the numeric id** once the Ingress has reconciled:
   ```
   # name is what BackendConfig/Ingress produced (also what feeds iap_backend_service_name):
   gcloud compute backend-services list  --global --format='value(name)'
   gcloud compute backend-services describe <name> --global --format='value(id)'
   ```
3. **Stage 2 — atomic co-deploy (aud + gate + image in ONE rollout).** Set
   `iap_backend_service_id = <numeric id>` (so `IAP_JWT_AUDIENCE` resolves), set
   `APP_ENV` to a non-local value and `REQUIRE_AUTHENTICATED_USER=true`, and roll
   the Vuln#4 (S2) image — all in a **single Deployment rollout / one apply**. The
   app now boots in iap mode **with a resolved audience**.

## How the FATAL-on-unset path is never hit on a live boot

The merged app (commit `69e8af20`) enforces two boot-time checks in
`common/verified_identity.py`:

- `validate_identity_config()` — in **iap mode** (`APP_ENV` non-local), an
  unset/empty `IAP_JWT_AUDIENCE` raises `IdentityConfigError` (FATAL, refuse to
  serve).
- managed-platform backstop — if `AUTH_MODE` resolves to **local** while a
  managed-platform marker is present (`KUBERNETES_SERVICE_HOST` on GKE), it also
  raises `IdentityConfigError` (refuse to serve, no easy override).

The sequence above guarantees the app is placed into **iap mode only in Stage 2**,
and Stage 2 always carries a resolved `IAP_JWT_AUDIENCE`. Concretely, on GKE every
possible boot state is fail-safe:

| Stage | `APP_ENV` | `IAP_JWT_AUDIENCE` | Image | Boot outcome |
|-------|-----------|--------------------|-------|--------------|
| 1 | local/unset | omitted | pre-S2 | Serves (no verification yet; perimeter IAP only — no worse than pre-fix). Backend service still auto-created. |
| 1 (if S2 image used) | local/unset | omitted | S2 | **Refuses to serve** via the managed-platform backstop (fail-safe DOWN). Backend service still auto-created from the Ingress spec regardless of pod health. |
| 2 | non-local (iap) | **resolved** | S2 | Serves, verifying the assertion against the aud. |

There is **no reachable state** where the app boots in iap mode with an empty
audience: iap mode is only entered in Stage 2, where the aud is already resolved
and delivered in the same revision. Because `IAP_JWT_AUDIENCE`, `APP_ENV` and the
image land in one Deployment rollout, there is no intra-deploy window either.

> This is argued from the config/sequence and the merged app checks — it was
> **not** proven by running `terraform apply` (apply is the owner's venue; only the
> offline gates were run here).

## Scope

GKE-only. Cloud Run non-prod/prod roots and the native path are untouched. No
app-code change. No `.terraform/` or lock file committed. No project
ids/numbers/SA/bucket literals.
