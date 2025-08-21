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

import { GoogleAuth } from 'google-auth-library';
import { GoogleGenAI, Part } from '@google/genai';

const LOCATION = process.env.LOCATION
const PROJECT_ID = process.env.PROJECT_ID
const MODEL = process.env.MODEL
const GCS_VIDEOS_STORAGE_URI = process.env.GCS_VIDEOS_STORAGE_URI


const ai = new GoogleGenAI({ vertexai: true, project: PROJECT_ID, location: LOCATION });


interface GenerateVideoResponse {
  name: string;
  done: boolean;
  response: {
    '@type': 'type.googleapis.com/cloud.ai.large_models.vision.GenerateVideoResponse';
    videos: Array<{
      gcsUri: string;
      mimeType: string;
    }>;
    raiMediaFilteredReasons?: string;
  };
  error?: { // Add an optional error field to handle operation errors
    code: number;
    message: string;
    status: string;
  };
}

async function getAccessToken(): Promise<string> {
  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });
  const client = await auth.getClient();
  const accessToken = (await client.getAccessToken()).token;
  if (accessToken) {
    return accessToken;
  } else {
    throw new Error('Failed to obtain access token.');
  }
}

async function checkOperation(operationName: string): Promise<GenerateVideoResponse> {
  const token = await getAccessToken();

  const response = await fetch(
    `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:fetchPredictOperation`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        operationName: operationName,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const jsonResponse = await response.json();
  return jsonResponse as GenerateVideoResponse;
}

export async function waitForOperation(operationName: string): Promise<GenerateVideoResponse> {
  const checkInterval = 2000; // Interval for checking operation status (in milliseconds)

  const pollOperation = async (): Promise<GenerateVideoResponse> => {
    const generateVideoResponse = await checkOperation(operationName);

    if (generateVideoResponse.done) {
      // Check if there was an error during the operation
      if (generateVideoResponse.error) {
        throw new Error(`Operation failed with error: ${generateVideoResponse.error.message}`);
      }
      return generateVideoResponse;
    } else {
      await delay(checkInterval);
      return pollOperation(); // Recursive call for the next poll
    }
  };

  return pollOperation();
}

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function generateSceneVideo(prompt: string, imageGcsUri: string): Promise<string> {
  const token = await getAccessToken();
  const maxRetries = 5; // Maximum number of retries
  const initialDelay = 1000; // Initial delay in milliseconds (1 second)

  const jsonPrompt = false
  let modifiedPrompt: string;
  if (jsonPrompt) {

    const tools = [
      {
        googleSearch: {
        }
      },
    ];
    const config = {
      thinkingConfig: {
        thinkingBudget: -1,
      },
      tools,
      responseMimeType: 'application/json',
    };
    const model = 'gemini-2.5-flash';
    const contents = [
      {
        role: 'user',
        parts: [
          {
            fileData: {
              fileUri: imageGcsUri,
              mimeType: `image/jpeg`,
            },
          },
          {
            text: `You are a specialist video director.

Your goal is to generate a structured json prompt for a video.
First analyse this image that will be the first frame of the video.


From this image and this pitch :
${prompt}


Add some dialogs.
Should never have music or songs.
Total duration should be 8s.
Generate a video prompt in YAML using this format :
{
  "character_name": [character's name],
  "character_profile": {
    "age": [character's age],
    "height": [character's height],
    "build": [character's physical build],
    "skin_tone": [character's skin tone],
    "hair": [character's hair description],
    "eyes": [character's eye description],
    "distinguishing_marks": [character's distinguishing marks],
    "demeanour": [character's general demeanour]
  },

  "global_style": {
    "camera": [overall camera style and motion],
    "color_grade": [overall color grading style],
    "lighting": [overall lighting style],
    "outfit": [overall character outfit description],
    "max_clip_duration_sec": [maximum duration of any clip in seconds],
    "aspect_ratio": [overall video aspect ratio]
  },

  "clips": [
    {
      "id": [unique clip identifier],
      "shot": {
        "composition": [shot composition details],
        "camera_motion": [shot camera motion],
        "frame_rate": [shot frame rate],
        "film_grain": [shot film grain intensity]
      },
      "subject": {
        "description": [detailed subject description for the clip],
        "wardrobe": [subject's wardrobe for the clip]
      },
      "scene": {
        "location": [scene location],
        "time_of_day": [scene time of day],
        "environment": [scene environment details]
      },
      "visual_details": {
        "action": [character's action in the clip],
        "props": [props visible in the clip]
      },
      "cinematography": {
        "lighting": [clip-specific lighting details],
        "tone": [clip's emotional tone]
      },
      "color_palette": [clip-specific color palette],
      "dialogue": {
        "character": [character speaking the dialogue],
        "line": [dialogue line spoken by the character],
        "subtitles": false
      },
      "duration_sec": [clip duration in seconds],
      "aspect_ratio": [clip aspect ratio]
    }
  ]
}`,
          },
        ],
      },
    ];

    const response = await ai.models.generateContent({
      model,
      config,
      contents,
    });

    console.log('text', response.text)
    modifiedPrompt = response.text || (prompt + '\nDialog: none\nSubtitles: off')
  } else {
    modifiedPrompt = prompt + '\nDialog: none\nSubtitles: off'
  }


  console.log(MODEL)
  const makeRequest = async (attempt: number) => {
    try {
      const response = await fetch(
        `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:predictLongRunning`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            instances: [
              {
                prompt: modifiedPrompt,
                image: {
                  gcsUri: imageGcsUri,
                  mimeType: "png",
                },
              },
            ],
            parameters: {
              storageUri: GCS_VIDEOS_STORAGE_URI,
              sampleCount: 1,
              aspectRatio: "16:9",
              generateAudio: true,
            },
          }),
        }
      );

      // Check if the response was successful
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const jsonResult = await response.json(); // Parse as JSON
      return jsonResult.name;
    } catch (error) {
      if (attempt < maxRetries) {
        const baseDelay = initialDelay * Math.pow(2, attempt); // Exponential backoff
        const jitter = Math.random() * 2000; // Random value between 0 and baseDelay
        const delay = baseDelay + jitter;
        console.warn(
          `Attempt ${attempt + 1} failed. Retrying in ${delay}ms...`,
          error instanceof Error ? error.message : error
        );
        await new Promise(resolve => setTimeout(resolve, delay));
        return makeRequest(attempt + 1); // Recursive call for retry
      } else {
        console.error(`Failed after ${maxRetries} attempts.`, error);
        throw error; // Re-throw the error after maximum retries
      }
    }
  };

  return makeRequest(0); // Start the initial request
}