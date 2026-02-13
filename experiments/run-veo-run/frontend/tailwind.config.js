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

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx,html}"],
  theme: {
    extend: {
      colors: {
        'lola-red': '#FF2400',       // Shock Red (Main Action)
        'lola-dark': '#1A1A1A',      // Concrete Dark (Background)
        'lola-panel': '#2D2D2D',     // Asphalt (Surfaces)
        'lola-yellow': '#FFD700',    // Caution Yellow (Accents/Warnings)
      },
      fontFamily: {
        'impact': ['Impact', 'Oswald', 'sans-serif'], // For Headers
        'mono': ['JetBrains Mono', 'Roboto Mono', 'monospace'], // For Data
      }
    },
  },
  plugins: [],
}
