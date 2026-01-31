# SAT Prep Help

SAT preparation web app with visual roadmap, skill-based worksheets, and timed skill tests.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Auth/DB**: Supabase (Postgres + Auth)
- **Styling**: Tailwind CSS
- **Hosting**: Vercel

## Project Structure

```
app/
├── (auth)/          # login, signup
├── roadmap/         # skill tree visualization
├── worksheet/[skill]/ # questions per skill
└── practice/        # skill test mode

components/
├── ui/              # Button, Card, Modal
├── roadmap/         # RoadmapTree, DomainNode, SkillNode
├── worksheet/       # QuestionCard, QuestionList
└── auth/            # AuthForm

lib/supabase/        # client.ts, server.ts, middleware.ts
```

## Database

Tables: `profiles`, `questions`, `worksheets`, `user_progress`, `test_attempts`

Questions indexed by (section, domain, skill) and difficulty (1-3).

## Content

- **R&W**: 1,590 questions across 4 domains, 10 skills
- **Math**: Scraping in progress

## Test Timing

- Reading & Writing: 71 seconds/question
- Math: 95 seconds/question

## Scrapers

```bash
cd scrape && source venv/bin/activate
python3 foo.py              # R&W
python3 math_scraper.py SAT MATH  # Math
```

Output in `output/SAT_RW/` and `output/SAT_MATH/`.
