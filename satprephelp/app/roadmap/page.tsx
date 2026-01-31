import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'

const ASSESSMENTS = [
  {
    id: 'sat',
    name: 'SAT',
    description: 'The main college entrance exam',
    icon: '🎓',
    color: 'from-blue-500 to-indigo-600',
  },
  {
    id: 'psat-nmsqt',
    name: 'PSAT/NMSQT',
    description: 'PSAT 10 & National Merit Qualifier',
    icon: '📝',
    color: 'from-purple-500 to-violet-600',
  },
  {
    id: 'psat-8-9',
    name: 'PSAT 8/9',
    description: 'For 8th and 9th graders',
    icon: '📚',
    color: 'from-emerald-500 to-teal-600',
  },
]

export default function RoadmapSelectPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">SAT Prep</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Choose Your Test</h2>
          <p className="text-gray-600">Select which test you're preparing for</p>
        </div>

        <div className="max-w-3xl mx-auto grid gap-6 md:grid-cols-3">
          {ASSESSMENTS.map((assessment) => (
            <Link key={assessment.id} href={`/roadmap/${assessment.id}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardContent className="p-0">
                  <div className={`bg-gradient-to-br ${assessment.color} p-6 rounded-t-xl text-center`}>
                    <span className="text-4xl">{assessment.icon}</span>
                  </div>
                  <div className="p-5">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{assessment.name}</h3>
                    <p className="text-gray-500 text-sm">{assessment.description}</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </main>
    </div>
  )
}
