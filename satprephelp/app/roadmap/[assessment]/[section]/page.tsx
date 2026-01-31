import Link from 'next/link'
import { notFound } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'

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

const SECTION_MAP: Record<string, string> = {
  'reading-and-writing': 'Reading and Writing',
  'math': 'Math',
}

interface DomainGroup {
  domain: string
  skills: string[]
}

export default async function SectionRoadmapPage({
  params,
}: {
  params: Promise<{ assessment: string; section: string }>
}) {
  const { assessment, section } = await params
  const assessmentName = ASSESSMENT_MAP[assessment]
  const displayName = ASSESSMENT_DISPLAY[assessment]
  const sectionName = SECTION_MAP[section]

  if (!assessmentName || !sectionName) {
    notFound()
  }

  const supabase = await createClient()

  // Fetch unique domains and skills from questions for this assessment and section
  const { data: questions, error } = await supabase
    .from('questions')
    .select('domain, skill')
    .eq('assessment', assessmentName)
    .eq('section', sectionName)
    .order('id')

  if (error) {
    console.error('Error fetching questions:', error)
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-red-500">Error loading roadmap. Please try again.</p>
      </div>
    )
  }

  // Group by domain, preserving order of first appearance
  const domainGroups: DomainGroup[] = []
  const domainMap = new Map<string, Set<string>>()
  const domainOrder: string[] = []

  for (const q of questions || []) {
    if (!domainMap.has(q.domain)) {
      domainMap.set(q.domain, new Set())
      domainOrder.push(q.domain)
    }
    domainMap.get(q.domain)!.add(q.skill)
  }

  for (const domain of domainOrder) {
    domainGroups.push({
      domain,
      skills: Array.from(domainMap.get(domain)!),
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href={`/roadmap/${assessment}`}
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              ← Back
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{sectionName}</h1>
              <p className="text-sm text-gray-500">{displayName}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {domainGroups.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No skills available for this section yet.</p>
            <Link
              href={`/roadmap/${assessment}`}
              className="inline-block mt-4 text-blue-600 hover:text-blue-700"
            >
              ← Choose another section
            </Link>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {domainGroups.map((domainData) => (
              <Card key={domainData.domain}>
                <CardHeader>
                  <h3 className="text-lg font-semibold text-gray-900">{domainData.domain}</h3>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {domainData.skills.map((skill) => (
                      <li key={skill}>
                        <Link
                          href={`/worksheet/${assessment}/${encodeURIComponent(skill)}`}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <span className="text-gray-700">{skill}</span>
                          <span className="text-sm text-gray-400">→</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
