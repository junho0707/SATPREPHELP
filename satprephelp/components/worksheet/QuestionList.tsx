'use client'

import { QuestionCard } from './QuestionCard'
import type { Question } from '@/types'

interface QuestionListProps {
  questions: Question[]
  skill: string
  showFilter?: boolean
}

export function QuestionList({ questions, skill, showFilter = true }: QuestionListProps) {
  return (
    <div>
      {/* Questions */}
      {questions.length > 0 ? (
        questions.map((question, index) => (
          <QuestionCard key={question.id} question={question} index={index} />
        ))
      ) : (
        <div className="text-center py-12 text-gray-500">
          No questions found.
        </div>
      )}
    </div>
  )
}
