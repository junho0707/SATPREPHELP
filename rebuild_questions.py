"""
Rebuild SAT Questions from Scraped Data

Takes the questions_enhanced.json output and rebuilds questions
with figures replaced by text, images, or other formats.

Usage:
    python rebuild_questions.py SAT MATH text      # Plain text output
    python rebuild_questions.py SAT MATH markdown  # Markdown with images
    python rebuild_questions.py SAT MATH html      # HTML with img tags
"""

import json
import os
import sys
from typing import Literal

Mode = Literal["text", "markdown", "html"]


def replace_figures(text: str, fig_map: dict, mode: Mode) -> str:
    """Replace {{FIG_N}} placeholders with appropriate content."""
    if not text:
        return text

    for placeholder, fig in fig_map.items():
        if mode == "text":
            # Use plain text representation
            replacement = fig["text_content"]
        elif mode == "markdown":
            # Use markdown image syntax
            img_path = fig.get("image_path", "")
            alt = fig["text_content"].replace('"', "'")
            replacement = f'![{alt}]({img_path})'
        elif mode == "html":
            # Use HTML img tag
            img_path = fig.get("image_path", "")
            alt = fig["text_content"].replace('"', "'")
            replacement = f'<img src="{img_path}" alt="{alt}" class="math-figure">'
        else:
            replacement = fig["text_content"]

        text = text.replace(placeholder, replacement)

    return text


def rebuild_question(q: dict, mode: Mode) -> dict:
    """Rebuild a single question with figures replaced."""
    # Build placeholder -> figure mapping
    fig_map = {fig["placeholder"]: fig for fig in q.get("figures", [])}

    # Rebuild all text fields
    rebuilt = {
        "question_id": q.get("question_id", ""),
        "assessment": q.get("assessment", ""),
        "section": q.get("section", ""),
        "domain": q.get("domain", ""),
        "skill": q.get("skill", ""),
        "difficulty": q.get("difficulty", 0),
        "prompt": replace_figures(q.get("prompt_text", ""), fig_map, mode),
        "question": replace_figures(q.get("question_text", ""), fig_map, mode),
        "choices": [replace_figures(c, fig_map, mode) for c in q.get("answer_choices", [])],
        "correct_answer": q.get("correct_answer", ""),
        "rationale": replace_figures(q.get("rationale", ""), fig_map, mode),
    }

    # Keep figure metadata for reference
    rebuilt["figure_count"] = len(q.get("figures", []))
    rebuilt["figure_types"] = list(set(f["type"] for f in q.get("figures", [])))

    return rebuilt


def rebuild_all(input_path: str, output_path: str, mode: Mode) -> list[dict]:
    """Rebuild all questions from input JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    rebuilt = []
    for q in questions:
        try:
            rebuilt.append(rebuild_question(q, mode))
        except Exception as e:
            print(f"Error rebuilding {q.get('question_id', 'unknown')}: {e}")
            rebuilt.append({
                "question_id": q.get("question_id", "unknown"),
                "error": str(e)
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rebuilt, f, indent=2, ensure_ascii=False)

    return rebuilt


def print_sample(questions: list[dict], n: int = 3):
    """Print sample questions to verify output."""
    print("\n" + "=" * 60)
    print("SAMPLE OUTPUT")
    print("=" * 60)

    for i, q in enumerate(questions[:n]):
        if "error" in q:
            print(f"\n[{i+1}] ERROR: {q['error']}")
            continue

        print(f"\n[{i+1}] {q['question_id']}")
        print(f"Domain: {q['domain']} | Skill: {q['skill']} | Difficulty: {q['difficulty']}")
        print("-" * 40)

        if q["prompt"]:
            print(f"Prompt: {q['prompt'][:200]}...")

        print(f"Question: {q['question'][:300]}...")

        if q["choices"]:
            print("Choices:")
            for j, c in enumerate(q["choices"]):
                print(f"  {chr(65+j)}. {c[:100]}")

        print(f"Answer: {q['correct_answer']}")
        print()


def main():
    if len(sys.argv) < 4:
        print("""
Usage: python rebuild_questions.py <assessment> <section> <mode>

Arguments:
    assessment  - SAT, PSAT, or PSAT89
    section     - RW or MATH
    mode        - text, markdown, or html

Examples:
    python rebuild_questions.py SAT MATH text
    python rebuild_questions.py SAT MATH markdown
    python rebuild_questions.py PSAT RW html
""")
        sys.exit(1)

    assessment = sys.argv[1].upper()
    section = sys.argv[2].upper()
    mode = sys.argv[3].lower()

    if mode not in ("text", "markdown", "html"):
        print(f"Invalid mode: {mode}")
        print("Valid modes: text, markdown, html")
        sys.exit(1)

    # Build paths
    base_dir = os.path.join("output", f"{assessment}_{section}")
    input_path = os.path.join(base_dir, "questions_enhanced.json")
    output_path = os.path.join(base_dir, f"questions_{mode}.json")

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        print("Run the scraper first: python math_figure_extractor.py SAT MATH")
        sys.exit(1)

    print(f"Rebuilding questions...")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Mode:   {mode}")

    rebuilt = rebuild_all(input_path, output_path, mode)

    # Stats
    total = len(rebuilt)
    errors = sum(1 for q in rebuilt if "error" in q)
    fig_counts = {}
    for q in rebuilt:
        for ft in q.get("figure_types", []):
            fig_counts[ft] = fig_counts.get(ft, 0) + 1

    print(f"\nDone! Rebuilt {total} questions ({errors} errors)")
    print(f"Output saved to: {output_path}")

    if fig_counts:
        print("\nFigure types in output:")
        for ft, count in sorted(fig_counts.items()):
            print(f"  {ft}: {count}")

    print_sample(rebuilt)


if __name__ == "__main__":
    main()
