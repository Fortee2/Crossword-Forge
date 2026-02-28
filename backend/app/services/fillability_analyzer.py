"""
Fillability Analyzer Service

Analyzes word slots in a crossword grid to determine how many valid words
can fill each slot. Helps constructors identify difficult-to-fill areas.
"""

import re
from functools import lru_cache
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Answer


# Severity thresholds
SEVERITY_THRESHOLDS = {
    'good': 100,
    'okay': 20,
    'tight': 5,
    'danger': 0,
}


def get_severity(fill_count: int, is_complete: bool = False) -> str:
    """Determine severity level based on fill count.
    
    A complete word (no blanks) with at least 1 match is valid — mark as 'good'.
    A complete word with 0 matches means it's not in the dictionary — mark as 'danger'.
    """
    if is_complete:
        return 'good' if fill_count >= 1 else 'danger'
    if fill_count >= SEVERITY_THRESHOLDS['good']:
        return 'good'
    elif fill_count >= SEVERITY_THRESHOLDS['okay']:
        return 'okay'
    elif fill_count >= SEVERITY_THRESHOLDS['tight']:
        return 'tight'
    else:
        return 'danger'


# Cache for empty slot counts by length (only ~12 possible lengths)
_length_cache: dict[int, int] = {}


def get_count_by_length(db: Session, length: int) -> int:
    """
    Get the count of words with a specific length.
    Cached since there are only ~12 possible lengths (3-15).
    """
    if length in _length_cache:
        return _length_cache[length]

    count = db.query(func.count(Answer.id)).filter(Answer.length == length).scalar() or 0
    _length_cache[length] = count
    return count


def clear_length_cache():
    """Clear the length cache (useful for testing or after imports)."""
    global _length_cache
    _length_cache = {}


def count_matching_words(db: Session, pattern: str) -> int:
    """
    Count words matching a pattern with underscores as wildcards.

    For fully empty patterns (all underscores), uses cached length lookup.
    For patterns with letters, uses regex matching.
    """
    pattern_upper = pattern.upper().strip()
    length = len(pattern_upper)

    if length < 3:
        return 0

    # Check if pattern is all underscores (empty slot)
    if pattern_upper == '_' * length:
        return get_count_by_length(db, length)

    # Build regex for pattern matching
    regex_chars = []
    for char in pattern_upper:
        if char == '_':
            regex_chars.append('.')
        else:
            regex_chars.append(re.escape(char))
    regex_pattern = "^" + "".join(regex_chars) + "$"
    regex = re.compile(regex_pattern)

    # Query candidates by length and filter with regex
    candidates = db.query(Answer.word).filter(Answer.length == length).all()

    count = 0
    for (word,) in candidates:
        if regex.match(word):
            count += 1

    return count


def extract_slots_from_grid(grid: list[list[dict]]) -> list[dict]:
    """
    Extract all word slots from a grid.

    Returns a list of slot dictionaries with:
    - number: the clue number
    - direction: 'across' or 'down'
    - row, col: starting position
    - length: slot length
    - pattern: the current pattern (letters and underscores)
    """
    rows = len(grid)
    if rows == 0:
        return []
    cols = len(grid[0])

    slots = []
    current_number = 1
    number_map = {}  # Maps (row, col) to clue number

    # First pass: assign numbers to cells that start words
    for row in range(rows):
        for col in range(cols):
            cell = grid[row][col]
            if cell.get('isBlack', False):
                continue

            starts_across = (
                (col == 0 or grid[row][col - 1].get('isBlack', False)) and
                col < cols - 1 and
                not grid[row][col + 1].get('isBlack', False)
            )

            starts_down = (
                (row == 0 or grid[row - 1][col].get('isBlack', False)) and
                row < rows - 1 and
                not grid[row + 1][col].get('isBlack', False)
            )

            if starts_across or starts_down:
                number_map[(row, col)] = current_number
                current_number += 1

    # Second pass: extract across words
    for row in range(rows):
        col = 0
        while col < cols:
            if grid[row][col].get('isBlack', False):
                col += 1
                continue

            start_col = col
            pattern = ''
            while col < cols and not grid[row][col].get('isBlack', False):
                letter = grid[row][col].get('letter', '')
                pattern += letter.upper() if letter else '_'
                col += 1

            length = len(pattern)
            if length >= 3:  # Only include words of length 3+
                number = number_map.get((row, start_col))
                if number:
                    slots.append({
                        'number': number,
                        'direction': 'across',
                        'row': row,
                        'col': start_col,
                        'length': length,
                        'pattern': pattern,
                    })

    # Third pass: extract down words
    for col in range(cols):
        row = 0
        while row < rows:
            if grid[row][col].get('isBlack', False):
                row += 1
                continue

            start_row = row
            pattern = ''
            while row < rows and not grid[row][col].get('isBlack', False):
                letter = grid[row][col].get('letter', '')
                pattern += letter.upper() if letter else '_'
                row += 1

            length = len(pattern)
            if length >= 3:  # Only include words of length 3+
                number = number_map.get((start_row, col))
                if number:
                    slots.append({
                        'number': number,
                        'direction': 'down',
                        'row': start_row,
                        'col': col,
                        'length': length,
                        'pattern': pattern,
                    })

    return slots


def analyze_fillability(db: Session, grid_data: list[list[dict]]) -> dict:
    """
    Analyze the fillability of all slots in a grid.

    Returns:
        {
            "slots": [
                {
                    "number": 1,
                    "direction": "across",
                    "row": 0,
                    "col": 0,
                    "length": 5,
                    "fill_count": 12847,
                    "severity": "good"
                },
                ...
            ],
            "summary": {"good": 30, "okay": 5, "tight": 2, "danger": 1}
        }
    """
    slots = extract_slots_from_grid(grid_data)

    result_slots = []
    summary = {'good': 0, 'okay': 0, 'tight': 0, 'danger': 0}

    for slot in slots:
        fill_count = count_matching_words(db, slot['pattern'])
        is_complete = '_' not in slot['pattern']
        severity = get_severity(fill_count, is_complete=is_complete)

        result_slots.append({
            'number': slot['number'],
            'direction': slot['direction'],
            'row': slot['row'],
            'col': slot['col'],
            'length': slot['length'],
            'fill_count': fill_count,
            'severity': severity,
        })

        summary[severity] += 1

    return {
        'slots': result_slots,
        'summary': summary,
    }
