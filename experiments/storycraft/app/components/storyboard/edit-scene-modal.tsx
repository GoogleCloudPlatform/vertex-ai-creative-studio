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

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { VideoPlayer } from '../video/video-player'
import { GcsImage } from '../ui/gcs-image'

interface EditSceneModalProps {
  isOpen: boolean;
  onClose: () => void;
  scene: {
    imagePrompt: string;
    videoPrompt: string;
    description: string;
    voiceover: string;
    charactersPresent: string[];
    imageGcsUri?: string;
    videoUri?: string | Promise<string>;
  };
  sceneNumber: number;
  onUpdate: (updatedScene: EditSceneModalProps['scene']) => void;
}

export function EditSceneModal({ isOpen, onClose, scene, sceneNumber, onUpdate }: EditSceneModalProps) {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [editedScene, setEditedScene] = useState(scene)
  
  useEffect(() => {
    setEditedScene(scene)
  }, [scene])
    
  useEffect(() => {
    const getVideoUrl = async () => {
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
        }
    }

    getVideoUrl();
  }, [scene.videoUri]);
  
  const handleSave = () => {
    onUpdate(editedScene)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[1200px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Scene {sceneNumber}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 py-4">
          {/* Left side - Image/Video */}
          <div className="space-y-4">
            <div className="relative w-full h-[300px] overflow-hidden rounded-lg bg-muted">
              {videoUrl ? (
                <div className="absolute inset-0">
                  <VideoPlayer src={videoUrl} />
                </div>
              ) : (
                <GcsImage
                  gcsUri={editedScene.imageGcsUri || null}
                  alt={`Scene ${sceneNumber}`}
                  className="w-full h-full object-cover object-center"
                />
              )}
            </div>
          </div>
          
          {/* Right side - Scene Parameters */}
          <div className="lg:col-span-2 space-y-4">
            <div className="grid gap-2">
              <label htmlFor="imagePrompt" className="text-sm font-medium">
                Image Prompt
              </label>
              <Textarea
                id="imagePrompt"
                value={editedScene.imagePrompt}
                onChange={(e) => setEditedScene({ ...editedScene, imagePrompt: e.target.value })}
                placeholder="Describe the scene visually..."
                rows={4}
              />
            </div>
            
            <div className="grid gap-2">
              <label htmlFor="videoPrompt" className="text-sm font-medium">
                Video Prompt
              </label>
              <Textarea
                id="videoPrompt"
                value={editedScene.videoPrompt}
                onChange={(e) => setEditedScene({ ...editedScene, videoPrompt: e.target.value })}
                placeholder="Describe the video..."
                rows={3}
              />
            </div>
            
            <div className="grid gap-2">
              <label htmlFor="description" className="text-sm font-medium">
                Description
              </label>
              <Textarea
                id="description"
                value={editedScene.description}
                onChange={(e) => setEditedScene({ ...editedScene, description: e.target.value })}
                placeholder="What happens in this scene?"
                rows={3}
              />
            </div>
            
            <div className="grid gap-2">
              <label htmlFor="voiceover" className="text-sm font-medium">
                Voiceover
              </label>
              <Textarea
                id="voiceover"
                value={editedScene.voiceover}
                onChange={(e) => setEditedScene({ ...editedScene, voiceover: e.target.value })}
                placeholder="What should the narrator say?"
                rows={3}
              />
            </div>
            
            <div className="grid gap-2">
              <label htmlFor="characters" className="text-sm font-medium">
                Characters Present
              </label>
              <div className="text-sm text-muted-foreground p-2 bg-muted rounded">
                {editedScene.charactersPresent.length > 0 
                  ? editedScene.charactersPresent.join(", ")
                  : "No characters in this scene"
                }
              </div>
            </div>
          </div>
        </div>
        <div className="flex justify-end space-x-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

