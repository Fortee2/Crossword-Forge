from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), unique=True, nullable=False, index=True)
    length = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clues = relationship("Clue", back_populates="answer", cascade="all, delete-orphan")


class Clue(Base):
    __tablename__ = "clues"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True)
    clue_text = Column(Text, nullable=False)
    difficulty = Column(Integer, default=3)  # 1-5 scale
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("Answer", back_populates="clues")


class Puzzle(Base):
    __tablename__ = "puzzles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Untitled Puzzle")
    grid_data = Column(JSON, nullable=False)
    word_placements = Column(JSON, nullable=True)
    difficulty = Column(Integer, nullable=True)
    status = Column(String(50), default="draft")
    theme = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
