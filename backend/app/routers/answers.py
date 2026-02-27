from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from pydantic import BaseModel
from typing import Optional
import csv
import io
import re

from ..database import get_db
from ..models import Answer, Clue
from ..services.word_suggester import get_word_suggestions

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
    display: Optional[str] = None
    length: int
    score: Optional[int] = 100
    source: Optional[str] = 'user'
    is_phrase: Optional[bool] = False
    created_at: str
    clue_count: int

    class Config:
        from_attributes = True


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class WordSuggestionResponse(BaseModel):
    id: int
    word: str
    display: str
    length: int
    score: int
    source: str
    is_phrase: bool
    clues: list[ClueResponse]

    class Config:
        from_attributes = True


class AnswerStatsResponse(BaseModel):
    total_answers: int
    total_clues: int
    avg_score: float
    by_source: dict[str, int]
    by_length: dict[int, int]
    phrase_count: int


class SeedImportResult(BaseModel):
    status: str
    message: str


# Helper functions
def pattern_to_regex(pattern: str) -> str:
    """Convert pattern like P_A_O to regex P.A.O"""
    result = ""
    for char in pattern:
        if char == '_':
            result += "."
        else:
            result += re.escape(char)
    return "^" + result + "$"


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


# === Static path routes MUST come before /{answer_id} to avoid conflicts ===

@router.get("/suggest", response_model=list[WordSuggestionResponse])
def suggest_words(
    pattern: str,
    limit: int = 20,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get word suggestions matching a pattern, sorted by score.
    Pattern uses underscores as wildcards (e.g., P_A_O matches PIANO, PLANO).
    """
    if not pattern or len(pattern) < 2:
        raise HTTPException(status_code=400, detail="Pattern must be at least 2 characters")

    suggestions = get_word_suggestions(db, pattern, limit, source_filter=source)

    return [
        WordSuggestionResponse(
            id=s["id"],
            word=s["word"],
            display=s.get("display", s["word"]),
            length=s["length"],
            score=s.get("score", 100),
            source=s.get("source", "user"),
            is_phrase=s.get("is_phrase", False),
            clues=[
                ClueResponse(
                    id=c["id"],
                    answer_id=s["id"],
                    clue_text=c["clue_text"],
                    difficulty=c["difficulty"],
                    tags=c.get("tags"),
                    created_at=""
                )
                for c in s["clues"]
            ]
        )
        for s in suggestions
    ]


@router.get("/stats", response_model=AnswerStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get statistics about the answer database."""
    total_answers = db.query(Answer).count()
    total_clues = db.query(Clue).count()

    avg_result = db.query(func.avg(Answer.score)).scalar()
    avg_score = float(avg_result) if avg_result else 0.0

    source_counts: dict[str, int] = {}
    sources = db.query(Answer.source, func.count(Answer.id)).group_by(Answer.source).all()
    for source, count in sources:
        if source:
            for s in source.split(','):
                s = s.strip()
                if s:
                    source_counts[s] = source_counts.get(s, 0) + count
        else:
            source_counts['unknown'] = source_counts.get('unknown', 0) + count

    length_counts: dict[int, int] = {}
    lengths = db.query(Answer.length, func.count(Answer.id)).group_by(Answer.length).all()
    for length, count in lengths:
        length_counts[length] = count

    phrase_count = db.query(Answer).filter(Answer.is_phrase == True).count()

    return AnswerStatsResponse(
        total_answers=total_answers,
        total_clues=total_clues,
        avg_score=round(avg_score, 1),
        by_source=source_counts,
        by_length=length_counts,
        phrase_count=phrase_count
    )


@router.get("/search", response_model=list[AnswerResponse])
def search_answers(
    pattern: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search answers by pattern or text."""
    query = db.query(Answer)

    if pattern:
        pattern_upper = pattern.upper().strip()
        query = query.filter(Answer.length == len(pattern_upper))
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


@router.post("/import", response_model=ImportResult)
async def import_answers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk import answers and clues from a CSV file (word,clue,difficulty,tags)."""
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="File must be CSV or TXT format")

    content = await file.read()
    text = content.decode('utf-8')
    imported = 0
    skipped = 0
    errors: list[str] = []

    reader = csv.reader(io.StringIO(text))
    for row_num, row in enumerate(reader, start=1):
        if not row or not row[0].strip():
            continue
        if row_num == 1 and row[0].lower() in ('word', 'answer'):
            continue
        try:
            word = row[0].upper().strip()
            if not word.isalpha():
                errors.append(f"Row {row_num}: Invalid word '{row[0]}'")
                skipped += 1
                continue

            existing = db.query(Answer).filter(Answer.word == word).first()
            if existing:
                if len(row) > 1 and row[1].strip():
                    clue_text = row[1].strip()
                    difficulty = int(row[2]) if len(row) > 2 and row[2].strip() else 3
                    tags = row[3].strip() if len(row) > 3 else None
                    existing_clue = db.query(Clue).filter(
                        Clue.answer_id == existing.id, Clue.clue_text == clue_text
                    ).first()
                    if not existing_clue:
                        db.add(Clue(answer_id=existing.id, clue_text=clue_text, difficulty=difficulty, tags=tags))
                        imported += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            else:
                db_answer = Answer(word=word, length=len(word))
                db.add(db_answer)
                db.flush()
                if len(row) > 1 and row[1].strip():
                    clue_text = row[1].strip()
                    difficulty = int(row[2]) if len(row) > 2 and row[2].strip() else 3
                    tags = row[3].strip() if len(row) > 3 else None
                    db.add(Clue(answer_id=db_answer.id, clue_text=clue_text, difficulty=difficulty, tags=tags))
                imported += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            skipped += 1

    db.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=errors[:10])


@router.post("/import-seed", response_model=SeedImportResult)
def import_seed_lists(background_tasks: BackgroundTasks):
    """Trigger import of seed word lists (Jones, Broda, CNEX) in background."""
    from ..services.import_wordlists import run_import

    def run_import_task():
        try:
            run_import()
        except Exception as e:
            print(f"Import error: {e}")

    background_tasks.add_task(run_import_task)
    return SeedImportResult(status="started", message="Import started in background. Check server logs for progress.")


# === CRUD endpoints (parameterized paths) ===

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
    db.flush()

    if answer.clues:
        for clue_data in answer.clues:
            db.add(Clue(
                answer_id=db_answer.id,
                clue_text=clue_data.clue_text,
                difficulty=clue_data.difficulty,
                tags=clue_data.tags
            ))

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
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: Optional[str] = "word",
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
    if min_score is not None:
        query = query.filter(Answer.score >= min_score)
    if max_score is not None:
        query = query.filter(Answer.score <= max_score)
    if source:
        query = query.filter(Answer.source.contains(source))
    if tag:
        query = query.join(Clue).filter(Clue.tags.contains(tag)).distinct()

    if sort_by == "score":
        query = query.order_by(desc(Answer.score), Answer.word)
    elif sort_by == "length":
        query = query.order_by(Answer.length, Answer.word)
    else:
        query = query.order_by(Answer.word)

    answers = query.offset(skip).limit(limit).all()
    return [
        AnswerListResponse(
            id=a.id, word=a.word, display=a.display, length=a.length,
            score=a.score, source=a.source, is_phrase=a.is_phrase,
            created_at=a.created_at.isoformat() if a.created_at else "",
            clue_count=len(a.clues)
        )
        for a in answers
    ]


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


# Clue CRUD (nested under answers)

@router.post("/{answer_id}/clues", response_model=ClueResponse)
def create_clue(answer_id: int, clue: ClueCreate, db: Session = Depends(get_db)):
    """Add a clue to an answer."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    db_clue = Clue(answer_id=answer_id, clue_text=clue.clue_text, difficulty=clue.difficulty, tags=clue.tags)
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
def update_clue(answer_id: int, clue_id: int, update: ClueUpdate, db: Session = Depends(get_db)):
    """Update a clue."""
    clue = db.query(Clue).filter(Clue.id == clue_id, Clue.answer_id == answer_id).first()
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
    clue = db.query(Clue).filter(Clue.id == clue_id, Clue.answer_id == answer_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")
    db.delete(clue)
    db.commit()
    return {"message": "Clue deleted successfully"}
