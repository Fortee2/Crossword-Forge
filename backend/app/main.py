from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import puzzles

# Create database tables
Base.metadata.create_all(bind=engine)

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


@app.get("/")
def root():
    return {"message": "CrosswordForge API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
