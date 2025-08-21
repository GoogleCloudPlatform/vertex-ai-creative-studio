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

import { tts } from '@/lib/tts';
import { Language } from '../types';

export async function generateVoiceover(
    scenes: Array<{
        voiceover: string;
      }>,  
      language: Language,
      voiceName?: string
): Promise<string[]> {
  console.log('Generating voiceover with voice:', voiceName || 'default');
  try {
    const speachAudioFiles = await Promise.all(scenes.map(async (scene) => {
        const filename = await tts(scene.voiceover, language.code, voiceName);
        return { filename, text: scene.voiceover };
    }));
    const voiceoverAudioUrls = speachAudioFiles.map(r => r.filename);
    return voiceoverAudioUrls;
  } catch (error) {
    console.error('Error generating voiceover:', error)
    throw new Error(`Failed to generate voiceover: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}
