import Link from 'next/link'
import { notFound } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Card, CardContent } from '@/components/ui/Card'

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

const SECTIONS = [
  {
    id: 'reading-and-writing',
    name: 'Reading and Writing',
    icon: '📖',
    color: 'from-blue-500 to-indigo-600',
  },
  {
    id: 'math',
    name: 'Math',
    icon: '🔢',
    color: 'from-emerald-500 to-teal-600',
  },
]

export default async function AssessmentPage({
  params,
}: {
  params: Promise<{ assessment: string }>
}) {
  const { assessment } = await params
  const assessmentName = ASSESSMENT_MAP[assessment]
  const displayName = ASSESSMENT_DISPLAY[assessment]

  if (!assessmentName) {
    notFound()
  }

  const supabase = await createClient()

  // Check which sections have content for this assessment
  const { data: availableSections } = await supabase
    .from('questions')
    .select('section')
    .eq('assessment', assessmentName)

  const sectionsWithContent = new Set(availableSections?.map(q => q.section) || [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href="/roadmap"
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              ← Back
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">{displayName}</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Choose a Section</h2>
          <p className="text-gray-600">Select which section to practice</p>
        </div>

        <div className="max-w-2xl mx-auto grid gap-6 md:grid-cols-2">
          {SECTIONS.map((section) => {
            const hasContent = sectionsWithContent.has(section.name)

            return (
              <div key={section.id}>
                {hasContent ? (
                  <Link href={`/roadmap/${assessment}/${section.id}`}>
                    <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                      <CardContent className="p-0">
                        <div className={`bg-gradient-to-br ${section.color} p-6 rounded-t-xl text-center`}>
                          <span className="text-4xl">{section.icon}</span>
                        </div>
                        <div className="p-6">
                          <h3 className="text-xl font-bold text-gray-900">{section.name}</h3>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ) : (
                  <Card className="opacity-60 cursor-not-allowed">
                    <CardContent className="p-0">
                      <div className={`bg-gradient-to-br ${section.color} p-6 rounded-t-xl text-center`}>
                        <span className="text-4xl">{section.icon}</span>
                      </div>
                      <div className="p-6">
                        <h3 className="text-xl font-bold text-gray-900 mb-2">{section.name}</h3>
                        <span className="inline-block px-3 py-1 bg-gray-100 text-gray-500 text-sm rounded-full">
                          Coming Soon
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )
          })}
        </div>
      </main>
    </div>
  )
}
