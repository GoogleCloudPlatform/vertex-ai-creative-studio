# Migration note: deprecated `imagen-3.0-capability-001` → Nano Banana (deferred)

> **Status: DEFERRED.** This is documentation only. No functional changes are made
> in the PR that introduces this file, and none should be made until closer to the
> **2026-06-30** sunset deadline. This note records the *current state*, the
> *suggested conversion path*, and a *refactor recommendation* so the eventual
> migration can start from an agreed plan rather than a cold read of the code.
>
> This experiment is a near-duplicate of
> [`experiments/veo3-item-consistency`](../veo3-item-consistency/MIGRATION.md), which
> is in the identical situation. Treat the two together — see the **Refactor note**
> below.

## 1. Current state

This demo uses **`imagen-3.0-capability-001`** for its image editing / capability
calls. That model is on Google's official **2026-06-30 sunset list**, so this is a
real deadline risk: after that date these calls will stop working.

Where it is used today (all via `client.models.edit_image(...)`):

| File | Call site | `edit_mode` | Purpose |
|---|---|---|---|
| `config.py` | `IMAGEN_MODEL_NAME = "imagen-3.0-capability-001"` | — | Model constant |
| `image_generator.py` | `generate_images_and_select_best()` | `EDIT_MODE_DEFAULT` + `SubjectReferenceImage` | Subject-customized generation of the character in the new scene |
| `utils/outpainting.py` | `outpaint_image()` (hard-codes `edit_model = "imagen-3.0-capability-001"`) | `EDIT_MODE_OUTPAINT` + `MaskReferenceImage` | Mask-based outpaint of the selected image to 16:9 |

Tracking issues:

- **[#1672](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/issues/1672)** —
  modernize the deprecated `imagen-3.0-capability-001` usage (and stale Veo/Gemini IDs) in this directory. **This is the issue the eventual code fix closes; it stays open.**
- **[#1684](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/issues/1684)** —
  related build breakage (Python 3.14 pin fails; README's `pip install -r requirements.txt` path has no `requirements.txt`). Independent of the model migration but worth fixing in the same pass.

## 2. Suggested conversion path to Nano Banana

There is **no direct Imagen 4.0 equivalent** for `imagen-3.0-capability-001`. The
capability model provides *mask-based* editing (subject reference customization and
mask inpaint/outpaint); the Imagen 4.0 generate models do not offer a like-for-like
edit/capability call. A straight version bump is therefore not an option.

The forward direction is **Nano Banana** — Gemini prompt-based image editing
(`gemini-3.1-flash-image`). This is the same decision the **core app** already made
and shipped for its Character Consistency feature:

- Precedent: **[PR #1659](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/pull/1659)**
  ported the core app's Character Consistency edit path off `imagen-3.0-capability-001`
  onto the existing Nano Banana adapter
  (`models.gemini.generate_image_from_prompt_and_images`, backed by
  `GEMINI_IMAGE_GEN_MODEL = gemini-3.1-flash-image`) rather than doing an
  Imagen-4.0 swap.

What that pattern means for **this experiment** when the work is actually done:

1. **Replace the edit client.** Swap the two `client.models.edit_image(...)` calls
   (in `image_generator.py` and `utils/outpainting.py`) for Gemini
   prompt-based image editing that passes the reference image(s) plus a text prompt.
2. **Subject customization** (`EDIT_MODE_DEFAULT` + `SubjectReferenceImage`) becomes
   a prompt-based edit: supply the reference image and describe the target scene in
   the prompt instead of via `SubjectReferenceConfig`.
3. **Outpainting** (`EDIT_MODE_OUTPAINT` + `MaskReferenceImage`) becomes a
   prompt-driven expand-to-16:9 edit. The Imagen mask/pad machinery in
   `utils/outpainting.py` (`pad_to_target_size`, `pad_image_and_mask`,
   `MaskReferenceImage`/`MaskReferenceConfig`) is no longer needed and can be
   removed — Nano Banana takes the aspect-ratio/scene intent from the prompt rather
   than from a user-provided mask.
4. **Drop `IMAGEN_MODEL_NAME`** from `config.py` and point the code at the Gemini
   image model instead.
5. **Expect a behavior change, not a drop-in.** Mask-based editing and prompt-based
   editing produce different results; the outpaint in particular moves from a
   precise mask fill to a prompt-described expansion. Any migration should re-verify
   output quality and document the user-visible difference (the core-app port called
   this out explicitly).

Because prompt-based editing is where Google is investing and where the core app
already landed, adopt Nano Banana rather than chasing an Imagen-4.0 substitute that
does not cover the edit/capability call.

## 3. Refactor note (plan, not a task for now)

`experiments/veo3-character-consistency` and
[`experiments/veo3-item-consistency`](../veo3-item-consistency/MIGRATION.md) are
**near-duplicate codebases**: near-identical `config.py`, the same
`utils/outpainting.py` pattern, the same `image_generator.py` edit call, and the
same stale model set (`gemini-2.5-pro`, `veo-3.0-generate-preview`,
`imagen-3.0-capability-001`). The item variant additionally carries an
`extend_video/` path that also references `IMAGEN_MODEL_NAME`.

When the migration is actually done, **strongly consider refactoring the two into a
single shared implementation** (one image/outpaint/video module parameterized by
subject type) rather than fixing each independently and re-introducing the drift.
Doing the Nano Banana port once against a shared module is less work and less risk
than doing it twice. This is a planning note — do not execute the refactor now.

## 4. Status

**Deferred until closer to the 2026-06-30 deadline.** Documentation only; no
functional changes. Issues [#1672](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/issues/1672)
and [#1684](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/issues/1684)
remain open to track the eventual code work.
