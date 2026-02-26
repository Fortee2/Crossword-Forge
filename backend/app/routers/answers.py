from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional
import csv
import io
import re

from ..database import get_db
from ..models import Answer, Clue

router = APIRouter(prefix="/answers", tags=["answers"])


# Pydantic models for request/response
class ClueCreate(BaseModel):
    clue_text: str
    difficulty: int = 3
    tags: Optional[str] = None


class ClueUpdate(BaseModel):
    clue_text: Optional[str] = None
    difficulty: Optional[int] = None
    tags: Optional[str] = None


class ClueResponse(BaseModel):
    id: int
    answer_id: int
    clue_text: str
    difficulty: int
    tags: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class AnswerCreate(BaseModel):
    word: str
    clues: Optional[list[ClueCreate]] = None


class AnswerUpdate(BaseModel):
    word: Optional[str] = None


class AnswerResponse(BaseModel):
    id: int
    word: str
    length: int
    created_at: str
    clues: list[ClueResponse]

    class Config:
        from_attributes = True


class AnswerListResponse(BaseModel):
    id: int
    word: str
    length: int
    created_at: str
    clue_count: int

    class Config:
        from_attributes = True


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# Helper function to convert pattern with underscores to SQL LIKE pattern
def pattern_to_sql_like(pattern: str) -> str:
    """Convert pattern like P_A_O to SQL LIKE pattern P%A%O"""
    # Each underscore represents exactly one character
    return pattern.replace("_", "_")  # SQL LIKE uses _ for single char


def pattern_to_regex(pattern: str) -> str:
    """Convert pattern like P_A_O to regex P.A.O"""
    # Replace underscores with a placeholder, then escape, then replace back
    result = ""
    for char in pattern:
        if char == '_':
            result += "."
        else:
            result += re.escape(char)
    return "^" + result + "$"


# CRUD endpoints for answers
@router.post("", response_model=AnswerResponse)
def create_answer(answer: AnswerCreate, db: Session = Depends(get_db)):
    """Create a new answer with optional clues."""
    word = answer.word.upper().strip()

    if not word or not word.isalpha():
        raise HTTPException(status_code=400, detail="Word must contain only letters")

    existing = db.query(Answer).filter(Answer.word == word).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Answer '{word}' already exists")

    db_answer = Answer(word=word, length=len(word))
    db.add(db_answer)
    db.flush()  # Get the ID

    if answer.clues:
        for clue_data in answer.clues:
            db_clue = Clue(
                answer_id=db_answer.id,
                clue_text=clue_data.clue_text,
                difficulty=clue_data.difficulty,
                tags=clue_data.tags
            )
            db.add(db_clue)

    db.commit()
    db.refresh(db_answer)

    return _answer_to_response(db_answer)


@router.get("", response_model=list[AnswerListResponse])
def list_answers(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all answers with optional filtering."""
    query = db.query(Answer)

    if q:
        query = query.filter(Answer.word.contains(q.upper()))

    if min_length:
        query = query.filter(Answer.length >= min_length)

    if max_length:
        query = query.filter(Answer.length <= max_length)

    if tag:
        # Filter by answers that have clues with the given tag
        query = query.join(Clue).filter(Clue.tags.contains(tag))
        query = query.distinct()

    answers = query.order_by(Answer.word).offset(skip).limit(limit).all()

    return [
        AnswerListResponse(
            id=a.id,
            word=a.word,
            length=a.length,
            created_at=a.created_at.isoformat() if a.created_at else "",
            clue_count=len(a.clues)
        )
        for a in answers
    ]


@router.get("/search", response_model=list[AnswerResponse])
def search_answers(
    pattern: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Search answers by pattern or text.

    - pattern: Use underscores as wildcards (e.g., P_A_O matches PIANO, PLANO)
    - q: Text search in word
    """
    query = db.query(Answer)

    if pattern:
        pattern_upper = pattern.upper().strip()
        # Filter by length first for efficiency
        query = query.filter(Answer.length == len(pattern_upper))

        # Get candidates and filter with regex for exact pattern matching
        regex = pattern_to_regex(pattern_upper)
        answers = query.all()
        matching = [a for a in answers if re.match(regex, a.word)]
        matching = matching[:limit]
    elif q:
        query = query.filter(Answer.word.contains(q.upper()))
        matching = query.limit(limit).all()
    else:
        matching = query.limit(limit).all()

    return [_answer_to_response(a) for a in matching]


@router.get("/{answer_id}", response_model=AnswerResponse)
def get_answer(answer_id: int, db: Session = Depends(get_db)):
    """Get a specific answer by ID."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    return _answer_to_response(answer)


@router.put("/{answer_id}", response_model=AnswerResponse)
def update_answer(answer_id: int, update: AnswerUpdate, db: Session = Depends(get_db)):
    """Update an answer."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    if update.word:
        word = update.word.upper().strip()
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")

        existing = db.query(Answer).filter(Answer.word == word, Answer.id != answer_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Answer '{word}' already exists")

        answer.word = word
        answer.length = len(word)

    db.commit()
    db.refresh(answer)
    return _answer_to_response(answer)


@router.delete("/{answer_id}")
def delete_answer(answer_id: int, db: Session = Depends(get_db)):
    """Delete an answer and all its clues."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    db.delete(answer)
    db.commit()
    return {"message": "Answer deleted successfully"}


# CRUD endpoints for clues (nested under answers)
@router.post("/{answer_id}/clues", response_model=ClueResponse)
def create_clue(answer_id: int, clue: ClueCreate, db: Session = Depends(get_db)):
    """Add a clue to an answer."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    db_clue = Clue(
        answer_id=answer_id,
        clue_text=clue.clue_text,
        difficulty=clue.difficulty,
        tags=clue.tags
    )
    db.add(db_clue)
    db.commit()
    db.refresh(db_clue)

    return _clue_to_response(db_clue)


@router.get("/{answer_id}/clues", response_model=list[ClueResponse])
def list_clues(answer_id: int, db: Session = Depends(get_db)):
    """List all clues for an answer."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    return [_clue_to_response(c) for c in answer.clues]


@router.put("/{answer_id}/clues/{clue_id}", response_model=ClueResponse)
def update_clue(
    answer_id: int,
    clue_id: int,
    update: ClueUpdate,
    db: Session = Depends(get_db)
):
    """Update a clue."""
    clue = db.query(Clue).filter(
        Clue.id == clue_id,
        Clue.answer_id == answer_id
    ).first()

    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")

    if update.clue_text is not None:
        clue.clue_text = update.clue_text
    if update.difficulty is not None:
        clue.difficulty = update.difficulty
    if update.tags is not None:
        clue.tags = update.tags

    db.commit()
    db.refresh(clue)
    return _clue_to_response(clue)


@router.delete("/{answer_id}/clues/{clue_id}")
def delete_clue(answer_id: int, clue_id: int, db: Session = Depends(get_db)):
    """Delete a clue."""
    clue = db.query(Clue).filter(
        Clue.id == clue_id,
        Clue.answer_id == answer_id
    ).first()

    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")

    db.delete(clue)
    db.commit()
    return {"message": "Clue deleted successfully"}


# Bulk import endpoint
@router.post("/import", response_model=ImportResult)
async def import_answers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Bulk import answers and clues from a CSV file.

    Expected CSV format:
    word,clue,difficulty,tags

    - word: required
    - clue: optional
    - difficulty: optional (1-5, defaults to 3)
    - tags: optional (comma-separated within quotes)
    """
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="File must be CSV or TXT format")

    content = await file.read()
    text = content.decode('utf-8')

    imported = 0
    skipped = 0
    errors = []

    # Try to parse as CSV
    reader = csv.reader(io.StringIO(text))

    for row_num, row in enumerate(reader, start=1):
        if not row or not row[0].strip():
            continue

        # Skip header row if present
        if row_num == 1 and row[0].lower() in ('word', 'answer'):
            continue

        try:
            word = row[0].upper().strip()

            if not word.isalpha():
                errors.append(f"Row {row_num}: Invalid word '{row[0]}'")
                skipped += 1
                continue

            # Check if answer already exists
            existing = db.query(Answer).filter(Answer.word == word).first()

            if existing:
                # Add clue if provided
                if len(row) > 1 and row[1].strip():
                    clue_text = row[1].strip()
                    difficulty = int(row[2]) if len(row) > 2 and row[2].strip() else 3
                    tags = row[3].strip() if len(row) > 3 else None

                    # Check for duplicate clue
                    existing_clue = db.query(Clue).filter(
                        Clue.answer_id == existing.id,
                        Clue.clue_text == clue_text
                    ).first()

                    if not existing_clue:
                        db_clue = Clue(
                            answer_id=existing.id,
                            clue_text=clue_text,
                            difficulty=difficulty,
                            tags=tags
                        )
                        db.add(db_clue)
                        imported += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            else:
                # Create new answer
                db_answer = Answer(word=word, length=len(word))
                db.add(db_answer)
                db.flush()

                # Add clue if provided
                if len(row) > 1 and row[1].strip():
                    clue_text = row[1].strip()
                    difficulty = int(row[2]) if len(row) > 2 and row[2].strip() else 3
                    tags = row[3].strip() if len(row) > 3 else None

                    db_clue = Clue(
                        answer_id=db_answer.id,
                        clue_text=clue_text,
                        difficulty=difficulty,
                        tags=tags
                    )
                    db.add(db_clue)

                imported += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(imported=imported, skipped=skipped, errors=errors[:10])  # Limit error messages


# Helper functions
def _answer_to_response(answer: Answer) -> AnswerResponse:
    return AnswerResponse(
        id=answer.id,
        word=answer.word,
        length=answer.length,
        created_at=answer.created_at.isoformat() if answer.created_at else "",
        clues=[_clue_to_response(c) for c in answer.clues]
    )


def _clue_to_response(clue: Clue) -> ClueResponse:
    return ClueResponse(
        id=clue.id,
        answer_id=clue.answer_id,
        clue_text=clue.clue_text,
        difficulty=clue.difficulty,
        tags=clue.tags,
        created_at=clue.created_at.isoformat() if clue.created_at else ""
    )
