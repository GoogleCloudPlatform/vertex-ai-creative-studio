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
import sharp from 'sharp';

// Initialize storage
const storage = new Storage({
    projectId: process.env.PROJECT_ID,
    // keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS, // Uncomment if needed
});

const storageUri = process.env.GCS_VIDEOS_STORAGE_URI; // Make sure this env var is set

export async function uploadImage(base64: string, filename: string): Promise<string | null> {
    if (!storageUri) {
        console.error('GCS_VIDEOS_STORAGE_URI environment variable is not set.');
        // Depending on requirements, you might want to throw an error instead
        // throw new Error('Server configuration error: STORAGE_URI not specified.'); 
        return null; // Return null to indicate failure due to missing config
    }
    if (!base64) {
        console.warn('Attempted to upload an empty base64 string.');
        return null;
    }

    try {
        // Decode the base64 string into a buffer
        // Remove the data URI prefix if it exists (e.g., "data:image/jpeg;base64,")
        const base64Data = base64.includes(',') ? base64.split(',')[1] : base64;
        const buffer = Buffer.from(base64Data, 'base64');

        // Get the bucket name from the storage URI
        // We know storageUri is defined here due to the check above
        const bucketName = storageUri.startsWith('gs://') 
                           ? storageUri.substring(5).split('/')[0]
                           : storageUri.split('/')[0]; // Basic fallback if not starting with gs://
        
        if (!bucketName) {
            console.error('Could not extract bucket name from STORAGE_URI:', storageUri);
            return null;
        }

        // Get a reference to the bucket
        const bucket = storage.bucket(bucketName);

        // Create a reference to the file object
        const file = bucket.file(filename);

        // Upload the buffer to GCS
        // We determine the content type; adjust if you expect other types
        const contentType = 'data:image/png';

        await file.save(buffer, {
            metadata: {
                contentType: contentType,
                // Optional: Add cache control headers, etc.
                // cacheControl: 'public, max-age=31536000',
            },
            public: false, // Keep files private unless explicitly made public
        });

        // Construct the GCS URI
        const gcsUri = `gs://${bucketName}/${filename}`; // Construct the standard gs:// URI
        console.log(`Successfully uploaded ${filename} to ${gcsUri}`);
        return gcsUri;

    } catch (error) {
        console.error(`Failed to upload image ${filename} to GCS:`, error);
        return null;
    }
}

export async function getSignedUrlFromGCS(gcsUri: string) {
  const [bucketName, ...pathSegments] = gcsUri.replace("gs://", "").split("/");
  const fileName = pathSegments.join("/");
  const options: GetSignedUrlConfig = {
    version: 'v4',
    action: 'read',
    expires: Date.now() + 60 * 60 * 1000,
  };
  const [url] = await storage.bucket(bucketName).file(fileName).getSignedUrl(options);
  return url;
}

/**
 * Downloads an image from a GCS URI and returns a sharp object.
 *
 * @param gcsUri The Google Cloud Storage URI (e.g., "gs://bucket-name/path/to/image.jpg").
 * @returns A Promise resolving to a sharp instance.
 */
export async function gcsUriToSharp(gcsUri: string): Promise<sharp.Sharp> {
  try {
    // 1. Parse the GCS URI to extract bucket name and file path
    const match = gcsUri.match(/^gs:\/\/([^\/]+)\/(.+)$/);
    if (!match) {
      throw new Error(`Invalid GCS URI format: ${gcsUri}`);
    }
    const bucketName = match[1];
    const filePath = match[2];

    // 2. Download the image file from GCS into a buffer
    console.log(`Downloading image from gs://${bucketName}/${filePath}`);
    const [buffer] = await storage.bucket(bucketName).file(filePath).download();
    console.log(`Image downloaded successfully (${buffer.length} bytes)`);

    // 3. Create a sharp object from the downloaded buffer
    return sharp(buffer);

  } catch (error) {
    console.error(`Error processing image from GCS URI ${gcsUri}:`, error);
    // Re-throw the error so the caller can handle it
    throw error;
  }
}

/**
 * Downloads an image from a GCS URI and returns its base64 encoded string
 * representation.
 *
 * @param gcsUri The Google Cloud Storage URI (e.g., "gs://bucket-name/path/to/image.jpg").
 * @returns A Promise resolving to the base64 data URI string.
 */
export async function gcsUriToBase64(gcsUri: string): Promise<string> {
  try {
    // 1. Parse the GCS URI
    const match = gcsUri.match(/^gs:\/\/([^\/]+)\/(.+)$/);
    if (!match) {
      throw new Error(`Invalid GCS URI format: ${gcsUri}`);
    }
    const bucketName = match[1];
    const filePath = match[2];

    // 2. Download the image file into a buffer
    console.log(`Downloading image for base64 conversion from gs://${bucketName}/${filePath}`);
    const [buffer] = await storage.bucket(bucketName).file(filePath).download();
    console.log(`Image downloaded successfully (${buffer.length} bytes)`);

    // // 3. Determine image format using sharp to get the correct MIME type
    // const imageSharp = sharp(buffer);
    // const metadata = await imageSharp.metadata();
    // const format = metadata.format; // e.g., 'jpeg', 'png', 'webp', etc.
    // if (!format) {
    //   throw new Error('Could not determine image format.');
    // }
    // const mimeType = `image/${format}`;

    // 4. Convert buffer to base64 string
    const base64Data = buffer.toString('base64');

    // 5. Construct the full data URI
    // const dataUri = `data:${mimeType};base64,${base64Data}`;
    const dataUri = `${base64Data}`;
    return dataUri;

  } catch (error) {
    console.error(`Error converting GCS URI ${gcsUri} to base64:`, error);
    // Re-throw the error so the caller can handle it
    throw error;
  }
}


export async function getMimeTypeFromGCS(gcsUri: string): Promise<string | null> {
  const [bucketName, ...pathSegments] = gcsUri.replace("gs://", "").split("/");
  const fileName = pathSegments.join("/");
  const [metadata] = await storage.bucket(bucketName).file(fileName).getMetadata();
  return metadata.contentType || null;
}
