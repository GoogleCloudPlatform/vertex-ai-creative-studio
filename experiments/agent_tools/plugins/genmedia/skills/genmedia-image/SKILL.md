---
name: genmedia-image
description: Generate images from a text prompt (optionally guided by reference images) using the genmedia Nanobanana MCP server's nanobanana_image_generation tool. Use when a task needs a still image produced from a description, with control over aspect ratio, resolution, and local vs GCS output, and verified by confirming the artifact was actually written.
license: Apache-2.0
---

# genmedia Image

This skill generates images by calling the `nanobanana_image_generation` tool
exposed by the genmedia **Nanobanana** MCP server. It is a single-purpose skill:
one tool, one job. It supports both local workspace execution and remote / managed
agent execution via GCS staging, and it always verifies that a real artifact was
produced — never that the call merely returned without error.

**Prerequisite:** the genmedia Nanobanana MCP server must already be configured
in your client (e.g. via this plugin's `mcp.json` / `.mcp.json`, or a manual MCP
config). The server needs `GOOGLE_CLOUD_PROJECT` and Application Default
Credentials (ADC) in its environment for Vertex AI calls.

## Instructions

1. **Resolve Output Storage Mode:**
   * **Local Mode (Default):** Pass `output_directory` pointing to the target
     local workspace directory. The artifact is written to that local path.
   * **Managed Agent / GCS Mode:** When executing inside a managed agent
     container where the MCP server runs remotely on Cloud Run, pass
     `gcs_bucket_uri` (a GCS URI prefix such as `your-bucket/outputs/`) — or set
     the `GENMEDIA_BUCKET` environment variable — pointing to the mounted GCS
     environment bucket.
   * Do not pass both modes' destinations for the same call unless you
     intentionally want output in both places.

2. **Formulate Imagery Parameters:**
   * **`prompt`** (required): a detailed text description. Favor concrete style,
     subject, lighting, and composition language (e.g. *"a photorealistic red
     panda sitting in a bamboo forest, golden hour lighting"*).
   * **`model`** (optional): defaults to `gemini-3.1-flash-image`. Leave unset
     unless you have a specific model requirement.
   * **`aspect_ratio`** (optional): defaults to `1:1`. Supported ratios are
     model-dependent (common values include `1:1`, `3:4`, `4:3`, `9:16`,
     `16:9`). Choose the ratio that matches the intended use (e.g. `16:9` for a
     hero banner, `9:16` for a vertical/mobile frame).
   * **`image_size`** (optional): `1K`, `2K`, or `4K`. Defaults to `1K` when
     unset. Supported sizes are model-dependent.
   * **`output_filename`** (optional): a client-predictable base name (e.g.
     `hero.png`). The extension is forced to the true output media type. When a
     single image is produced the name is used as-is; when multiple images are
     produced they are suffixed `_1`, `_2`, … before the extension. An existing
     file/object of the same name is overwritten.
   * **`seed`** (optional): a non-negative integer for best-effort reproducible
     generation.

3. **Reference Images (optional, `images`):**
   * To guide generation with existing media, pass `images` as a list of
     **local file paths or GCS URIs** (images, and — where the model supports it
     — videos or PDFs). Use this for edits, style transfer, character
     consistency, or compositing from source frames.
   * Ensure every referenced path/URI actually exists before the call; a
     missing reference produces a degraded or failed result.

4. **Invoke the tool:**
   * Call `nanobanana_image_generation` with the parameters assembled above.
   * **Local Mode example params:**
     `{ "prompt": "...", "aspect_ratio": "16:9", "output_directory": "./out", "output_filename": "hero.png" }`
   * **GCS Mode example params:**
     `{ "prompt": "...", "aspect_ratio": "16:9", "gcs_bucket_uri": "your-bucket/outputs/", "output_filename": "hero.png" }`
   * **Reference-guided example params:**
     `{ "prompt": "same character, new pose", "images": ["./refs/character.png"], "output_directory": "./out", "output_filename": "pose.png" }`

5. **Verify the Artifact By Existence (do not trust the response alone):**
   * A tool call that returns without an error is **not** proof an image was
     written. In some clients and in GCS mode the server returns a
     `resource_link` content type that cannot be rendered even though the file
     was written — never assume inline data.
   * **Local Mode:** confirm the file exists and is a real, non-empty image, and
     inspect its type:
     ```sh
     file "<output_directory>/<output_filename>"   # e.g. "... PNG image data, 1024 x 1024"
     ```
   * **GCS Mode:** confirm the object exists at the destination prefix by
     listing it — do **not** parse the tool response:
     ```sh
     gcloud storage ls "gs://<gcs_bucket_uri prefix>"
     ```
     Note: if you relied on the `GENMEDIA_BUCKET` environment variable instead of
     passing `gcs_bucket_uri` explicitly, the server writes under a
     `nanobanana_outputs/` subprefix — list `gs://<GENMEDIA_BUCKET>/nanobanana_outputs/`,
     not the bare bucket.
   * If no artifact is found, treat the generation as failed and surface the
     tool response for debugging rather than reporting success.
