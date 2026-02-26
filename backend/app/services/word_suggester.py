"""
Word Suggestion Service

Provides pattern-based word suggestions from the clue database.
Used by the grid editor to suggest words as letters are filled in.
"""

import re
from sqlalchemy.orm import Session
from ..models import Answer, Clue


def get_word_suggestions(
    db: Session,
    pattern: str,
    limit: int = 20
) -> list[dict]:
    """
    Get word suggestions matching a pattern.

    Args:
        db: Database session
        pattern: Pattern with underscores for unknown letters (e.g., "P_A_O")
        limit: Maximum number of suggestions to return

    Returns:
        List of answer dictionaries with their clues
    """
    pattern_upper = pattern.upper().strip()
    length = len(pattern_upper)

    if length == 0:
        return []

    # Query answers of matching length
    query = db.query(Answer).filter(Answer.length == length)
    candidates = query.all()

    # Build regex for pattern matching
    # Escape special regex characters except underscores (which become .)
    regex_chars = []
    for char in pattern_upper:
        if char == '_':
            regex_chars.append('.')
        else:
            regex_chars.append(re.escape(char))
    regex_pattern = "^" + "".join(regex_chars) + "$"
    regex = re.compile(regex_pattern)

    # Filter candidates
    matching = []
    for answer in candidates:
        if regex.match(answer.word):
            matching.append({
                "id": answer.id,
                "word": answer.word,
                "length": answer.length,
                "clues": [
                    {
                        "id": c.id,
                        "clue_text": c.clue_text,
                        "difficulty": c.difficulty,
                        "tags": c.tags
                    }
                    for c in answer.clues
                ]
            })

            if len(matching) >= limit:
                break

    return matching


def get_suggestions_for_slot(
    db: Session,
    grid: list[list[dict]],
    row: int,
    col: int,
    direction: str,
    limit: int = 20
) -> list[dict]:
    """
    Get word suggestions for a specific slot in the grid.

    Args:
        db: Database session
        grid: 2D grid of cells with 'isBlack' and 'letter' properties
        row: Starting row of the slot
        col: Starting column of the slot
        direction: 'across' or 'down'
        limit: Maximum number of suggestions

    Returns:
        List of matching words with their clues
    """
    # Extract the pattern from the grid
    pattern = ""
    r, c = row, col

    if direction == "across":
        while c < len(grid[0]) and not grid[r][c].get("isBlack", False):
            letter = grid[r][c].get("letter", "")
            pattern += letter if letter else "_"
            c += 1
    else:  # down
        while r < len(grid) and not grid[r][c].get("isBlack", False):
            letter = grid[r][c].get("letter", "")
            pattern += letter if letter else "_"
            r += 1

    if not pattern or len(pattern) < 3:
        return []

    return get_word_suggestions(db, pattern, limit)
