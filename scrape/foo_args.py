from __future__ import annotations
import json
import os
import time
from typing import Literal
from playwright.sync_api import sync_playwright, Page

Assessment = Literal["SAT", "PSAT/NMSQT & PSAT 10", "PSAT 8/9"]
Section = Literal["RW", "MATH", "Reading and Writing", "Math"]

ASSESSMENT_VALUE_MAP = {
    "SAT": "99",
    "PSAT/NMSQT & PSAT 10": "100",
    "PSAT 8/9": "102",
}

SECTION_VALUE_MAP = {
    "RW": "1",
    "Reading and Writing": "1",
    "MATH": "2",
    "Math": "2",
}

OUTPUT_DIR = "output"


def get_output_dirs(assessment: Assessment, section: Section) -> tuple[str, str]:
    """Get output directory paths for given assessment and section."""
    # Create a clean folder name
    assessment_clean = assessment.replace("/", "_").replace(" ", "_").replace("&", "and")
    section_clean = section
    
    base_dir = os.path.join(OUTPUT_DIR, f"{assessment_clean}_{section_clean}")
    images_dir = os.path.join(base_dir, "images")
    return base_dir, images_dir


def setup_output_dirs(assessment: Assessment, section: Section) -> tuple[str, str]:
    """Create output directories if they don't exist. Returns (base_dir, images_dir)."""
    base_dir, images_dir = get_output_dirs(assessment, section)
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    return base_dir, images_dir


def get_difficulty_from_bars(page: Page) -> int:
    """
    Map difficulty indicator bars to 1, 2, or 3.
    Counts the number of 'filled' difficulty indicators.
    """
    filled_bars = page.locator(
        "#modalID1 .question-detail-info .difficulty-table-icon .difficulty-indicator.filled"
    )
    return filled_bars.count()


def capture_figure(page: Page, question_id: str, images_dir: str, index: int = 1) -> str | None:
    """
    Screenshot a figure element (table/graph) and save it.
    Returns the relative path to the saved image, or None if capture fails.
    """
    try:
        # Look for figures within the prompt area
        figures = page.locator("#modalID1 .prompt figure")
        if figures.count() == 0:
            return None
        
        fig = figures.nth(index - 1)
        filename = f"{question_id}_{index}.png"
        filepath = os.path.join(images_dir, filename)
        
        fig.screenshot(path=filepath)
        print(f"    📸 Captured figure: {filename}")
        return os.path.join("images", filename)
    except Exception as e:
        print(f"    ⚠ Could not capture figure: {e}")
        return None


def extract_question_data(page: Page, question_id: str, images_dir: str) -> dict:
    """
    Extract all data from the question detail modal.
    """
    modal_selector = "#modalID1"
    page.wait_for_selector(f"{modal_selector} .cb-dialog-content", timeout=10000)
    page.wait_for_timeout(500)  # Let content fully render

    question_data = {
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

    # -------------------------
    # 1) Extract info table data (Assessment, Section, Domain, Skill, Difficulty)
    # -------------------------
    info_table_selector = f"{modal_selector} .question-detail-info table tbody tr td"
    info_cells = page.locator(info_table_selector)
    
    if info_cells.count() >= 5:
        question_data["assessment"] = info_cells.nth(0).inner_text().strip()
        question_data["section"] = info_cells.nth(1).inner_text().strip()
        question_data["domain"] = info_cells.nth(2).inner_text().strip()
        question_data["skill"] = info_cells.nth(3).inner_text().strip()
        # Difficulty from bar count
        question_data["difficulty"] = get_difficulty_from_bars(page)

    # -------------------------
    # 2) Extract prompt (text + optional figure)
    # -------------------------
    prompt_selector = f"{modal_selector} .prompt"
    prompt_element = page.locator(prompt_selector)
    
    if prompt_element.count() > 0:
        # Get all text content from prompt
        prompt_text_parts = []
        prompt_paragraphs = prompt_element.locator("p")
        for i in range(prompt_paragraphs.count()):
            text = prompt_paragraphs.nth(i).inner_text().strip()
            if text:
                prompt_text_parts.append(text)
        question_data["prompt_text"] = "\n\n".join(prompt_text_parts)

        # Check for and capture figures/tables
        figures = prompt_element.locator("figure")
        figure_count = figures.count()
        if figure_count > 0:
            question_data["has_figure"] = True
            for i in range(figure_count):
                fig_path = capture_figure(page, question_id, images_dir, i + 1)
                if fig_path:
                    question_data["figure_paths"].append(fig_path)

    # -------------------------
    # 3) Extract question text
    # -------------------------
    question_selector = f"{modal_selector} .question"
    question_element = page.locator(question_selector)
    if question_element.count() > 0:
        question_data["question_text"] = question_element.inner_text().strip()

    # -------------------------
    # 4) Extract answer choices
    # -------------------------
    choices_selector = f"{modal_selector} .answer-choices ul li"
    choices = page.locator(choices_selector)
    
    for i in range(choices.count()):
        choice_text = choices.nth(i).inner_text().strip()
        question_data["answer_choices"].append(choice_text)

    # -------------------------
    # 5) Extract correct answer and rationale
    # -------------------------
    rationale_selector = f"{modal_selector} .rationale"
    rationale_element = page.locator(rationale_selector)
    
    if rationale_element.count() > 0:
        # Get correct answer (e.g., "Correct Answer: A")
        correct_answer_el = rationale_element.locator("p.cb-font-weight-bold")
        if correct_answer_el.count() > 0:
            correct_text = correct_answer_el.first.inner_text().strip()
            # Extract just the letter (e.g., "A" from "Correct Answer: A")
            if ":" in correct_text:
                question_data["correct_answer"] = correct_text.split(":")[-1].strip()

        # Get full rationale text
        rationale_div = rationale_element.locator("div").last
        if rationale_div.count() > 0:
            question_data["rationale"] = rationale_div.inner_text().strip()

    return question_data


def close_modal(page: Page):
    """Close the question detail modal."""
    close_btn = page.locator("#modalID1 button[aria-label='Close']")
    if close_btn.count() > 0:
        close_btn.click()
        page.wait_for_timeout(300)


def has_next_question_in_modal(page: Page) -> bool:
    """Check if Next button exists inside the modal and is clickable."""
    next_btn = page.locator("#modalID1 .footer div.cb-align-right button:has-text('Next')")
    if next_btn.count() == 0:
        return False
    return not next_btn.is_disabled()


def click_next_question_in_modal(page: Page) -> bool:
    """Click the Next button inside modal to go to next question. Returns True if successful."""
    try:
        next_btn = page.locator("#modalID1 .footer div.cb-align-right button:has-text('Next')")
        if next_btn.count() > 0 and not next_btn.is_disabled():
            next_btn.click()
            page.wait_for_timeout(800)  # Wait for next question to load
            return True
    except Exception as e:
        print(f"⚠ Could not click Next in modal: {e}")
    return False


def get_current_question_id(page: Page) -> str | None:
    """Get the current question ID from the modal header or content."""
    import re
    try:
        # Try to get from the modal title/header area
        header = page.locator("#modalID1 .cb-dialog-header")
        if header.count() > 0:
            text = header.inner_text()
            # Handle format "Question ID: xxxxxxxx"
            if "ID:" in text:
                id_part = text.split("ID:")[-1].strip().split()[0]
                # Clean any trailing punctuation
                id_part = re.sub(r'[^a-zA-Z0-9]$', '', id_part)
                if id_part:
                    return id_part
            # Handle format "Question xxxxxxxx" (no "ID:" prefix)
            elif "Question" in text:
                id_part = text.split("Question")[-1].strip().split()[0]
                id_part = re.sub(r'[^a-zA-Z0-9]$', '', id_part)
                if id_part and id_part != "ID":
                    return id_part

        # Fallback: try to find 8-char hex ID pattern anywhere in modal
        id_cell = page.locator("#modalID1 .question-detail-info")
        if id_cell.count() > 0:
            text = id_cell.inner_text()
            match = re.search(r'\b[a-f0-9]{8}\b', text)
            if match:
                return match.group()

        # Last resort: check the full modal content for hex ID
        modal = page.locator("#modalID1")
        if modal.count() > 0:
            text = modal.inner_text()
            match = re.search(r'\b[a-f0-9]{8}\b', text)
            if match:
                return match.group()
    except Exception:
        pass
    return None


def run_scraper(
    *,
    url: str = "https://satsuiteeducatorquestionbank.collegeboard.org/digital/search",
    assessment: Assessment = "SAT",
    section: Section = "RW",
    headless: bool = False,
    slow_mo_ms: int = 150,
    timeout_ms: int = 20_000,
    max_questions: int | None = None,  # Limit for testing (None = all)
) -> list[dict]:
    """
    Full scraper flow:
    1) Search with filters
    2) Click first question to open modal
    3) Extract data, click Next inside modal, repeat
    4) Save to JSON
    """
    base_dir, images_dir = setup_output_dirs(assessment, section)
    
    assessment_value = ASSESSMENT_VALUE_MAP[assessment]
    section_value = SECTION_VALUE_MAP[section]

    select_assessment = r"select#apricot_select_\:r0\:"
    select_section = r"select#apricot_select_\:r1\:"
    all_domain_checkbox_inputs = "input[id^='checkbox-'][type='checkbox']"
    search_btn = "button.cb-btn.cb-btn-yellow"

    all_questions = []
    total_processed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        # -------------------------
        # 1) Search page setup
        # -------------------------
        print("🚀 Starting scraper...")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(select_assessment)
        page.select_option(select_assessment, value=assessment_value)

        page.wait_for_selector(select_section)
        page.select_option(select_section, value=section_value)
        page.wait_for_timeout(400)

        boxes = page.locator(all_domain_checkbox_inputs)
        for i in range(boxes.count()):
            try:
                boxes.nth(i).check()
            except Exception:
                boxes.nth(i).click(force=True)

        page.wait_for_selector(search_btn)
        page.wait_for_timeout(800)

        for _ in range(40):
            if not page.locator(search_btn).is_disabled():
                break
            page.wait_for_timeout(200)

        page.click(search_btn)
        print("🔍 Search submitted...")
        page.wait_for_timeout(600)

        # Wait for results table
        page.wait_for_selector("table.cb-table-react", timeout=timeout_ms)
        page.wait_for_timeout(500)

        # -------------------------
        # 2) Click first question to open modal
        # -------------------------
        first_question_btn = page.locator("button.view-question-button").first
        first_question_id = first_question_btn.get_attribute("id")
        print(f"📖 Opening first question: {first_question_id}")
        first_question_btn.click()
        
        # Wait for modal to fully load
        page.wait_for_selector("#modalID1 .cb-dialog-content", timeout=timeout_ms)
        page.wait_for_timeout(500)

        # -------------------------
        # 3) Loop: extract data, click Next in modal
        # -------------------------
        while True:
            # Check if we've hit the limit
            if max_questions is not None and total_processed >= max_questions:
                print(f"\n🛑 Reached limit of {max_questions} questions")
                break

            # Get current question ID
            question_id = get_current_question_id(page)
            if not question_id:
                # Fallback: use counter-based ID
                question_id = f"unknown_{total_processed + 1}"
            
            total_processed += 1
            print(f"\n[{total_processed}] Processing question: {question_id}")

            # Extract data from modal
            try:
                question_data = extract_question_data(page, question_id, images_dir)
                all_questions.append(question_data)
                print(f"    ✓ Extracted: {question_data['domain']} / {question_data['skill']}")
                if question_data["has_figure"]:
                    print(f"    📊 Has {len(question_data['figure_paths'])} figure(s)")
            except Exception as e:
                print(f"    ❌ Error extracting data: {e}")
                all_questions.append({
                    "question_id": question_id,
                    "error": str(e)
                })

            # Try to go to next question via modal Next button
            if has_next_question_in_modal(page):
                click_next_question_in_modal(page)
            else:
                print("\n🏁 No more questions (Next button disabled/gone)")
                break

        # Close modal when done
        close_modal(page)
        browser.close()

    # -------------------------
    # 4) Save to JSON
    # -------------------------
    output_file = os.path.join(base_dir, "questions.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Done! Saved {len(all_questions)} questions to {output_file}")
    print(f"   Images saved to {images_dir}/")
    
    return all_questions


def print_usage():
    """Print usage instructions."""
    print("""
Usage: python sat_scraper.py <assessment> <section> [limit]

Arguments:
  assessment  - SAT, PSAT, or PSAT89
  section     - RW or MATH
  limit       - (optional) number of questions to scrape

Examples:
  python sat_scraper.py SAT RW          # All SAT Reading & Writing questions
  python sat_scraper.py SAT MATH 10     # 10 SAT Math questions
  python sat_scraper.py PSAT RW 5       # 5 PSAT/NMSQT Reading & Writing questions
  python sat_scraper.py PSAT89 MATH     # All PSAT 8/9 Math questions
""")


def parse_assessment(arg: str) -> Assessment | None:
    """Parse assessment argument to valid Assessment type."""
    arg_upper = arg.upper()
    if arg_upper == "SAT":
        return "SAT"
    elif arg_upper in ("PSAT", "PSAT10", "PSAT/NMSQT"):
        return "PSAT/NMSQT & PSAT 10"
    elif arg_upper in ("PSAT89", "PSAT8/9", "PSAT9"):
        return "PSAT 8/9"
    return None


def parse_section(arg: str) -> Section | None:
    """Parse section argument to valid Section type."""
    arg_upper = arg.upper()
    if arg_upper in ("RW", "READING", "READINGWRITING", "R"):
        return "RW"
    elif arg_upper in ("MATH", "M", "MATHEMATICS"):
        return "MATH"
    return None


if __name__ == "__main__":
    import sys
    
    # Parse CLI arguments: python sat_scraper.py <assessment> <section> [limit]
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    # Parse assessment
    assessment = parse_assessment(sys.argv[1])
    if assessment is None:
        print(f"❌ Invalid assessment: '{sys.argv[1]}'")
        print("   Valid options: SAT, PSAT, PSAT89")
        sys.exit(1)
    
    # Parse section
    section = parse_section(sys.argv[2])
    if section is None:
        print(f"❌ Invalid section: '{sys.argv[2]}'")
        print("   Valid options: RW, MATH")
        sys.exit(1)
    
    # Parse optional limit
    limit = None
    if len(sys.argv) > 3:
        try:
            limit = int(sys.argv[3])
        except ValueError:
            print(f"⚠ Invalid limit '{sys.argv[3]}', running full scrape")
    
    # Print config
    print(f"📋 Config:")
    print(f"   Assessment: {assessment}")
    print(f"   Section:    {section}")
    print(f"   Limit:      {limit if limit else 'All'}")
    print()
    
    questions = run_scraper(
        assessment=assessment,
        section=section,
        headless=False,
        max_questions=limit,
    )
