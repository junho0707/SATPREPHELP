"""
SAT Math Scraper - Simplified Version

Same approach as the RW scraper: screenshot figure containers, not individual elements.
"""

from __future__ import annotations
import json
import os
import re
from typing import Literal
from playwright.sync_api import sync_playwright, Page

Assessment = Literal["SAT", "PSAT/NMSQT & PSAT 10", "PSAT 8/9"]
Section = Literal["RW", "MATH"]

ASSESSMENT_VALUE_MAP = {
    "SAT": "99",
    "PSAT/NMSQT & PSAT 10": "100",
    "PSAT 8/9": "102",
    # Short aliases
    "PSAT": "100",
    "PSAT89": "102",
}

SECTION_VALUE_MAP = {
    "RW": "1",
    "MATH": "2",
}


def get_output_dirs(assessment: str, section: str) -> tuple[str, str]:
    """Get output directory paths for the given assessment/section."""
    # Normalize names for directory
    assessment_name = assessment.replace("/", "_").replace(" ", "_")
    section_name = "RW" if section in ("RW", "1") else "MATH"

    base_dir = os.path.join("output", f"{assessment_name}_{section_name}")
    images_dir = os.path.join(base_dir, "images")
    return base_dir, images_dir


def setup_output_dirs(assessment: str, section: str) -> tuple[str, str]:
    """Create output directories and return paths."""
    base_dir, images_dir = get_output_dirs(assessment, section)
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    return base_dir, images_dir


def get_difficulty_from_bars(page: Page) -> int:
    """Count filled difficulty indicator bars (1, 2, or 3)."""
    filled = page.locator(
        "#modalID1 .question-detail-info .difficulty-table-icon .difficulty-indicator.filled"
    )
    return filled.count()


def get_current_question_id(page: Page) -> str | None:
    """Extract 8-character hex question ID from modal."""
    try:
        selectors = [
            "#modalID1 .cb-dialog-header h2",
            "#modalID1 .cb-dialog-header",
            "#modalID1 .question-detail-info",
        ]

        for selector in selectors:
            el = page.locator(selector)
            if el.count() > 0:
                text = el.inner_text()
                match = re.search(r'\b([a-f0-9]{8})\b', text, re.IGNORECASE)
                if match:
                    return match.group(1)

        # Fallback: check pressed view button
        view_btn = page.locator("button.view-question-button[aria-pressed='true']")
        if view_btn.count() > 0:
            btn_id = view_btn.get_attribute("id") or ""
            match = re.search(r'([a-f0-9]{8})', btn_id, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def capture_figures(page: Page, question_id: str, images_dir: str) -> list[str]:
    """
    Screenshot visual content: figures, graphs, tables.
    """
    paths = []
    modal = "#modalID1"
    index = 1


    # Check prompt area
    prompt = page.locator(f"{modal} .prompt")
    if prompt.count() > 0:
        # <figure> elements
        figures = prompt.locator("figure")
        for i in range(figures.count()):
            try:
                filename = f"{question_id}_{index}.png"
                figures.nth(i).screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured figure: {filename}")
                index += 1
            except Exception as e:
                print(f"    Figure error: {e}")

        # SVG graphs with role="img" (actual graph figures, NOT MathJax)
        graph_svgs = prompt.locator('svg[role="img"]')
        for i in range(graph_svgs.count()):
            try:
                svg = graph_svgs.nth(i)
                # Skip MathJax equation SVGs
                in_mjx = svg.evaluate("el => !!el.closest('mjx-container')")
                if in_mjx:
                    continue
                filename = f"{question_id}_{index}.png"
                svg.screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured graph svg: {filename}")
                index += 1
            except Exception as e:
                print(f"    Graph SVG error: {e}")

        # Other SVGs not in MathJax, size > 100x100
        svgs = prompt.locator("svg")
        for i in range(svgs.count()):
            try:
                svg = svgs.nth(i)
                # Skip if already captured (has role="img") or is MathJax
                has_role = svg.evaluate("el => el.getAttribute('role') === 'img'")
                if has_role:
                    continue
                in_mjx = svg.evaluate("el => !!el.closest('mjx-container')")
                if in_mjx:
                    continue
                box = svg.bounding_box()
                if box and box['width'] >= 100 and box['height'] >= 100:
                    filename = f"{question_id}_{index}.png"
                    svg.screenshot(path=os.path.join(images_dir, filename))
                    paths.append(f"images/{filename}")
                    print(f"    Captured svg: {filename}")
                    index += 1
            except Exception as e:
                print(f"    SVG error: {e}")

        # Tables not in figure
        tables = prompt.locator("table")
        for i in range(tables.count()):
            try:
                table = tables.nth(i)
                in_fig = table.evaluate("el => !!el.closest('figure')")
                if in_fig:
                    continue
                filename = f"{question_id}_{index}.png"
                table.screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured table: {filename}")
                index += 1
            except Exception as e:
                print(f"    Table error: {e}")

    # Check question area (graphs can appear here too)
    question = page.locator(f"{modal} .question")
    if question.count() > 0:
        # SVG graphs with role="img" (NOT MathJax)
        graph_svgs = question.locator('svg[role="img"]')
        for i in range(graph_svgs.count()):
            try:
                svg = graph_svgs.nth(i)
                # Skip MathJax equation SVGs
                in_mjx = svg.evaluate("el => !!el.closest('mjx-container')")
                if in_mjx:
                    continue
                filename = f"{question_id}_{index}.png"
                svg.screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured question graph svg: {filename}")
                index += 1
            except Exception as e:
                print(f"    Question graph SVG error: {e}")

        # <figure> elements
        figures = question.locator("figure")
        for i in range(figures.count()):
            try:
                filename = f"{question_id}_{index}.png"
                figures.nth(i).screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured question figure: {filename}")
                index += 1
            except Exception as e:
                print(f"    Question figure error: {e}")

        # Tables
        tables = question.locator("table")
        for i in range(tables.count()):
            try:
                table = tables.nth(i)
                in_fig = table.evaluate("el => !!el.closest('figure')")
                if in_fig:
                    continue
                filename = f"{question_id}_{index}.png"
                table.screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured question table: {filename}")
                index += 1
            except Exception as e:
                print(f"    Question table error: {e}")

    # Check answer choices - only figures and large SVGs
    choices = page.locator(f"{modal} .answer-choices")
    if choices.count() > 0:
        figures = choices.locator("figure")
        for i in range(figures.count()):
            try:
                filename = f"{question_id}_{index}.png"
                figures.nth(i).screenshot(path=os.path.join(images_dir, filename))
                paths.append(f"images/{filename}")
                print(f"    Captured choice figure: {filename}")
                index += 1
            except Exception as e:
                print(f"    Choice figure error: {e}")

        svgs = choices.locator("svg")
        for i in range(svgs.count()):
            try:
                svg = svgs.nth(i)
                # Skip MathJax equation SVGs
                if svg.evaluate("el => !!el.closest('mjx-container')"):
                    continue
                box = svg.bounding_box()
                if box and box['width'] >= 50 and box['height'] >= 50:
                    filename = f"{question_id}_{index}.png"
                    svg.screenshot(path=os.path.join(images_dir, filename))
                    paths.append(f"images/{filename}")
                    print(f"    Captured choice svg: {filename}")
                    index += 1
            except Exception:
                pass

    return paths


def extract_text_with_math(element) -> str:
    """
    Extract text content, preserving math as readable text where possible.
    MathJax elements have 'alttext' attribute with LaTeX-like representation.
    """
    try:
        # Use JavaScript to extract text with math alttext substitution
        text = element.evaluate("""el => {
            const clone = el.cloneNode(true);

            // Replace MathJax with alttext
            clone.querySelectorAll('mjx-container').forEach(mjx => {
                const alt = mjx.getAttribute('alttext') || '';
                mjx.replaceWith(alt ? ` ${alt} ` : ' [math] ');
            });

            // Replace math images with alt text
            clone.querySelectorAll('img.math-img').forEach(img => {
                const alt = img.getAttribute('alt') || '';
                img.replaceWith(alt ? ` ${alt} ` : ' [math] ');
            });

            // Replace SVG graphs with aria-label
            clone.querySelectorAll('svg[role="img"]').forEach(svg => {
                const label = svg.getAttribute('aria-label') || '';
                svg.replaceWith(label ? ` [Figure: ${label}] ` : ' [figure] ');
            });

            return clone.textContent || '';
        }""")

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception:
        return element.inner_text().strip()


def extract_question_data(page: Page, question_id: str, images_dir: str) -> dict:
    """Extract all data from the question detail modal."""
    modal = "#modalID1"
    page.wait_for_selector(f"{modal} .cb-dialog-content", timeout=10000)
    page.wait_for_timeout(500)

    data = {
        "question_id": question_id,
        "assessment": "",
        "section": "",
        "domain": "",
        "skill": "",
        "difficulty": 0,
        "prompt_text": "",
        "question_text": "",
        "answer_choices": [],
        "correct_answer": "",
        "rationale": "",
        "has_figure": False,
        "figure_paths": [],
    }

    # --- Info table ---
    info_cells = page.locator(f"{modal} .question-detail-info table tbody tr td")
    if info_cells.count() >= 5:
        data["assessment"] = info_cells.nth(0).inner_text().strip()
        data["section"] = info_cells.nth(1).inner_text().strip()
        data["domain"] = info_cells.nth(2).inner_text().strip()
        data["skill"] = info_cells.nth(3).inner_text().strip()
        data["difficulty"] = get_difficulty_from_bars(page)

    # --- Prompt ---
    prompt = page.locator(f"{modal} .prompt")
    if prompt.count() > 0:
        data["prompt_text"] = extract_text_with_math(prompt)

    # --- Question ---
    question = page.locator(f"{modal} .question")
    if question.count() > 0:
        data["question_text"] = extract_text_with_math(question)

    # --- Answer choices ---
    choices = page.locator(f"{modal} .answer-choices ul li")
    for i in range(choices.count()):
        choice_text = extract_text_with_math(choices.nth(i))
        data["answer_choices"].append(choice_text)

    # --- Correct answer & rationale ---
    rationale = page.locator(f"{modal} .rationale")
    if rationale.count() > 0:
        correct_el = rationale.locator("p.cb-font-weight-bold")
        if correct_el.count() > 0:
            correct_text = correct_el.first.inner_text().strip()
            if ":" in correct_text:
                data["correct_answer"] = correct_text.split(":")[-1].strip()

        rationale_div = rationale.locator("div").last
        if rationale_div.count() > 0:
            data["rationale"] = extract_text_with_math(rationale_div)

    # --- Capture figures ---
    figure_paths = capture_figures(page, question_id, images_dir)
    if figure_paths:
        data["has_figure"] = True
        data["figure_paths"] = figure_paths

    return data


def close_modal(page: Page):
    """Close the question detail modal."""
    close_btn = page.locator("#modalID1 button[aria-label='Close']")
    if close_btn.count() > 0:
        close_btn.click()
        page.wait_for_timeout(300)


def has_next_question(page: Page) -> bool:
    """Check if Next button exists and is enabled."""
    next_btn = page.locator("#modalID1 .footer div.cb-align-right button:has-text('Next')")
    if next_btn.count() == 0:
        return False
    return not next_btn.is_disabled()


def click_next_question(page: Page) -> bool:
    """Click Next button to go to next question."""
    try:
        next_btn = page.locator("#modalID1 .footer div.cb-align-right button:has-text('Next')")
        if next_btn.count() > 0 and not next_btn.is_disabled():
            next_btn.click()
            page.wait_for_timeout(800)
            return True
    except Exception as e:
        print(f"    Could not click Next: {e}")
    return False


def run_scraper(
    *,
    assessment: str = "SAT",
    section: str = "MATH",
    headless: bool = False,
    slow_mo_ms: int = 150,
    timeout_ms: int = 20_000,
    max_questions: int | None = None,
    start_from: int = 0,  # Skip first N questions (for resuming)
) -> list[dict]:
    """
    Main scraper flow:
    1. Set filters and search
    2. Open first question modal
    3. Extract data, click Next, repeat
    4. Save to JSON
    """
    base_dir, images_dir = setup_output_dirs(assessment, section)

    # Map to actual values
    assessment_value = ASSESSMENT_VALUE_MAP.get(assessment, ASSESSMENT_VALUE_MAP["SAT"])
    section_value = SECTION_VALUE_MAP.get(section, SECTION_VALUE_MAP["MATH"])

    url = "https://satsuiteeducatorquestionbank.collegeboard.org/digital/search"
    select_assessment = r"select#apricot_select_\:r0\:"
    select_section = r"select#apricot_select_\:r1\:"
    all_domain_checkbox = "input[id^='checkbox-'][type='checkbox']"
    search_btn = "button.cb-btn.cb-btn-yellow"

    all_questions = []
    total_processed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        print(f"Starting scraper: {assessment} {section}")
        print(f"Output: {base_dir}/")

        # --- Setup filters ---
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(select_assessment)
        page.select_option(select_assessment, value=assessment_value)

        page.wait_for_selector(select_section)
        page.select_option(select_section, value=section_value)
        page.wait_for_timeout(400)

        # Check all domain boxes
        boxes = page.locator(all_domain_checkbox)
        for i in range(boxes.count()):
            try:
                boxes.nth(i).check()
            except Exception:
                boxes.nth(i).click(force=True)

        # Wait for search button to be ready
        page.wait_for_selector(search_btn)
        page.wait_for_timeout(800)
        for _ in range(40):
            if not page.locator(search_btn).is_disabled():
                break
            page.wait_for_timeout(200)

        # Search
        page.click(search_btn)
        print("Search submitted...")
        page.wait_for_timeout(600)

        page.wait_for_selector("table.cb-table-react", timeout=timeout_ms)
        page.wait_for_timeout(500)

        # --- Open first question ---
        first_btn = page.locator("button.view-question-button").first
        print(f"Opening first question...")
        first_btn.click()

        page.wait_for_selector("#modalID1 .cb-dialog-content", timeout=timeout_ms)
        page.wait_for_timeout(500)

        # --- Skip to start_from if resuming ---
        if start_from > 0:
            print(f"Skipping to question {start_from + 1}...")
            for i in range(start_from):
                if has_next_question(page):
                    click_next_question(page)
                else:
                    print(f"Only {i} questions available, can't skip to {start_from}")
                    break

        # --- Main extraction loop ---
        while True:
            if max_questions is not None and total_processed >= max_questions:
                print(f"\nReached limit of {max_questions} questions")
                break

            question_id = get_current_question_id(page)
            if not question_id:
                question_id = f"unknown_{total_processed + 1}"

            total_processed += 1
            print(f"\n[{total_processed}] Processing: {question_id}")

            try:
                question_data = extract_question_data(page, question_id, images_dir)
                all_questions.append(question_data)
                print(f"    {question_data['domain']} / {question_data['skill']}")
                if question_data["has_figure"]:
                    print(f"    Figures: {len(question_data['figure_paths'])}")
            except Exception as e:
                print(f"    Error: {e}")
                all_questions.append({"question_id": question_id, "error": str(e)})

            if has_next_question(page):
                click_next_question(page)
            else:
                print("\nNo more questions")
                break

        close_modal(page)
        browser.close()

    # --- Save ---
    output_file = os.path.join(base_dir, "questions.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(all_questions)} questions to {output_file}")
    print(f"Images: {images_dir}/")

    return all_questions


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    import sys

    args = {
        "assessment": "SAT",
        "section": "MATH",
        "limit": None,
        "start": 0,
        "headless": False,
    }

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ("--help", "-h"):
            print("""
SAT Math Scraper

Usage: python math_scraper.py [assessment] [section] [options]

Arguments:
  assessment    SAT, PSAT, or PSAT89 (default: SAT)
  section       MATH or RW (default: MATH)

Options:
  --limit N     Only scrape N questions
  --start N     Skip first N questions (for resuming)
  --headless    Run browser in headless mode

Examples:
  python math_scraper.py SAT MATH
  python math_scraper.py SAT MATH --limit 10
  python math_scraper.py SAT MATH --start 100 --limit 50
  python math_scraper.py PSAT MATH --headless
""")
            sys.exit(0)

        elif arg == "--limit":
            i += 1
            args["limit"] = int(sys.argv[i])
        elif arg == "--start":
            i += 1
            args["start"] = int(sys.argv[i])
        elif arg == "--headless":
            args["headless"] = True
        elif arg.upper() in ASSESSMENT_VALUE_MAP:
            args["assessment"] = arg.upper()
        elif arg.upper() in SECTION_VALUE_MAP:
            args["section"] = arg.upper()
        else:
            # Try as limit number (backwards compat)
            try:
                args["limit"] = int(arg)
            except ValueError:
                print(f"Unknown argument: {arg}")

        i += 1

    return args


if __name__ == "__main__":
    args = parse_args()

    print(f"Config:")
    print(f"  Assessment: {args['assessment']}")
    print(f"  Section:    {args['section']}")
    print(f"  Limit:      {args['limit'] or 'All'}")
    print(f"  Start from: {args['start']}")
    print(f"  Headless:   {args['headless']}")
    print()

    run_scraper(
        assessment=args["assessment"],
        section=args["section"],
        headless=args["headless"],
        max_questions=args["limit"],
        start_from=args["start"],
    )
