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

"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { LucideIcon } from "lucide-react"

interface StepperProps extends React.HTMLAttributes<HTMLOListElement> {
  steps: {
    id: string
    label: string
    icon: LucideIcon
    disabled?: boolean
  }[]
  currentStep: string
  onStepClick?: (stepId: string) => void
}

export function Stepper({ steps, currentStep, onStepClick, className, ...props }: StepperProps) {
  const currentStepIndex = steps.findIndex(step => step.id === currentStep)

  return (
    <ol className={cn("flex items-center w-full text-sm font-medium text-center text-gray-500 dark:text-gray-400 sm:text-base", className)} {...props}>
      {steps.map((step, index) => {
        const isActive = step.id === currentStep
        const isCompleted = index < currentStepIndex
        const Icon = step.icon

        return (
          <li 
            key={step.id}
            className={cn(
              "flex md:w-full items-center relative",
              isActive ? "text-blue-600 dark:text-blue-500" : "",
              isCompleted ? "text-green-600 dark:text-green-500" : "",
              step.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
              index < steps.length - 1 ? "after:content-[''] after:w-full after:h-[2px] after:border-b-2 after:border-gray-300 after:border-solid after:hidden sm:after:inline-block after:mx-6 xl:after:mx-10 dark:after:border-gray-600" : ""
            )}
            onClick={() => !step.disabled && onStepClick?.(step.id)}
          >
            <div className={cn(
              "flex items-center relative z-10 bg-background px-2",
              step.disabled ? "cursor-not-allowed" : "cursor-pointer"
            )}>
              <span className={cn(
                "flex items-center justify-center w-8 h-8 border rounded-full shrink-0 me-2.5",
                isActive ? "border-blue-600 dark:border-blue-500" : "border-gray-300 dark:border-gray-600",
                isCompleted ? "bg-green-600 border-green-600 dark:bg-green-500 dark:border-green-500" : "",
                step.disabled ? "border-gray-200 dark:border-gray-700" : ""
              )}>
                {isCompleted ? (
                  <svg className="w-4 h-4 text-white" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 16 12">
                    <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M1 5.917 5.724 10.5 15 1.5"/>
                  </svg>
                ) : (
                  <span className={cn(
                    "text-sm font-medium",
                    isActive ? "text-blue-600 dark:text-blue-500" : "text-gray-500 dark:text-gray-400",
                    step.disabled ? "text-gray-300 dark:text-gray-600" : ""
                  )}>
                    {index + 1}
                  </span>
                )}
              </span>
              <span className="flex items-center">
                <Icon className={cn(
                  "w-3.5 h-3.5 sm:w-4 sm:h-4 me-2.5",
                  step.disabled ? "text-gray-300 dark:text-gray-600" : ""
                )} />
                {step.label}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
} 