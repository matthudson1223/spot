"""
PDF generator for crossword puzzles

Creates professional PDF output with:
- Page 1: Empty grid for solving
- Page 2: Clues
- Page 3: Solution grid (optional)
"""
from typing import Dict, List, Optional
from pathlib import Path
import logging

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generates PDF crossword puzzles"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='PuzzleTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        self.styles.add(ParagraphStyle(
            name='PuzzleSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='ClueNumber',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='ClueText',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20
        ))

    def generate_pdf(
        self,
        puzzle_data: Dict,
        output_path: str,
        include_solution: bool = True
    ) -> None:
        """
        Generate complete crossword PDF

        Args:
            puzzle_data: Puzzle dictionary
            output_path: Output PDF file path
            include_solution: Whether to include solution page
        """
        logger.info(f"Generating PDF: {output_path}")

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Build content
        story = []

        # Page 1: Title and empty grid
        story.extend(self._create_title_page(puzzle_data))
        story.append(Spacer(1, 0.3*inch))
        story.append(self._create_grid_table(puzzle_data, show_solution=False))

        # Page 2: Clues
        story.append(PageBreak())
        story.extend(self._create_clues_page(puzzle_data))

        # Page 3: Solution (optional)
        if include_solution:
            story.append(PageBreak())
            story.append(Paragraph("SOLUTION", self.styles['PuzzleTitle']))
            story.append(Spacer(1, 0.2*inch))
            story.append(self._create_grid_table(puzzle_data, show_solution=True))

        # Build PDF
        doc.build(story)
        logger.info(f"PDF generated: {output_path}")

    def _create_title_page(self, puzzle_data: Dict) -> List:
        """Create title and metadata"""
        elements = []

        # Title
        title = f"Crossword Puzzle"
        elements.append(Paragraph(title, self.styles['PuzzleTitle']))

        # Metadata
        theme = puzzle_data.get('theme', 'General')
        difficulty = puzzle_data.get('day_of_week', puzzle_data.get('difficulty', 'Wednesday'))
        size = puzzle_data.get('size', [15, 15])

        subtitle = f"Theme: {theme} | Difficulty: {difficulty} | Size: {size[0]}x{size[1]}"
        elements.append(Paragraph(subtitle, self.styles['PuzzleSubtitle']))

        return elements

    def _create_grid_table(
        self,
        puzzle_data: Dict,
        show_solution: bool = False
    ) -> Table:
        """Create crossword grid as a table"""
        grid_layout = puzzle_data.get('grid', {}).get('layout', [])
        grid_numbers = puzzle_data.get('grid', {}).get('numbers', [])

        if not grid_layout:
            return Table([["No grid data"]])

        n = len(grid_layout)
        m = len(grid_layout[0]) if n > 0 else 0

        # Create solution grid if needed
        solution_grid = None
        if show_solution:
            solution_grid = self._create_solution_grid(puzzle_data)

        # Build table data
        table_data = []
        for i in range(n):
            row = []
            for j in range(m):
                if grid_layout[i][j] == 0:  # Black square
                    row.append("")
                else:  # White square
                    cell_text = ""
                    if grid_numbers[i][j] > 0:
                        cell_text = str(grid_numbers[i][j])

                    if show_solution and solution_grid:
                        letter = solution_grid[i][j]
                        if cell_text:
                            cell_text += f"\n{letter}"
                        else:
                            cell_text = letter

                    row.append(cell_text)
            table_data.append(row)

        # Calculate cell size based on grid size
        # Fit grid to ~6 inches
        cell_size = min(6.0 * inch / max(n, m), 0.5 * inch)

        # Create table
        table = Table(
            table_data,
            colWidths=[cell_size] * m,
            rowHeights=[cell_size] * n
        )

        # Style the table
        style_commands = [
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]

        # Fill black squares
        for i in range(n):
            for j in range(m):
                if grid_layout[i][j] == 0:
                    style_commands.append(
                        ('BACKGROUND', (j, i), (j, i), colors.black)
                    )

        table.setStyle(TableStyle(style_commands))

        return table

    def _create_solution_grid(self, puzzle_data: Dict) -> List[List[str]]:
        """Create grid filled with solution letters"""
        grid_layout = puzzle_data.get('grid', {}).get('layout', [])
        n = len(grid_layout)
        if n == 0:
            return []
        m = len(grid_layout[0])

        # Initialize empty grid
        solution = [["" for _ in range(m)] for _ in range(n)]

        # Fill in across answers
        for answer_info in puzzle_data.get('answers', {}).get('across', []):
            answer = answer_info.get('answer', '')
            start_pos = answer_info.get('start_pos', [0, 0])
            i, j = start_pos

            for k, letter in enumerate(answer):
                if j + k < m:
                    solution[i][j + k] = letter

        # Fill in down answers
        for answer_info in puzzle_data.get('answers', {}).get('down', []):
            answer = answer_info.get('answer', '')
            start_pos = answer_info.get('start_pos', [0, 0])
            i, j = start_pos

            for k, letter in enumerate(answer):
                if i + k < n:
                    solution[i + k][j] = letter

        return solution

    def _create_clues_page(self, puzzle_data: Dict) -> List:
        """Create clues page"""
        elements = []

        clues = puzzle_data.get('clues', {})

        # Across clues
        elements.append(Paragraph("ACROSS", self.styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))

        across_clues = clues.get('across', {})
        for number in sorted([int(n) for n in across_clues.keys()]):
            clue_text = across_clues[str(number)]
            clue_para = Paragraph(
                f"<b>{number}.</b> {clue_text}",
                self.styles['Normal']
            )
            elements.append(clue_para)
            elements.append(Spacer(1, 0.05*inch))

        elements.append(Spacer(1, 0.2*inch))

        # Down clues
        elements.append(Paragraph("DOWN", self.styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))

        down_clues = clues.get('down', {})
        for number in sorted([int(n) for n in down_clues.keys()]):
            clue_text = down_clues[str(number)]
            clue_para = Paragraph(
                f"<b>{number}.</b> {clue_text}",
                self.styles['Normal']
            )
            elements.append(clue_para)
            elements.append(Spacer(1, 0.05*inch))

        return elements


def main():
    """Test PDF generator"""
    import sys
    from utils import load_jsonl

    if len(sys.argv) < 2:
        print("Usage: python pdf_generator.py <puzzle_file.jsonl> [output.pdf]")
        sys.exit(1)

    # Load puzzle
    puzzles = load_jsonl(sys.argv[1])
    if not puzzles:
        print(f"No puzzles found in {sys.argv[1]}")
        sys.exit(1)

    # Output path
    output_path = sys.argv[2] if len(sys.argv) > 2 else "puzzle.pdf"

    # Generate PDF
    generator = PDFGenerator()
    generator.generate_pdf(puzzles[0], output_path, include_solution=True)

    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    main()
