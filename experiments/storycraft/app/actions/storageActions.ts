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

'use server';

import { getMimeTypeFromGCS, getSignedUrlFromGCS, uploadImage } from '@/lib/storage';
import { unstable_cache as cache } from 'next/cache';
import { v4 as uuidv4 } from 'uuid';

// Define a cached version of the URL fetching logic
const getCachedSignedUrl = cache(
  async (gcsUri: string): Promise<{ url: string | null; mimeType: string | null; }> => {
    console.log(`CACHE MISS: Fetching signed URL for ${gcsUri}`);
    if (!gcsUri || !gcsUri.startsWith('gs://')) {
      console.error("Invalid GCS URI passed to cached function:", gcsUri);
      return { url: null, mimeType: null }; 
    }
    try {
      // get mime type from gcs uri
      const mimeType = await getMimeTypeFromGCS(gcsUri);
      // Call the original GCS function
      const url = await getSignedUrlFromGCS(gcsUri);
      return { url, mimeType }  ;
    } catch (error) {
      console.error(`Error getting signed URL for ${gcsUri} inside cache function:`, error);
      return { url: null, mimeType: null };  // Return null on error
    }
  },
  ['gcs-signed-url'], // Cache key prefix
  {
    revalidate: 60 * 55, // Revalidate every 55 minutes (3300 seconds)
    tags: ['gcs-url'] // Optional tag for on-demand revalidation if needed later
  }
);

/**
 * Server Action to securely get a signed URL for a GCS object.
 * Uses unstable_cache for time-based caching.
 * 
 * @param gcsUri The gs:// URI of the object.
 * @returns A promise that resolves to the signed URL string, or null if an error occurs or URI is invalid.
 */
export async function getDynamicImageUrl(gcsUri: string): Promise<{ url: string | null; mimeType: string | null; }> {
  // Call the cached function
  console.log('getDynamicImageUrl', gcsUri);
  return getCachedSignedUrl(gcsUri);
}

export async function uploadImageToGCS(base64: string): Promise<string | null> {
  const gcsUri = await uploadImage(base64, uuidv4());
  return gcsUri;
}