# `mcp-nanobanana-go` MCP Server

This server provides an MCP interface to Google's NanoBanana (Gemini Image) models, allowing for multimodal content generation.

## Tools

### `nanobanana_image_generation`

Generates content (text and/or images) based on a multimodal prompt.

**Parameters:**

- `prompt` (string, required): The text prompt for content generation.
- `model` (string, optional): The specific NanoBanana (Gemini Image) model to use. Defaults to `gemini-3.1-flash-image`.
- `images` (string array, optional): A list of local file paths or GCS URIs for input images.
- `output_directory` (string, optional): Local directory to save any generated image(s) to.
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store any generated images.




## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID.
    *   **Override**: You can override this globally for this specific server by setting `NANOBANANA_PROJECT_ID`.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud location/region for Vertex AI services.
    *   Default: `"us-central1"`
    *   **Fallback**: `LOCATION` is also supported as a fallback for `GOOGLE_CLOUD_LOCATION`.
    *   **Override**: You can override this globally for this specific server by setting `NANOBANANA_LOCATION`.
*   `ALLOW_UNSAFE_MODELS` (boolean): Optional (`true`/`false`). Allows users to bypass strict local model constraint validation, enabling them to test experimental or pre-release model strings that are not yet hardcoded in the registry.
    *   Default: `false`
*   `ENABLE_OPTIONAL_HEADER_CAPTURE` (boolean): Optional (`true`/`false`). Intended for internal debugging. When set to `true`, the server intercepts API requests and injects the raw ADC Bearer token to capture and surface the `x-goog-sherlog-link` header in the tool output. This feature is supported for NanoBanana.
    *   Default: `false`
*   `GENMEDIA_BUCKET` (string): Optional. Bucket name (no `gs://` prefix) used as the **fallback** destination for generated images when the `gcs_bucket_uri` parameter is not passed. Images are written under `<bucket>/nanobanana_outputs/`.
*   `NANOBANANA_SIGNED_URL_EXPIRY_HOURS` (integer): Optional. Validity, in hours, of the V4 signed HTTPS URLs returned alongside each uploaded image.
    *   Default: `24`
    *   Values are clamped to `168` (7 days, the V4 maximum).
    *   Set to `0` to disable signed-URL generation entirely (the `gs://` URI is still returned).

## Saving to Google Cloud Storage

When `gcs_bucket_uri` (or the `GENMEDIA_BUCKET` fallback) is set, the tool uploads each generated image to GCS, returns the `gs://` URI, and additionally returns a **V4-signed HTTPS URL** so MCP clients can display the image without the bucket being public. This is useful for remote/containerized deployments (SSE bridge, Cloud Run) where no retrievable local directory exists — without a bucket configured and no `output_directory`, generated image bytes are discarded.

### Signed URLs — credentials

Generating a signed URL requires an RSA signer:

*   With a **service-account JSON key** (`GOOGLE_APPLICATION_CREDENTIALS`), signing is done locally — no extra IAM required.
*   Under **Application Default Credentials without a private key** (the normal Cloud Run / GKE / metadata-server case), the tool signs via the IAM `signBlob` API. This requires the **runtime service account to hold `roles/iam.serviceAccountTokenCreator` on itself** (which grants `iam.serviceAccounts.signBlob`):

    ```bash
    gcloud iam service-accounts add-iam-policy-binding RUNTIME_SA_EMAIL \
      --member="serviceAccount:RUNTIME_SA_EMAIL" \
      --role="roles/iam.serviceAccountTokenCreator"
    ```

*   **If this permission is absent, signing is skipped (non-fatal): the upload still succeeds and the `gs://` URI is still returned — only the HTTPS signed link is omitted.**

## Example Usage

### Generating an Image

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project

mcptools call nanobanana_image_generation \
  --params '{"prompt": "a picture of a cat sitting on a table", "output_directory": "./output"}' \
  mcp-nanobanana-go
```
