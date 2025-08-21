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

import { GetSignedUrlConfig, Storage } from '@google-cloud/storage';
import * as fs from 'fs';
import * as path from 'path';
import { GoogleAuth } from 'google-auth-library';
import { v4 as uuidv4 } from 'uuid';
import { concatenateMusicWithFade } from './ffmpeg';

const USE_SIGNED_URL = process.env.USE_SIGNED_URL === "true";
const GCS_VIDEOS_STORAGE_URI = process.env.GCS_VIDEOS_STORAGE_URI || '';
const LOCATION = process.env.LOCATION
const PROJECT_ID = process.env.PROJECT_ID
const MODEL = 'lyria-002'


const storage = new Storage();

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

export async function generateMusicRest(prompt: string): Promise<string> {
  const token = await getAccessToken();
  const maxRetries = 1; // Maximum number of retries
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
              sampleCount: 1,
            },
          }),
        }
      )
      // Check if the response was successful
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const jsonResult = await response.json(); // Parse as JSON
      const audioContent = jsonResult.predictions[0].bytesBase64Encoded;
      // Decode base64 to buffer
      const audioBuffer = Buffer.from(audioContent, 'base64');
      const outputBuffer = await concatenateMusicWithFade(audioBuffer, 'mp3')
      

      // Define the directory where you want to save the audio files
      const publicDir = path.join(process.cwd(), 'public');
      const outputDir = path.join(publicDir, 'music');

      // Ensure the directory exists
      fs.mkdirSync(outputDir, { recursive: true });

      // Generate a unique filename, e.g., using a timestamp or a UUID
      const uuid = uuidv4();
      const fileName = `music-${uuid}.mp3`;

      // Return the relative file path (for serving the file)
      let musicUrl: string;
      if (USE_SIGNED_URL) {
        // Upload to GCS
        console.log(`Upload result to GCS`);
        const bucketName = GCS_VIDEOS_STORAGE_URI.replace("gs://", "").split("/")[0];
        const destinationPath = path.join(GCS_VIDEOS_STORAGE_URI.replace(`gs://${bucketName}/`, ''), fileName);
        const bucket = storage.bucket(bucketName);
        const file = bucket.file(destinationPath);

        await file.save(outputBuffer, {
          metadata: {
            contentType: `audio/mpeg`, // Set the correct content type for MP3
          }
        });

        // Generate signed URLs
        const options: GetSignedUrlConfig = {
          version: 'v4',
          action: 'read',
          expires: Date.now() + 60 * 60 * 1000, // 1 hour expiration
        };
        [musicUrl] = await file.getSignedUrl(options);
      } else {
        // Write the audio content to a file
        const filePath = path.join(outputDir, fileName);
        fs.writeFileSync(filePath, outputBuffer);
        musicUrl = filePath.split('public/')[1];
      }
      return musicUrl;
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