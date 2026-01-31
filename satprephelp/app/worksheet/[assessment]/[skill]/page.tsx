import { createClient } from '@/lib/supabase/server'
import { Card, CardContent } from '@/components/ui/Card'
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

interface SkillPageProps {
  params: Promise<{ assessment: string; skill: string }>
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

export default async function SkillPage({ params }: SkillPageProps) {
  const { assessment, skill } = await params
  const assessmentName = ASSESSMENT_MAP[assessment]
  const displayName = ASSESSMENT_DISPLAY[assessment]
  const decodedSkill = decodeURIComponent(skill)

  if (!assessmentName) {
    notFound()
  }

  const supabase = await createClient()

  // Fetch questions for this skill AND assessment
  const { data: questions, error } = await supabase
    .from('questions')
    .select('*')
    .eq('assessment', assessmentName)
    .eq('skill', decodedSkill)
    .order('id')

  if (error) {
    console.error('Error fetching questions:', error)
  }

  // Fetch worksheet info (for video URL)
  const { data: worksheet } = await supabase
    .from('worksheets')
    .select('*')
    .eq('skill', decodedSkill)
    .single()

  const questionList = (questions as Question[]) || []

  // Group by difficulty
  const easyQuestions = questionList.filter(q => q.difficulty === 1)
  const mediumQuestions = questionList.filter(q => q.difficulty === 2)
  const hardQuestions = questionList.filter(q => q.difficulty === 3)

  // Create worksheets for each difficulty
  const easyWorksheets = createWorksheets(easyQuestions)
  const mediumWorksheets = createWorksheets(mediumQuestions)
  const hardWorksheets = createWorksheets(hardQuestions)

  const difficultyGroups = [
    { label: 'Easy', dotColor: 'bg-green-500', badgeBg: 'bg-green-100', badgeText: 'text-green-600', worksheets: easyWorksheets, prefix: 'easy' },
    { label: 'Medium', dotColor: 'bg-yellow-500', badgeBg: 'bg-yellow-100', badgeText: 'text-yellow-600', worksheets: mediumWorksheets, prefix: 'medium' },
    { label: 'Hard', dotColor: 'bg-red-500', badgeBg: 'bg-red-100', badgeText: 'text-red-600', worksheets: hardWorksheets, prefix: 'hard' },
  ]

  // Determine section slug for back navigation
  const sectionSlug = worksheet?.section === 'Reading and Writing'
    ? 'reading-and-writing'
    : worksheet?.section === 'Math'
      ? 'math'
      : 'reading-and-writing'

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href={`/roadmap/${assessment}/${sectionSlug}`}
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{decodedSkill}</h1>
              <p className="text-sm text-gray-500">
                {displayName} • {worksheet?.section} • {worksheet?.domain}
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Section 1: Strategy Video */}
        <section className="mb-10">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Strategy Video</h2>
          {worksheet?.video_url ? (
            <Card>
              <CardContent className="py-6">
                <a
                  href={worksheet.video_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 text-blue-600 hover:text-blue-800"
                >
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </div>
                  <span className="font-medium">Watch explanation video</span>
                </a>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-6">
                <p className="text-gray-500">No strategy video available yet.</p>
              </CardContent>
            </Card>
          )}
        </section>

        {/* Section 2: Worksheets by Difficulty */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Worksheets</h2>

          {questionList.length === 0 ? (
            <Card>
              <CardContent className="py-6">
                <p className="text-gray-500">No questions available for this skill yet.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-8">
              {difficultyGroups.map(({ label, dotColor, badgeBg, badgeText, worksheets, prefix }) => (
                worksheets.length > 0 && (
                  <div key={label}>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`w-3 h-3 rounded-full ${dotColor}`}></span>
                      <h3 className="text-lg font-medium text-gray-800">{label}</h3>
                      <span className="text-sm text-gray-500">
                        ({worksheets.reduce((acc, w) => acc + w.length, 0)} questions)
                      </span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {worksheets.map((ws, index) => (
                        <Link
                          key={`${prefix}-${index}`}
                          href={`/worksheet/${assessment}/${encodeURIComponent(decodedSkill)}/${prefix}-${index + 1}`}
                        >
                          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                            <CardContent className="py-4">
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-medium text-gray-900">
                                    Worksheet {index + 1}
                                  </p>
                                  <p className="text-sm text-gray-500">
                                    {ws.length} questions
                                  </p>
                                </div>
                                <div className={`w-10 h-10 rounded-full ${badgeBg} flex items-center justify-center`}>
                                  <span className={`${badgeText} font-semibold`}>
                                    {index + 1}
                                  </span>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        </Link>
                      ))}
                    </div>
                  </div>
                )
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
