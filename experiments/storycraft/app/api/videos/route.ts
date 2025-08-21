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

import { Scene } from '@/app/types';
import { generateSceneVideo, waitForOperation } from '@/lib/veo';
import { getRAIUserMessage } from '@/lib/rai';
import { GetSignedUrlConfig, Storage } from '@google-cloud/storage';
import * as fs from 'fs/promises';
import * as path from 'path';


const USE_SIGNED_URL = process.env.USE_SIGNED_URL === "true";
const USE_COSMO = process.env.USE_COSMO === "true";

const placeholderVideoUrls = [
  'cosmo.mp4',
  'dogs1.mp4',
  'dogs2.mp4',
  'cats1.mp4',
];

/**
 * Handles POST requests to generate videos from a list of scenes.
 *
 * @param req - The incoming request object, containing a JSON payload with an array of scenes.
 *               Each scene should have `imagePrompt`, `description`, `voiceover`, and optionally `imageBase64`.
 * @returns A Promise that resolves to a Response object. The response will be a JSON object
 *          with either a success flag and the generated video URLs or an error message.
 */
export async function POST(req: Request): Promise<Response> {

  const { scenes }: {
    scenes: Array<Scene>
  } = await req.json();



  try {
    console.log('Generating videos in parallel...');
    console.log('scenes', scenes);
    const storage = new Storage();

    const videoGenerationTasks = scenes
      .filter(scene => scene.imageGcsUri)
      .map(async (scene, index) => {
        console.log(`Starting video generation for scene ${index + 1}`);
        let url: string;
        if (USE_COSMO) {
          // randomize the placeholder video urls
          url = placeholderVideoUrls[Math.floor(Math.random() * placeholderVideoUrls.length)];
        } else {
          const operationName = await generateSceneVideo(scene.videoPrompt, scene.imageGcsUri!);
          console.log(`Operation started for scene ${index + 1}`);

          const generateVideoResponse = await waitForOperation(operationName);
          console.log(`Video generation completed for scene ${index + 1}`);
          console.log(generateVideoResponse)

          if (generateVideoResponse.response.raiMediaFilteredReasons) {
            // Throw an error with the determined user-friendly message
            throw new Error(generateVideoResponse.response.raiMediaFilteredReasons);
          }

          const gcsUri = generateVideoResponse.response.videos[0].gcsUri;
          const [bucketName, ...pathSegments] = gcsUri.replace("gs://", "").split("/");
          const fileName = pathSegments.join("/");

          if (USE_SIGNED_URL) {
            const options: GetSignedUrlConfig = {
              version: 'v4',
              action: 'read',
              expires: Date.now() + 60 * 60 * 1000,
            };

            // storage.bucket(bucketName).file(fileName).copy()

            [url] = await storage.bucket(bucketName).file(fileName).getSignedUrl(options);
          } else {
            const publicDir = path.join(process.cwd(), 'public');
            const videoFile = path.join(publicDir, fileName);
            // Get the directory of the destination path
            const destinationDir = path.dirname(videoFile);
            // Create the destination directory if it doesn't exist (recursive)
            await fs.mkdir(destinationDir, { recursive: true });

            await storage.bucket(bucketName).file(fileName).download({ destination: videoFile });
            url = fileName;
          }
        }
        console.log('Video Generated!', url)
        return url;
      });

    const videoUrls = await Promise.all(videoGenerationTasks);

    return Response.json({ success: true, videoUrls }); // Return response data if needed
  } catch (error) {
    console.error('Error in generateVideo:', error);
    return Response.json(
      { success: false, error: error instanceof Error ? error.message : 'Failed to generate video(s)' }
    );
  }
}


