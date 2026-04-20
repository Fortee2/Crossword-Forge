import io
import math
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white, HexColor, Color
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.tableofcontents import TableOfContents
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
    difficulty_label: Optional[str] = None,
) -> bytes:
    """Generate a PDF for a single crossword puzzle."""
    from reportlab.platypus import SimpleDocTemplate
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

    difficulty_style = ParagraphStyle(
        "PuzzleDifficulty",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=HexColor("#666666"),
    )

    numbered_cells = calculate_numbered_cells(grid_data)
    across_clues, down_clues = extract_clues(word_placements)

    available_width = page_size[0] - 1.5 * inch
    grid_cols = len(grid_data[0]) if grid_data else 15
    cell_size = min(24, available_width / grid_cols)

    story = []

    story.append(Paragraph(title, title_style))
    if difficulty_label:
        story.append(Paragraph(f"Difficulty: {difficulty_label}", difficulty_style))
    story.append(Spacer(1, 6))

    grid_flowable = CrosswordGrid(grid_data, numbered_cells, cell_size=cell_size, show_answers=False)
    story.append(grid_flowable)
    story.append(Spacer(1, 16))

    if across_clues:
        story.append(Paragraph("Across", section_style))
        for number, clue_text in across_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

    if down_clues:
        story.append(Paragraph("Down", section_style))
        for number, clue_text in down_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", clue_style))

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


def _ws_cell_size(
    grid_rows: int,
    grid_cols: int,
    word_count: int,
    available_width: float,
    available_height: float,
    has_difficulty: bool = False,
) -> float:
    """Return the largest cell size (pts) that keeps a word-search page in bounds.

    Estimates the vertical space consumed by non-grid elements so the grid,
    title, difficulty line, and word list all fit on one page.
    """
    # Approximate heights (pts) of non-grid elements
    title_h    = 40   # title paragraph + spaceAfter
    diff_h     = 22 if has_difficulty else 0  # difficulty line
    spacers_h  = 18   # spacer before grid + spacer after grid
    heading_h  = 36   # "Find these words:" heading
    row_h      = 19   # one row in the word-list table (leading + cell padding)
    word_rows  = max(1, (word_count + 2) // 3)   # 3-column layout

    overhead = title_h + diff_h + spacers_h + heading_h + word_rows * row_h

    # Never shrink below 40 % of the page (sanity floor)
    max_grid_h = max(available_height - overhead, available_height * 0.40)

    cell_from_height = max_grid_h / max(grid_rows, 1)
    cell_from_width  = available_width / max(grid_cols, 1)

    return min(26.0, cell_from_width, cell_from_height)


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

DIRECTION_ANGLES = {
    "E": 0,   "W": 0,
    "N": 90,  "S": 90,
    "NE": 45, "SW": 45,
    "NW": 135, "SE": 135,
}

WORD_OVAL_COLOR = HexColor("#1D4ED8")


def _build_highlight_set(placements: list) -> set:
    highlighted = set()
    for p in placements:
        dr, dc = DIRECTION_VECTORS.get(p["direction"], (0, 0))
        for i in range(len(p["word"])):
            highlighted.add((p["row"] + dr * i, p["col"] + dc * i))
    return highlighted


class WordSearchGrid(Flowable):
    def __init__(
        self,
        grid: list,
        cell_size: float = 24,
        highlight_cells: Optional[set] = None,
        placements: Optional[list] = None,
    ):
        super().__init__()
        self.grid = grid
        self.cell_size = cell_size
        self.highlight_cells = highlight_cells or set()
        self.placements = placements or []
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

                if is_highlighted:
                    canvas.setFillColor(HIGHLIGHT_BG)
                else:
                    canvas.setFillColor(white)
                canvas.setStrokeColor(LIGHT_GRAY)
                canvas.setLineWidth(0.25)
                canvas.rect(x, y, cs, cs, fill=1, stroke=1)

                letter_text = self.grid[row][col] if row < len(self.grid) and col < len(self.grid[row]) else ""
                if letter_text:
                    if is_highlighted:
                        canvas.setFillColor(HIGHLIGHT_TEXT)
                        canvas.setFont("Helvetica-Bold", cs * 0.55)
                    else:
                        canvas.setFillColor(black)
                        canvas.setFont("Helvetica", cs * 0.55)
                    canvas.drawCentredString(x + cs / 2, y + cs * 0.22, letter_text.upper())

        if self.placements:
            self._draw_word_ovals(canvas)

    def _draw_word_ovals(self, canvas):
        cs = self.cell_size
        padding = cs * 0.3

        canvas.setStrokeColor(WORD_OVAL_COLOR)
        canvas.setLineWidth(1.5)

        for p in self.placements:
            dr, dc = DIRECTION_VECTORS.get(p["direction"], (0, 0))
            n = len(p["word"])
            r0, c0 = p["row"], p["col"]
            rl = r0 + dr * (n - 1)
            cl = c0 + dc * (n - 1)

            x0 = c0 * cs + cs / 2
            y0 = self.height - (r0 + 1) * cs + cs / 2
            xl = cl * cs + cs / 2
            yl = self.height - (rl + 1) * cs + cs / 2

            mid_x = (x0 + xl) / 2
            mid_y = (y0 + yl) / 2
            angle = DIRECTION_ANGLES.get(p["direction"], 0)

            span = math.sqrt((xl - x0) ** 2 + (yl - y0) ** 2)
            half_w = span / 2 + cs * 0.65
            half_h = (cs + padding) / 2

            canvas.saveState()
            canvas.translate(mid_x, mid_y)
            canvas.rotate(angle)
            canvas.ellipse(-half_w, -half_h, half_w, half_h, fill=0, stroke=1)
            canvas.restoreState()


def generate_word_search_pdf(
    title: str,
    grid: list,
    words: list,
    placements: Optional[list] = None,
    include_answer_key: bool = True,
    page_size: tuple = letter,
    difficulty_label: Optional[str] = None,
) -> bytes:
    """Generate a PDF for a single word search puzzle."""
    from reportlab.platypus import SimpleDocTemplate
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

    ws_difficulty_style = ParagraphStyle(
        "WSDifficulty",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=HexColor("#666666"),
    )

    available_width  = page_size[0] - 1.5 * inch
    available_height = page_size[1] - 1.0 * inch   # top + bottom margins
    grid_rows = len(grid)
    grid_cols = len(grid[0]) if grid else 15
    cell_size = _ws_cell_size(
        grid_rows, grid_cols, len(words),
        available_width, available_height,
        has_difficulty=bool(difficulty_label),
    )

    story = []

    story.append(Paragraph(title, title_style))
    if difficulty_label:
        story.append(Paragraph(f"Difficulty: {difficulty_label}", ws_difficulty_style))
    story.append(Spacer(1, 6))

    grid_flowable = WordSearchGrid(grid, cell_size=cell_size)
    story.append(grid_flowable)
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
        answer_grid = WordSearchGrid(
            grid, cell_size=cell_size, highlight_cells=highlight_set, placements=placements
        )
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
KDP_MARGIN_LR = 0.75 * inch


def _add_page_number(canvas, doc):
    """Draw a centred page number at the bottom of every content page."""
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


# Style names used to trigger TOC entries in afterFlowable
_TOC_STYLE_LEVELS = {
    "BookChapterHeading": 0,   # chapter title divider page
    "BookPuzzleTitleFlat": 0,  # puzzle in flat (no-chapter) mode
    "BookPuzzleTitleInCh": 1,  # puzzle within a chapter
    "BookAnswerKeyHeading": 0, # "Answer Key" section
}


class BookDocTemplate(BaseDocTemplate):
    """BaseDocTemplate subclass that feeds heading paragraphs into the TOC."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            level = _TOC_STYLE_LEVELS.get(style_name)
            if level is not None:
                text = flowable.getPlainText()
                self.notify("TOCEntry", (level, text, self.page))


def _make_book_styles(styles):
    """Return a dict of named ParagraphStyle objects for book PDFs."""
    return {
        "book_title": ParagraphStyle(
            "BookTitle", parent=styles["Title"],
            fontSize=32, alignment=TA_CENTER, spaceAfter=16,
        ),
        "book_subtitle": ParagraphStyle(
            "BookSubtitle", parent=styles["Heading2"],
            fontSize=18, alignment=TA_CENTER, spaceAfter=12, textColor=HexColor("#555555"),
        ),
        "book_author": ParagraphStyle(
            "BookAuthor", parent=styles["Normal"],
            fontSize=14, alignment=TA_CENTER, spaceAfter=6,
        ),
        "toc_heading": ParagraphStyle(
            "TOCHeading", parent=styles["Heading1"],
            fontSize=22, alignment=TA_CENTER, spaceAfter=24,
        ),
        "chapter_num_label": ParagraphStyle(
            "ChapterNumLabel", parent=styles["Normal"],
            fontSize=11, alignment=TA_CENTER, spaceAfter=6,
            textColor=HexColor("#777777"), fontName="Helvetica",
        ),
        "chapter_heading": ParagraphStyle(
            # Name must match _TOC_STYLE_LEVELS key
            "BookChapterHeading", parent=styles["Heading1"],
            fontSize=28, alignment=TA_CENTER, spaceAfter=16,
        ),
        "chapter_desc": ParagraphStyle(
            "ChapterDesc", parent=styles["Normal"],
            fontSize=13, alignment=TA_CENTER, spaceAfter=8,
            textColor=HexColor("#555555"), leading=20,
        ),
        "puzzle_title_flat": ParagraphStyle(
            "BookPuzzleTitleFlat", parent=styles["Heading1"],
            fontSize=20, alignment=TA_CENTER, spaceAfter=12,
        ),
        "puzzle_title_in_ch": ParagraphStyle(
            "BookPuzzleTitleInCh", parent=styles["Heading1"],
            fontSize=20, alignment=TA_CENTER, spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "BookSection", parent=styles["Heading2"],
            fontSize=14, spaceBefore=12, spaceAfter=6,
        ),
        "clue": ParagraphStyle(
            "BookClue", parent=styles["Normal"],
            fontSize=10, leading=13, leftIndent=18, firstLineIndent=-18,
        ),
        "word": ParagraphStyle(
            "BookWSWord", parent=styles["Normal"],
            fontSize=11, leading=15,
        ),
        "answer_key_heading": ParagraphStyle(
            "BookAnswerKeyHeading", parent=styles["Heading1"],
            fontSize=24, alignment=TA_CENTER, spaceAfter=20,
        ),
        "answer_puzzle_label": ParagraphStyle(
            "AnswerPuzzleLabel", parent=styles["Heading3"],
            fontSize=11, spaceBefore=10, spaceAfter=4, alignment=TA_CENTER,
        ),
        "answer_chapter_label": ParagraphStyle(
            "AnswerChapterLabel", parent=styles["Heading2"],
            fontSize=14, spaceBefore=16, spaceAfter=8, alignment=TA_CENTER,
            textColor=HexColor("#333333"),
        ),
        "puzzle_difficulty": ParagraphStyle(
            "BookPuzzleDifficulty", parent=styles["Normal"],
            fontSize=10, alignment=TA_CENTER, spaceAfter=6,
            textColor=HexColor("#666666"),
        ),
    }


def _add_crossword_puzzle(story, p: dict, st: dict, available_width: float, title_style_name: str):
    """Append crossword puzzle flowables to story. Returns the story (mutated)."""
    grid_data = p["grid_data"]
    word_placements = p.get("word_placements")
    numbered_cells = calculate_numbered_cells(grid_data)
    across_clues, down_clues = extract_clues(word_placements)

    grid_cols = len(grid_data[0]) if grid_data else 15
    cell_size = min(24, available_width / grid_cols)

    story.append(Paragraph(p["title"], st[title_style_name]))
    if p.get("difficulty_label"):
        story.append(Paragraph(f"Difficulty: {p['difficulty_label']}", st["puzzle_difficulty"]))
    story.append(Spacer(1, 6))
    story.append(CrosswordGrid(grid_data, numbered_cells, cell_size=cell_size, show_answers=False))
    story.append(Spacer(1, 16))

    if across_clues:
        story.append(Paragraph("Across", st["section"]))
        for number, clue_text in across_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", st["clue"]))

    if down_clues:
        story.append(Paragraph("Down", st["section"]))
        for number, clue_text in down_clues:
            story.append(Paragraph(f"<b>{number}.</b> {clue_text}", st["clue"]))

    story.append(PageBreak())


def _add_wordsearch_puzzle(story, p: dict, st: dict, available_width: float, title_style_name: str, available_height: float = 720.0):
    """Append word search puzzle flowables to story."""
    grid = p["grid"]
    words = p.get("words", [])

    grid_rows = len(grid)
    grid_cols = len(grid[0]) if grid else 15
    cell_size = _ws_cell_size(
        grid_rows, grid_cols, len(words),
        available_width, available_height,
        has_difficulty=bool(p.get("difficulty_label")),
    )

    story.append(Paragraph(p["title"], st[title_style_name]))
    if p.get("difficulty_label"):
        story.append(Paragraph(f"Difficulty: {p['difficulty_label']}", st["puzzle_difficulty"]))
    story.append(Spacer(1, 6))
    story.append(WordSearchGrid(grid, cell_size=cell_size))
    story.append(Spacer(1, 12))

    if words:
        story.append(Paragraph("Find these words:", st["section"]))
        sorted_words = sorted(words, key=str.upper)
        num_cols = 3
        rows_needed = (len(sorted_words) + num_cols - 1) // num_cols
        table_data = []
        for r in range(rows_needed):
            row_cells = []
            for c in range(num_cols):
                ws_idx = r + c * rows_needed
                if ws_idx < len(sorted_words):
                    row_cells.append(Paragraph(sorted_words[ws_idx].upper(), st["word"]))
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


def generate_book_pdf(
    title: str,
    subtitle: Optional[str],
    author: Optional[str],
    book_type: str,
    puzzles: list,
    chapters: Optional[list] = None,
) -> bytes:
    """Generate a multi-puzzle book PDF formatted for KDP (8.5 x 11).

    Pass ``chapters`` (list of {name, description, puzzles}) for chapter mode,
    or ``puzzles`` (flat list) for legacy mode.
    """
    buffer = io.BytesIO()
    page_w, page_h = KDP_PAGE_SIZE

    frame = Frame(
        KDP_MARGIN_LR, KDP_MARGIN_BOTTOM,
        page_w - 2 * KDP_MARGIN_LR,
        page_h - KDP_MARGIN_TOP - KDP_MARGIN_BOTTOM,
        id="main",
    )

    title_template = PageTemplate(id="title_page", frames=[frame], onPage=_no_page_number)
    content_template = PageTemplate(id="content", frames=[frame], onPage=_add_page_number)

    doc = BookDocTemplate(
        buffer,
        pagesize=KDP_PAGE_SIZE,
        topMargin=KDP_MARGIN_TOP,
        bottomMargin=KDP_MARGIN_BOTTOM,
        leftMargin=KDP_MARGIN_LR,
        rightMargin=KDP_MARGIN_LR,
    )
    doc.addPageTemplates([title_template, content_template])

    base_styles = getSampleStyleSheet()
    st = _make_book_styles(base_styles)

    available_width  = page_w - 2 * KDP_MARGIN_LR
    available_height = page_h - KDP_MARGIN_TOP - KDP_MARGIN_BOTTOM

    # Build Table of Contents flowable
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel0",
            parent=base_styles["Normal"],
            fontSize=12,
            leading=22,
            leftIndent=0,
            rightIndent=0,
            spaceBefore=2,
        ),
        ParagraphStyle(
            "TOCLevel1",
            parent=base_styles["Normal"],
            fontSize=10,
            leading=18,
            leftIndent=28,
            rightIndent=0,
            spaceBefore=0,
        ),
    ]

    story = []

    # ===================== TITLE PAGE =======================================
    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph(title, st["book_title"]))
    if subtitle:
        story.append(Paragraph(subtitle, st["book_subtitle"]))
    if author:
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(author, st["book_author"]))

    from reportlab.platypus.doctemplate import NextPageTemplate
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ===================== TABLE OF CONTENTS ================================
    story.append(Paragraph("Contents", st["toc_heading"]))
    story.append(toc)
    story.append(PageBreak())

    # ===================== PUZZLE PAGES =====================================
    use_chapters = bool(chapters)

    if use_chapters:
        for ch_idx, ch in enumerate(chapters, 1):
            # Chapter divider page
            story.append(Spacer(1, 2.0 * inch))
            story.append(Paragraph(f"Chapter {ch_idx}", st["chapter_num_label"]))
            story.append(Paragraph(ch["name"], st["chapter_heading"]))
            if ch.get("description"):
                story.append(Spacer(1, 0.25 * inch))
                story.append(Paragraph(ch["description"], st["chapter_desc"]))
            story.append(PageBreak())

            # Puzzles within the chapter
            for p in ch.get("puzzles", []):
                if book_type == "crossword":
                    _add_crossword_puzzle(story, p, st, available_width, "puzzle_title_in_ch")
                else:
                    _add_wordsearch_puzzle(story, p, st, available_width, "puzzle_title_in_ch", available_height)
    else:
        # Flat (legacy) mode
        for p in puzzles:
            if book_type == "crossword":
                _add_crossword_puzzle(story, p, st, available_width, "puzzle_title_flat")
            else:
                _add_wordsearch_puzzle(story, p, st, available_width, "puzzle_title_flat", available_height)

    # ===================== ANSWER KEY SECTION ===============================
    story.append(Paragraph("Answer Key", st["answer_key_heading"]))
    story.append(Spacer(1, 12))

    if use_chapters:
        for ch in chapters:
            if ch.get("name"):
                story.append(Paragraph(ch["name"], st["answer_chapter_label"]))
            for p in ch.get("puzzles", []):
                if book_type == "crossword":
                    grid_data = p["grid_data"]
                    numbered_cells = calculate_numbered_cells(grid_data)
                    grid_cols = len(grid_data[0]) if grid_data else 15
                    full_cell = min(24, available_width / grid_cols)
                    ans_cell = full_cell * 0.65
                    story.append(Paragraph(p["title"], st["answer_puzzle_label"]))
                    story.append(CrosswordGrid(grid_data, numbered_cells, cell_size=ans_cell, show_answers=True))
                    story.append(Spacer(1, 18))
                else:
                    grid = p["grid"]
                    placements = p.get("placements", [])
                    grid_cols = len(grid[0]) if grid else 15
                    full_cell = min(26, available_width / grid_cols)
                    ans_cell = full_cell * 0.65
                    highlight_set = _build_highlight_set(placements) if placements else set()
                    story.append(Paragraph(p["title"], st["answer_puzzle_label"]))
                    story.append(WordSearchGrid(
                        grid, cell_size=ans_cell, highlight_cells=highlight_set, placements=placements
                    ))
                    story.append(Spacer(1, 18))
    else:
        if book_type == "crossword":
            for p in puzzles:
                grid_data = p["grid_data"]
                numbered_cells = calculate_numbered_cells(grid_data)
                grid_cols = len(grid_data[0]) if grid_data else 15
                full_cell = min(24, available_width / grid_cols)
                ans_cell = full_cell * 0.65
                story.append(Paragraph(p["title"], st["answer_puzzle_label"]))
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
                story.append(Paragraph(p["title"], st["answer_puzzle_label"]))
                story.append(WordSearchGrid(
                    grid, cell_size=ans_cell, highlight_cells=highlight_set, placements=placements
                ))
                story.append(Spacer(1, 18))

    doc.multiBuild(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
