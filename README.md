# CrosswordForge

A crossword construction workbench for building, managing, and publishing crossword puzzles.

## Phase 1: Grid Editor

This phase implements the core visual grid editor with:

- 15x15 crossword grid
- Click to toggle black squares (right-click or Shift+click)
- Type letters with arrow key navigation
- Rotational symmetry toggle (auto-mirrors black squares 180°)
- Auto-numbered squares following standard crossword rules
- Live Across/Down word lists
- Validation warnings (isolated regions, short words, broken symmetry)
- Save/load puzzles via API
- Dark mode support (follows system preference)

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at http://localhost:5173

## Usage

### Grid Controls

| Action | Control |
|--------|---------|
| Select cell | Click on cell |
| Toggle black square | Right-click or Shift+click |
| Enter letter | Type any letter (A-Z) |
| Navigate | Arrow keys |
| Switch direction | Tab or Space |
| Delete letter | Backspace or Delete |
| Clear grid | Click "Clear Grid" button |

### Features

- **Rotational Symmetry**: When enabled, toggling a black square automatically mirrors it 180° around the center
- **Auto-numbering**: Square numbers are calculated automatically based on crossword rules (start of across/down words)
- **Word Lists**: Live display of all across and down words as you build
- **Validation**: Real-time warnings for common issues

### Save/Load

1. Enter a title for your puzzle
2. Click "Create" to save a new puzzle or "Save" to update
3. Click "Load" to see all saved puzzles
4. Click "New" to start fresh

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /puzzles | Create a new puzzle |
| GET | /puzzles | List all puzzles |
| GET | /puzzles/{id} | Get a specific puzzle |
| PUT | /puzzles/{id} | Update a puzzle |
| DELETE | /puzzles/{id} | Delete a puzzle |
| POST | /puzzles/validate | Validate grid |

## Project Structure

```
CrosswordForge/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── database.py       # Database config
│   │   ├── routers/
│   │   │   └── puzzles.py    # Puzzle endpoints
│   │   └── services/
│   │       └── grid_validator.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── GridEditor/
│   │   ├── api/
│   │   │   └── puzzles.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── data/
│   └── crossword.db          # SQLite database (auto-created)
└── README.md
```

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite
- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: SQLite
