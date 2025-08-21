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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useState } from 'react'

export interface Voice {
  name: string
  gender: 'Male' | 'Female'
  description: string
}

const AVAILABLE_VOICES: Voice[] = [
  { name: 'Aoede', gender: 'Female', description: 'Breezy, Middle pitch' },
  { name: 'Puck', gender: 'Male', description: 'Upbeat, Middle pitch' },
  { name: 'Charon', gender: 'Male', description: 'Informative, Lower pitch' },
  { name: 'Kore', gender: 'Female', description: 'Firm, Middle pitch' },
  { name: 'Fenrir', gender: 'Male', description: 'Excitable, Lower middle pitch' },
  { name: 'Leda', gender: 'Female', description: 'Youthful, Higher pitch' },
  { name: 'Orus', gender: 'Male', description: 'Firm, Lower middle pitch' },
  { name: 'Zephyr', gender: 'Female', description: 'Bright, Higher pitch' },
  { name: 'Achird', gender: 'Male', description: 'Friendly, Lower middle pitch' },
  { name: 'Algenib', gender: 'Male', description: 'Gravelly, Lower pitch' },
  { name: 'Algieba', gender: 'Male', description: 'Smooth, Lower pitch' },
  { name: 'Alnilam', gender: 'Male', description: 'Firm, Lower middle pitch' },
  { name: 'Autonoe', gender: 'Female', description: 'Bright, Middle pitch' },
  { name: 'Callirrhoe', gender: 'Female', description: 'Easy-going, Middle pitch' },
  { name: 'Despina', gender: 'Female', description: 'Smooth, Middle pitch' },
  { name: 'Enceladus', gender: 'Male', description: 'Breathy, Lower pitch' },
  { name: 'Erinome', gender: 'Female', description: 'Clear, Middle pitch' },
  { name: 'Gacrux', gender: 'Female', description: 'Mature, Middle pitch' },
  { name: 'Iapetus', gender: 'Male', description: 'Clear, Lower middle pitch' },
  { name: 'Laomedeia', gender: 'Female', description: 'Upbeat, Higher pitch' },
  { name: 'Pulcherrima', gender: 'Female', description: 'Forward, Middle pitch' },
  { name: 'Rasalgethi', gender: 'Male', description: 'Informative, Middle pitch' },
  { name: 'Sadachbia', gender: 'Male', description: 'Gentle, Lower pitch' },
  { name: 'Sadaltager', gender: 'Male', description: 'Knowledgeable, Lower pitch' },
  { name: 'Schedar', gender: 'Male', description: 'Even, Lower middle pitch' },
  { name: 'Sulafat', gender: 'Female', description: 'Warm, Middle pitch' },
  { name: 'Umbriel', gender: 'Male', description: 'Easy-going, Lower middle pitch' },
  { name: 'Vindemiatrix', gender: 'Female', description: 'Gentle, Middle pitch' },
  { name: 'Zubenelgenubi', gender: 'Male', description: 'Casual, Lower middle pitch' },
  { name: 'Achernar', gender: 'Female', description: 'Soft, Higher pitch' }
]

interface VoiceSelectionDialogProps {
  isOpen: boolean
  onClose: () => void
  onVoiceSelect: (voice: Voice) => void
  isGenerating: boolean
}

export function VoiceSelectionDialog({
  isOpen,
  onClose,
  onVoiceSelect,
  isGenerating
}: VoiceSelectionDialogProps) {
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>('')

  const handleVoiceSelect = (voiceName: string) => {
    setSelectedVoiceName(voiceName)
  }

  const handleGenerate = () => {
    if (selectedVoiceName) {
      const selectedVoice = AVAILABLE_VOICES.find(voice => voice.name === selectedVoiceName)
      if (selectedVoice) {
        onVoiceSelect(selectedVoice)
        setSelectedVoiceName('')
      }
    }
  }

  const handleClose = () => {
    setSelectedVoiceName('')
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Select Voice for Voiceover Generation</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Choose a voice:</label>
            <Select value={selectedVoiceName} onValueChange={handleVoiceSelect}>
              <SelectTrigger>
                <SelectValue placeholder="Select a voice..." />
              </SelectTrigger>
              <SelectContent>
                {AVAILABLE_VOICES.map((voice) => (
                  <SelectItem key={voice.name} value={voice.name}>
                    <div className="flex items-center justify-between w-full">
                      <div>
                        <span className="font-medium">{voice.name}</span>
                        <span className="text-xs text-gray-500 ml-2">({voice.description})</span>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        voice.gender === 'Male' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'bg-pink-100 text-pink-700'
                      }`}>
                        {voice.gender}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex justify-end space-x-2 pt-4 border-t">
            <Button variant="outline" onClick={handleClose} disabled={isGenerating}>
              Cancel
            </Button>
            <Button 
              onClick={handleGenerate} 
              disabled={!selectedVoiceName || isGenerating}
              className="bg-green-600 hover:bg-green-700"
            >
              {isGenerating ? 'Generating...' : 'Generate Voiceover'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
} 