
# Media Performance and Caching Improvement Plan

### Summary
The current method of serving media by proxying downloads through the FastAPI application is a significant performance bottleneck. This plan outlines a two-step approach to deliver media securely and efficiently.

The core goal is to remove the application server from the data transfer path, allowing users to download media directly from Google's high-performance infrastructure while maintaining strict access control.

---

## Short-Term Recommendation: Signed URL Redirect

This approach immediately removes the application server from the data transfer path, providing a significant performance boost with minimal code changes. It is the quickest way to solve the current latency problem.

### How it Works
1.  A user's browser requests an image from the app (e.g., by rendering an `<img>` tag that points to your server).
2.  The request hits the existing `/media` endpoint in the FastAPI application.
3.  Instead of downloading the file and streaming it back, the backend generates a time-limited **GCS Signed URL**.
4.  The backend responds with an **HTTP 302 Redirect**, pointing the user's browser to this new Signed URL.
5.  The browser automatically follows the redirect and downloads the file directly from Google's high-performance storage infrastructure, bypassing your application server completely.

### Pros
- **Immediate Performance Gain:** Offloads all data transfer from the application server to GCS, freeing up application resources and dramatically improving download speed for users.
- **Minimal Code Change:** Only the logic of the `/media` endpoint needs to be changed. No infrastructure changes are required.
- **Secure:** The GCS bucket remains private, and access is granted on a temporary, per-request basis.

### Cons
- **No Caching:** Signed URLs are unique and time-sensitive by nature, which prevents them from being effectively cached by browsers or downstream Content Delivery Networks (CDNs).

---

## Long-Term Recommendation: Cloud CDN with Signed Cookies

This is the industry-standard, most scalable solution that provides maximum performance, security, and caching. It directly implements your idea for a "signing cookie" in a robust and scalable way.

### How it Works
1.  **Infrastructure:** A Google Cloud Load Balancer with **Cloud CDN** is placed in front of the GCS bucket. The load balancer is configured with two backends: one for the application (Cloud Run) and one for the media (GCS bucket).
2.  **Authentication:** When a user logs in via IAP, the FastAPI backend generates a secure, signed **cookie** and sets it in the user's browser. This cookie, not the URL, contains the authorization token, granting the user permission to view media for a limited time.
3.  **Delivery:** The application renders `<img>` tags with clean, stable, and cacheable URLs that point to the CDN (e.g., `https://your-cdn-domain.com/media/image.jpg`).
4.  **Validation & Caching:** The browser requests the image from the CDN, automatically sending the signed cookie with the request.
    - Cloud CDN inspects and validates the cookie. If it's valid, it serves the file directly from its **global edge cache**.
    - If the file is not in the cache, the CDN fetches it from the private GCS bucket, caches it for future requests, and then serves it to the user.

---

## Implementation Details and Application Changes

This section provides a detailed guide for implementing the long-term Cloud CDN solution.

### Interaction with Existing Application Logic

A key goal is to minimize regression impact. The new infrastructure complements your existing code in the following ways:

1.  **The `/media` Proxy Becomes Obsolete:** With the new Terraform setup, the Google Cloud Load Balancer will route all requests for `/media/*` directly to the GCS/CDN backend. These requests will **no longer reach the FastAPI application**. The `get_media_proxy` function in `main.py` will become unused for external traffic and can eventually be removed.

2.  **Keep Existing URL Generation:** To minimize changes, you should **keep your application configured as if `USE_MEDIA_PROXY=true`**. This ensures the application continues to generate the same `/media/<bucket>/<path>` URL format that it does today. This logic does not need to change. The frontend will receive the same URL format it is used to, but the backend infrastructure that serves it will be different.

3.  **Add New Cookie-Generation Logic:** The only net-new code required in the application is a middleware that generates and sets the signed cookie for authenticated users. This is an isolated addition, not a complex refactoring.

### Example: Signed Cookie Generation Middleware

Below is a detailed example of a FastAPI middleware that generates a Cloud CDN signed cookie for users authenticated by IAP. This code would be added to your `main.py` file.

**Prerequisites:**
Your `requirements.txt` will need to include:
```
google-cloud-secret-manager
cryptography
```

**Example Code (`main.py`):**

```python
import base64
import datetime
import json
import os
from functools import lru_cache

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import Request
from google.cloud import secretmanager

# --- Add these imports to the top of your main.py ---

# Environment variable for the Secret Manager secret containing the CDN signing key
# This will be set in your main.tf for the Cloud Run service.
CDN_SIGNING_KEY_SECRET_ID = os.environ.get("CDN_SIGNING_KEY_SECRET_ID")
# The name of the key configured in the Terraform `google_compute_backend_bucket_signed_url_key` resource.
CDN_KEY_NAME = os.environ.get("CDN_KEY_NAME", "my-cdn-key")
# The base URL for media, matching the load balancer path rule.
CDN_MEDIA_PATH = "/media/"


@lru_cache(maxsize=1)
def get_cdn_signing_key(secret_resource_id: str) -> bytes:
    """
    Fetches the raw CDN signing key from Secret Manager.
    Uses lru_cache to fetch the secret only once per application instance.
    """
    if not secret_resource_id:
        raise ValueError("CDN_SIGNING_KEY_SECRET_ID environment variable not set.")

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_resource_id)
    return response.payload.data


def create_signed_cookie(url_prefix: str, key: bytes, key_name: str, expiration_time: datetime.datetime) -> str:
    """Creates a signed cookie value for Cloud CDN."""
    encoded_url_prefix = base64.urlsafe_b64encode(url_prefix.encode("utf-8")).decode(
        "utf-8"
    )
    expires = int(expiration_time.timestamp())

    policy = f"URLPrefix={encoded_url_prefix}:Expires={expires}:KeyName={key_name}"

    # Load the private key from the raw bytes
    private_key = serialization.load_pem_private_key(key, password=None)

    # Sign the policy
    signature = private_key.sign(policy.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())

    encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8")

    return f"{policy}:Signature={encoded_signature}"


# --- Add this new middleware to your main.py, preferably after the `set_request_context` middleware ---

@app.middleware("http")
async def cdn_signed_cookie_middleware(request: Request, call_next):
    """
    This middleware checks for an IAP-authenticated user and, if found,
    sets a Cloud CDN signed cookie to grant them access to media assets.
    """
    # First, get the response that will be sent to the user.
    response = await call_next(request)

    # Only proceed if the required configuration is present.
    if not CDN_SIGNING_KEY_SECRET_ID:
        return response

    # Check if the user was authenticated by IAP.
    user_email = request.scope.get("MESOP_USER_EMAIL")
    is_authenticated_by_iap = user_email and user_email != "anonymous@google.com"

    # Also check if the user already has a valid cookie.
    has_valid_cookie = "Cloud-CDN-Cookie" in request.cookies

    # If the user is authenticated and doesn't already have a cookie, generate one.
    if is_authenticated_by_iap and not has_valid_cookie:
        try:
            # Fetch the key from Secret Manager (this will be cached).
            signing_key_bytes = get_cdn_signing_key(CDN_SIGNING_KEY_SECRET_ID)

            # Set the cookie to be valid for 1 day.
            expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)

            # Create the signed cookie value.
            cookie_value = create_signed_cookie(
                url_prefix=CDN_MEDIA_PATH,
                key=signing_key_bytes,
                key_name=CDN_KEY_NAME,
                expiration_time=expiration,
            )

            # Set the cookie in the user's browser.
            # It is important to set `path`, `secure`, `httponly`, and `samesite`.
            response.set_cookie(
                key="Cloud-CDN-Cookie",
                value=cookie_value,
                expires=expiration,
                path="/",
                secure=True,       # Only send over HTTPS
                httponly=True,     # Prevent access from JavaScript
                samesite="Lax",
            )
        except Exception as e:
            # If cookie generation fails, log the error but do not block the user's request.
            # They will still be able to use the app, but media might appear broken.
            print(f"Error generating CDN signed cookie: {e}")

    return response

```

This detailed plan provides a clear path forward, minimizing application changes while moving to a robust, scalable, and high-performance architecture for media delivery.

