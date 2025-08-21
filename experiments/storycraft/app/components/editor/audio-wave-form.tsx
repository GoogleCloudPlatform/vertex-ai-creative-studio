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

interface AudioWaveformProps {
    src: string
    className?: string
    color?: string
    duration: number
}

export function AudioWaveform({ src, className, color = 'bg-green-500', duration }: AudioWaveformProps) {
    const [waveformData, setWaveformData] = useState<number[]>([])
    const audioContextRef = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)

    useEffect(() => {
        const analyzeAudio = async () => {
            try {
                // Create audio context and analyzer
                audioContextRef.current = new AudioContext()
                analyserRef.current = audioContextRef.current.createAnalyser()
                analyserRef.current.fftSize = 256 // Adjust for desired detail level

                // Fetch and decode audio
                const response = await fetch(src)
                const arrayBuffer = await response.arrayBuffer()
                const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)

                // Calculate number of bars based on duration (10 bars per second)
                const samples = Math.max(10, Math.floor(duration * 10)) // At least 10 bars, then 10 per second
                const blockSize = Math.floor(audioBuffer.length / samples)
                const waveform: number[] = []

                // Get waveform data
                const channelData = audioBuffer.getChannelData(0)
                for (let i = 0; i < samples; i++) {
                    const start = blockSize * i
                    let sum = 0
                    for (let j = 0; j < blockSize; j++) {
                        sum += Math.abs(channelData[start + j])
                    }
                    waveform.push(sum / blockSize)
                }

                // Normalize waveform data
                const max = Math.max(...waveform)
                const normalizedWaveform = waveform.map(value => value / max)
                setWaveformData(normalizedWaveform)
            } catch (error) {
                console.error('Error analyzing audio:', error)
                // Fallback to a simple waveform if analysis fails
                setWaveformData(Array(Math.max(10, Math.floor(duration * 10))).fill(0.5))
            }
        }

        analyzeAudio()

        return () => {
            if (audioContextRef.current) {
                audioContextRef.current.close()
            }
        }
    }, [src, duration])

    return (
        <div className={`${className} flex items-center gap-px`}>
            {waveformData.map((height, index) => (
                <div
                    key={index}
                    className={`${color} w-full transition-all duration-100`}
                    style={{
                        height: `${Math.max(20, height * 100)}%`,
                        opacity: 0.7
                    }}
                />
            ))}
        </div>
    )
} 