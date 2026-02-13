# Brand Consistency with Gemini & Vertex AI

This repository contains two case study notebooks demonstrating how to build automated brand compliance pipelines for generative AI content. As detailed in the accompanying blog post, these examples tackle the challenge of "hallucinated styles" by using Gemini's multimodal capabilities to act as an automated creative director.

## The Challenge

Standard generative AI models are trained on the open internet, not your specific brand book. This often leads to inconsistent assets—wrong hex codes, off-brand tones, or drifted logo placements—that require manual review.

## The Solution: Automated Review Pipeline

These notebooks implement a "Generate → Analyze → Refine" workflow:
1.  **Generate:** Create initial content (Image or Video) from a prompt.
2.  **Analyze:** Use Gemini to evaluate the asset against strict JSON-based brand guidelines (e.g., specific hex codes, "natural" tone).
3.  **Refine:** Automatically update the prompt based on Gemini's specific feedback to correct violations in the next iteration.

## Notebooks

### 1. [Image Generation Case Study]([Blogpost]_Case_Study_1_Cymber_Coffee_Image_Generation_with_Brand_Adherence_py.ipynb)
**Focus:** Static Asset Compliance
**Fictional Brand:** Cymber Coffee ("Forest Tones", "Natural Guide" persona)

This notebook demonstrates:
*   **Structured Evaluation:** Defining brand rules (color palettes, clear space) using Gemini's JSON schema mode.
*   **Closed-Loop Feedback:** How to parse Gemini's critique to programmatically adjust the prompt for Imagen.
*   **Result:** Transforming generic "coffee shop" images into on-brand assets with correct `#184F35` greens and specific tonal qualities.

### 2. [Video Generation Case Study]([Blogpost]_Case_Study_2_Cymber_Coffee_Video_Generation_py.ipynb)
**Focus:** Temporal Consistency
**Model:** Veo (via Vertex AI)

This notebook extends the concept to video generation:
*   **Frame Sampling:** Extracting keyframes across the video's duration.
*   **Temporal Verification:** Ensuring brand elements (like logo placement or color grading) remain consistent from the first second to the last, preventing "drift."
*   **Video Compliance:** Automated checks to ensure the generated video adheres to the "Natural Guide" persona throughout the entire clip.

## Prerequisites

*   **SDK:** `google-genai`
*   **Authentication:** 
    *   Image Generation: Google AI Studio API Key
    *   Video Generation: Google Cloud Project (Vertex AI) authentication
