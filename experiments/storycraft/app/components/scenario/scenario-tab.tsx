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
import { LayoutGrid, Loader2, Pencil } from "lucide-react";
import { Scenario } from "../../types";
import { useState, useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { GcsImage } from "../ui/gcs-image";

interface ScenarioTabProps {
    scenario?: Scenario;
    onGenerateStoryBoard: () => void;
    isLoading: boolean;
    onScenarioUpdate?: (updatedScenario: Scenario) => void;
    onRegenerateCharacterImage?: (characterIndex: number, description: string) => Promise<void>;
    generatingCharacterImages?: Set<number>;
}

export function ScenarioTab({ scenario, onGenerateStoryBoard, isLoading, onScenarioUpdate, onRegenerateCharacterImage, generatingCharacterImages }: ScenarioTabProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedScenario, setEditedScenario] = useState(scenario?.scenario || '');
    const [isScenarioHovering, setIsScenarioHovering] = useState(false);
    const [editingCharacterIndex, setEditingCharacterIndex] = useState<number | null>(null);
    const [editedCharacterDescriptions, setEditedCharacterDescriptions] = useState<string[]>([]);
    const [characterHoverStates, setCharacterHoverStates] = useState<boolean[]>([]);
    const scenarioRef = useRef<HTMLDivElement>(null);
    const characterEditingRefs = useRef<(HTMLDivElement | null)[]>([]);

    useEffect(() => {
        if (scenario?.scenario) {
            setEditedScenario(scenario.scenario);
        }
        if (scenario?.characters) {
            setEditedCharacterDescriptions(scenario.characters.map(char => char.description));
            // Initialize refs array for character editing areas
            characterEditingRefs.current = new Array(scenario.characters.length).fill(null);
            // Initialize hover states for characters
            setCharacterHoverStates(new Array(scenario.characters.length).fill(false));
        }
    }, [scenario?.scenario, scenario?.characters]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Node;
            
            // Check if click is outside scenario editing area
            if (scenarioRef.current && !scenarioRef.current.contains(target)) {
                if (isEditing) {
                    handleSave();
                }
            }
            
            // Check if click is outside character editing area
            if (editingCharacterIndex !== null) {
                const currentCharacterRef = characterEditingRefs.current[editingCharacterIndex];
                if (currentCharacterRef && !currentCharacterRef.contains(target)) {
                    handleSaveCharacter(editingCharacterIndex);
                }
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isEditing, editedScenario, editingCharacterIndex, editedCharacterDescriptions]);

    const handleScenarioChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setEditedScenario(e.target.value);
    };

    const handleCharacterDescriptionChange = (index: number, value: string) => {
        const newDescriptions = [...editedCharacterDescriptions];
        newDescriptions[index] = value;
        setEditedCharacterDescriptions(newDescriptions);
    };

    const handleCharacterHover = (index: number, isHovering: boolean) => {
        const newHoverStates = [...characterHoverStates];
        newHoverStates[index] = isHovering;
        setCharacterHoverStates(newHoverStates);
    };

    const handleSave = async () => {
        if (scenario && onScenarioUpdate) {
            const updatedScenario = {
                ...scenario,
                scenario: editedScenario
            };
            onScenarioUpdate(updatedScenario);
            setEditedScenario(updatedScenario.scenario);
        }
        setIsEditing(false);
    };

    const handleSaveCharacter = async (index: number) => {
        if (scenario && onScenarioUpdate && onRegenerateCharacterImage) {
            const updatedDescription = editedCharacterDescriptions[index];
            
            // Update the scenario with the new description
            const updatedCharacters = [...scenario.characters];
            updatedCharacters[index] = {
                ...updatedCharacters[index],
                description: updatedDescription
            };
            const updatedScenario = {
                ...scenario,
                characters: updatedCharacters
            };
            onScenarioUpdate(updatedScenario);
            
            // Regenerate image with the updated description
            await onRegenerateCharacterImage(index, updatedDescription);
        }
        setEditingCharacterIndex(null);
    };

    return (
        <div className="space-y-8">
            {scenario && (
                <>
                    <div className="flex justify-end">
                        <Button
                            onClick={onGenerateStoryBoard}
                            disabled={isLoading}
                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                        >
                            {isLoading ? (
                                <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Generating Storyboard...
                                </>
                            ) : (
                                <>
                                <LayoutGrid className="mr-2 h-4 w-4" />
                                Generate Storyboard with Imagen 4.0
                                </>
                            )}
                        </Button>
                    </div>
                    <div className="max-w-4xl mx-auto space-y-4">
                        <div className="col-span-1">
                            <h3 className="text-xl font-bold">Scenario</h3>
                        </div>
                        <div 
                            ref={scenarioRef}
                            className="relative group"
                            onMouseEnter={() => setIsScenarioHovering(true)}
                            onMouseLeave={() => setIsScenarioHovering(false)}
                        >
                            {!isEditing && isScenarioHovering && (
                                <button
                                    onClick={() => setIsEditing(true)}
                                    className="absolute top-2 right-2 p-2 rounded-full bg-white/80 hover:bg-white shadow-sm transition-all"
                                >
                                    <Pencil className="h-4 w-4 text-gray-600" />
                                </button>
                            )}
                            {isEditing ? (
                                <Textarea
                                    value={editedScenario}
                                    onChange={handleScenarioChange}
                                    className="min-h-[200px] w-full"
                                    placeholder="Enter your scenario..."
                                    autoFocus
                                />
                            ) : (
                                <p className="whitespace-pre-wrap p-4 rounded-lg border border-transparent group-hover:border-gray-200 transition-colors">{scenario.scenario}</p>
                            )}
                        </div>
                        <div className="col-span-1">
                            <h3 className="text-xl font-bold">Characters</h3>
                        </div>
                        {scenario.characters.map((character, index) => (
                            <div key={character.name} className="flex gap-4 items-start">
                                <div className="flex-shrink-0 w-[200px] h-[200px] relative">
                                    {generatingCharacterImages?.has(index) && (
                                        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-10 rounded-lg">
                                            <Loader2 className="h-8 w-8 text-white animate-spin" />
                                        </div>
                                    )}
                                    <GcsImage
                                        gcsUri={character.imageGcsUri || null}
                                        alt={`Character ${character.name}`}
                                        className="object-cover rounded-lg shadow-md"
                                        sizes="200px"
                                    />
                                </div>
                                <div className="flex-grow relative group">
                                    <h4 className="text-lg font-semibold mb-2">{character.name}</h4>
                                    <div 
                                        ref={(el) => {
                                            characterEditingRefs.current[index] = el;
                                            return;
                                        }}
                                        className="relative"
                                        onMouseEnter={() => handleCharacterHover(index, true)}
                                        onMouseLeave={() => handleCharacterHover(index, false)}
                                    >
                                        {editingCharacterIndex !== index && characterHoverStates[index] && (
                                            <button
                                                onClick={() => setEditingCharacterIndex(index)}
                                                className="absolute top-0 right-0 p-2 rounded-full bg-white/80 hover:bg-white shadow-sm transition-all"
                                            >
                                                <Pencil className="h-4 w-4 text-gray-600" />
                                            </button>
                                        )}
                                        {editingCharacterIndex === index ? (
                                            <Textarea
                                                value={editedCharacterDescriptions[index] || ''}
                                                onChange={(e) => handleCharacterDescriptionChange(index, e.target.value)}
                                                className="min-h-[100px] w-full"
                                                placeholder="Enter character description..."
                                                autoFocus
                                            />
                                        ) : (
                                            <p className="whitespace-pre-wrap p-4 rounded-lg border border-transparent group-hover:border-gray-200 transition-colors">
                                                {character.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div className="col-span-1">
                            <h3 className="text-xl font-bold">Settings</h3>
                        </div>
                        {scenario.settings.map((setting) => (
                            <div key={setting.name}>
                                <div className="col-span-1">
                                    <h4 className="text-lg">{setting.name}</h4>
                                </div>
                                <div className="col-span-2">
                                    <p>{setting.description}</p>
                                </div>
                            </div>
                        ))}
                        <div className="col-span-1">
                            <h3 className="text-xl font-bold">Music</h3>
                        </div>
                        <div className="col-span-2">
                            <p>{scenario.music}</p>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

