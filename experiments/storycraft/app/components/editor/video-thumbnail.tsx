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

import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'

interface VideoThumbnailProps {
    src: string
    duration: number
    className?: string
}

export function VideoThumbnail({ src, duration, className }: VideoThumbnailProps) {
    const [thumbnails, setThumbnails] = useState<string[]>([])
    const videoRef = useRef<HTMLVideoElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)

    useEffect(() => {
        if (!videoRef.current || !canvasRef.current) return

        const video = videoRef.current
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const captureFrame = async (time: number): Promise<string> => {
            return new Promise((resolve) => {
                video.currentTime = time
                const handleSeeked = () => {
                    canvas.width = video.videoWidth
                    canvas.height = video.videoHeight
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
                    resolve(canvas.toDataURL('image/jpeg'))
                    video.removeEventListener('seeked', handleSeeked)
                }
                video.addEventListener('seeked', handleSeeked)
            })
        }

        const generateThumbnails = async () => {
            try {
                const frames: string[] = []
                // Capture one frame every 2 seconds, up to the duration
                for (let time = 0; time < duration; time += 2) {
                    const frame = await captureFrame(time)
                    frames.push(frame)
                }
                setThumbnails(frames)
            } catch (error) {
                console.error('Error generating thumbnails:', error)
            }
        }

        video.addEventListener('loadeddata', generateThumbnails)
        return () => {
            video.removeEventListener('loadeddata', generateThumbnails)
        }
    }, [src, duration])

    return (
        <>
            <video ref={videoRef} src={src} className="hidden" crossOrigin="anonymous" />
            <canvas ref={canvasRef} className="hidden" />
            {thumbnails.length > 0 ? (
                <div className={`${className} grid grid-flow-col auto-cols-fr gap-px bg-black/10`}>
                    {thumbnails.map((thumbnail, index) => (
                        <div key={index} className="relative w-full h-full">
                            <Image
                                src={thumbnail}
                                alt={`Frame ${index + 1}`}
                                className="w-full h-full object-cover"
                                fill
                                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                            />
                        </div>
                    ))}
                </div>
            ) : (
                <div className={`${className} bg-blue-500/20 border border-blue-500`} />
            )}
        </>
    )
} 