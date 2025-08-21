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
import { cn } from "@/lib/utils"
import { Grid, List, Loader2, Presentation, Video, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Scene } from "../../types"
import { SceneData } from './scene-data'
import { GcsImage } from '../ui/gcs-image'

type ViewMode = 'grid' | 'list' | 'slideshow'

interface StoryboardTabProps {
  scenes: Scene[]
  isVideoLoading: boolean
  generatingScenes: Set<number>
  errorMessage: string | null
  onGenerateAllVideos: () => Promise<void>
  onUpdateScene: (index: number, updatedScene: Scene) => void
  onRegenerateImage: (index: number) => Promise<void>
  onGenerateVideo: (index: number) => Promise<void>
  onUploadImage: (index: number, file: File) => Promise<void>
}

export function StoryboardTab({
  scenes,
  isVideoLoading,
  generatingScenes,
  errorMessage,
  onGenerateAllVideos,
  onUpdateScene,
  onRegenerateImage,
  onGenerateVideo,
  onUploadImage,
}: StoryboardTabProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [currentSlide, setCurrentSlide] = useState(0)

  const renderScenes = () => {
    switch (viewMode) {
      case 'grid':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {scenes.map((scene, index) => (
              <SceneData
                key={index}
                sceneNumber={index + 1}
                scene={scene}
                onUpdate={(updatedScene) => onUpdateScene(index, updatedScene)}
                onRegenerateImage={() => onRegenerateImage(index)}
                onGenerateVideo={() => onGenerateVideo(index)}
                onUploadImage={(file) => onUploadImage(index, file)}
                isGenerating={generatingScenes.has(index)}
              />
            ))}
          </div>
        )
      case 'list':
        return (
          <div className="space-y-6">
            {scenes.map((scene, index) => (
              <div key={index} className="flex gap-6">
                <div className="w-1/3">
                  <SceneData
                    sceneNumber={index + 1}
                    scene={scene}
                    onUpdate={(updatedScene) => onUpdateScene(index, updatedScene)}
                    onRegenerateImage={() => onRegenerateImage(index)}
                    onGenerateVideo={() => onGenerateVideo(index)}
                    onUploadImage={(file) => onUploadImage(index, file)}
                    isGenerating={generatingScenes.has(index)}
                    hideControls
                  />
                </div>
                <div className="w-2/3">
                  <div className="p-4 bg-card rounded-lg border h-full">
                    <h3 className="font-semibold mb-4 text-card-foreground">Scene {index + 1}</h3>
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-sm font-medium text-card-foreground mb-1">Image Prompt</h4>
                        <p className="text-sm text-card-foreground/80">{scene.imagePrompt}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-card-foreground mb-1">Video Prompt</h4>
                        <p className="text-sm text-card-foreground/80">{scene.videoPrompt}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-card-foreground mb-1">Voiceover</h4>
                        <p className="text-sm text-card-foreground/80">{scene.voiceover}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      case 'slideshow':
        if (scenes.length === 0) return null
        const goToPrevious = () => {
          setCurrentSlide((prev) => (prev > 0 ? prev - 1 : scenes.length - 1))
        }
        const goToNext = () => {
          setCurrentSlide((prev) => (prev < scenes.length - 1 ? prev + 1 : 0))
        }
        return (
          <div className="relative max-w-4xl mx-auto">
            <div className="aspect-video relative bg-black rounded-lg overflow-hidden max-h-[60vh] group">
              <GcsImage
                gcsUri={scenes[currentSlide].imageGcsUri || null}
                alt={`Scene ${currentSlide + 1}`}
                className="w-full h-full object-contain"
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={goToPrevious}
                className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/75 text-white opacity-0 group-hover:opacity-100 transition-opacity z-10"
              >
                <ChevronLeft className="h-6 w-6" />
                <span className="sr-only">Previous scene</span>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={goToNext}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/75 text-white opacity-0 group-hover:opacity-100 transition-opacity z-10"
              >
                <ChevronRight className="h-6 w-6" />
                <span className="sr-only">Next scene</span>
              </Button>
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 px-3 py-2 bg-black/50 rounded-full backdrop-blur-sm z-10">
                {scenes.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentSlide(index)}
                    className={cn(
                      "w-3 h-3 rounded-full transition-colors",
                      currentSlide === index ? "bg-white" : "bg-white/50 hover:bg-white/75"
                    )}
                    aria-label={`Go to scene ${index + 1}`}
                  />
                ))}
              </div>
            </div>
            <div className="mt-4 space-y-4">
              <div className="p-4 bg-card rounded-lg border">
                <h3 className="font-semibold mb-2 text-card-foreground">Scene {currentSlide + 1}</h3>
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-card-foreground mb-1">Image Prompt</h4>
                    <p className="text-sm text-card-foreground/80">{scenes[currentSlide].imagePrompt}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-card-foreground mb-1">Voiceover</h4>
                    <p className="text-sm text-card-foreground/80">{scenes[currentSlide].voiceover}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setViewMode('grid')}
            className={cn(
              "hover:bg-accent hover:text-accent-foreground",
              viewMode === 'grid' && "bg-accent text-accent-foreground"
            )}
          >
            <Grid className="h-4 w-4" />
            <span className="sr-only">Grid view</span>
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setViewMode('list')}
            className={cn(
              "hover:bg-accent hover:text-accent-foreground",
              viewMode === 'list' && "bg-accent text-accent-foreground"
            )}
          >
            <List className="h-4 w-4" />
            <span className="sr-only">List view</span>
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setViewMode('slideshow')}
            className={cn(
              "hover:bg-accent hover:text-accent-foreground",
              viewMode === 'slideshow' && "bg-accent text-accent-foreground"
            )}
          >
            <Presentation className="h-4 w-4" />
            <span className="sr-only">Slideshow view</span>
          </Button>
        </div>
        <Button
          onClick={onGenerateAllVideos}
          disabled={isVideoLoading || scenes.length === 0 || generatingScenes.size > 0}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isVideoLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating Videos...
            </>
          ) : (
            <>
              <Video className="mr-2 h-4 w-4" />
              Generate Videos with Veo 3.0
            </>
          )}
        </Button>
      </div>

      {renderScenes()}

      {errorMessage && (
        <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded whitespace-pre-wrap">
          {errorMessage}
        </div>
      )}
    </div>
  )
} 