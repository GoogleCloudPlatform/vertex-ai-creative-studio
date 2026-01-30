/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export interface VeoResponse {
  videoUri: string;
  sourceUri: string;
}

export interface GenerateOptions {
  prompt: string;
  model?: string;
  aspectRatio?: string;
  imageUri?: string;
  imageMimeType?: string;
  lastFrameUri?: string;
  lastFrameMimeType?: string;
  refImageUris?: string[];
  refImageTypes?: string[];
}

export async function generateVideo(options: GenerateOptions): Promise<VeoResponse> {
  const response = await fetch('/api/veo/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Generation failed: ${response.status} ${errorText}`);
  }

  return response.json();
}

export async function extendVideo(videoUri: string, prompt: string, model?: string): Promise<VeoResponse> {
  const response = await fetch('/api/veo/extend', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      videoUri, 
      prompt,
      model
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Extension failed: ${response.status} ${errorText}`);
  }

  return response.json();
}