from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import WordSearch
from ..services.pdf_exporter import generate_word_search_pdf


router = APIRouter(prefix="/word-searches", tags=["word-searches"])


class WordSearchPlacement(BaseModel):
    word: str
    row: int
    col: int
    direction: str


class WordSearchConfig(BaseModel):
    rows: int
    cols: int
    allowedDirections: List[str]


class WordSearchCreate(BaseModel):
    title: str = "Untitled Word Search"
    grid: List[List[str]]
    words: List[str]
    placements: List[WordSearchPlacement]
    config: WordSearchConfig
    status: str = "draft"


class WordSearchUpdate(BaseModel):
    title: Optional[str] = None
    grid: Optional[List[List[str]]] = None
    words: Optional[List[str]] = None
    placements: Optional[List[WordSearchPlacement]] = None
    config: Optional[WordSearchConfig] = None
    status: Optional[str] = None


class WordSearchResponse(BaseModel):
    id: int
    title: str
    grid: List[List[str]]
    words: List[str]
    placements: List[dict]
    config: dict
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=WordSearchResponse)
def create_word_search(data: WordSearchCreate, db: Session = Depends(get_db)):
    db_ws = WordSearch(
        title=data.title,
        grid=data.grid,
        words=data.words,
        placements=[p.model_dump() for p in data.placements],
        config=data.config.model_dump(),
        status=data.status,
    )
    db.add(db_ws)
    db.commit()
    db.refresh(db_ws)
    return db_ws


@router.get("", response_model=List[WordSearchResponse])
def list_word_searches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return db.query(WordSearch).order_by(WordSearch.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/{ws_id}", response_model=WordSearchResponse)
def get_word_search(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(WordSearch).filter(WordSearch.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Word search not found")
    return ws


@router.put("/{ws_id}", response_model=WordSearchResponse)
def update_word_search(ws_id: int, data: WordSearchUpdate, db: Session = Depends(get_db)):
    ws = db.query(WordSearch).filter(WordSearch.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Word search not found")

    update_data = data.model_dump(exclude_unset=True)
    if "placements" in update_data and update_data["placements"]:
        update_data["placements"] = [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in update_data["placements"]
        ]
    if "config" in update_data and update_data["config"] and hasattr(update_data["config"], "model_dump"):
        update_data["config"] = update_data["config"].model_dump()

    for key, value in update_data.items():
        setattr(ws, key, value)

    db.commit()
    db.refresh(ws)
    return ws


@router.get("/{ws_id}/pdf")
def export_word_search_pdf(
    ws_id: int,
    include_answer_key: bool = True,
    db: Session = Depends(get_db),
):
    """Export a word search puzzle as a PDF file."""
    ws = db.query(WordSearch).filter(WordSearch.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Word search not found")

    pdf_bytes = generate_word_search_pdf(
        title=ws.title,
        grid=ws.grid,
        words=ws.words,
        placements=ws.placements,
        include_answer_key=include_answer_key,
    )

    safe_title = "".join(c for c in ws.title if c.isalnum() or c in " -_").strip() or "word-search"
    filename = f"{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{ws_id}")
def delete_word_search(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(WordSearch).filter(WordSearch.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Word search not found")

    db.delete(ws)
    db.commit()
    return {"message": "Word search deleted successfully"}
