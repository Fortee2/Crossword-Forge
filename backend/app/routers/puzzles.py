from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Puzzle
from ..services.grid_validator import validate_grid
from ..services.word_suggester import get_word_suggestions, get_suggestions_for_slot
from ..services.fillability_analyzer import analyze_fillability
from ..services.crossing_analyzer import get_suggestions_with_crossings


router = APIRouter(prefix="/puzzles", tags=["puzzles"])


class GridCell(BaseModel):
    isBlack: bool = False
    letter: str = ""


class WordPlacement(BaseModel):
    word: str
    clue: Optional[str] = None
    row: int
    col: int
    direction: str
    number: int


class PuzzleCreate(BaseModel):
    title: str = "Untitled Puzzle"
    grid_data: List[List[dict]]
    word_placements: Optional[List[WordPlacement]] = None
    difficulty: Optional[int] = None
    status: str = "draft"
    theme: Optional[str] = None
    notes: Optional[str] = None


class PuzzleUpdate(BaseModel):
    title: Optional[str] = None
    grid_data: Optional[List[List[dict]]] = None
    word_placements: Optional[List[WordPlacement]] = None
    difficulty: Optional[int] = None
    status: Optional[str] = None
    theme: Optional[str] = None
    notes: Optional[str] = None


class PuzzleResponse(BaseModel):
    id: int
    title: str
    grid_data: List[List[dict]]
    word_placements: Optional[List[dict]] = None
    difficulty: Optional[int] = None
    status: str
    theme: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationRequest(BaseModel):
    grid_data: List[List[dict]]
    symmetry_enabled: bool = True


class ValidationResponse(BaseModel):
    valid: bool
    warnings: List[dict]


@router.post("", response_model=PuzzleResponse)
def create_puzzle(puzzle: PuzzleCreate, db: Session = Depends(get_db)):
    db_puzzle = Puzzle(
        title=puzzle.title,
        grid_data=puzzle.grid_data,
        word_placements=[wp.model_dump() for wp in puzzle.word_placements] if puzzle.word_placements else None,
        difficulty=puzzle.difficulty,
        status=puzzle.status,
        theme=puzzle.theme,
        notes=puzzle.notes
    )
    db.add(db_puzzle)
    db.commit()
    db.refresh(db_puzzle)
    return db_puzzle


@router.get("", response_model=List[PuzzleResponse])
def list_puzzles(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Puzzle)
    if status:
        query = query.filter(Puzzle.status == status)
    return query.order_by(Puzzle.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/{puzzle_id}", response_model=PuzzleResponse)
def get_puzzle(puzzle_id: int, db: Session = Depends(get_db)):
    puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return puzzle


@router.put("/{puzzle_id}", response_model=PuzzleResponse)
def update_puzzle(puzzle_id: int, puzzle_update: PuzzleUpdate, db: Session = Depends(get_db)):
    puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    update_data = puzzle_update.model_dump(exclude_unset=True)
    if "word_placements" in update_data and update_data["word_placements"]:
        update_data["word_placements"] = [wp.model_dump() if hasattr(wp, 'model_dump') else wp for wp in update_data["word_placements"]]

    for key, value in update_data.items():
        setattr(puzzle, key, value)

    db.commit()
    db.refresh(puzzle)
    return puzzle


@router.delete("/{puzzle_id}")
def delete_puzzle(puzzle_id: int, db: Session = Depends(get_db)):
    puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    db.delete(puzzle)
    db.commit()
    return {"message": "Puzzle deleted successfully"}


@router.post("/validate", response_model=ValidationResponse)
def validate_puzzle_grid(request: ValidationRequest):
    result = validate_grid(request.grid_data, request.symmetry_enabled)
    return result


class FillabilityRequest(BaseModel):
    grid_data: List[List[dict]]


class SlotFillability(BaseModel):
    number: int
    direction: str
    row: int
    col: int
    length: int
    fill_count: int
    severity: str


class FillabilitySummary(BaseModel):
    good: int
    okay: int
    tight: int
    danger: int


class FillabilityResponse(BaseModel):
    slots: List[SlotFillability]
    summary: FillabilitySummary


@router.post("/fillability", response_model=FillabilityResponse)
def analyze_grid_fillability(request: FillabilityRequest, db: Session = Depends(get_db)):
    """
    Analyze fillability of all word slots in a grid.

    For each slot (across and down), counts how many words in the database
    can fill that slot based on its length and any filled letters.

    Severity levels:
    - good: 100+ matching words
    - okay: 20-99 matching words
    - tight: 5-19 matching words
    - danger: 0-4 matching words
    """
    result = analyze_fillability(db, request.grid_data)
    return result


class SuggestionRequest(BaseModel):
    pattern: Optional[str] = None
    grid_data: Optional[List[List[dict]]] = None
    row: Optional[int] = None
    col: Optional[int] = None
    direction: Optional[str] = None
    limit: int = 20


class ClueInfo(BaseModel):
    id: int
    clue_text: str
    difficulty: int
    tags: Optional[str] = None


class SuggestionResponse(BaseModel):
    id: int
    word: str
    length: int
    clues: List[ClueInfo]


@router.post("/suggestions", response_model=List[SuggestionResponse])
def get_suggestions(request: SuggestionRequest, db: Session = Depends(get_db)):
    """
    Get word suggestions for filling in a puzzle slot.

    Either provide:
    - pattern: A pattern like "P_A_O" with underscores for unknowns
    - OR grid_data + row + col + direction: Extract pattern from grid
    """
    if request.pattern:
        suggestions = get_word_suggestions(db, request.pattern, request.limit)
    elif request.grid_data and request.row is not None and request.col is not None and request.direction:
        suggestions = get_suggestions_for_slot(
            db, request.grid_data, request.row, request.col, request.direction, request.limit
        )
    else:
        return []

    return suggestions


class CrossingSuggestionRequest(BaseModel):
    grid_data: List[List[dict]]
    row: int
    col: int
    direction: str
    limit: int = 30


class CrossingDetail(BaseModel):
    position: int
    direction: str
    length: int
    fill_count: int


class CrossingSuggestion(BaseModel):
    id: int
    word: str
    display: Optional[str] = None
    length: int
    score: Optional[int] = None
    source: Optional[str] = None
    is_phrase: Optional[bool] = None
    clues: List[ClueInfo]
    crossing_score: int
    crossing_details: List[CrossingDetail]


class CrossingSuggestionResponse(BaseModel):
    suggestions: List[CrossingSuggestion]


@router.post("/suggestions-with-crossings", response_model=CrossingSuggestionResponse)
def get_suggestions_with_crossing_analysis(
    request: CrossingSuggestionRequest,
    db: Session = Depends(get_db)
):
    """
    Get word suggestions with crossing analysis.

    For each suggestion, calculates how many valid crossing words can be formed
    at each intersection. The crossing_score is the MINIMUM fill count across
    all crossings (bottleneck metric - the weakest crossing determines viability).

    Suggestions are sorted by crossing_score descending (most fillable first),
    with word score as tiebreaker.
    """
    suggestions = get_suggestions_with_crossings(
        db,
        request.grid_data,
        request.row,
        request.col,
        request.direction,
        request.limit
    )

    return {"suggestions": suggestions}
