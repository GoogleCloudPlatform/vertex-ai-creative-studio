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

export interface Scene {
  imagePrompt: string;
  videoPrompt: string;
  description: string;
  voiceover: string;
  charactersPresent: string[];
  imageGcsUri?: string;
  videoUri?: string | Promise<string>;
  voiceoverAudioUri?: string | Promise<string>;
  errorMessage?: string;
}

export interface Scenario {
  scenario: string;
  genre: string;
  mood: string;
  music: string;
  musicUrl?: string;
  language: Language;
  characters: Array<{ name: string, description: string, imageGcsUri?: string }>;
  settings: Array<{ name: string, description: string }>;
  logoOverlay?: string;
  scenes: Scene[];
}

export interface Language {
  name: string;
  code: string;
} 

export interface TimelineLayer {
  id: string
  name: string
  type: 'video' | 'voiceover' | 'music'
  items: TimelineItem[]
}

export interface TimelineItem {
  id: string
  startTime: number
  duration: number
  content: string // URL for video/music/voiceover
  type: 'video' | 'voiceover' | 'music'
  metadata?: {
    logoOverlay?: string
    [key: string]: any // Allow for additional metadata fields
  }
}