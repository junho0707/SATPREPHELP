# SAT Prep Help - Project Plan

## Overview

A web application for SAT preparation featuring a visual roadmap/progress tree, worksheets organized by skill, and optional test simulation.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | Next.js 14 (App Router) | SSR for landing SEO, API routes, file-based routing |
| Auth | Supabase Auth | Integrated with DB, simple setup, free tier |
| Database | Supabase (Postgres) | Auth + DB in one, row-level security, free tier |
| Styling | Tailwind CSS | Rapid UI development, utility-first |
| Hosting | Vercel | Zero-config Next.js deployment, free tier |

---

## Features

### Phase 1: Core (MVP)

- [ ] **Landing Page**
  - Hero section with value proposition
  - Interactive roadmap preview (clickable → takes to full roadmap)
  - Sign up / Login CTAs

- [ ] **Authentication**
  - Email/password sign up & login
  - OAuth (Google) - optional
  - Protected routes for progress tracking

- [ ] **Roadmap Page**
  - Visual tree/graph showing all domains and skills
  - Progress indicators for signed-in users
  - Click skill → opens worksheet list

- [ ] **Worksheet View**
  - List of questions for selected skill
  - Filter by difficulty (Easy/Medium/Hard)
  - Link to explanation video (YouTube embed or link)
  - Mark complete functionality

- [ ] **Progress Tracking**
  - Store completed worksheets per user
  - Visual progress on roadmap (filled nodes, percentages)

### Phase 2: Test Simulation (Optional)

- [ ] **Practice Test Mode**
  - Timer (32 min for RW module, 35 min for Math module)
  - Question navigation panel
  - Flag for review functionality
  - Answer selection with A/B/C/D

- [ ] **Results & Review**
  - Score calculation
  - Review incorrect answers with rationale
  - Save test history

---

## Database Schema

### Tables

```sql
-- Users (managed by Supabase Auth, extended with profile)
create table profiles (
  id uuid references auth.users primary key,
  display_name text,
  created_at timestamptz default now()
);

-- Questions
create table questions (
  id text primary key,  -- question_id from scraped data
  assessment text not null,  -- 'SAT'
  section text not null,  -- 'Reading and Writing', 'Math'
  domain text not null,
  skill text not null,
  difficulty int not null,  -- 1, 2, 3
  prompt_text text not null,
  question_text text not null,
  answer_choices jsonb not null,  -- ["A", "B", "C", "D"]
  correct_answer text not null,
  rationale text,
  has_figure boolean default false,
  figure_paths jsonb default '[]'
);

-- Worksheets (skill groupings with optional video links)
create table worksheets (
  id uuid primary key default gen_random_uuid(),
  section text not null,
  domain text not null,
  skill text not null,
  video_url text,  -- YouTube explanation link
  display_order int default 0
);

-- User progress on individual questions
create table user_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  question_id text references questions not null,
  completed boolean default false,
  correct boolean,
  completed_at timestamptz,
  unique(user_id, question_id)
);

-- User test attempts (for Phase 2)
create table test_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  section text not null,
  score int,
  total_questions int,
  time_taken_seconds int,
  answers jsonb,  -- { "question_id": "selected_answer", ... }
  created_at timestamptz default now()
);
```

### Indexes

```sql
create index idx_questions_section_domain_skill on questions(section, domain, skill);
create index idx_questions_difficulty on questions(difficulty);
create index idx_user_progress_user on user_progress(user_id);
```

---

## Project Structure

```
satprephelp/
├── app/
│   ├── layout.tsx           # Root layout with providers
│   ├── page.tsx             # Landing page
│   ├── globals.css
│   │
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   │
│   ├── roadmap/
│   │   └── page.tsx         # Full roadmap view
│   │
│   ├── worksheet/
│   │   └── [skill]/page.tsx # Worksheet for specific skill
│   │
│   └── practice/            # Phase 2
│       ├── page.tsx         # Test selection
│       └── [testId]/page.tsx
│
├── components/
│   ├── ui/                  # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── Modal.tsx
│   │
│   ├── roadmap/
│   │   ├── RoadmapTree.tsx  # Main visualization
│   │   ├── DomainNode.tsx
│   │   └── SkillNode.tsx
│   │
│   ├── worksheet/
│   │   ├── QuestionCard.tsx
│   │   └── QuestionList.tsx
│   │
│   └── auth/
│       └── AuthForm.tsx
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts        # Browser client
│   │   ├── server.ts        # Server client
│   │   └── middleware.ts
│   │
│   └── utils.ts
│
├── types/
│   └── index.ts             # TypeScript interfaces
│
└── public/
    └── images/              # Question figures
```

---

## Content Structure (from Scraped Data)

### Reading and Writing Section

| Domain | Skills |
|--------|--------|
| Information and Ideas | Central Ideas and Details, Inferences, Command of Evidence, Cross-Text Connections |
| Craft and Structure | Words in Context, Text Structure and Purpose |
| Expression of Ideas | Rhetorical Synthesis, Transitions |
| Standard English Conventions | Boundaries, Form Structure and Sense |

### Math Section (TBD - pending scraping)

| Domain | Skills |
|--------|--------|
| Algebra | Linear equations, Systems, etc. |
| Advanced Math | Quadratics, Polynomials, etc. |
| Problem Solving | Ratios, Percentages, etc. |
| Geometry & Trig | TBD |

---

## Data Pipeline

1. **Scrape** → JSON files in `output/` directory
2. **Transform** → Script to format for Supabase import
3. **Seed** → Upload to Supabase via API or SQL import
4. **Incremental** → Add new sections as scraping completes

```bash
# Example seed script (to be created)
npm run seed:questions -- --file=output/SAT_RW/questions.json
npm run seed:questions -- --file=output/SAT_MATH/questions.json
```

---

## Milestones

### M1: Project Setup
- [x] Plan document
- [ ] Initialize Next.js project
- [ ] Configure Supabase
- [ ] Set up Tailwind
- [ ] Create database tables

### M2: Auth & Layout
- [ ] Implement auth flow
- [ ] Create nav/header component
- [ ] Protected route middleware

### M3: Roadmap
- [ ] Build roadmap visualization
- [ ] Connect to skills data
- [ ] Progress display for logged-in users

### M4: Worksheets
- [ ] Worksheet list view
- [ ] Question display component
- [ ] Mark complete functionality
- [ ] Seed RW questions

### M5: Test Simulation (Phase 2)
- [ ] Timer component
- [ ] Test-taking UI
- [ ] Results & review

---

## Environment Variables

```env
# .env.local
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key  # server-side only
```

---

## Scrapers

### Completed Scrapers

| Scraper | File | Status |
|---------|------|--------|
| SAT Reading & Writing | `scrape/foo.py` | Done (1,590 questions) |
| SAT Math | `scrape/math_scraper.py` | Ready to run |

### Usage

```bash
cd scrape
source venv/bin/activate

# RW scraper
python3 foo.py [limit]

# Math scraper
python3 math_scraper.py SAT MATH                    # Full run
python3 math_scraper.py SAT MATH --limit 10         # Test with 10
python3 math_scraper.py SAT MATH --start 100        # Resume from #100
python3 math_scraper.py SAT MATH --headless         # No browser window
```

### Output Structure

```
output/
├── SAT_RW/
│   ├── questions.json      # 1,590 questions
│   └── images/             # 120 figure screenshots
│
└── SAT_MATH/
    ├── questions.json      # Generated by math_scraper.py
    └── images/             # Graphs, tables (not inline equations)
```

### Question JSON Schema

```json
{
  "question_id": "f1bfbed3",
  "assessment": "SAT",
  "section": "Math",
  "domain": "Algebra",
  "skill": "Linear equations in one variable",
  "difficulty": 2,
  "prompt_text": "Question prompt with math as text...",
  "question_text": "What is x?",
  "answer_choices": ["A) 5", "B) 10", "C) 15", "D) 20"],
  "correct_answer": "B",
  "rationale": "Explanation...",
  "has_figure": false,
  "figure_paths": []
}
```

### Math Scraper Notes

- **MathJax equations** → Extracted as text (via `alttext` attribute)
- **Graphs/SVGs** → Screenshot only if NOT inside MathJax and size ≥ 50x50
- **Tables** → Screenshot only if standalone (not in `<figure>`)
- **`<figure>` elements** → Always screenshot

This avoids the old scraper's problem of taking 10+ screenshots per question for every inline equation.

---

## Notes

- Start with RW section (1,590 questions ready)
- Math section will follow same schema
- Images stored in `public/images/` or Supabase Storage
- YouTube video links to be added manually per skill/worksheet
