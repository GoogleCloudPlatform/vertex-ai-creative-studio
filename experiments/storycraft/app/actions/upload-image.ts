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

import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

export async function saveImageToPublic(base64String: string, originalFilename: string): Promise<string> {
  try {
    // Extract the file extension from the original filename
    const fileExtension = path.extname(originalFilename).toLowerCase();
    
    // Create a unique filename
    const uniqueFilename = `${uuidv4()}${fileExtension}`;
    
    // Define the directory and full path where the image will be saved
    const uploadDir = path.join(process.cwd(), 'public', 'uploads');
    const filePath = path.join(uploadDir, uniqueFilename);
    
    // Create the directory if it doesn't exist
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    
    // Remove the data URL prefix and convert base64 to buffer
    const base64Data = base64String.split(',')[1];
    const buffer = Buffer.from(base64Data, 'base64');
    
    // Write the file to the public directory
    fs.writeFileSync(filePath, buffer);
    
    // Return the public URL path to the saved image
    return `/uploads/${uniqueFilename}`;
  } catch (error) {
    console.error('Error saving image:', error);
    throw new Error('Failed to save image');
  }
}