export interface Question {
  id: string
  assessment: string
  section: 'Reading and Writing' | 'Math'
  domain: string
  skill: string
  difficulty: 1 | 2 | 3
  prompt_text: string
  question_text: string
  answer_choices: string[]
  correct_answer: string
  rationale: string | null
  has_figure: boolean
  figure_paths: string[]
}

export interface Worksheet {
  id: string
  section: string
  domain: string
  skill: string
  video_url: string | null
  display_order: number
}

export interface UserProgress {
  id: string
  user_id: string
  question_id: string
  completed: boolean
  correct: boolean | null
  completed_at: string | null
}

export interface TestAttempt {
  id: string
  user_id: string
  section: string
  skill: string
  score: number | null
  total_questions: number | null
  time_taken_seconds: number | null
  answers: Record<string, string>
  created_at: string
}

export interface Profile {
  id: string
  display_name: string | null
  created_at: string
}

// Roadmap data structure
export interface SkillNode {
  skill: string
  questionCount: number
  completedCount: number
}

export interface DomainNode {
  domain: string
  skills: SkillNode[]
}

export interface SectionData {
  section: 'Reading and Writing' | 'Math'
  domains: DomainNode[]
}
