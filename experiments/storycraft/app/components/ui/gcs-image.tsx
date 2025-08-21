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

'use client'

import { useQuery } from "@tanstack/react-query"
import Image from 'next/image'
import { getDynamicImageUrl } from "@/app/actions/storageActions"
import { Loader2 } from 'lucide-react'
import { useEffect } from 'react'

interface GcsImageProps {
  gcsUri: string | null
  alt: string
  className?: string
  fill?: boolean
  sizes?: string
}

export function GcsImage({ gcsUri, alt, className, fill = true, sizes }: GcsImageProps) {
  const { data: imageData, isLoading, error } = useQuery({
    queryKey: ['image', gcsUri],
    queryFn: async () => {
      if (!gcsUri) {
        return null
      }
      if (!gcsUri.startsWith('gs://')) {
        console.error('Invalid GCS URI format:', gcsUri)
        return null
      }
      try {
        const result = await getDynamicImageUrl(gcsUri)
        return result
      } catch (error) {
        console.error('Error fetching image URL:', error)
        throw error
      }
    },
    enabled: !!gcsUri,
  })

  const imageUrl = imageData?.url || null

  // Preload the image when we have the URL
  useEffect(() => {
    if (imageUrl) {
      const img = new window.Image()
      img.src = imageUrl
    }
  }, [imageUrl])

  if (isLoading) {
    return (
      <div className={`relative w-full h-full bg-gray-100 ${className}`}>
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-10">
          <Loader2 className="h-12 w-12 text-white animate-spin" />
        </div>
        <Image
          src="/placeholder.svg"
          alt={`Loading ${alt}`}
          className={className}
          fill={fill}
          sizes={sizes}
          priority
        />
      </div>
    )
  }

  if (!imageUrl) {
    return (
      <div className={`relative w-full h-full bg-gray-100 ${className}`}>
        <Image
          src="/placeholder.svg"
          alt={alt}
          className={className}
          fill={fill}
          sizes={sizes}
          priority
          onError={(e) => {
            const target = e.target as HTMLImageElement
            target.src = "/placeholder.svg"
            target.onerror = null // Prevent infinite loop
          }}
        />
      </div>
    )
  }

  return (
    <div className={`relative w-full h-full bg-gray-100 ${className}`}>
      <Image
        src={imageUrl}
        alt={alt}
        className={className}
        fill={fill}
        sizes={sizes}
        priority
        onError={(e) => {
          const target = e.target as HTMLImageElement
          target.src = "/placeholder.svg"
          target.onerror = null // Prevent infinite loop
        }}
      />
    </div>
  )
} 