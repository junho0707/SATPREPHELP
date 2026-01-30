# SAT Math Figures Scraping Plan

## Overview
This document outlines the different types of mathematical figures found in the College Board SAT Question Bank and how to handle each type during scraping.

---

## Figure Types Identified

### 1. Equation (MathJax/SVG)
**Description:** Mathematical equations rendered using MathJax, appearing as `<mjx-container>` elements containing SVG.

**Extraction strategy:**
- Extract the `alttext` attribute for plain text representation
- Extract MathML from `<mjx-assistive-mml>` if available
- Screenshot the container for visual representation

---

### 2. Graph-Image (SVG)
**Description:** Coordinate plane graphs rendered as inline SVG elements with `role="img"` and `aria-label` descriptions.

**Extraction strategy:**
- Extract `aria-label` for text description
- Screenshot the entire SVG element
- Store SVG source if needed for re-rendering

---

### 3. Table (HTML Style)
**Description:** HTML tables containing MathJax expressions in cells.

**Extraction strategy:**
- Parse table structure (rows/columns)
- Extract MathJax alttext from each cell
- Store as structured data: `{ "headers": [...], "rows": [[...]] }`
- Screenshot the table for visual representation

---

### 4. Equation-Image Style
**Description:** Equations rendered as base64-encoded PNG images within `<img>` tags.

**Extraction strategy:**
- Extract `alt` attribute for text representation
- Decode and save base64 image data as PNG file
- Store path reference to saved image

---

## Data Schema

Questions are extracted with `{{FIG_N}}` placeholders that map to figures:

```json
{
  "question_id": "abc12345",
  "assessment": "SAT",
  "section": "Math",
  "domain": "Algebra",
  "skill": "Linear equations",
  "difficulty": 2,
  "prompt_text": "Given {{FIG_1}}, solve for x.",
  "question_text": "What is the value of {{FIG_2}}?",
  "answer_choices": ["A", "B", "C", "D"],
  "correct_answer": "B",
  "rationale": "The answer is {{FIG_3}} because...",
  "figures": [
    {
      "figure_index": 1,
      "placeholder": "{{FIG_1}}",
      "type": "mathjax",
      "position": "prompt",
      "text_content": "x + 2 = 5",
      "image_path": "images/abc12345_mathjax_1.png",
      "structured_data": {"alttext": "x + 2 = 5"},
      "raw_html": "<mjx-container>...</mjx-container>"
    }
  ]
}
```

---

## Implementation

### File: `math_figure_extractor.py`

```python
"""
Math Figure Extractor for SAT Question Bank Scraper

This module implements specialized extraction for different types of mathematical
figures found in the College Board SAT Question Bank, building on foo_args.py logic.

Figure Types:
1. MathJax Equations (mjx-container with SVG)
2. Graph SVG (inline SVG with aria-label)
3. Mixed Content (equations inline with text)
4. HTML Tables (with MathJax cells)
5. Equation Images (base64 PNG math-img)
6. Table Images (tables with base64 cells)
7. Complex Graphs (detailed SVG graphs)
"""

from __future__ import annotations
import base64
import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Literal, Optional
from playwright.sync_api import sync_playwright, Page, Locator, ElementHandle

# Import from existing scraper
from foo_args import (
    Assessment, Section,
    ASSESSMENT_VALUE_MAP, SECTION_VALUE_MAP,
    get_output_dirs, setup_output_dirs,
    get_difficulty_from_bars, close_modal,
    has_next_question_in_modal, click_next_question_in_modal,
    parse_assessment, parse_section, print_usage
)


def get_current_question_id(page: Page) -> str | None:
    """
    Get the current question ID from the modal.
    Looks for 8-character hex ID pattern.
    """
    try:
        # Try multiple sources for the question ID
        selectors_to_try = [
            "#modalID1 .cb-dialog-header h2",  # Header title specifically
            "#modalID1 .cb-dialog-header",     # Full header
            "#modalID1 .question-detail-info", # Info section
        ]

        for selector in selectors_to_try:
            element = page.locator(selector)
            if element.count() > 0:
                text = element.evaluate("el => el.textContent || ''").strip()
                # Look for 8-char hex ID pattern (the actual question ID format)
                match = re.search(r'\b([a-f0-9]{8})\b', text, re.IGNORECASE)
                if match:
                    return match.group(1)

        # Last resort: try the view button ID from the table
        view_btn = page.locator("button.view-question-button[aria-pressed='true']")
        if view_btn.count() > 0:
            btn_id = view_btn.get_attribute("id")
            if btn_id:
                # Extract just the hex part if present
                match = re.search(r'([a-f0-9]{8})', btn_id, re.IGNORECASE)
                if match:
                    return match.group(1)
                return btn_id

    except Exception:
        pass
    return None


class FigureType(str, Enum):
    """Types of mathematical figures that can appear in SAT questions."""
    MATHJAX = "mathjax"
    GRAPH_SVG = "graph_svg"
    MIXED_CONTENT = "mixed"
    TABLE_HTML = "table_html"
    EQUATION_IMAGE = "equation_image"
    TABLE_IMAGE = "table_image"
    GRAPH_COMPLEX = "graph_complex"
    UNKNOWN = "unknown"


class FigurePosition(str, Enum):
    """Position where a figure appears in the question."""
    PROMPT = "prompt"
    QUESTION = "question"
    CHOICES = "choices"
    RATIONALE = "rationale"


@dataclass
class FigureData:
    """Structured data for an extracted figure."""
    figure_type: FigureType
    position: FigurePosition
    text_content: str = ""
    image_path: Optional[str] = None
    structured_data: dict = field(default_factory=dict)
    raw_html: Optional[str] = None
    figure_index: int = 0  # Maps to {{FIG_N}} placeholder

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "figure_index": self.figure_index,  # For mapping to {{FIG_N}}
            "placeholder": f"{{{{FIG_{self.figure_index}}}}}",  # Ready-to-use placeholder
            "type": self.figure_type.value,
            "position": self.position.value,
            "text_content": self.text_content,
            "image_path": self.image_path,
            "structured_data": self.structured_data,
            "raw_html": self.raw_html,
        }


# ============================================================================
# FIGURE TYPE DETECTION
# ============================================================================

def get_element_text(element: Locator) -> str:
    """Safely get text content from any element (including SVG)."""
    try:
        return element.evaluate("el => el.textContent || ''").strip()
    except Exception:
        return ""


def get_text_with_placeholders(element: Locator, start_index: int = 1) -> tuple[str, int]:
    """
    Extract text from element, replacing figures with {{FIG_N}} placeholders.

    Returns:
        tuple: (text_with_placeholders, next_figure_index)
    """
    try:
        result = element.evaluate("""(el, startIndex) => {
            // Clone the element so we don't modify the original
            const clone = el.cloneNode(true);
            let figIndex = startIndex;

            // Figure selectors in priority order (MUST match extraction order!)
            const figureSelectors = [
                'figure',
                'table:has(mjx-container)',
                'table:has(img.math-img)',
                'mjx-container',                    // Before svg - mjx contains svg!
                'svg[role="img"][aria-label]',      // Only actual graphs with descriptions
                'img.math-img'
            ];

            // Track replaced elements to avoid duplicates
            const replaced = new Set();

            for (const selector of figureSelectors) {
                const elements = clone.querySelectorAll(selector);
                for (const figEl of elements) {
                    // Skip if already replaced (e.g., mjx inside figure)
                    let dominated = false;
                    for (const r of replaced) {
                        if (r.contains(figEl) || figEl.contains(r)) {
                            dominated = true;
                            break;
                        }
                    }
                    if (dominated) continue;

                    // Check if this element is inside an already-replaced element
                    let parent = figEl.parentElement;
                    let skipThis = false;
                    while (parent && parent !== clone) {
                        if (replaced.has(parent)) {
                            skipThis = true;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    if (skipThis) continue;

                    // Replace with placeholder
                    const placeholder = document.createTextNode(`{{FIG_${figIndex}}}`);
                    figEl.parentNode.replaceChild(placeholder, figEl);
                    replaced.add(figEl);
                    figIndex++;
                }
            }

            return {
                text: clone.textContent || '',
                nextIndex: figIndex
            };
        }""", start_index)

        return result["text"].strip(), result["nextIndex"]
    except Exception as e:
        print(f"    [placeholder] Error: {e}")
        return get_element_text(element), start_index


def get_tag_name(element: Locator) -> str:
    """Get the tag name of an element."""
    try:
        return element.evaluate("el => el.tagName.toLowerCase()")
    except Exception:
        return ""


def detect_figure_type(element: Locator) -> FigureType:
    """
    Detect the type of figure based on its HTML structure.

    Priority order:
    1. SVG with graph-related aria-label -> GRAPH_SVG or GRAPH_COMPLEX
    2. mjx-container -> MATHJAX
    3. img.math-img with base64 -> EQUATION_IMAGE
    4. table containing math-img -> TABLE_IMAGE
    5. table containing mjx-container -> TABLE_HTML
    6. Mixed content with multiple mjx-containers -> MIXED_CONTENT
    """
    try:
        tag_name = get_tag_name(element)

        # If the element itself is an SVG
        if tag_name == "svg":
            aria_label = element.get_attribute("aria-label") or ""
            role = element.get_attribute("role") or ""
            if role == "img" or aria_label:
                if any(kw in aria_label.lower() for kw in
                       ["graph", "coordinate", "plane", "axis", "line", "curve", "parabola"]):
                    if len(aria_label) > 100 or "system" in aria_label.lower():
                        return FigureType.GRAPH_COMPLEX
                    return FigureType.GRAPH_SVG
            return FigureType.GRAPH_SVG  # Default SVG to graph

        # If the element itself is an mjx-container
        if tag_name == "mjx-container":
            return FigureType.MATHJAX

        # If the element itself is an img.math-img
        if tag_name == "img":
            class_attr = element.get_attribute("class") or ""
            if "math-img" in class_attr:
                return FigureType.EQUATION_IMAGE

        # If the element itself is a table
        if tag_name == "table":
            # Check what's inside the table
            math_imgs = element.locator("img.math-img")
            if math_imgs.count() > 0:
                return FigureType.TABLE_IMAGE
            mjx = element.locator("mjx-container")
            if mjx.count() > 0:
                return FigureType.TABLE_HTML
            return FigureType.TABLE_HTML  # Default table

        # For container elements (figure, div, etc.), check children
        outer_html = element.evaluate("el => el.outerHTML")

        # Check for SVG graphs inside container
        if '<svg' in outer_html:
            svg = element.locator("svg[role='img']")
            if svg.count() > 0:
                aria_label = svg.first.get_attribute("aria-label") or ""
                if any(kw in aria_label.lower() for kw in
                       ["graph", "coordinate", "plane", "axis", "line", "curve", "parabola"]):
                    if len(aria_label) > 100 or "system" in aria_label.lower():
                        return FigureType.GRAPH_COMPLEX
                    return FigureType.GRAPH_SVG

        # Check for equation images inside container
        math_imgs = element.locator("img.math-img")
        if math_imgs.count() > 0:
            tables = element.locator("table")
            if tables.count() > 0:
                return FigureType.TABLE_IMAGE
            return FigureType.EQUATION_IMAGE

        # Check for tables with MathJax inside container
        tables = element.locator("table")
        if tables.count() > 0:
            mjx_in_table = element.locator("table mjx-container")
            if mjx_in_table.count() > 0:
                return FigureType.TABLE_HTML

        # Check for MathJax equations inside container
        mjx_containers = element.locator("mjx-container")
        mjx_count = mjx_containers.count()

        if mjx_count > 0:
            text_content = get_element_text(element)
            if mjx_count > 1 or (len(text_content) > 50 and mjx_count >= 1):
                paragraphs = element.locator("p")
                if paragraphs.count() > 1:
                    return FigureType.MIXED_CONTENT
            return FigureType.MATHJAX

        return FigureType.UNKNOWN

    except Exception as e:
        print(f"    [detect] Error: {e}")
        return FigureType.UNKNOWN


def detect_element_figure_type(page: Page, selector: str) -> FigureType:
    """Detect figure type for an element specified by selector."""
    element = page.locator(selector)
    if element.count() == 0:
        return FigureType.UNKNOWN
    return detect_figure_type(element.first)


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_mathjax_equation(element: Locator, page: Page, images_dir: str,
                              question_id: str, index: int) -> FigureData:
    """Extract MathJax equation data."""
    figure = FigureData(
        figure_type=FigureType.MATHJAX,
        position=FigurePosition.PROMPT,
    )

    try:
        tag = get_tag_name(element)
        if tag == "mjx-container":
            mjx = element
        else:
            mjx = element.locator("mjx-container").first

        alttext = mjx.get_attribute("alttext") or ""
        figure.text_content = alttext
        figure.structured_data["alttext"] = alttext

        mathml = mjx.locator("mjx-assistive-mml math")
        if mathml.count() > 0:
            try:
                mathml_content = mathml.first.evaluate("el => el.outerHTML")
                figure.structured_data["mathml"] = mathml_content
            except Exception:
                pass

        filename = f"{question_id}_mathjax_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            mjx.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
            print(f"    [mathjax] Captured: {filename}")
        except Exception as e:
            print(f"    [mathjax] Screenshot failed: {e}")

        figure.raw_html = mjx.evaluate("el => el.outerHTML")

    except Exception as e:
        print(f"    [mathjax] Extraction error: {e}")

    return figure


def extract_graph_svg(element: Locator, page: Page, images_dir: str,
                      question_id: str, index: int, is_complex: bool = False) -> FigureData:
    """Extract SVG graph data."""
    fig_type = FigureType.GRAPH_COMPLEX if is_complex else FigureType.GRAPH_SVG
    figure = FigureData(
        figure_type=fig_type,
        position=FigurePosition.PROMPT,
    )

    try:
        tag = get_tag_name(element)
        if tag == "svg":
            svg = element
        else:
            svg = element.locator("svg[role='img']").first

        aria_label = svg.get_attribute("aria-label") or ""
        figure.text_content = aria_label
        figure.structured_data["aria_label"] = aria_label

        viewbox = svg.get_attribute("viewBox") or ""
        figure.structured_data["viewBox"] = viewbox

        axis_labels = svg.locator("text")
        if axis_labels.count() > 0:
            labels = []
            for i in range(min(axis_labels.count(), 10)):
                try:
                    label_text = axis_labels.nth(i).evaluate("el => el.textContent || ''")
                    if label_text.strip():
                        labels.append(label_text.strip())
                except Exception:
                    pass
            figure.structured_data["axis_labels"] = labels

        suffix = "graph_complex" if is_complex else "graph_svg"
        filename = f"{question_id}_{suffix}_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            svg.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
            print(f"    [graph] Captured: {filename}")
        except Exception as e:
            print(f"    [graph] Screenshot failed: {e}")

        try:
            figure.raw_html = svg.evaluate("el => el.outerHTML")
        except Exception:
            pass

    except Exception as e:
        print(f"    [graph] Extraction error: {e}")

    return figure


def extract_equation_image(element: Locator, page: Page, images_dir: str,
                           question_id: str, index: int) -> FigureData:
    """Extract base64-encoded equation image."""
    figure = FigureData(
        figure_type=FigureType.EQUATION_IMAGE,
        position=FigurePosition.PROMPT,
    )

    try:
        tag = get_tag_name(element)
        if tag == "img":
            img = element
        else:
            img = element.locator("img.math-img").first

        alt_text = img.get_attribute("alt") or ""
        figure.text_content = alt_text
        figure.structured_data["alt"] = alt_text

        src = img.get_attribute("src") or ""
        if src.startswith("data:image/png;base64,"):
            base64_data = src.replace("data:image/png;base64,", "")
            filename = f"{question_id}_eqimg_{index}.png"
            filepath = os.path.join(images_dir, filename)

            try:
                image_bytes = base64.b64decode(base64_data)
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                figure.image_path = os.path.join("images", filename)
                print(f"    [eqimg] Saved: {filename}")
            except Exception as e:
                print(f"    [eqimg] Save failed: {e}")

    except Exception as e:
        print(f"    [eqimg] Extraction error: {e}")

    return figure


def extract_table_html(element: Locator, page: Page, images_dir: str,
                       question_id: str, index: int) -> FigureData:
    """Extract HTML table with MathJax cells."""
    figure = FigureData(
        figure_type=FigureType.TABLE_HTML,
        position=FigurePosition.PROMPT,
    )

    try:
        tag = get_tag_name(element)
        if tag == "table":
            table = element
        else:
            table = element.locator("table").first

        headers = []
        rows = []

        header_cells = table.locator("thead th, tbody tr:first-child th")
        for i in range(header_cells.count()):
            cell = header_cells.nth(i)
            mjx = cell.locator("mjx-container")
            if mjx.count() > 0:
                headers.append(mjx.first.get_attribute("alttext") or get_element_text(cell))
            else:
                headers.append(get_element_text(cell))

        body_rows = table.locator("tbody tr")
        start_idx = 1 if headers else 0

        for i in range(start_idx, body_rows.count()):
            row = body_rows.nth(i)
            cells = row.locator("td")
            row_data = []

            for j in range(cells.count()):
                cell = cells.nth(j)
                mjx = cell.locator("mjx-container")
                if mjx.count() > 0:
                    row_data.append(mjx.first.get_attribute("alttext") or get_element_text(cell))
                else:
                    row_data.append(get_element_text(cell))

            if row_data:
                rows.append(row_data)

        figure.structured_data["headers"] = headers
        figure.structured_data["rows"] = rows

        text_parts = []
        if headers:
            text_parts.append(" | ".join(headers))
            text_parts.append("-" * 20)
        for row in rows:
            text_parts.append(" | ".join(row))
        figure.text_content = "\n".join(text_parts)

        filename = f"{question_id}_table_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            table.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
            print(f"    [table] Captured: {filename}")
        except Exception as e:
            print(f"    [table] Screenshot failed: {e}")

    except Exception as e:
        print(f"    [table] Extraction error: {e}")

    return figure


def extract_table_image(element: Locator, page: Page, images_dir: str,
                        question_id: str, index: int) -> FigureData:
    """Extract table containing base64 equation images."""
    figure = FigureData(
        figure_type=FigureType.TABLE_IMAGE,
        position=FigurePosition.PROMPT,
    )

    try:
        tag = get_tag_name(element)
        if tag == "table":
            table = element
        else:
            table = element.locator("table").first
        rows_data = []
        text_parts = []

        imgs = table.locator("img.math-img")
        for i in range(imgs.count()):
            img = imgs.nth(i)
            alt_text = img.get_attribute("alt") or ""
            text_parts.append(alt_text)

            row_item = {"text": alt_text, "image_path": None}

            src = img.get_attribute("src") or ""
            if src.startswith("data:image/png;base64,"):
                base64_data = src.replace("data:image/png;base64,", "")
                filename = f"{question_id}_tableimg_{index}_{i}.png"
                filepath = os.path.join(images_dir, filename)

                try:
                    image_bytes = base64.b64decode(base64_data)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    row_item["image_path"] = os.path.join("images", filename)
                except Exception:
                    pass

            rows_data.append(row_item)

        figure.structured_data["rows"] = rows_data
        figure.text_content = "\n".join(text_parts)

        filename = f"{question_id}_tableimg_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            table.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
            print(f"    [tableimg] Captured: {filename}")
        except Exception as e:
            print(f"    [tableimg] Screenshot failed: {e}")

    except Exception as e:
        print(f"    [tableimg] Extraction error: {e}")

    return figure


def extract_mixed_content(element: Locator, page: Page, images_dir: str,
                          question_id: str, index: int) -> FigureData:
    """Extract mixed content with inline equations and text."""
    figure = FigureData(
        figure_type=FigureType.MIXED_CONTENT,
        position=FigurePosition.PROMPT,
    )

    try:
        equations = []

        mjx_containers = element.locator("mjx-container")
        for i in range(mjx_containers.count()):
            alttext = mjx_containers.nth(i).get_attribute("alttext") or ""
            equations.append(alttext)

        figure.structured_data["equations"] = equations
        figure.structured_data["has_inline_equations"] = True

        figure.text_content = get_element_text(element)

        filename = f"{question_id}_mixed_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            element.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
            print(f"    [mixed] Captured: {filename}")
        except Exception as e:
            print(f"    [mixed] Screenshot failed: {e}")

        figure.raw_html = element.evaluate("el => el.outerHTML")

    except Exception as e:
        print(f"    [mixed] Extraction error: {e}")

    return figure


# ============================================================================
# MAIN EXTRACTION ORCHESTRATOR
# ============================================================================

def extract_figure(element: Locator, page: Page, images_dir: str,
                   question_id: str, index: int, position: FigurePosition) -> FigureData:
    """Main entry point: detect type and extract figure accordingly."""
    fig_type = detect_figure_type(element)

    extractors = {
        FigureType.MATHJAX: extract_mathjax_equation,
        FigureType.GRAPH_SVG: lambda e, p, d, q, i: extract_graph_svg(e, p, d, q, i, False),
        FigureType.GRAPH_COMPLEX: lambda e, p, d, q, i: extract_graph_svg(e, p, d, q, i, True),
        FigureType.EQUATION_IMAGE: extract_equation_image,
        FigureType.TABLE_HTML: extract_table_html,
        FigureType.TABLE_IMAGE: extract_table_image,
        FigureType.MIXED_CONTENT: extract_mixed_content,
    }

    extractor = extractors.get(fig_type)
    if extractor:
        figure = extractor(element, page, images_dir, question_id, index)
    else:
        figure = FigureData(
            figure_type=FigureType.UNKNOWN,
            position=position,
            text_content=get_element_text(element),
        )
        filename = f"{question_id}_unknown_{index}.png"
        filepath = os.path.join(images_dir, filename)
        try:
            element.screenshot(path=filepath)
            figure.image_path = os.path.join("images", filename)
        except Exception:
            pass

    figure.position = position
    figure.figure_index = index
    return figure


def extract_all_figures_from_section(page: Page, section_selector: str,
                                     position: FigurePosition, images_dir: str,
                                     question_id: str, start_index: int = 1) -> list[FigureData]:
    """Extract all figures from a section with deduplication."""
    figures = []
    section = page.locator(section_selector)

    if section.count() == 0:
        return figures

    # Selectors in priority order - containers first
    figure_selectors = [
        "figure",
        "table:has(mjx-container)",
        "table:has(img.math-img)",
        "mjx-container",                    # Before svg - mjx contains svg!
        "svg[role='img'][aria-label]",      # Only actual graphs with descriptions
        "img.math-img",
    ]

    index = start_index

    for selector in figure_selectors:
        elements = section.locator(selector)
        for i in range(elements.count()):
            element = elements.nth(i)

            try:
                is_duplicate = element.evaluate("""(el) => {
                    if (el.dataset.figureProcessed === 'true') return true;
                    let parent = el.parentElement;
                    while (parent) {
                        if (parent.dataset.figureProcessed === 'true') return true;
                        parent = parent.parentElement;
                    }
                    const processed = el.querySelector('[data-figure-processed="true"]');
                    if (processed) return true;
                    return false;
                }""")

                if is_duplicate:
                    continue

                element.evaluate("el => el.dataset.figureProcessed = 'true'")

            except Exception:
                pass

            figure = extract_figure(element, page, images_dir, question_id, index, position)
            if figure.text_content or figure.image_path:
                figures.append(figure)
                index += 1

    try:
        section.evaluate("""el => {
            el.querySelectorAll('[data-figure-processed]').forEach(e => {
                delete e.dataset.figureProcessed;
            });
        }""")
    except Exception:
        pass

    return figures


# ============================================================================
# ENHANCED QUESTION DATA EXTRACTION
# ============================================================================

def extract_question_data_enhanced(page: Page, question_id: str, images_dir: str) -> dict:
    """Extract all data from question detail modal with enhanced figure extraction."""
    modal = "#modalID1"
    page.wait_for_selector(f"{modal} .cb-dialog-content", timeout=10000)
    page.wait_for_timeout(500)

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
        "figures": [],
    }

    # 1) Info table
    info_cells = page.locator(f"{modal} .question-detail-info table tbody tr td")
    if info_cells.count() >= 5:
        question_data["assessment"] = get_element_text(info_cells.nth(0))
        question_data["section"] = get_element_text(info_cells.nth(1))
        question_data["domain"] = get_element_text(info_cells.nth(2))
        question_data["skill"] = get_element_text(info_cells.nth(3))
        question_data["difficulty"] = get_difficulty_from_bars(page)

    figure_index = 1

    # 2) Prompt area
    prompt = page.locator(f"{modal} .prompt")
    if prompt.count() > 0:
        prompt_text, next_idx = get_text_with_placeholders(prompt, figure_index)
        question_data["prompt_text"] = prompt_text

        prompt_figures = extract_all_figures_from_section(
            page, f"{modal} .prompt", FigurePosition.PROMPT,
            images_dir, question_id, figure_index
        )
        for fig in prompt_figures:
            question_data["figures"].append(fig.to_dict())
        figure_index += len(prompt_figures)

    # 3) Question text
    question = page.locator(f"{modal} .question")
    if question.count() > 0:
        question_text, next_idx = get_text_with_placeholders(question, figure_index)
        question_data["question_text"] = question_text

        q_figures = extract_all_figures_from_section(
            page, f"{modal} .question", FigurePosition.QUESTION,
            images_dir, question_id, figure_index
        )
        for fig in q_figures:
            question_data["figures"].append(fig.to_dict())
        figure_index += len(q_figures)

    # 4) Answer choices
    choices = page.locator(f"{modal} .answer-choices ul li")
    choices_start_index = figure_index
    for i in range(choices.count()):
        choice_text, next_idx = get_text_with_placeholders(choices.nth(i), figure_index)
        question_data["answer_choices"].append(choice_text)
        figure_index = next_idx

    choice_figures = extract_all_figures_from_section(
        page, f"{modal} .answer-choices", FigurePosition.CHOICES,
        images_dir, question_id, choices_start_index
    )
    for fig in choice_figures:
        question_data["figures"].append(fig.to_dict())
    figure_index = choices_start_index + len(choice_figures)

    # 5) Correct answer and rationale
    rationale = page.locator(f"{modal} .rationale")
    if rationale.count() > 0:
        correct_el = rationale.locator("p.cb-font-weight-bold")
        if correct_el.count() > 0:
            correct_text = get_element_text(correct_el.first)
            if ":" in correct_text:
                question_data["correct_answer"] = correct_text.split(":")[-1].strip()

        rationale_div = rationale.locator("div").last
        if rationale_div.count() > 0:
            rationale_text, next_idx = get_text_with_placeholders(rationale_div, figure_index)
            question_data["rationale"] = rationale_text

        rat_figures = extract_all_figures_from_section(
            page, f"{modal} .rationale", FigurePosition.RATIONALE,
            images_dir, question_id, figure_index
        )
        for fig in rat_figures:
            question_data["figures"].append(fig.to_dict())

    return question_data


# ============================================================================
# ENHANCED SCRAPER
# ============================================================================

def run_math_scraper(
    *,
    url: str = "https://satsuiteeducatorquestionbank.collegeboard.org/digital/search",
    assessment: Assessment = "SAT",
    section: Section = "MATH",
    headless: bool = False,
    slow_mo_ms: int = 150,
    timeout_ms: int = 20_000,
    max_questions: int | None = None,
) -> list[dict]:
    """Enhanced scraper for SAT Math questions with detailed figure extraction."""
    base_dir, images_dir = setup_output_dirs(assessment, section)

    assessment_value = ASSESSMENT_VALUE_MAP[assessment]
    section_value = SECTION_VALUE_MAP[section]

    select_assessment = r"select#apricot_select_\:r0\:"
    select_section = r"select#apricot_select_\:r1\:"
    all_domain_checkbox_inputs = "input[id^='checkbox-'][type='checkbox']"
    search_btn = "button.cb-btn.cb-btn-yellow"

    all_questions = []
    total_processed = 0

    stats = {ft.value: 0 for ft in FigureType}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        print("Starting Math Figure Extractor...")
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
        print("Search submitted...")
        page.wait_for_timeout(600)

        page.wait_for_selector("table.cb-table-react", timeout=timeout_ms)
        page.wait_for_timeout(500)

        first_question_btn = page.locator("button.view-question-button").first
        first_question_id = first_question_btn.get_attribute("id")
        print(f"Opening first question: {first_question_id}")
        first_question_btn.click()

        page.wait_for_selector("#modalID1 .cb-dialog-content", timeout=timeout_ms)
        page.wait_for_timeout(500)

        while True:
            if max_questions is not None and total_processed >= max_questions:
                print(f"\nReached limit of {max_questions} questions")
                break

            question_id = get_current_question_id(page)
            if not question_id:
                question_id = f"unknown_{total_processed + 1}"

            total_processed += 1
            print(f"\n[{total_processed}] Processing question: {question_id}")

            try:
                question_data = extract_question_data_enhanced(page, question_id, images_dir)
                all_questions.append(question_data)

                for fig in question_data["figures"]:
                    stats[fig["type"]] += 1

                print(f"    Domain: {question_data['domain']} / Skill: {question_data['skill']}")
                if question_data["figures"]:
                    fig_types = [f["type"] for f in question_data["figures"]]
                    print(f"    Figures: {fig_types}")

            except Exception as e:
                print(f"    Error extracting data: {e}")
                all_questions.append({
                    "question_id": question_id,
                    "error": str(e)
                })

            if has_next_question_in_modal(page):
                click_next_question_in_modal(page)
            else:
                print("\nNo more questions (Next button disabled/gone)")
                break

        close_modal(page)
        browser.close()

    output_file = os.path.join(base_dir, "questions_enhanced.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(all_questions)} questions to {output_file}")
    print(f"Images saved to {images_dir}/")
    print("\nFigure Statistics:")
    for fig_type, count in stats.items():
        if count > 0:
            print(f"  {fig_type}: {count}")

    return all_questions


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("""
Usage: python math_figure_extractor.py <assessment> <section> [limit]

Arguments:
  assessment  - SAT, PSAT, or PSAT89
  section     - RW or MATH (use MATH for best results with this extractor)
  limit       - (optional) number of questions to scrape

Examples:
  python math_figure_extractor.py SAT MATH          # All SAT Math questions
  python math_figure_extractor.py SAT MATH 10       # 10 SAT Math questions
  python math_figure_extractor.py PSAT MATH 5       # 5 PSAT/NMSQT Math questions
""")
        sys.exit(1)

    assessment = parse_assessment(sys.argv[1])
    if assessment is None:
        print(f"Invalid assessment: '{sys.argv[1]}'")
        print("Valid options: SAT, PSAT, PSAT89")
        sys.exit(1)

    section = parse_section(sys.argv[2])
    if section is None:
        print(f"Invalid section: '{sys.argv[2]}'")
        print("Valid options: RW, MATH")
        sys.exit(1)

    limit = None
    if len(sys.argv) > 3:
        try:
            limit = int(sys.argv[3])
        except ValueError:
            print(f"Invalid limit '{sys.argv[3]}', running full scrape")

    print(f"Config:")
    print(f"  Assessment: {assessment}")
    print(f"  Section:    {section}")
    print(f"  Limit:      {limit if limit else 'All'}")
    print()

    questions = run_math_scraper(
        assessment=assessment,
        section=section,
        headless=False,
        max_questions=limit,
    )
```

---

## Usage

```bash
# Run the extractor
python math_figure_extractor.py SAT MATH 10

# Output
# - output/SAT_MATH/questions_enhanced.json
# - output/SAT_MATH/images/*.png
```

## Rebuilding Questions

```python
import json

with open("output/SAT_MATH/questions_enhanced.json") as f:
    questions = json.load(f)

for q in questions:
    text = q["question_text"]
    for fig in q["figures"]:
        # Replace placeholder with text representation
        text = text.replace(fig["placeholder"], fig["text_content"])
        # Or with image: text = text.replace(fig["placeholder"], f"![{fig['type']}]({fig['image_path']})")
    print(text)
```
