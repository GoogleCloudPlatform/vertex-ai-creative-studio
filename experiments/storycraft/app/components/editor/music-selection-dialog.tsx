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

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { useState } from 'react'

export interface MusicParams {
  description: string
}

interface MusicSelectionDialogProps {
  isOpen: boolean
  onClose: () => void
  onMusicGenerate: (params: MusicParams) => void
  isGenerating: boolean
  currentParams: MusicParams
}

export function MusicSelectionDialog({
  isOpen,
  onClose,
  onMusicGenerate,
  isGenerating,
  currentParams
}: MusicSelectionDialogProps) {
  const [description, setDescription] = useState<string>(currentParams.description)

  const handleGenerate = () => {
    if (description.trim()) {
      onMusicGenerate({
        description: description.trim()
      })
    }
  }

  const handleClose = () => {
    // Reset to current params when closing
    setDescription(currentParams.description)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Configure Music Generation</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Music Description:</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the music you want to generate..."
              className="min-h-[80px]"
            />
            <p className="text-xs text-gray-500">
              Describe the style, instruments, tempo, genre, mood, or any specific characteristics you want in the music.
            </p>
          </div>
          
          <div className="flex justify-end space-x-2 pt-4 border-t">
            <Button variant="outline" onClick={handleClose} disabled={isGenerating}>
              Cancel
            </Button>
            <Button 
              onClick={handleGenerate} 
              disabled={!description.trim() || isGenerating}
              className="bg-green-600 hover:bg-green-700"
            >
              {isGenerating ? 'Generating...' : 'Generate Music'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
} 