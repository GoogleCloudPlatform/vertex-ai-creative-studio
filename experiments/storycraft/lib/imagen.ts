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

import { GoogleAuth } from 'google-auth-library'


const LOCATION = process.env.LOCATION
const PROJECT_ID = process.env.PROJECT_ID
const GCS_VIDEOS_STORAGE_URI = process.env.GCS_VIDEOS_STORAGE_URI
const MODEL = 'imagen-4.0-generate-preview-06-06' //'imagen-3.0-generate-002'
const MODEL_EDIT = 'imagen-3.0-capability-001'

async function getAccessToken(): Promise<string> {
  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });
  const client = await auth.getClient();
  const accessToken = (await client.getAccessToken()).token;
  // Check if accessToken is null or undefined
  if (accessToken) {
    return accessToken;
  } else {
    // Handle the case where accessToken is null or undefined
    // This could involve throwing an error, retrying, or providing a default value
    throw new Error('Failed to obtain access token.');
  }
}

interface GenerateImageResponse {
  predictions: Array<{
    bytesBase64Encoded: string;
    mimeType: string;
    gcsUri: string;
    raiFilteredReason?: string;
  }>;
}

export async function generateImageRest(prompt: string, aspectRatio?: string, enhancePrompt?: boolean): Promise<GenerateImageResponse> {
  const token = await getAccessToken();
  const maxRetries = 5; // Maximum number of retries
  const initialDelay = 1000; // Initial delay in milliseconds (1 second)
  console.log(MODEL)

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(
        `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:predict`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: JSON.stringify({
            instances: [
              {
                prompt: prompt
              },
            ],
            parameters: {
              // storageUri: "gs://svc-demo-vertex-us/",
              safetySetting: 'block_only_high',
              personGeneration: 'allow_adult',
              sampleCount: 1,
              aspectRatio: aspectRatio ? aspectRatio : "16:9",
              includeRaiReason: true,
              storageUri: GCS_VIDEOS_STORAGE_URI,
              enhancePrompt: enhancePrompt !== undefined ? enhancePrompt : true,
              language: 'auto',
            },
          }),
        }
      )
      // Check if the response was successful
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const jsonResult = await response.json(); // Parse as JSON
      return jsonResult;
    } catch (error) {
      if (attempt < maxRetries) {
        const baseDelay = initialDelay * Math.pow(2, attempt); // Exponential backoff
        const jitter = Math.random() * 2000; // Random value between 0 and baseDelay
        const delay = baseDelay + jitter;
        console.warn(`Attempt ${attempt + 1} failed. Retrying in ${delay}ms...`, error);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        console.error(`Failed after ${maxRetries} attempts.`, error);
        throw error; // Re-throw the error after maximum retries
      }
    }
  }
  throw new Error("Function should have returned or thrown an error before this line.");
}

export async function generateImageCustomizationRest(prompt: string, characters: Array<{ name: string, description: string, imageBase64?: string }>, aspectRatio?: string): Promise<GenerateImageResponse> {
  const token = await getAccessToken();
  const maxRetries = 1;
  const initialDelay = 1000;

  const referenceImagesPayload = characters
    .filter(character => character.imageBase64)
    .map((character, index) => ({
      referenceType: 'REFERENCE_TYPE_SUBJECT',
      referenceId: index + 1,
      referenceImage: {
        bytesBase64Encoded: character.imageBase64!,
      },
      subjectImageConfig: {
        subjectDescription: character.description,
        subjectType: 'SUBJECT_TYPE_PERSON',
      },
    }));

  const customizedPrompt = `Generate an image of ${referenceImagesPayload.map((ref) => `${ref.subjectImageConfig.subjectDescription} [${ref.referenceId}]`)} to match this description: ${prompt}`

  const body = JSON.stringify({
    instances: [
      {
        prompt: customizedPrompt,
        referenceImages: referenceImagesPayload,
      },
    ],
    parameters: {
      // storageUri: "gs://svc-demo-vertex-us/",
      safetySetting: 'block_only_high',
      sampleCount: 1,
      aspectRatio: aspectRatio ? aspectRatio : "16:9",
      includeRaiReason: true,
      language: 'auto',
    },
  })

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(
        `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_EDIT}:predict`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: body,
        }
      )
      // Check if the response was successful
      if (!response.ok) {
        console.log(response)
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const jsonResult = await response.json(); // Parse as JSON
      return jsonResult;
    } catch (error) {
      if (attempt < maxRetries) {
        const baseDelay = initialDelay * Math.pow(2, attempt); // Exponential backoff
        const jitter = Math.random() * 2000; // Random value between 0 and baseDelay
        const delay = baseDelay + jitter;
        console.warn(`Attempt ${attempt + 1} failed. Retrying in ${delay}ms...`, error);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        console.error(`Failed after ${maxRetries} attempts.`, error);
        throw error; // Re-throw the error after maximum retries
      }
    }
  }
  throw new Error("Function should have returned or thrown an error before this line.");
}