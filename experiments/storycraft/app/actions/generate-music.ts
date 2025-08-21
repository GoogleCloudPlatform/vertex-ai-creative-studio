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

import { generateMusicRest } from '@/lib/lyria';

export async function generateMusic(prompt: string): Promise<string> {
  console.log('Genrating music')
  try {
    const musicUrl = await generateMusicRest(prompt)
    console.log('Music generated!')
    return musicUrl; 
  } catch (error) {
    console.error('Error generating music:', error)
    throw new Error(`Failed to music: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}
