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

"use client"

import { useState } from "react"
import Image from "next/image"

export interface Style {
  name: string
  image: string
}

interface StyleSelectorProps {
  styles: Style[]
  onSelect: (style: string) => void
}

export function StyleSelector({ styles, onSelect }: StyleSelectorProps) {
  const [selectedStyle, setSelectedStyle] = useState<Style | null>(null)

  const handleSelect = (style: Style) => {
    setSelectedStyle(style)
    onSelect(style.name)
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {styles.map((style) => (
        <button
          key={style.name}
          onClick={() => handleSelect(style)}
          className={`relative aspect-square rounded-lg overflow-hidden transition-all duration-200 ${
            selectedStyle?.name === style.name
              ? "ring-4 ring-primary ring-offset-2"
              : "hover:ring-2 hover:ring-primary/50"
          }`}
        >
          <Image
            src={style.image || "/placeholder.svg"}
            alt={style.name}
            fill
            className="rounded-lg object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
          <div className="absolute inset-0 bg-black bg-opacity-40 flex items-end justify-center p-2">
            <span className="text-white text-sm font-medium">{style.name}</span>
          </div>
        </button>
      ))}
    </div>
  )
}

