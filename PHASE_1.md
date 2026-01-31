# Phase 1 Progress

## Completed

### Project Setup
- [x] CLAUDE.md created
- [x] Next.js 14 initialized with TypeScript + Tailwind
- [x] Supabase packages installed (@supabase/supabase-js, @supabase/ssr)
- [x] Directory structure created

### Supabase Setup
- [x] Supabase project created
- [x] `.env.local` configured with URL + anon key + service role key
- [x] Database schema executed (`supabase/schema.sql`)
- [x] Email confirmation disabled (for dev)

### Auth Flow
- [x] Signup works → redirects to /roadmap
- [x] Login works
- [x] Middleware protects /roadmap (redirects to /login if not authenticated)

### Data Seeding
- [x] Multi-assessment seed script (`scripts/seed.ts`)
- [x] `question-images` storage bucket created (public)
- [x] All R&W questions seeded across 3 assessments:

| Assessment | Questions | Images |
|------------|-----------|--------|
| SAT | 1,590 | 120 |
| PSAT/NMSQT & PSAT 10 | 1,270 | 93 |
| PSAT 8/9 | 1,372 | 103 |
| **Total** | **4,232** | **316** |

### Seed Script Usage
```bash
cd satprephelp

# Seed specific assessments
npx tsx scripts/seed.ts sat-rw
npx tsx scripts/seed.ts psat-nmsqt-rw psat-8-9-rw

# Seed all assessments
npx tsx scripts/seed.ts
```

Available assessment keys: `sat-rw`, `sat-math`, `psat-nmsqt-rw`, `psat-8-9-rw`

### Multi-Assessment Roadmap
- [x] Assessment selection page (`/roadmap`)
  - SAT, PSAT/NMSQT, PSAT 8/9 cards
- [x] Section selection page (`/roadmap/[assessment]`)
  - Reading & Writing, Math options
  - Dynamically shows "Coming Soon" for sections without content
- [x] Skills roadmap page (`/roadmap/[assessment]/[section]`)
  - Fetches skills from database grouped by domain
  - Links to assessment-specific worksheets

### Worksheet Pages
- [x] Skill overview (`/worksheet/[assessment]/[skill]`)
  - Strategy video section
  - Worksheets grouped by difficulty (Easy/Medium/Hard)
  - Each worksheet contains ~7 questions
- [x] Individual worksheet (`/worksheet/[assessment]/[skill]/[worksheetId]`)
  - Shows questions for selected worksheet
  - Previous/Next worksheet navigation
  - Back to skill overview link
- [x] Questions filtered by assessment (no cross-contamination)
- [x] Renders images from Supabase Storage
- [x] Shows correct/incorrect feedback after answering
- [x] Collapsible explanation/rationale

### URL Structure
```
/roadmap                                    → Choose test (SAT, PSAT/NMSQT, PSAT 8/9)
/roadmap/sat                                → Choose section (R&W, Math)
/roadmap/sat/reading-and-writing            → Skills grouped by domain
/worksheet/sat/Central%20Ideas%20and%20Details          → Skill worksheets
/worksheet/sat/Central%20Ideas%20and%20Details/easy-1   → Individual worksheet
```

Assessment URL slugs:
- `sat` → SAT
- `psat-nmsqt` → PSAT/NMSQT & PSAT 10
- `psat-8-9` → PSAT 8/9

### Files Structure

```
satprephelp/
├── app/
│   ├── page.tsx                    # Landing page
│   ├── layout.tsx                  # Root layout
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── roadmap/
│   │   ├── page.tsx                # Assessment selection (SAT/PSAT)
│   │   └── [assessment]/
│   │       ├── page.tsx            # Section selection (R&W/Math)
│   │       └── [section]/
│   │           └── page.tsx        # Skills roadmap (fetches from DB)
│   └── worksheet/
│       └── [assessment]/
│           └── [skill]/
│               ├── page.tsx        # Skill overview + worksheet cards
│               └── [worksheetId]/
│                   └── page.tsx    # Individual worksheet
├── components/
│   ├── ui/
│   │   ├── Button.tsx
│   │   └── Card.tsx
│   ├── worksheet/
│   │   ├── QuestionCard.tsx
│   │   └── QuestionList.tsx
│   └── auth/
│       └── AuthForm.tsx
├── lib/supabase/
│   ├── client.ts
│   └── server.ts
├── scripts/
│   └── seed.ts                     # Multi-assessment seeder
├── middleware.ts
├── types/index.ts
└── supabase/schema.sql
```

## Next Steps

### Priority 1: Progress Tracking
- [ ] Show user progress on roadmap (% complete per skill)
- [ ] Mark questions complete functionality (save to user_progress table)
- [ ] Connect roadmap to real data (question counts per skill)

### Priority 2: Math Content
- [ ] Run math scraper for all assessments
- [ ] Seed math questions
- [ ] Enable Math section in UI

### Dev Server
```bash
cd satprephelp
npm run dev
# Runs on http://localhost:3000
```

## Current State
- Landing page: Working
- Auth: Working (signup/login)
- Roadmap: Working
  - Multi-assessment support (SAT, PSAT/NMSQT, PSAT 8/9)
  - Dynamic section/skill pages from database
- Worksheet: Working
  - Assessment-specific question filtering
  - Skill page shows video + worksheet cards by difficulty
  - Individual worksheets show ~7 questions each
  - Answer feedback + rationale working
- Database: 4,232 questions seeded, 316 images in Supabase Storage
