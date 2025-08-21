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

import { Stepper } from "@/components/ui/stepper"
import { BookOpen, Film, LayoutGrid, PenLine, Scissors } from 'lucide-react'
import Image from 'next/image'
import { useEffect, useState } from 'react'
import { generateScenes, generateStoryboard } from './actions/generate-scenes'
import { editVideo, exportMovieAction } from './actions/generate-video'
import { regenerateImage, regenerateCharacterImage } from './actions/regenerate-image'
import { resizeImage } from './actions/resize-image'
import { saveImageToPublic } from './actions/upload-image'
import { CreateTab } from './components/create/create-tab'
import { ScenarioTab } from "./components/scenario/scenario-tab"
import { StoryboardTab } from './components/storyboard/storyboard-tab'
import { type Style } from "./components/create/style-selector"
import { VideoTab } from './components/video/video-tab'
import { Scenario, Scene, type Language, TimelineLayer } from './types'
import { EditorTab } from './components/editor/editor-tab'
import { generateMusic } from "./actions/generate-music"
import { generateVoiceover } from "./actions/generate-voiceover"
import { Voice } from './components/editor/voice-selection-dialog'

const styles: Style[] = [
  { name: "Photographic", image: "/styles/cinematic.jpg" },
  { name: "2D Animation", image: "/styles/2d.jpg" },
  { name: "Anime", image: "/styles/anime.jpg" },
  { name: "3D Animation", image: "/styles/3d.jpg" },
  { name: "Claymation Animation", image: "/styles/claymation.jpg" },
]

const DEFAULT_LANGUAGE: Language = {
  name: "English (United States)",
  code: "en-US"
};

export default function Home() {
  const [pitch, setPitch] = useState('')
  const [style, setStyle] = useState('Photographic')
  const [language, setLanguage] = useState<Language>(DEFAULT_LANGUAGE)
  const [logoOverlay, setLogoOverlay] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false);
  const [numScenes, setNumScenes] = useState(6)
  const [isLoading, setIsLoading] = useState(false)
  const [withVoiceOver, setWithVoiceOver] = useState(false)
  const [isVideoLoading, setIsVideoLoading] = useState(false)
  const [scenario, setScenario] = useState<Scenario>()
  const [scenes, setScenes] = useState<Array<Scene>>([])
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const [generatingCharacterImages, setGeneratingCharacterImages] = useState<Set<number>>(new Set());
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [videoUri, setVideoUri] = useState<string | null>(null)
  const [vttUri, setVttUri] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>("create")
  const [currentTime, setCurrentTime] = useState(0)
  const [isGeneratingMusic, setIsGeneratingMusic] = useState(false)
  const [isGeneratingVoiceover, setIsGeneratingVoiceover] = useState(false)
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null)
  const FALLBACK_URL = "https://videos.pexels.com/video-files/4276282/4276282-hd_1920_1080_25fps.mp4"

  useEffect(() => {
    console.log("generatingScenes (in useEffect):", generatingScenes);
  }, [generatingScenes]); // Log only when generatingScenes changes

  const handleGenerate = async () => {
    if (pitch.trim() === '' || numScenes < 1) return
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const scenario = await generateScenes(pitch, numScenes, style, language)
      setScenario(scenario)
      if (logoOverlay) {
        scenario.logoOverlay = logoOverlay
      }
      setScenes(scenario.scenes)
      setActiveTab("scenario") // Switch to scenario tab after successful generation
    } catch (error) {
      console.error('Error generating scenes:', error)
      setErrorMessage(error instanceof Error ? error.message : 'An unknown error occurred while generating scenes')
      setScenes([]) // Clear any partially generated scenes
    } finally {
      setIsLoading(false)
    }
  }

  const handleRegenerateImage = async (index: number) => {
    setGeneratingScenes(prev => new Set([...prev, index]));
    setErrorMessage(null)
    try {
      // Regenerate a single image
      const scene = scenes[index]
      const { imageGcsUri, errorMessage } = await regenerateImage(scene.imagePrompt)
      const updatedScenes = [...scenes]
      updatedScenes[index] = { ...scene, imageGcsUri, videoUri: undefined, errorMessage: errorMessage }
      console.log(updatedScenes)
      setScenes(updatedScenes)
    } catch (error) {
      console.error("Error regenerating images:", error)
      setErrorMessage(`Failed to regenerate image(s): ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setGeneratingScenes(prev => {
        const updated = new Set(prev);
        updated.delete(index); // Remove index from generatingScenes
        return updated;
      });
    }
  }

  const handleRegenerateCharacterImage = async (characterIndex: number, description: string) => {
    if (!scenario) return;
    
    setGeneratingCharacterImages(prev => new Set([...prev, characterIndex]));
    setErrorMessage(null)
    try {
      // Regenerate character image using the updated description
      const { imageGcsUri } = await regenerateCharacterImage(`${style}: ${description}`);
      
      // Update the character with the new image AND the updated description
      const updatedCharacters = [...scenario.characters];
      updatedCharacters[characterIndex] = {
        ...updatedCharacters[characterIndex],
        description: description, // Preserve the updated description
        imageGcsUri
      };
      
      const updatedScenario = {
        ...scenario,
        characters: updatedCharacters
      };
      
      setScenario(updatedScenario);
    } catch (error) {
      console.error("Error regenerating character image:", error)
      setErrorMessage(`Failed to regenerate character image: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setGeneratingCharacterImages(prev => {
        const updated = new Set(prev);
        updated.delete(characterIndex);
        return updated;
      });
    }
  }

  const handleEditVideo = async () => {
    setIsVideoLoading(true)
    setErrorMessage(null)
    try {
      console.log('Edit Video');
      console.log(withVoiceOver);
      if (scenario && scenes && scenes.every((scene) => typeof scene.videoUri === 'string')) {
        const result = await editVideo(
          await Promise.all(
            scenes.map(async (scene) => {
              return {
                voiceover: scene.voiceover,
                videoUri: scene.videoUri,
              };
            })
          ),
          scenario.mood,
          withVoiceOver,
          scenario.language,
          scenario.logoOverlay,
          selectedVoice?.name
        );
        if (result.success) {
          setVideoUri(result.videoUrl)
          setVttUri(result.vttUrl || null)
        } else {
          setVideoUri(FALLBACK_URL)
          setVttUri(null)
        }
      } else {
        setErrorMessage("All scenes should have a generated video")
        setVideoUri(FALLBACK_URL)
        setVttUri(null)
      }
    } catch (error) {
      console.error("Error generating video:", error)
      setErrorMessage(error instanceof Error ? error.message : "An unknown error occurred while generating video")
      setVttUri(null)
    } finally {
      setIsVideoLoading(false)
    }
  }

  const handleExportMovie = async (layers: TimelineLayer[]) => {
    setIsVideoLoading(true)
    setErrorMessage(null)
    try {
      console.log('Export Movie');
      console.log(layers)
      const result = await exportMovieAction(
        layers
      );
      if (result.success) {
        setVideoUri(result.videoUrl)
        setVttUri(result.vttUrl || null)
        setActiveTab("video")
      } else {
        setVideoUri(FALLBACK_URL)
        setVttUri(null)
      }
    } catch (error) {
      console.error("Error generating video:", error)
      setErrorMessage(error instanceof Error ? error.message : "An unknown error occurred while generating video")
      setVttUri(null)
    } finally {
      setIsVideoLoading(false)
    }
  }

  const handleGenerateAllVideos = async () => {
    setErrorMessage(null);
    console.log("[Client] Generating videos for all scenes - START");
    setGeneratingScenes(new Set(scenes.map((_, i) => i)));

    const regeneratedScenes = await Promise.all(
      scenes.map(async (scene) => {
        try {
          const response = await fetch('/api/videos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenes: [scene], language: scenario?.language }),
          });

          const { success, videoUrls, error } = await response.json();

          if (success) {
            return { ...scene, videoUri: videoUrls[0] || FALLBACK_URL };
          } else {
            throw new Error(error);
          }
        } catch (error) {
          console.error("Error regenerating video:", error);
          if (error instanceof Error) {
            return { ...scene, videoUri: FALLBACK_URL, errorMessage: error.message };
          } else {
            return { ...scene, videoUri: FALLBACK_URL };
          }
        }
      })
    );

    setScenes(regeneratedScenes);
    if (scenario) {
      setScenario({
        ...scenario,
        scenes: regeneratedScenes
      });
    }
    setGeneratingScenes(new Set());
    setActiveTab("editor")
  };

  const handleGenerateVoiceover = async (voice?: Voice) => {
    if (!scenario) return
    setIsGeneratingVoiceover(true)
    setErrorMessage(null)
    try {
      // Set the selected voice for future video generation
      if (voice) {
        setSelectedVoice(voice)
      }
      
      const scenesVoiceovers = scenario.scenes.map((scene) => ({
        voiceover: scene.voiceover
      }))
      const voiceoverAudioUrls = await generateVoiceover(scenesVoiceovers, scenario.language, voice?.name)
      const updatedScenes = scenes.map((scene, index) => ({
        ...scene,
        voiceoverAudioUri: voiceoverAudioUrls[index]
      }))
      setScenes(updatedScenes)
      setScenario({
        ...scenario,
        scenes: updatedScenes // Update scenario with the new scenes that include voiceover URLs
      })
    } catch (error) {
      console.error('Error generating voiceover:', error)
      setErrorMessage(error instanceof Error ? error.message : 'An unknown error occurred while generating voiceover')
    } finally {
      setIsGeneratingVoiceover(false)
    }
  }

  const handleGenerateMusic = async (musicParams?: { description: string }) => {
    if (!scenario) return
    setIsGeneratingMusic(true)
    setErrorMessage(null)
    try {
      // Update scenario with new music description if provided
      let updatedScenario = scenario
      if (musicParams) {
        updatedScenario = {
          ...scenario,
          music: musicParams.description
        }
        setScenario(updatedScenario)
      }
      
      const musicUrl = await generateMusic(updatedScenario.music)
      const finalScenario = {
        ...updatedScenario,
        musicUrl: musicUrl
      }
      setScenario(finalScenario)
      console.log(musicUrl)
    } catch (error) {
      console.error('Error generating music:', error)
      setErrorMessage(error instanceof Error ? error.message : 'An unknown error occurred while generating music')
    } finally {
      setIsGeneratingMusic(false)
    }
  }

  const handleGenerateStoryBoard = async () => {
    console.log("Generating storyboard");

    if (!scenario) return
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const scenarioWithStoryboard = await generateStoryboard(scenario, numScenes, style, language)
      setScenario(scenarioWithStoryboard)
      setScenes(scenarioWithStoryboard.scenes)
      setActiveTab("storyboard") // Switch to storyboard tab after successful generation
    } catch (error) {
      console.error('Error generating storyboard:', error)
      setErrorMessage(error instanceof Error ? error.message : 'An unknown error occurred while generating storyboard')
      setScenes([]) // Clear any partially generated scenes
      setActiveTab("scenario") // Stay on scenario tab if there's an error
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateVideo = async (index: number) => {
    setErrorMessage(null);
    try {
      // Single scene generation logic remains the same
      setGeneratingScenes(prev => new Set([...prev, index]));
      const scene = scenes[index];
      console.log('scene', scene);

      const response = await fetch('/api/videos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenes: [scene] }),
      });

      const { success, videoUrls } = await response.json();
      const videoUri = success ? videoUrls[0] : FALLBACK_URL;
      const updatedScenes = [...scenes]
      updatedScenes[index] = { ...updatedScenes[index], videoUri }
      setScenes(updatedScenes)
      if (scenario) {
        setScenario({
          ...scenario,
          scenes: updatedScenes
        });
      }
    } catch (error) {
      console.error("[Client] Error generating video:", error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "An unknown error occurred while generating video"
      );

      const videoUri = FALLBACK_URL;
      setScenes(prevScenes =>
        prevScenes.map((s, i) => (i === index ? { ...s, videoUri } : s))
      );
    } finally {
      console.log(`[Client] Generating video done`);
      setGeneratingScenes(prev => {
        const updated = new Set(prev);
        updated.delete(index); // Remove index from generatingScenes
        return updated;
      });
    }
  };

  const handleUpdateScene = (index: number, updatedScene: Scene) => {
    const newScenes = [...scenes]
    newScenes[index] = updatedScene
    setScenes(newScenes)
  };

  const handleUploadImage = async (index: number, file: File) => {
    setErrorMessage(null)
    try {
      const reader = new FileReader()
      reader.onloadend = async () => {
        const base64String = reader.result as string
        const imageBase64 = base64String.split(",")[1] // Remove the data URL prefix
        const resizedImageGcsUri = await resizeImage(imageBase64);
        const updatedScenes = [...scenes]
        updatedScenes[index] = { ...updatedScenes[index], imageGcsUri: resizedImageGcsUri, videoUri: undefined }
        setScenes(updatedScenes)
      }
      reader.onerror = () => {
        throw new Error("Failed to read the image file")
      }
      reader.readAsDataURL(file)
    } catch (error) {
      console.error("Error uploading image:", error)
      setErrorMessage(error instanceof Error ? error.message : "An unknown error occurred while uploading the image")
    }
  }

  const handleLogoRemove = () => {
    setLogoOverlay(null);

    // Also remove logoOverlay from scenario if it exists
    if (scenario) {
      setScenario({
        ...scenario,
        logoOverlay: undefined
      });
    }
  }

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    try {
      // Convert file to base64 string
      const base64String = await fileToBase64(file);

      // Call server action to save the image
      const imagePath = await saveImageToPublic(base64String, file.name);

      // Update state with the path to the saved image
      console.log(imagePath)
      setLogoOverlay(imagePath);

      // Update scenario's logoOverlay if it exists
      if (scenario) {
        setScenario({
          ...scenario,
          logoOverlay: imagePath
        });
      }
    } catch (error) {
      console.error("Error uploading logo:", error);
    } finally {
      setIsUploading(false);
    }
  };

  // Utility function to convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  console.log("Component rendered");

  const steps = [
    {
      id: "create",
      label: "Create",
      icon: PenLine
    },
    {
      id: "scenario",
      label: "Scenario",
      icon: BookOpen,
      disabled: !scenario
    },
    {
      id: "storyboard",
      label: "Storyboard",
      icon: LayoutGrid,
      disabled: !scenario
    },
    {
      id: "editor",
      label: "Editor",
      icon: Scissors,
      disabled: !scenario || !scenes || !scenes.every(scene => typeof scene.videoUri === 'string')
    },
    {
      id: "video",
      label: "Video",
      icon: Film,
      disabled: !scenario || !scenes || !scenes.every(scene => typeof scene.videoUri === 'string')
    }
  ]

  const handleScenarioUpdate = (updatedScenario: Scenario) => {
    setScenario(updatedScenario);
  };

  const handleRemoveVoiceover = (sceneIndex: number) => {
    if (!scenario) return;
    
    // Create updated scenes with voiceover removed from the specific scene
    const updatedScenes = scenario.scenes.map((scene, index) => {
      if (index === sceneIndex) {
        return {
          ...scene,
          voiceoverAudioUri: undefined
        };
      }
      return scene;
    });
    
    // Update both scenes and scenario
    setScenes(updatedScenes);
    setScenario({
      ...scenario,
      scenes: updatedScenes
    });
  };

  const handleRemoveMusic = () => {
    if (!scenario) return;
    
    // Remove music from scenario
    setScenario({
      ...scenario,
      musicUrl: undefined
    });
  };

  return (
    <main className="container mx-auto p-8 min-h-screen bg-background flex flex-col">
      <div className="flex items-center justify-center gap-2 mb-8">
        <Image
          src="/logo5.png"
          alt="Storycraft"
          width={32}
          height={32}
          className="h-8"
        />
        <h1 className="text-3xl font-bold text-primary ml-[-10px]">
          toryCraft
        </h1>
      </div>
      <div className="flex-1 space-y-4">
        <Stepper
          steps={steps}
          currentStep={activeTab}
          onStepClick={setActiveTab}
          className="mb-8"
        />

        {activeTab === "create" && (
          <CreateTab
            pitch={pitch}
            setPitch={setPitch}
            numScenes={numScenes}
            setNumScenes={setNumScenes}
            style={style}
            setStyle={setStyle}
            language={language}
            setLanguage={setLanguage}
            isLoading={isLoading}
            errorMessage={errorMessage}
            onGenerate={handleGenerate}
            styles={styles}
          />
        )}

        {activeTab === "scenario" && (
          <ScenarioTab
            scenario={scenario}
            onGenerateStoryBoard={handleGenerateStoryBoard}
            isLoading={isLoading}
            onScenarioUpdate={handleScenarioUpdate}
            onRegenerateCharacterImage={handleRegenerateCharacterImage}
            generatingCharacterImages={generatingCharacterImages}
          />
        )}

        {activeTab === "storyboard" && (
          <StoryboardTab
            scenes={scenes}
            isVideoLoading={isVideoLoading}
            generatingScenes={generatingScenes}
            errorMessage={errorMessage}
            onGenerateAllVideos={handleGenerateAllVideos}
            onUpdateScene={handleUpdateScene}
            onRegenerateImage={handleRegenerateImage}
            onGenerateVideo={handleGenerateVideo}
            onUploadImage={handleUploadImage}
          />
        )}

        {activeTab === "editor" && scenario && (
          <EditorTab
            scenario={scenario}
            currentTime={currentTime}
            onTimeUpdate={setCurrentTime}
            onTimelineItemUpdate={(layerId, itemId, updates) => {
              // TODO: Implement timeline item updates
              console.log('Timeline item update:', { layerId, itemId, updates })
            }}
            logoOverlay={logoOverlay}
            setLogoOverlay={setLogoOverlay}
            onLogoUpload={handleLogoUpload}
            onLogoRemove={handleLogoRemove}
            onGenerateMusic={handleGenerateMusic}
            isGeneratingMusic={isGeneratingMusic}
            onGenerateVoiceover={handleGenerateVoiceover}
            isGeneratingVoiceover={isGeneratingVoiceover}
            onExportMovie={handleExportMovie}
            isExporting={isVideoLoading}
            onRemoveVoiceover={handleRemoveVoiceover}
            onRemoveMusic={handleRemoveMusic}
          />
        )}

        {activeTab === "video" && (
          <VideoTab
            videoUri={videoUri}
            vttUri={vttUri}
            isVideoLoading={isVideoLoading}
            language={scenario?.language || DEFAULT_LANGUAGE}
          />
        )}
      </div>
      <footer className="mt-auto pt-8">
        <div className="flex items-center justify-center gap-2">
          <p className="text-sm text-muted-foreground">
            Made with ❤️ by @mblanc
          </p>
        </div>
      </footer>
    </main>
  )
}

