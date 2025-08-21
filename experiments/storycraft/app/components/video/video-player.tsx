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

import { useRef, useEffect } from "react"

interface VideoPlayerProps {
  src: string
  vttSrc?: string | null
  language?: { name: string; code: string }
}

export function VideoPlayer({ src, vttSrc, language }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load()
    }
  }, [src, vttSrc])

  return (
    <div className="w-full max-w-3xl mx-auto">
      <video ref={videoRef} controls className="w-full rounded-lg shadow-lg">
        <source src={src} type="video/mp4" />
        {vttSrc && (
          <track
            src={vttSrc}
            kind="subtitles"
            srcLang={language?.code}
            label={language?.name}
            default
          />
        )}
        Your browser does not support the video tag.
      </video>
    </div>
  )
}

