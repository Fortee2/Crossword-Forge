"""
Word List Import Service

Imports words from seed files (Jones, Broda, CNEX) into the answers database.
Normalizes scores to 0-100 and merges duplicates keeping highest score.

Run as: python -m app.services.import_wordlists
"""

import os
import csv
import sys
from collections import defaultdict
from typing import NamedTuple

# Add parent directory to path for imports when run as module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Answer


class WordEntry(NamedTuple):
    word: str           # uppercase, no spaces
    display: str        # natural case
    score: int          # normalized 0-100
    sources: set        # set of source names
    is_phrase: bool     # contains spaces in display


def normalize_jones_score(score: int) -> int:
    """Jones: 1-50 -> multiply by 2 -> 2-100"""
    return min(100, max(0, score * 2))


def normalize_broda_score(score: int) -> int:
    """Broda: 38-80 -> linear map to 45-100"""
    # Linear map: (score - 38) / (80 - 38) * (100 - 45) + 45
    if score <= 38:
        return 45
    if score >= 80:
        return 100
    return int(((score - 38) / 42) * 55 + 45)


def normalize_cnex_score(score: int) -> int:
    """CNEX: 5-90 -> linear map to 5-100"""
    # Linear map: (score - 5) / (90 - 5) * (100 - 5) + 5
    if score <= 5:
        return 5
    if score >= 90:
        return 100
    return int(((score - 5) / 85) * 95 + 5)


def parse_jones(filepath: str) -> dict[str, WordEntry]:
    """
    Parse Jones word list.
    Format: word;score (mixed case, includes phrases with spaces)
    """
    words = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or ';' not in line:
                continue

            try:
                parts = line.rsplit(';', 1)
                display = parts[0].strip()
                score = int(parts[1].strip())

                # Create uppercase key (remove spaces for matching)
                word = display.upper().replace(' ', '')

                # Skip if not alphabetic
                if not word.isalpha():
                    continue

                normalized_score = normalize_jones_score(score)
                is_phrase = ' ' in display

                # Keep entry with higher score
                if word not in words or normalized_score > words[word].score:
                    words[word] = WordEntry(
                        word=word,
                        display=display,
                        score=normalized_score,
                        sources={'jones'},
                        is_phrase=is_phrase
                    )
            except (ValueError, IndexError) as e:
                print(f"  Warning: Jones line {line_num} parse error: {e}")
                continue

    return words


def parse_broda(filepath: str) -> dict[str, WordEntry]:
    """
    Parse Broda word list.
    Format: CSV with word,score (mixed case)
    """
    words = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for line_num, row in enumerate(reader, 1):
            if not row or len(row) < 2:
                continue

            # Skip header
            if line_num == 1 and row[0].lower() == 'word':
                continue

            try:
                display = row[0].strip()
                score = int(row[1].strip())

                # Create uppercase key (remove spaces, hyphens for matching)
                word = ''.join(c for c in display.upper() if c.isalpha())

                if not word:
                    continue

                normalized_score = normalize_broda_score(score)
                is_phrase = ' ' in display or '-' in display

                # Keep entry with higher score
                if word not in words or normalized_score > words[word].score:
                    words[word] = WordEntry(
                        word=word,
                        display=display,
                        score=normalized_score,
                        sources={'broda'},
                        is_phrase=is_phrase
                    )
            except (ValueError, IndexError) as e:
                print(f"  Warning: Broda line {line_num} parse error: {e}")
                continue

    return words


def parse_cnex(filepath: str) -> dict[str, WordEntry]:
    """
    Parse CNEX word list.
    Format: WORD;score (all caps, no spaces in multi-word entries)
    """
    words = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or ';' not in line:
                continue

            try:
                parts = line.rsplit(';', 1)
                raw_word = parts[0].strip()
                score = int(parts[1].strip())

                # Remove any non-alpha chars (some entries have numbers)
                word = ''.join(c for c in raw_word.upper() if c.isalpha())

                if not word or len(word) < 2:
                    continue

                normalized_score = normalize_cnex_score(score)

                # CNEX words are all caps with no spaces, will get display from other sources
                # or default to title case
                if word not in words or normalized_score > words[word].score:
                    words[word] = WordEntry(
                        word=word,
                        display=raw_word,  # Keep original, will be title-cased later if needed
                        score=normalized_score,
                        sources={'cnex'},
                        is_phrase=False  # Can't detect phrases in CNEX
                    )
            except (ValueError, IndexError) as e:
                print(f"  Warning: CNEX line {line_num} parse error: {e}")
                continue

    return words


def merge_word_lists(*word_dicts: dict[str, WordEntry]) -> dict[str, WordEntry]:
    """
    Merge multiple word lists.
    - Keep highest normalized score
    - Combine sources
    - Prefer display from Jones/Broda over CNEX
    """
    merged = {}

    for word_dict in word_dicts:
        for word, entry in word_dict.items():
            if word in merged:
                existing = merged[word]

                # Combine sources
                combined_sources = existing.sources | entry.sources

                # Keep higher score
                best_score = max(existing.score, entry.score)

                # Prefer display from Jones/Broda (natural casing) over CNEX
                if 'jones' in entry.sources or 'broda' in entry.sources:
                    if 'jones' not in existing.sources and 'broda' not in existing.sources:
                        # New entry has better display
                        best_display = entry.display
                        is_phrase = entry.is_phrase
                    elif entry.score >= existing.score:
                        # Prefer newer high-scoring entry's display
                        best_display = entry.display
                        is_phrase = entry.is_phrase
                    else:
                        best_display = existing.display
                        is_phrase = existing.is_phrase
                else:
                    best_display = existing.display
                    is_phrase = existing.is_phrase

                merged[word] = WordEntry(
                    word=word,
                    display=best_display,
                    score=best_score,
                    sources=combined_sources,
                    is_phrase=is_phrase
                )
            else:
                merged[word] = entry

    return merged


def title_case_word(word: str) -> str:
    """Convert a word to title case, handling special cases."""
    if len(word) <= 1:
        return word.upper()
    return word[0].upper() + word[1:].lower()


def import_to_database(words: dict[str, WordEntry], db: Session) -> tuple[int, int, int]:
    """
    Import merged word list to database.
    Returns (inserted, updated, skipped) counts.
    """
    inserted = 0
    updated = 0
    skipped = 0

    batch_size = 1000
    word_items = list(words.items())
    total = len(word_items)

    for i in range(0, total, batch_size):
        batch = word_items[i:i + batch_size]

        for word, entry in batch:
            # Check if word exists
            existing = db.query(Answer).filter(Answer.word == word).first()

            if existing:
                # Only update if not a user entry and new score is higher
                if existing.source == 'user':
                    skipped += 1
                    continue

                # Update with new data if score is higher
                if entry.score > (existing.score or 0):
                    # Determine display
                    display = entry.display
                    if display.isupper() and 'cnex' in entry.sources:
                        # Title case CNEX-only words
                        display = title_case_word(display)

                    existing.display = display
                    existing.score = entry.score
                    existing.source = ','.join(sorted(entry.sources))
                    existing.is_phrase = entry.is_phrase or (' ' in display)
                    updated += 1
                else:
                    # Just add sources if not updating
                    current_sources = set((existing.source or '').split(','))
                    new_sources = current_sources | entry.sources
                    existing.source = ','.join(sorted(s for s in new_sources if s))
                    skipped += 1
            else:
                # Insert new entry
                display = entry.display
                if display.isupper() and 'cnex' in entry.sources and 'jones' not in entry.sources and 'broda' not in entry.sources:
                    # Title case CNEX-only words
                    display = title_case_word(display)

                db_answer = Answer(
                    word=word,
                    display=display,
                    length=len(word),
                    score=entry.score,
                    source=','.join(sorted(entry.sources)),
                    is_phrase=entry.is_phrase or (' ' in display)
                )
                db.add(db_answer)
                inserted += 1

        # Commit batch
        db.commit()

        progress = min(i + batch_size, total)
        print(f"  Progress: {progress:,}/{total:,} words processed...")

    return inserted, updated, skipped


def run_import():
    """Main import function."""
    # Get paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    seed_dir = os.path.join(base_dir, 'data', 'seed_lists')

    jones_path = os.path.join(seed_dir, 'jones.txt')
    broda_path = os.path.join(seed_dir, 'broda.csv')
    cnex_path = os.path.join(seed_dir, 'cnex.txt')

    print("=" * 60)
    print("CrosswordForge Word List Import")
    print("=" * 60)
    print()

    # Parse each file
    all_words = {}

    if os.path.exists(jones_path):
        print(f"Parsing Jones word list: {jones_path}")
        jones_words = parse_jones(jones_path)
        print(f"  Found {len(jones_words):,} words")
        all_words['jones'] = jones_words
    else:
        print(f"Warning: Jones file not found at {jones_path}")

    if os.path.exists(broda_path):
        print(f"Parsing Broda word list: {broda_path}")
        broda_words = parse_broda(broda_path)
        print(f"  Found {len(broda_words):,} words")
        all_words['broda'] = broda_words
    else:
        print(f"Warning: Broda file not found at {broda_path}")

    if os.path.exists(cnex_path):
        print(f"Parsing CNEX word list: {cnex_path}")
        cnex_words = parse_cnex(cnex_path)
        print(f"  Found {len(cnex_words):,} words")
        all_words['cnex'] = cnex_words
    else:
        print(f"Warning: CNEX file not found at {cnex_path}")

    if not all_words:
        print("\nNo word lists found to import!")
        return

    print()
    print("Merging word lists...")
    merged = merge_word_lists(*all_words.values())
    print(f"  Total unique words after merge: {len(merged):,}")

    # Count by source combination
    source_counts = defaultdict(int)
    for entry in merged.values():
        source_key = ','.join(sorted(entry.sources))
        source_counts[source_key] += 1

    print("\n  Words by source:")
    for source, count in sorted(source_counts.items()):
        print(f"    {source}: {count:,}")

    # Count phrases
    phrase_count = sum(1 for e in merged.values() if e.is_phrase)
    print(f"\n  Phrases (multi-word): {phrase_count:,}")

    # Import to database
    print()
    print("Importing to database...")

    # Create tables if needed
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        inserted, updated, skipped = import_to_database(merged, db)

        print()
        print("=" * 60)
        print("Import Complete!")
        print("=" * 60)
        print(f"  Inserted: {inserted:,}")
        print(f"  Updated:  {updated:,}")
        print(f"  Skipped:  {skipped:,} (user entries or lower scores)")
        print()

        # Final stats
        total_count = db.query(Answer).count()
        avg_score = db.query(Answer).with_entities(
            Answer.score
        ).all()
        avg_score = sum(s[0] or 0 for s in avg_score) / len(avg_score) if avg_score else 0

        print("Database Stats:")
        print(f"  Total answers: {total_count:,}")
        print(f"  Average score: {avg_score:.1f}")

    finally:
        db.close()


if __name__ == "__main__":
    run_import()
