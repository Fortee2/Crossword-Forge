"""
Crossing Analyzer Service

Analyzes crossing word options for word suggestions. For each suggested word,
calculates how many valid crossing words can be formed at each intersection.
Uses the minimum crossing count as the "bottleneck" metric - a word is only
as fillable as its hardest crossing.
"""

import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Answer
from .word_suggester import get_word_suggestions
from .fillability_analyzer import count_matching_words


# In-memory index: {(length, position, letter): count}
# This tells us how many words of a given length have a specific letter at a position
_crossing_index: dict[tuple[int, int, str], int] = {}
_index_built = False


def build_crossing_index(db: Session) -> None:
    """
    Build an in-memory index for fast crossing lookups.

    Index structure: {(length, position, letter): count}
    For each word length, position, and letter, stores how many words match.
    """
    global _crossing_index, _index_built

    if _index_built:
        return

    _crossing_index = {}

    # Query all words grouped by length
    words = db.query(Answer.word, Answer.length).all()

    for word, length in words:
        if length < 3:
            continue
        for pos, letter in enumerate(word):
            key = (length, pos, letter)
            _crossing_index[key] = _crossing_index.get(key, 0) + 1

    _index_built = True


def clear_crossing_index() -> None:
    """Clear the crossing index (useful for testing or after imports)."""
    global _crossing_index, _index_built
    _crossing_index = {}
    _index_built = False


def get_crossing_count_fast(length: int, position: int, letter: str) -> int:
    """
    Fast lookup: how many words of given length have the specified letter at position?

    This is used when the crossing pattern is all underscores except one letter.
    """
    key = (length, position, letter.upper())
    return _crossing_index.get(key, 0)


def find_crossing_slot(
    grid: list[list[dict]],
    row: int,
    col: int,
    slot_direction: str
) -> dict | None:
    """
    Find the crossing slot at a given position.

    If slot_direction is 'across', find the 'down' slot crossing this cell.
    If slot_direction is 'down', find the 'across' slot crossing this cell.

    Returns dict with: row, col, length, position_in_slot (index where intersection occurs)
    or None if no valid crossing exists (e.g., at grid edge or single-cell word).
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    crossing_direction = 'down' if slot_direction == 'across' else 'across'

    if crossing_direction == 'down':
        # Find the down word at this column
        # Go up to find start of word
        start_row = row
        while start_row > 0 and not grid[start_row - 1][col].get('isBlack', False):
            start_row -= 1

        # Go down to find end of word
        end_row = row
        while end_row < rows - 1 and not grid[end_row + 1][col].get('isBlack', False):
            end_row += 1

        length = end_row - start_row + 1
        if length < 3:  # Skip short words
            return None

        position_in_slot = row - start_row

        return {
            'row': start_row,
            'col': col,
            'length': length,
            'position_in_slot': position_in_slot,
            'direction': 'down'
        }
    else:  # across
        # Find the across word at this row
        # Go left to find start of word
        start_col = col
        while start_col > 0 and not grid[row][start_col - 1].get('isBlack', False):
            start_col -= 1

        # Go right to find end of word
        end_col = col
        while end_col < cols - 1 and not grid[row][end_col + 1].get('isBlack', False):
            end_col += 1

        length = end_col - start_col + 1
        if length < 3:  # Skip short words
            return None

        position_in_slot = col - start_col

        return {
            'row': row,
            'col': start_col,
            'length': length,
            'position_in_slot': position_in_slot,
            'direction': 'across'
        }


def build_crossing_pattern(
    grid: list[list[dict]],
    crossing_slot: dict,
    new_letter: str
) -> str:
    """
    Build the pattern for a crossing slot, including the new letter from a suggestion.

    Args:
        grid: The current grid
        crossing_slot: Dict with row, col, length, position_in_slot, direction
        new_letter: The letter to place at the intersection position

    Returns:
        Pattern string with letters and underscores
    """
    pattern = []
    row = crossing_slot['row']
    col = crossing_slot['col']
    length = crossing_slot['length']
    position_in_slot = crossing_slot['position_in_slot']
    direction = crossing_slot['direction']

    for i in range(length):
        if direction == 'down':
            cell = grid[row + i][col]
        else:  # across
            cell = grid[row][col + i]

        if i == position_in_slot:
            # This is where our suggested letter goes
            pattern.append(new_letter.upper())
        else:
            letter = cell.get('letter', '')
            pattern.append(letter.upper() if letter else '_')

    return ''.join(pattern)


def count_crossing_options(
    db: Session,
    grid: list[list[dict]],
    crossing_slot: dict,
    new_letter: str
) -> int:
    """
    Count how many valid words can fill a crossing slot after placing a letter.

    Uses the fast index when the crossing pattern is all underscores except the
    intersection letter (common case). Falls back to regex for partial patterns.
    """
    pattern = build_crossing_pattern(grid, crossing_slot, new_letter)

    # Check if we can use the fast path
    # Fast path: pattern is all underscores except for one letter at the intersection
    non_underscore_positions = [(i, c) for i, c in enumerate(pattern) if c != '_']

    if len(non_underscore_positions) == 1:
        # Fast path: only the intersection letter is set
        pos, letter = non_underscore_positions[0]
        return get_crossing_count_fast(len(pattern), pos, letter)

    # Slow path: use regex matching
    return count_matching_words(db, pattern)


def analyze_crossings_for_word(
    db: Session,
    grid: list[list[dict]],
    word: str,
    slot_row: int,
    slot_col: int,
    slot_direction: str
) -> tuple[int, list[dict]]:
    """
    Analyze all crossings for a word placed in a slot.

    Args:
        db: Database session
        grid: Current grid state
        word: The word to analyze
        slot_row, slot_col: Starting position of the slot
        slot_direction: 'across' or 'down'

    Returns:
        (crossing_score, crossing_details)
        crossing_score is the MINIMUM fill count across all crossings (bottleneck)
        crossing_details is a list of dicts with position, direction, length, fill_count
    """
    crossing_details = []
    min_fill_count = float('inf')

    for i, letter in enumerate(word):
        if slot_direction == 'across':
            cell_row = slot_row
            cell_col = slot_col + i
        else:  # down
            cell_row = slot_row + i
            cell_col = slot_col

        # Check bounds
        if cell_row >= len(grid) or cell_col >= len(grid[0]):
            continue

        # Find the crossing slot at this position
        crossing_slot = find_crossing_slot(grid, cell_row, cell_col, slot_direction)

        if crossing_slot is None:
            # No valid crossing at this position (edge or short word)
            continue

        # Check if crossing is already fully filled (no blanks except intersection)
        crossing_pattern = build_crossing_pattern(grid, crossing_slot, letter)
        unfilled_count = crossing_pattern.count('_')

        if unfilled_count == 0:
            # Crossing is fully filled after placing our letter
            # Still check if it's a valid word
            fill_count = count_matching_words(db, crossing_pattern)
        else:
            # Count how many words can fill this crossing
            fill_count = count_crossing_options(db, grid, crossing_slot, letter)

        crossing_details.append({
            'position': i,
            'direction': crossing_slot['direction'],
            'length': crossing_slot['length'],
            'fill_count': fill_count
        })

        if fill_count < min_fill_count:
            min_fill_count = fill_count

    # If no crossings were analyzed, return high score (unconstrained)
    if min_fill_count == float('inf'):
        min_fill_count = 99999

    return int(min_fill_count), crossing_details


def get_suggestions_with_crossings(
    db: Session,
    grid: list[list[dict]],
    row: int,
    col: int,
    direction: str,
    limit: int = 30
) -> list[dict]:
    """
    Get word suggestions for a slot with crossing analysis.

    Algorithm:
    1. Get top suggestions sorted by word score
    2. For each suggestion, analyze crossing options
    3. Sort by crossing_score descending (most fillable first), word score as tiebreaker

    Returns:
        List of suggestions with crossing_score and crossing_details fields added
    """
    # Ensure index is built
    build_crossing_index(db)

    # Get basic suggestions (sorted by word score)
    suggestions = get_word_suggestions(db, _extract_pattern(grid, row, col, direction), limit)

    if not suggestions:
        return []

    # Analyze crossings for each suggestion
    results = []
    for suggestion in suggestions:
        crossing_score, crossing_details = analyze_crossings_for_word(
            db, grid, suggestion['word'], row, col, direction
        )

        results.append({
            **suggestion,
            'crossing_score': crossing_score,
            'crossing_details': crossing_details
        })

    # Sort by crossing_score descending, then by word score descending
    results.sort(key=lambda x: (-x['crossing_score'], -(x.get('score', 0) or 0)))

    return results


def _extract_pattern(grid: list[list[dict]], row: int, col: int, direction: str) -> str:
    """Extract the pattern from a grid slot."""
    pattern = []
    r, c = row, col

    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    if direction == 'across':
        while c < cols and not grid[r][c].get('isBlack', False):
            letter = grid[r][c].get('letter', '')
            pattern.append(letter.upper() if letter else '_')
            c += 1
    else:  # down
        while r < rows and not grid[r][c].get('isBlack', False):
            letter = grid[r][c].get('letter', '')
            pattern.append(letter.upper() if letter else '_')
            r += 1

    return ''.join(pattern)
