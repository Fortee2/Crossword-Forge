"""
Word Suggestion Service

Provides pattern-based word suggestions from the clue database.
Used by the grid editor to suggest words as letters are filled in.
Results are sorted by score (highest first).
"""

import re
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Answer, Clue


def get_word_suggestions(
    db: Session,
    pattern: str,
    limit: int = 20,
    source_filter: str | None = None,
    include_shorter: bool = False
) -> list[dict]:
    """
    Get word suggestions matching a pattern, sorted by score.

    Args:
        db: Database session
        pattern: Pattern with underscores for unknown letters (e.g., "P_A_O")
        limit: Maximum number of suggestions to return

    Returns:
        List of answer dictionaries with their clues, sorted by score descending
    """
    pattern_upper = pattern.upper().strip()
    length = len(pattern_upper)

    if length == 0:
        return []

    # Build SQL LIKE pattern (underscores already match single chars in LIKE)
    like_pattern = pattern_upper

    # Query answers matching length and pattern, ordered by score descending
    query = db.query(Answer).filter(Answer.length == length)
    
    # Only apply LIKE if there are known letters
    if '_' * length != pattern_upper:
        query = query.filter(Answer.word.like(like_pattern))
        
    if source_filter:
        query = query.filter(Answer.source.contains(source_filter))
        
    query = query.order_by(desc(Answer.score)).limit(limit)
    matching_answers = query.all()

    # Build response format
    matching = []
    for answer in matching_answers:
        matching.append({
            "id": answer.id,
            "word": answer.word,
            "display": answer.display or answer.word,
            "length": answer.length,
            "score": answer.score or 100,
            "source": answer.source or 'user',
            "is_phrase": answer.is_phrase or False,
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

    if include_shorter and length > 3:
        shorter_answers = []
        # Get top words for each shorter length down to 3
        for k in range(length - 1, 2, -1):
            short_pattern = pattern_upper[:k]
            q = db.query(Answer).filter(Answer.length == k)
            if '_' * k != short_pattern:
                q = q.filter(Answer.word.like(short_pattern))
            if source_filter:
                q = q.filter(Answer.source.contains(source_filter))
            q = q.order_by(desc(Answer.score)).limit(15)
            shorter_answers.extend(q.all())
            
        shorter_answers.sort(key=lambda x: -(x.score or 0))
        # Take the top `limit` shorter words overall
        for answer in shorter_answers[:limit]:
            matching.append({
                "id": answer.id,
                "word": answer.word,
                "display": answer.display or answer.word,
                "length": answer.length,
                "score": answer.score or 100,
                "source": answer.source or 'user',
                "is_phrase": answer.is_phrase or False,
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
