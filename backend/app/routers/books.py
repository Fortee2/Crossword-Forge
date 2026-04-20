from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Book, Puzzle, WordSearch
from ..services.pdf_exporter import generate_book_pdf


router = APIRouter(prefix="/books", tags=["books"])


class ChapterIn(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    puzzle_ids: List[int] = []


class BookCreate(BaseModel):
    title: str = "Untitled Book"
    subtitle: Optional[str] = None
    author: Optional[str] = None
    book_type: str  # "crossword" | "wordsearch"
    puzzle_ids: List[int] = []
    chapters: Optional[List[ChapterIn]] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    author: Optional[str] = None
    puzzle_ids: Optional[List[int]] = None
    chapters: Optional[List[ChapterIn]] = None


class ResolvedItem(BaseModel):
    id: int
    title: str
    status: str
    difficulty_label: Optional[str] = None


class ChapterOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    puzzle_ids: List[int] = []
    resolved_items: List[ResolvedItem] = []


class BookResponse(BaseModel):
    id: int
    title: str
    subtitle: Optional[str]
    author: Optional[str]
    book_type: str
    puzzle_ids: List[int]
    chapters: Optional[List[ChapterOut]] = None
    resolved_items: List[ResolvedItem] = []
    status: str
    created_at: datetime
    updated_at: datetime
    exported_at: Optional[datetime]

    class Config:
        from_attributes = True


def _resolve_items(db: Session, book_type: str, puzzle_ids: list) -> List[dict]:
    """Look up titles and statuses for each puzzle_id."""
    model = Puzzle if book_type == "crossword" else WordSearch
    resolved = []
    for pid in puzzle_ids:
        item = db.query(model).filter(model.id == pid).first()
        if item:
            resolved.append({
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "difficulty_label": getattr(item, "difficulty_label", None),
            })
    return resolved


def _resolve_chapters(db: Session, book_type: str, chapters: list) -> List[dict]:
    result = []
    for ch in chapters:
        resolved = _resolve_items(db, book_type, ch.get("puzzle_ids", []))
        result.append({
            "id": ch["id"],
            "name": ch["name"],
            "description": ch.get("description"),
            "puzzle_ids": ch.get("puzzle_ids", []),
            "resolved_items": resolved,
        })
    return result


def _book_response(book: Book, db: Session) -> dict:
    chapters_raw = book.chapters or []
    return {
        "id": book.id,
        "title": book.title,
        "subtitle": book.subtitle,
        "author": book.author,
        "book_type": book.book_type,
        "puzzle_ids": book.puzzle_ids or [],
        "chapters": _resolve_chapters(db, book.book_type, chapters_raw) if chapters_raw else None,
        "resolved_items": _resolve_items(db, book.book_type, book.puzzle_ids or []),
        "status": book.status,
        "created_at": book.created_at,
        "updated_at": book.updated_at,
        "exported_at": book.exported_at,
    }


def _apply_chapters(book: Book, chapters: List[ChapterIn]) -> None:
    """Store chapters on the book and derive the flat puzzle_ids from them."""
    book.chapters = [ch.model_dump() for ch in chapters]
    book.puzzle_ids = [pid for ch in chapters for pid in ch.puzzle_ids]


@router.post("", response_model=BookResponse)
def create_book(data: BookCreate, db: Session = Depends(get_db)):
    if data.book_type not in ("crossword", "wordsearch"):
        raise HTTPException(status_code=400, detail="book_type must be 'crossword' or 'wordsearch'")
    db_book = Book(
        title=data.title,
        subtitle=data.subtitle,
        author=data.author,
        book_type=data.book_type,
        puzzle_ids=data.puzzle_ids,
    )
    if data.chapters is not None:
        _apply_chapters(db_book, data.chapters)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return _book_response(db_book, db)


@router.get("", response_model=List[BookResponse])
def list_books(db: Session = Depends(get_db)):
    books = db.query(Book).order_by(Book.updated_at.desc()).all()
    return [_book_response(b, db) for b in books]


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return _book_response(book, db)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(book_id: int, data: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle chapters — derive puzzle_ids from them
    if "chapters" in update_data and update_data["chapters"] is not None:
        _apply_chapters(book, data.chapters)
        del update_data["chapters"]
        update_data.pop("puzzle_ids", None)  # chapters win

    for key, value in update_data.items():
        setattr(book, key, value)

    db.commit()
    db.refresh(book)
    return _book_response(book, db)


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}


@router.get("/{book_id}/pdf")
def export_book_pdf(book_id: int, db: Session = Depends(get_db)):
    """Export a book as a print-ready PDF."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    puzzle_ids = book.puzzle_ids or []
    if not puzzle_ids:
        raise HTTPException(status_code=400, detail="Book has no puzzles")

    model = Puzzle if book.book_type == "crossword" else WordSearch

    def _puzzle_dict(item):
        if book.book_type == "crossword":
            return {"title": item.title, "grid_data": item.grid_data, "word_placements": item.word_placements, "difficulty_label": getattr(item, "difficulty_label", None)}
        return {"title": item.title, "grid": item.grid, "words": item.words, "placements": item.placements, "difficulty_label": getattr(item, "difficulty_label", None)}

    # Build chapter-aware structure for PDF generator
    chapters_raw = book.chapters or []
    if chapters_raw:
        pdf_chapters = []
        for ch in chapters_raw:
            ch_puzzles = []
            for pid in ch.get("puzzle_ids", []):
                item = db.query(model).filter(model.id == pid).first()
                if item:
                    ch_puzzles.append(_puzzle_dict(item))
            pdf_chapters.append({
                "name": ch["name"],
                "description": ch.get("description"),
                "puzzles": ch_puzzles,
            })
        pdf_bytes = generate_book_pdf(
            title=book.title,
            subtitle=book.subtitle,
            author=book.author,
            book_type=book.book_type,
            puzzles=[],
            chapters=pdf_chapters,
        )
    else:
        # Legacy flat mode
        puzzles = []
        for pid in puzzle_ids:
            item = db.query(model).filter(model.id == pid).first()
            if item:
                puzzles.append(_puzzle_dict(item))

        if not puzzles:
            raise HTTPException(status_code=400, detail="None of the referenced puzzles exist")

        pdf_bytes = generate_book_pdf(
            title=book.title,
            subtitle=book.subtitle,
            author=book.author,
            book_type=book.book_type,
            puzzles=puzzles,
        )

    # Update export status
    from sqlalchemy.sql import func
    book.status = "exported"
    book.exported_at = func.now()
    db.commit()

    safe_title = "".join(c for c in book.title if c.isalnum() or c in " -_").strip() or "book"
    filename = f"{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
