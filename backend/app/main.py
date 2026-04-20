from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, Base
from .routers import puzzles, answers, word_searches, books

# Create database tables
Base.metadata.create_all(bind=engine)

# Migrate existing databases: add new columns if missing
with engine.connect() as _conn:
    for _col, _ddl in [
        ("chapters", "ALTER TABLE books ADD COLUMN chapters JSON"),
        ("puzzles_difficulty_label", "ALTER TABLE puzzles ADD COLUMN difficulty_label VARCHAR(20)"),
        ("ws_difficulty_label", "ALTER TABLE word_searches ADD COLUMN difficulty_label VARCHAR(20)"),
    ]:
        try:
            _conn.execute(text(_ddl))
            _conn.commit()
        except Exception:
            pass  # column already exists

app = FastAPI(
    title="CrosswordForge API",
    description="API for the CrosswordForge puzzle construction workbench",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(puzzles.router)
app.include_router(answers.router)
app.include_router(word_searches.router)
app.include_router(books.router)


@app.get("/")
def root():
    return {"message": "CrosswordForge API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
