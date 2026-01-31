# SAT Math Scrape Summary

**Date:** 2026-01-31
**Scraper:** `scrape/math_scraper.py`

## Results

| Metric | Count |
|--------|-------|
| Total questions | 1,682 |
| Figure images | 652 |
| Questions with figures | 307 |
| Scrape errors | 0 |

## Domain Distribution

| Domain | Count |
|--------|-------|
| Algebra | 561 |
| Advanced Math | 477 |
| Problem-Solving and Data Analysis | 374 |
| Geometry and Trigonometry | 270 |

## Data Quality

### Figures
- All 652 image files exist and are retrievable
- Stored in `images/` directory as PNG screenshots
- Referenced in JSON via `figure_paths` array
- `has_figure: true` flag set correctly

### Minor Issues (not blocking)
- **81 empty `correct_answer`:**
  - 68 recoverable from `rationale` text (format: "The correct answer is X")
  - 13 truly missing (~0.8% of total)
- **1 empty `question_text`:** Content exists in `prompt_text` field instead

## Output Files

```
output/SAT_MATH/
├── questions.json    # All question data
├── images/           # 652 PNG figure screenshots
│   ├── {question_id}_1.png
│   ├── {question_id}_2.png
│   └── ...
└── SCRAPE_SUMMARY.md # This file
```

## JSON Schema

```json
{
  "question_id": "8-char hex",
  "assessment": "SAT",
  "section": "Math",
  "domain": "Algebra | Advanced Math | Problem-Solving and Data Analysis | Geometry and Trigonometry",
  "skill": "specific skill name",
  "difficulty": 1-3,
  "prompt_text": "passage/context if any",
  "question_text": "the actual question",
  "answer_choices": ["A", "B", "C", "D"] or [] for SPR,
  "correct_answer": "A/B/C/D or numeric value",
  "rationale": "explanation text",
  "has_figure": true/false,
  "figure_paths": ["images/xxx_1.png", ...]
}
```

## Bug Fix Applied

Fixed `capture_figures()` in `math_scraper.py` to:
1. Detect `svg[role="img"]` elements (graph figures)
2. Check `.question` area in addition to `.prompt` area
3. Filter out MathJax equation SVGs via `mjx-container` check
