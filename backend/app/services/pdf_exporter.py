import io
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white, HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


LIGHT_GRAY = HexColor("#CCCCCC")


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
        story.append(Spacer(1, 0))  # Force page break via KeepTogether logic
        from reportlab.platypus import PageBreak
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
