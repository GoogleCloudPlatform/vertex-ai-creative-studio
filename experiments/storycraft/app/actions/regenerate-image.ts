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

'use server'

import { generateImageRest } from '@/lib/imagen';

export async function regenerateImage(prompt: string) {
  try {
    console.log('Regenerating image with prompt:', prompt);
    const resultJson = await generateImageRest(prompt);
    if (resultJson.predictions[0].raiFilteredReason) {
      throw new Error(resultJson.predictions[0].raiFilteredReason)
    } else {
      console.log('Generated image:', resultJson.predictions[0].gcsUri);
      return { imageGcsUri: resultJson.predictions[0].gcsUri };
    }
  } catch (error) {
    console.error('Error generating image:', error);
    if (error instanceof Error) {
      return { imageGcsUri: undefined, errorMessage: error.message };
    } else {
      return { imageGcsUri: undefined };
    }
  }
}

export async function regenerateCharacterImage(prompt: string) {
  try {
    console.log('Regenerating character image with prompt:', prompt);
    const resultJson = await generateImageRest(prompt, "1:1", false);
    if (resultJson.predictions[0].raiFilteredReason) {
      throw new Error(resultJson.predictions[0].raiFilteredReason)
    } else {
      console.log('Generated character image:', resultJson.predictions[0].gcsUri);
      return { imageGcsUri: resultJson.predictions[0].gcsUri };
    }
  } catch (error) {
    console.error('Error generating image:', error);
    if (error instanceof Error) {
      return { imageGcsUri: undefined, errorMessage: error.message };
    } else {
      return { imageGcsUri: undefined };
    }
  }
}

