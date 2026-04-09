import io
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white, HexColor, Color
from reportlab.platypus import (
    SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


LIGHT_GRAY = HexColor("#CCCCCC")
HIGHLIGHT_BG = HexColor("#D4EDDA")
HIGHLIGHT_TEXT = HexColor("#155724")


class CrosswordGrid(Flowable):
    """Custom flowable that draws a crossword grid."""

    def __init__(self, grid_data: list, numbered_cells: dict, cell_size: float = 24, show_answers: bool = False):
        super().__init__()
        self.grid_data = grid_data
        self.numbered_cells = numbered_cells  # {(row, col): number}
        self.cell_size = cell_size
        self.show_answers = show_answers
        self.rows = len(grid_data)
        self.cols = len(grid_data[0]) if grid_data else 0
        self.width = self.cols * cell_size
        self.height = self.rows * cell_size

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        cs = self.cell_size

        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.grid_data[row][col]
                x = col * cs
                # ReportLab draws from bottom-left, so flip y
                y = self.height - (row + 1) * cs

                if cell.get("isBlack", False):
                    canvas.setFillColor(black)
                    canvas.rect(x, y, cs, cs, fill=1, stroke=1)
                else:
                    canvas.setFillColor(white)
                    canvas.setStrokeColor(black)
                    canvas.setLineWidth(0.5)
                    canvas.rect(x, y, cs, cs, fill=1, stroke=1)

                    # Draw cell number
                    num = self.numbered_cells.get((row, col))
                    if num is not None:
                        canvas.setFillColor(black)
                        canvas.setFont("Helvetica", 6)
                        canvas.drawString(x + 1.5, y + cs - 7, str(num))

                    # Draw letter if showing answers
                    if self.show_answers and cell.get("letter", ""):
                        canvas.setFillColor(black)
                        canvas.setFont("Helvetica-Bold", cs * 0.5)
                        letter_text = cell["letter"]
                        canvas.drawCentredString(x + cs / 2, y + cs * 0.2, letter_text)


def calculate_numbered_cells(grid_data: list) -> dict:
    """Calculate which cells get numbers, returns {(row, col): number}."""
    rows = len(grid_data)
    cols = len(grid_data[0]) if grid_data else 0
    numbered = {}
    current_number = 1

    for row in range(rows):
        for col in range(cols):
            if grid_data[row][col].get("isBlack", False):
                continue

            starts_across = (
                (col == 0 or grid_data[row][col - 1].get("isBlack", False))
                and col < cols - 1
                and not grid_data[row][col + 1].get("isBlack", False)
            )

            starts_down = (
                (row == 0 or grid_data[row - 1][col].get("isBlack", False))
                and row < rows - 1
                and not grid_data[row + 1][col].get("isBlack", False)
            )

            if starts_across or starts_down:
                numbered[(row, col)] = current_number
                current_number += 1

    return numbered


def extract_clues(word_placements: list) -> tuple:
    """Extract across and down clues from word placements."""
    across_clues = []
    down_clues = []

    if not word_placements:
        return across_clues, down_clues

    for wp in word_placements:
        clue_text = wp.get("clue", "")
        number = wp.get("number", 0)
        direction = wp.get("direction", "")

        if not clue_text:
            continue

        entry = (number, clue_text)
        if direction == "across":
            across_clues.append(entry)
        elif direction == "down":
            down_clues.append(entry)

    across_clues.sort(key=lambda x: x[0])
    down_clues.sort(key=lambda x: x[0])

    return across_clues, down_clues


def generate_puzzle_pdf(
    title: str,
    grid_data: list,
    word_placements: Optional[list] = None,
    include_answer_key: bool = True,
    page_size: tuple = letter,
) -> bytes:
    """Generate a PDF for a single crossword puzzle.

    Returns the PDF as bytes.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PuzzleTitle",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
    )

    clue_style = ParagraphStyle(
        "Clue",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        leftIndent=18,
        firstLineIndent=-18,
    )

    numbered_cells = calculate_numbered_cells(grid_data)
    across_clues, down_clues = extract_clues(word_placements)

    # Calculate cell size to fit the page width
    available_width = page_size[0] - 1.5 * inch
    grid_cols = len(grid_data[0]) if grid_data else 15
    cell_size = min(24, available_width / grid_cols)

    story = []

    # Title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 6))

    # Empty grid (puzzle page)
    grid_flowable = CrosswordGrid(grid_data, numbered_cells, cell_size=cell_size, show_answers=False)
    story.append(grid_flowable)
    story.append(Spacer(1, 16))

    # Clues
    if across_clues:
        story.append(Paragraph("Across", section_style))
        for number, clue_text in across_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

    if down_clues:
        story.append(Paragraph("Down", section_style))
        for number, clue_text in down_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

    # Answer key on a new page
    if include_answer_key:
        story.append(PageBreak())

        answer_title_style = ParagraphStyle(
            "AnswerTitle",
            parent=styles["Heading2"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        story.append(Paragraph(f"{title} - Answer Key", answer_title_style))
        story.append(Spacer(1, 6))

        answer_grid = CrosswordGrid(grid_data, numbered_cells, cell_size=cell_size, show_answers=True)
        story.append(answer_grid)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Word Search PDF
# ---------------------------------------------------------------------------

# Direction vectors matching the frontend's WordSearchDirection type
DIRECTION_VECTORS = {
    "E": (0, 1),
    "W": (0, -1),
    "N": (-1, 0),
    "S": (1, 0),
    "NE": (-1, 1),
    "NW": (-1, -1),
    "SE": (1, 1),
    "SW": (1, -1),
}


def _build_highlight_set(placements: list) -> set:
    """Return a set of (row, col) tuples that belong to placed words."""
    highlighted = set()
    for p in placements:
        dr, dc = DIRECTION_VECTORS.get(p["direction"], (0, 0))
        for i in range(len(p["word"])):
            highlighted.add((p["row"] + dr * i, p["col"] + dc * i))
    return highlighted


class WordSearchGrid(Flowable):
    """Custom flowable that draws a word search letter grid."""

    def __init__(
        self,
        grid: list,
        cell_size: float = 24,
        highlight_cells: Optional[set] = None,
    ):
        super().__init__()
        self.grid = grid
        self.cell_size = cell_size
        self.highlight_cells = highlight_cells or set()
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0
        self.width = self.cols * cell_size
        self.height = self.rows * cell_size

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        cs = self.cell_size

        for row in range(self.rows):
            for col in range(self.cols):
                x = col * cs
                y = self.height - (row + 1) * cs
                is_highlighted = (row, col) in self.highlight_cells

                # Cell background
                if is_highlighted:
                    canvas.setFillColor(HIGHLIGHT_BG)
                else:
                    canvas.setFillColor(white)
                canvas.setStrokeColor(LIGHT_GRAY)
                canvas.setLineWidth(0.25)
                canvas.rect(x, y, cs, cs, fill=1, stroke=1)

                # Letter
                letter_text = self.grid[row][col] if row < len(self.grid) and col < len(self.grid[row]) else ""
                if letter_text:
                    if is_highlighted:
                        canvas.setFillColor(HIGHLIGHT_TEXT)
                        canvas.setFont("Helvetica-Bold", cs * 0.55)
                    else:
                        canvas.setFillColor(black)
                        canvas.setFont("Helvetica", cs * 0.55)
                    canvas.drawCentredString(x + cs / 2, y + cs * 0.22, letter_text.upper())


def generate_word_search_pdf(
    title: str,
    grid: list,
    words: list,
    placements: Optional[list] = None,
    include_answer_key: bool = True,
    page_size: tuple = letter,
) -> bytes:
    """Generate a PDF for a single word search puzzle.

    Returns the PDF as bytes.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "WSTitle",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    section_style = ParagraphStyle(
        "WSSection",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
    )

    word_style = ParagraphStyle(
        "WSWord",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
    )

    # Calculate cell size to fit the page
    available_width = page_size[0] - 1.5 * inch
    grid_cols = len(grid[0]) if grid else 15
    cell_size = min(26, available_width / grid_cols)

    story = []

    # Title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 6))

    # Puzzle grid (no highlights)
    grid_flowable = WordSearchGrid(grid, cell_size=cell_size)
    story.append(grid_flowable)
    story.append(Spacer(1, 12))

    # Word list in columns
    if words:
        story.append(Paragraph("Find these words:", section_style))

        sorted_words = sorted(words, key=str.upper)
        # Lay out words in a multi-column table
        num_cols = 3
        rows_needed = (len(sorted_words) + num_cols - 1) // num_cols
        table_data = []
        for r in range(rows_needed):
            row_cells = []
            for c in range(num_cols):
                idx = r + c * rows_needed
                if idx < len(sorted_words):
                    row_cells.append(Paragraph(sorted_words[idx].upper(), word_style))
                else:
                    row_cells.append("")
            table_data.append(row_cells)

        col_width = available_width / num_cols
        word_table = Table(table_data, colWidths=[col_width] * num_cols)
        word_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(word_table)

    # Answer key
    if include_answer_key and placements:
        story.append(PageBreak())

        answer_title_style = ParagraphStyle(
            "WSAnswerTitle",
            parent=styles["Heading2"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        story.append(Paragraph(f"{title} - Answer Key", answer_title_style))
        story.append(Spacer(1, 6))

        highlight_set = _build_highlight_set(placements)
        answer_grid = WordSearchGrid(grid, cell_size=cell_size, highlight_cells=highlight_set)
        story.append(answer_grid)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Book PDF
# ---------------------------------------------------------------------------

KDP_PAGE_SIZE = (8.5 * inch, 11 * inch)
KDP_MARGIN_TOP = 0.5 * inch
KDP_MARGIN_BOTTOM = 0.5 * inch
KDP_MARGIN_LR = 0.75 * inch  # symmetric; meets gutter minimum for ≤300 pages


def _add_page_number(canvas, doc):
    """Draw a centred page number at the bottom of every page after the title page."""
    page_num = canvas.getPageNumber()
    if page_num > 1:
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(
            doc.pagesize[0] / 2, 0.35 * inch, str(page_num)
        )
        canvas.restoreState()


def _no_page_number(canvas, doc):
    """Title page — no page number."""
    pass


def generate_book_pdf(
    title: str,
    subtitle: Optional[str],
    author: Optional[str],
    book_type: str,
    puzzles: list,
) -> bytes:
    """Generate a multi-puzzle book PDF formatted for KDP (8.5 x 11).

    *puzzles* is a list of dicts — crossword dicts have keys
    ``title``, ``grid_data``, ``word_placements``; word-search dicts have
    ``title``, ``grid``, ``words``, ``placements``.
    """
    buffer = io.BytesIO()
    page_w, page_h = KDP_PAGE_SIZE

    # --- document with two page templates (title vs content) ---------------
    frame = Frame(
        KDP_MARGIN_LR, KDP_MARGIN_BOTTOM,
        page_w - 2 * KDP_MARGIN_LR,
        page_h - KDP_MARGIN_TOP - KDP_MARGIN_BOTTOM,
        id="main",
    )

    title_template = PageTemplate(id="title_page", frames=[frame], onPage=_no_page_number)
    content_template = PageTemplate(id="content", frames=[frame], onPage=_add_page_number)

    doc = BaseDocTemplate(
        buffer,
        pagesize=KDP_PAGE_SIZE,
        topMargin=KDP_MARGIN_TOP,
        bottomMargin=KDP_MARGIN_BOTTOM,
        leftMargin=KDP_MARGIN_LR,
        rightMargin=KDP_MARGIN_LR,
    )
    doc.addPageTemplates([title_template, content_template])

    styles = getSampleStyleSheet()

    # --- shared styles ------------------------------------------------------
    book_title_style = ParagraphStyle(
        "BookTitle", parent=styles["Title"],
        fontSize=32, alignment=TA_CENTER, spaceAfter=16,
    )
    book_subtitle_style = ParagraphStyle(
        "BookSubtitle", parent=styles["Heading2"],
        fontSize=18, alignment=TA_CENTER, spaceAfter=12, textColor=HexColor("#555555"),
    )
    book_author_style = ParagraphStyle(
        "BookAuthor", parent=styles["Normal"],
        fontSize=14, alignment=TA_CENTER, spaceAfter=6,
    )
    toc_heading_style = ParagraphStyle(
        "TOCHeading", parent=styles["Heading1"],
        fontSize=22, alignment=TA_CENTER, spaceAfter=20,
    )
    toc_entry_style = ParagraphStyle(
        "TOCEntry", parent=styles["Normal"],
        fontSize=12, leading=20, leftIndent=36,
    )
    puzzle_title_style = ParagraphStyle(
        "BookPuzzleTitle", parent=styles["Heading1"],
        fontSize=20, alignment=TA_CENTER, spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "BookSection", parent=styles["Heading2"],
        fontSize=14, spaceBefore=12, spaceAfter=6,
    )
    clue_style = ParagraphStyle(
        "BookClue", parent=styles["Normal"],
        fontSize=10, leading=13, leftIndent=18, firstLineIndent=-18,
    )
    word_style = ParagraphStyle(
        "BookWSWord", parent=styles["Normal"],
        fontSize=11, leading=15,
    )
    answer_heading_style = ParagraphStyle(
        "AnswerHeading", parent=styles["Heading1"],
        fontSize=24, alignment=TA_CENTER, spaceAfter=20,
    )
    answer_puzzle_label = ParagraphStyle(
        "AnswerPuzzleLabel", parent=styles["Heading3"],
        fontSize=11, spaceBefore=10, spaceAfter=4, alignment=TA_CENTER,
    )

    available_width = page_w - 2 * KDP_MARGIN_LR

    story = []

    # ===================== TITLE PAGE =======================================
    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph(title, book_title_style))
    if subtitle:
        story.append(Paragraph(subtitle, book_subtitle_style))
    if author:
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(author, book_author_style))

    # Switch to content template from now on
    from reportlab.platypus.doctemplate import NextPageTemplate
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ===================== TABLE OF CONTENTS ================================
    story.append(Paragraph("Contents", toc_heading_style))
    for idx, p in enumerate(puzzles, 1):
        story.append(Paragraph(f"{idx}. &nbsp; {p['title']}", toc_entry_style))
    story.append(PageBreak())

    # ===================== PUZZLE PAGES =====================================
    if book_type == "crossword":
        for p in puzzles:
            grid_data = p["grid_data"]
            word_placements = p.get("word_placements")
            numbered_cells = calculate_numbered_cells(grid_data)
            across_clues, down_clues = extract_clues(word_placements)

            grid_cols = len(grid_data[0]) if grid_data else 15
            cell_size = min(24, available_width / grid_cols)

            story.append(Paragraph(p["title"], puzzle_title_style))
            story.append(Spacer(1, 6))
            story.append(CrosswordGrid(grid_data, numbered_cells, cell_size=cell_size, show_answers=False))
            story.append(Spacer(1, 16))

            if across_clues:
                story.append(Paragraph("Across", section_style))
                for number, clue_text in across_clues:
                    story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

            if down_clues:
                story.append(Paragraph("Down", section_style))
                for number, clue_text in down_clues:
                    story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

            story.append(PageBreak())
    else:
        # word search
        for p in puzzles:
            grid = p["grid"]
            words = p.get("words", [])

            grid_cols = len(grid[0]) if grid else 15
            cell_size = min(26, available_width / grid_cols)

            story.append(Paragraph(p["title"], puzzle_title_style))
            story.append(Spacer(1, 6))
            story.append(WordSearchGrid(grid, cell_size=cell_size))
            story.append(Spacer(1, 12))

            if words:
                story.append(Paragraph("Find these words:", section_style))
                sorted_words = sorted(words, key=str.upper)
                num_cols = 3
                rows_needed = (len(sorted_words) + num_cols - 1) // num_cols
                table_data = []
                for r in range(rows_needed):
                    row_cells = []
                    for c in range(num_cols):
                        ws_idx = r + c * rows_needed
                        if ws_idx < len(sorted_words):
                            row_cells.append(Paragraph(sorted_words[ws_idx].upper(), word_style))
                        else:
                            row_cells.append("")
                    table_data.append(row_cells)

                col_width = available_width / num_cols
                word_table = Table(table_data, colWidths=[col_width] * num_cols)
                word_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]))
                story.append(word_table)

            story.append(PageBreak())

    # ===================== ANSWER KEY SECTION ===============================
    story.append(Paragraph("Answer Key", answer_heading_style))
    story.append(Spacer(1, 12))

    if book_type == "crossword":
        for p in puzzles:
            grid_data = p["grid_data"]
            numbered_cells = calculate_numbered_cells(grid_data)
            grid_cols = len(grid_data[0]) if grid_data else 15
            full_cell = min(24, available_width / grid_cols)
            ans_cell = full_cell * 0.65

            story.append(Paragraph(p["title"], answer_puzzle_label))
            story.append(CrosswordGrid(grid_data, numbered_cells, cell_size=ans_cell, show_answers=True))
            story.append(Spacer(1, 18))
    else:
        for p in puzzles:
            grid = p["grid"]
            placements = p.get("placements", [])
            grid_cols = len(grid[0]) if grid else 15
            full_cell = min(26, available_width / grid_cols)
            ans_cell = full_cell * 0.65

            highlight_set = _build_highlight_set(placements) if placements else set()
            story.append(Paragraph(p["title"], answer_puzzle_label))
            story.append(WordSearchGrid(grid, cell_size=ans_cell, highlight_cells=highlight_set))
            story.append(Spacer(1, 18))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
