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

import { ContentListUnion, GoogleGenAI, GenerateContentConfig } from '@google/genai';

const LOCATION = process.env.LOCATION
const PROJECT_ID = process.env.PROJECT_ID

const ai = new GoogleGenAI({ vertexai: true, project: PROJECT_ID, location: LOCATION });


export async function generateText(
    prompt: ContentListUnion,
    config: GenerateContentConfig = {
        thinkingConfig: {
            includeThoughts: true,
            thinkingBudget: -1,
        },
        responseMimeType: 'application/json',
        maxOutputTokens: -1,
    }): Promise<string | undefined> {

    const model = 'gemini-2.5-flash';
    const response = await ai.models.generateContent({
        model,
        config,
        contents: prompt,
    });

    return response.text;
}