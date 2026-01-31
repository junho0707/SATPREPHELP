import { createClient } from '@/lib/supabase/server'
import { QuestionList } from '@/components/worksheet/QuestionList'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import type { Question } from '@/types'

const ASSESSMENT_MAP: Record<string, string> = {
  'sat': 'SAT',
  'psat-nmsqt': 'PSAT/NMSQT & PSAT 10',
  'psat-8-9': 'PSAT 8/9',
}

const ASSESSMENT_DISPLAY: Record<string, string> = {
  'sat': 'SAT',
  'psat-nmsqt': 'PSAT/NMSQT',
  'psat-8-9': 'PSAT 8/9',
}

interface WorksheetPageProps {
  params: Promise<{ assessment: string; skill: string; worksheetId: string }>
}

// Split questions into worksheets of ~7 questions each
function createWorksheets(questions: Question[]): Question[][] {
  if (questions.length === 0) return []

  const targetSize = 7
  const numWorksheets = Math.ceil(questions.length / targetSize)

  if (numWorksheets === 0) return []

  const baseSize = Math.floor(questions.length / numWorksheets)
  const remainder = questions.length % numWorksheets

  const worksheets: Question[][] = []
  let index = 0

  for (let i = 0; i < numWorksheets; i++) {
    const size = baseSize + (i < remainder ? 1 : 0)
    worksheets.push(questions.slice(index, index + size))
    index += size
  }

  return worksheets
}

export default async function WorksheetPage({ params }: WorksheetPageProps) {
  const { assessment, skill, worksheetId } = await params
  const assessmentName = ASSESSMENT_MAP[assessment]
  const displayName = ASSESSMENT_DISPLAY[assessment]
  const decodedSkill = decodeURIComponent(skill)

  if (!assessmentName) {
    notFound()
  }

  // Parse worksheetId (e.g., "easy-1", "medium-2", "hard-3")
  const [difficultyStr, indexStr] = worksheetId.split('-')
  const worksheetIndex = parseInt(indexStr, 10) - 1 // Convert to 0-based

  const difficultyMap: Record<string, number> = { easy: 1, medium: 2, hard: 3 }
  const difficulty = difficultyMap[difficultyStr]

  const difficultyLabels: Record<string, string> = { easy: 'Easy', medium: 'Medium', hard: 'Hard' }

  const supabase = await createClient()

  // Fetch questions for this skill, assessment, and difficulty
  const { data: questions, error } = await supabase
    .from('questions')
    .select('*')
    .eq('assessment', assessmentName)
    .eq('skill', decodedSkill)
    .eq('difficulty', difficulty)
    .order('id')

  if (error) {
    console.error('Error fetching questions:', error)
  }

  // Fetch worksheet info
  const { data: worksheet } = await supabase
    .from('worksheets')
    .select('*')
    .eq('skill', decodedSkill)
    .single()

  const questionList = (questions as Question[]) || []

  // Create worksheets and get the specific one
  const worksheets = createWorksheets(questionList)
  const currentWorksheet = worksheets[worksheetIndex] || []

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}`}
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{decodedSkill}</h1>
              <p className="text-sm text-gray-500">
                {displayName} • {difficultyLabels[difficultyStr]} • Worksheet {worksheetIndex + 1}
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-3xl">
        {currentWorksheet.length > 0 ? (
          <>
            <div className="mb-6 flex items-center justify-between">
              <p className="text-gray-600">
                {currentWorksheet.length} question{currentWorksheet.length !== 1 ? 's' : ''}
              </p>
              <div className="text-sm text-gray-500">
                Worksheet {worksheetIndex + 1} of {worksheets.length}
              </div>
            </div>
            <QuestionList questions={currentWorksheet} skill={decodedSkill} showFilter={false} />

            {/* Navigation */}
            <div className="mt-8 flex justify-between">
              {worksheetIndex > 0 ? (
                <Link
                  href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}/${difficultyStr}-${worksheetIndex}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  ← Previous Worksheet
                </Link>
              ) : (
                <div></div>
              )}
              {worksheetIndex < worksheets.length - 1 ? (
                <Link
                  href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}/${difficultyStr}-${worksheetIndex + 2}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Next Worksheet →
                </Link>
              ) : (
                <Link
                  href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Back to Skill Overview
                </Link>
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">Worksheet not found.</p>
            <Link
              href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}`}
              className="mt-4 inline-block text-blue-600 hover:text-blue-800"
            >
              Back to Skill Overview
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
