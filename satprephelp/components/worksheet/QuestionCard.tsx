'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/Card'
import type { Question } from '@/types'

interface QuestionCardProps {
  question: Question
  index: number
}

export function QuestionCard({ question, index }: QuestionCardProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [showRationale, setShowRationale] = useState(false)

  const isCorrect = selectedAnswer === question.correct_answer
  const hasAnswered = selectedAnswer !== null

  const difficultyLabels = { 1: 'Easy', 2: 'Medium', 3: 'Hard' }
  const difficultyColors = {
    1: 'bg-green-100 text-green-800',
    2: 'bg-yellow-100 text-yellow-800',
    3: 'bg-red-100 text-red-800',
  }

  return (
    <Card className="mb-6">
      <CardContent className="pt-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-medium text-gray-500">Question {index + 1}</span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${difficultyColors[question.difficulty]}`}>
            {difficultyLabels[question.difficulty]}
          </span>
        </div>

        {/* Prompt */}
        {question.prompt_text && (
          <div className="mb-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-gray-700 whitespace-pre-wrap">{question.prompt_text}</p>
          </div>
        )}

        {/* Figures */}
        {question.has_figure && question.figure_paths.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-4">
            {question.figure_paths.map((path, i) => (
              <img
                key={i}
                src={path}
                alt={`Figure ${i + 1}`}
                className="max-w-full h-auto rounded-lg border border-gray-200"
              />
            ))}
          </div>
        )}

        {/* Question */}
        <p className="text-lg font-medium text-gray-900 mb-4">{question.question_text}</p>

        {/* Answer choices */}
        <div className="space-y-2">
          {question.answer_choices.map((choice) => {
            const letter = choice.charAt(0)
            const isSelected = selectedAnswer === letter
            const isCorrectAnswer = letter === question.correct_answer

            let buttonStyle = 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
            if (hasAnswered) {
              if (isCorrectAnswer) {
                buttonStyle = 'border-green-500 bg-green-50'
              } else if (isSelected && !isCorrect) {
                buttonStyle = 'border-red-500 bg-red-50'
              }
            } else if (isSelected) {
              buttonStyle = 'border-blue-500 bg-blue-50'
            }

            return (
              <button
                key={choice}
                onClick={() => !hasAnswered && setSelectedAnswer(letter)}
                disabled={hasAnswered}
                className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${buttonStyle} ${
                  hasAnswered ? 'cursor-default' : 'cursor-pointer'
                }`}
              >
                <span className="text-gray-700">{choice}</span>
              </button>
            )
          })}
        </div>

        {/* Result and rationale */}
        {hasAnswered && (
          <div className="mt-4">
            <div className={`p-3 rounded-lg ${isCorrect ? 'bg-green-100' : 'bg-red-100'}`}>
              <p className={`font-medium ${isCorrect ? 'text-green-800' : 'text-red-800'}`}>
                {isCorrect ? 'Correct!' : `Incorrect. The correct answer is ${question.correct_answer}.`}
              </p>
            </div>

            {question.rationale && (
              <div className="mt-3">
                <button
                  onClick={() => setShowRationale(!showRationale)}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  {showRationale ? 'Hide explanation' : 'Show explanation'}
                </button>
                {showRationale && (
                  <div className="mt-2 p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-700 whitespace-pre-wrap">{question.rationale}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
