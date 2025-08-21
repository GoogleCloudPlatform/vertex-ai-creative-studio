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

export function getRAIUserMessage(reasonString: string): string {
    console.warn(`Media generation blocked due to RAI filter reason: ${reasonString}`);
        
    // Default message includes the original reason string for clarity if no code matches
    let userMessage = `Media generation failed due to safety guidelines (Reason: ${reasonString}).`; 

    // Check if the reason string contains specific codes
    if (reasonString.includes('58061214') || reasonString.includes('17301594')) {
        userMessage = "Media generation blocked: Detected potentially harmful child content.";
    } else if (reasonString.includes('29310472') || reasonString.includes('15236754')) {
        userMessage = "Media generation blocked: Detected a photorealistic celebrity likeness.";
    } else if (reasonString.includes('64151117') || reasonString.includes('42237218')) {
        userMessage = "Media generation blocked: Detected a safety violation.";
    } else if (reasonString.includes('62263041')) {
         userMessage = "Media generation blocked: Detected potentially dangerous content.";
    } else if (reasonString.includes('57734940') || reasonString.includes('22137204')) {
        userMessage = "Media generation blocked: Detected hate speech or related content.";
    } else if (reasonString.includes('74803281') || reasonString.includes('29578790') || reasonString.includes('42876398')) {
        userMessage = "Media generation blocked: Miscellaneous safety issue detected.";
    } else if (reasonString.includes('39322892')) {
         userMessage = "Media generation blocked: Detected people/faces when not permitted by safety settings.";
    } else if (reasonString.includes('92201652')) {
         userMessage = "Media generation blocked: Detected potential personal identifiable information (PII).";
    } else if (reasonString.includes('89371032') || reasonString.includes('49114662') || reasonString.includes('72817394')) {
        userMessage = "Media generation blocked: Detected prohibited content.";
    } else if (reasonString.includes('90789179') || reasonString.includes('63429089') || reasonString.includes('43188360')) {
        userMessage = "Media generation blocked: Detected sexually explicit or adult content.";
    } else if (reasonString.includes('78610348')) {
         userMessage = "Media generation blocked: Detected toxic language or content.";
    } else if (reasonString.includes('61493863') || reasonString.includes('56562880')) {
        userMessage = "Media generation blocked: Detected violence-related content.";
    } else if (reasonString.includes('32635315')) {
         userMessage = "Media generation blocked: Detected vulgar language or content.";
    } else {
       // Optional: Log if no known code was found in the string
       console.warn(`RAI filter reason string did not contain any specific known codes from the list.`);
    }

    // Return the determined user-friendly message (or the default if no code matched)
    // Append the original reason string for debugging/more info if needed elsewhere
    return `${userMessage} (Code: ${reasonString})`; 
}