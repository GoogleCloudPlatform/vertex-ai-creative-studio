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

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, Pencil, RefreshCw, Upload, Video } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Scene } from '../../types'
import { EditSceneModal } from './edit-scene-modal'
import { VideoPlayer } from "../video/video-player"
import { GcsImage } from "../ui/gcs-image"
import { cn } from "@/lib/utils"

interface SceneDataProps {
  scene: Scene;
  sceneNumber: number;
  onUpdate: (updatedScene: SceneDataProps['scene']) => void;
  onRegenerateImage: () => void;
  onGenerateVideo: () => void;
  onUploadImage: (file: File) => void;
  isGenerating: boolean;
  hideControls?: boolean;
}

export function SceneData({
  scene,
  sceneNumber,
  onUpdate,
  onRegenerateImage,
  onGenerateVideo,
  onUploadImage,
  isGenerating,
  hideControls = false,
}: SceneDataProps) {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const getVideoUrl = async () => {
      console.log('Video URL change!')
      if (typeof scene.videoUri === 'string') {
        setVideoUrl(scene.videoUri);
      } else if (scene.videoUri instanceof Promise) {
        try {
          const resolvedUrl = await scene.videoUri;
          setVideoUrl(resolvedUrl);
        } catch (error) {
          console.error('Error resolving video URL:', error);
          setVideoUrl(null);
        }
      } else {
        setVideoUrl(null);
      }
    }

    getVideoUrl();
  }, [scene.videoUri]);

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      onUploadImage(file)
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col">
        <div className="relative w-full aspect-video overflow-hidden group">
          {isGenerating && (
            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-10">
              <Loader2 className="h-8 w-8 text-white animate-spin" />
            </div>
          )}
          {videoUrl ? (
            <div className="absolute inset-0">
              <VideoPlayer src={videoUrl} />
            </div>
          ) : (
            <GcsImage
              gcsUri={scene.imageGcsUri || null}
              alt={`Scene ${sceneNumber}`}
              className="absolute inset-0 w-full h-full object-cover object-center rounded-t-lg"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
          )}
          {!hideControls && (
            <>
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="secondary"
                  size="icon"
                  className="bg-black/50 hover:bg-blue-500 hover:text-white"
                  onClick={onGenerateVideo}
                  disabled={isGenerating}
                >
                  <Video className="h-4 w-4" />
                  <span className="sr-only">Generate video for scene</span>
                </Button>
              </div>
              <div className="absolute top-2 left-2 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="secondary"
                  size="icon"
                  className="bg-black/50 hover:bg-red-500 hover:text-white"
                  onClick={onRegenerateImage}
                  disabled={isGenerating}
                >
                  <RefreshCw className="h-4 w-4" />
                  <span className="sr-only">Regenerate image</span>
                </Button>
                <Button
                  variant="secondary"
                  size="icon"
                  className="bg-black/50 hover:bg-green-500 hover:text-white"
                  onClick={handleUploadClick}
                  disabled={isGenerating}
                >
                  <Upload className="h-4 w-4" />
                  <span className="sr-only">Upload image</span>
                </Button>
                <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="image/*" className="hidden" />
              </div>
            </>
          )}
        </div>
        <CardContent className="p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-semibold text-primary">Scene {sceneNumber}</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsEditModalOpen(true)}
              className="text-secondary hover:text-primary hover:bg-primary/10"
            >
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </div>
          {scene.errorMessage && (
              <p className="text-sm text-red-600">{scene.errorMessage}</p>
          )}
          <p className="text-sm text-muted-foreground">{scene.description}</p>
        </CardContent>
      </div>
      <EditSceneModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        scene={scene}
        sceneNumber={sceneNumber}
        onUpdate={onUpdate}
      />
    </Card>
  )
}