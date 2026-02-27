# CrosswordForge

**A crossword construction workbench for building, managing, and publishing crossword puzzles.**

You're the constructor. The app is your workshop.

---

## Vision

A web application that makes it enjoyable to hand-craft 15x15 crossword puzzles, manage a personal clue/answer database, and compile finished puzzles into print-ready books for self-publishing (Amazon KDP).

## Core Principles

- **Creator-first** — the tool supports your creative process, it doesn't replace it
- **Your clue database is your most valuable asset** — it grows with you over time
- **Side project pace** — built in phases, each phase is independently useful

---

## Architecture

### Stack
- **Frontend:** React (visual grid editor, clue management, book builder)
- **Backend:** Python (FastAPI)
- **Database:** SQLite (simple, portable, no server needed)
- **PDF Export:** ReportLab or WeasyPrint (KDP-formatted output)

### Data Model

```
answers
  id          INTEGER PRIMARY KEY
  word        TEXT UNIQUE         -- uppercase, e.g. "PIANO"
  length      INTEGER
  created_at  TIMESTAMP

clues
  id          INTEGER PRIMARY KEY
  answer_id   INTEGER FK → answers
  clue_text   TEXT                -- e.g. "Baby grand, for one"
  difficulty  INTEGER (1-5)
  tags        TEXT                -- comma-separated: "music, instruments"
  created_at  TIMESTAMP

puzzles
  id          INTEGER PRIMARY KEY
  title       TEXT
  grid_data   JSON               -- 15x15 grid state (black squares, letters)
  word_placements JSON           -- [{word, clue_id, row, col, direction}]
  difficulty  INTEGER (1-5)
  status      TEXT               -- draft | complete | published
  theme       TEXT
  notes       TEXT
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

books
  id          INTEGER PRIMARY KEY
  title       TEXT
  subtitle    TEXT
  trim_size   TEXT               -- e.g. "8.5x11", "6x9"
  puzzle_ids  JSON               -- ordered list of puzzle IDs
  status      TEXT               -- draft | exported
  created_at  TIMESTAMP
  exported_at TIMESTAMP
```

---

## Phases

### Phase 1 — The Grid Editor
The foundation. A visual 15x15 grid where you build puzzles by hand.

**Features:**
- Click to toggle black squares
- Type to fill in letters (arrow keys to navigate)
- Automatic rotational symmetry toggle (auto-mirrors black squares)
- Validation warnings:
  - Isolated white square regions
  - Words shorter than 3 letters
  - Broken symmetry (when enabled)
- Numbered squares (auto-calculated based on black square pattern)
- Across/Down word list display (updates live as you build)
- Save/load grid state

**Done when:** You can open the app, build a valid 15x15 grid, fill it with words, and save it.

---

### Phase 2 — Clue Database & Word Suggestions
Your personal dictionary of answers and clues. Grows over time.

**Features:**
- Add/edit/delete answers and clues
- Multiple clues per answer (easy/medium/hard)
- Difficulty ratings and tags
- Import from open-source crossword word lists (seed your database)
- **Grid integration:** As you type letters in the grid, suggest matching words from your database
  - Pattern matching: `P_A_O` → shows "PIANO", "PLANO", etc.
  - Shows your existing clues inline
- Search/browse your clue database

**Done when:** You can build a grid with word suggestions pulling from your database, and write/store clues as you go.

#### Word List Seed Sources

The database starts empty but can be seeded from these free, community-maintained lists:

| Source | Entries | Format | Score Range | License | Notes |
|--------|---------|--------|-------------|---------|-------|
| **[STWL](https://www.spreadthewordlist.com/)** | 310K | scored | 0–50 | Free | Community-curated, data-driven. Top pick. |
| **[Jones](https://github.com/christophsjones/crossword-wordlist)** | 176K | `word;score` | 1–50 | Free | Composite of NYT/WSJ/WaPo/Broda/Norvig + hand-picked. Mixed case, preserves phrases. |
| **[Broda](https://github.com/gregpoulos/crossword-owl)** | 493K | `word,score` CSV | 38–80 | Free (OWL project) | Classic constructor list. Largest, but most entries undifferentiated at 50. |
| **[CNEX](https://github.com/Crossword-Nexus/collaborative-word-list)** | 568K | `WORD;score` | 5–90 | MIT | Biggest, widest score range. All caps, no spaces in multi-word entries. |
| **[Ginsberg Clues](https://tiwwdty.com/clue/)** | Millions | App + DB | N/A | Free | Clue-answer pairs from published puzzles. For clue inspiration, not word fill. |

**Paid option:** [XWordInfo](https://www.xwordinfo.com/WordList) (~$30/yr) — scored by actual NYT frequency. Best quality signal available.

#### Import Design

Extended `answers` table to support seeded data alongside user entries:

```
answers
  id          INTEGER PRIMARY KEY
  word        TEXT UNIQUE         -- uppercase, no spaces, e.g. "PIANO" (for matching)
  display     TEXT                -- natural case, e.g. "Piano" (for UI)
  length      INTEGER             -- pre-computed for fast pattern matching
  score       INTEGER             -- normalized 0–100
  source      TEXT                -- "jones", "broda", "cnex", "stwl", "user"
  is_phrase   BOOLEAN             -- multi-word entry
  created_at  TIMESTAMP
```

**Score normalization** (all mapped to 0–100 scale):
- Jones 1–50 → ×2 → 2–100
- Broda 38–80 → linear map → ~45–100
- CNEX 5–90 → linear map → ~5–100
- STWL 0–50 → ×2 → 0–100
- User entries → default 100 (always surface first)

**Merge rules:** If same word appears in multiple lists, keep highest normalized score and note all sources. User entries always win.

**CNEX caveat:** Multi-word entries are space-stripped (`BONNIEANDCLYDE`). The import script should attempt to reconstruct display names from Jones/Broda where available, or flag for manual review.

---

### Phase 3 — Puzzle Management
Organize your growing collection.

**Features:**
- Puzzle list view (title, difficulty, status, date, theme)
- Filter/sort/search
- Status workflow: draft → complete → published
- Duplicate a puzzle (use as starting template)
- Puzzle preview (rendered grid with clue lists)

**Done when:** You can browse, search, and manage a library of puzzles.

---

### Phase 4 — Book Compiler & PDF Export
Turn your puzzles into a publishable book.

**Features:**
- Create a book: title, subtitle, author, trim size
- Add puzzles in order (drag to reorder)
- Difficulty progression options
- Preview book layout
- Generate print-ready PDF:
  - Title page
  - Table of contents
  - One puzzle per page (grid + clues)
  - Answer key section in the back (filled grids, smaller)
  - Page numbers
  - KDP trim sizes (8.5x11, 6x9, etc.)
  - Bleed and margin settings per KDP specs

**Done when:** You can select puzzles, compile a book, and upload the PDF to Amazon KDP.

---

## Future Ideas (Maybe Later)
- Themed puzzle generation ("seed these 5 words, auto-fill the rest")
- Difficulty scoring algorithm
- Clue quality suggestions (flag vague or duplicate clues)
- Puzzle statistics (most-used words, average difficulty)
- Export individual puzzles (PNG, PDF single page)
- Collaborative clue writing
- Mobile-friendly grid editor

---

## KDP Publishing Notes
- Common trim sizes: 8.5" x 11" (most popular for puzzles), 6" x 9"
- Interior: black & white
- Bleed: not typically needed for puzzle books
- Margins: minimum 0.25" outside, 0.375" gutter (varies with page count)
- File format: PDF (PDF/X-1a preferred)
- Cover: separate PDF, dimensions depend on page count + trim size

---

## Project Structure
```
CrosswordForge/
├── PROJECT.md          # This file
├── backend/            # Python FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── routers/
│   │   └── services/
│   │       ├── grid_validator.py
│   │       ├── word_suggester.py
│   │       └── pdf_exporter.py
│   └── requirements.txt
├── frontend/           # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── GridEditor/
│   │   │   ├── CluePanel/
│   │   │   ├── PuzzleManager/
│   │   │   └── BookBuilder/
│   │   └── App.tsx
│   └── package.json
└── data/
    └── crossword.db    # SQLite database
```
