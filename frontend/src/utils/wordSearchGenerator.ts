import { WordSearchConfig, WordSearchDirection, WordSearchGenerationResult, WordSearchPlacement } from '../types';

const DIRECTION_DELTAS: Record<WordSearchDirection, { dr: number; dc: number }> = {
  E:  { dr: 0,  dc: 1  },
  W:  { dr: 0,  dc: -1 },
  N:  { dr: -1, dc: 0  },
  S:  { dr: 1,  dc: 0  },
  NE: { dr: -1, dc: 1  },
  NW: { dr: -1, dc: -1 },
  SE: { dr: 1,  dc: 1  },
  SW: { dr: 1,  dc: -1 },
};

const MAX_ATTEMPTS_PER_DIRECTION = 150;

function shuffleArray<T>(arr: T[]): T[] {
  const result = [...arr];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function canPlaceWord(
  grid: string[][],
  word: string,
  row: number,
  col: number,
  direction: WordSearchDirection,
  rows: number,
  cols: number
): boolean {
  const { dr, dc } = DIRECTION_DELTAS[direction];
  for (let i = 0; i < word.length; i++) {
    const r = row + i * dr;
    const c = col + i * dc;
    if (r < 0 || r >= rows || c < 0 || c >= cols) return false;
    const existing = grid[r][c];
    if (existing !== '' && existing !== word[i]) return false;
  }
  return true;
}

function placeWord(
  grid: string[][],
  word: string,
  row: number,
  col: number,
  direction: WordSearchDirection
): void {
  const { dr, dc } = DIRECTION_DELTAS[direction];
  for (let i = 0; i < word.length; i++) {
    grid[row + i * dr][col + i * dc] = word[i];
  }
}

export function generateWordSearch(config: WordSearchConfig, words: string[]): WordSearchGenerationResult {
  const { rows, cols, allowedDirections } = config;

  // Initialize empty grid
  const grid: string[][] = Array.from({ length: rows }, () => Array(cols).fill(''));

  // Sort longest first for better packing
  const sorted = [...words]
    .map(w => w.toUpperCase().replace(/[^A-Z]/g, ''))
    .filter(w => w.length > 0)
    .sort((a, b) => b.length - a.length);

  const placements: WordSearchPlacement[] = [];
  const unplaced: string[] = [];

  for (const word of sorted) {
    let placed = false;
    const directions = shuffleArray(allowedDirections);

    outer:
    for (const direction of directions) {
      for (let attempt = 0; attempt < MAX_ATTEMPTS_PER_DIRECTION; attempt++) {
        const row = Math.floor(Math.random() * rows);
        const col = Math.floor(Math.random() * cols);
        if (canPlaceWord(grid, word, row, col, direction, rows, cols)) {
          placeWord(grid, word, row, col, direction);
          placements.push({ word, row, col, direction });
          placed = true;
          break outer;
        }
      }
    }

    if (!placed) {
      unplaced.push(word);
    }
  }

  // Fill remaining empty cells with random letters
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (grid[r][c] === '') {
        grid[r][c] = alphabet[Math.floor(Math.random() * 26)];
      }
    }
  }

  return { grid, placements, unplaced };
}

export function getPlacementCells(
  placement: WordSearchPlacement
): { row: number; col: number }[] {
  const { dr, dc } = DIRECTION_DELTAS[placement.direction];
  return Array.from({ length: placement.word.length }, (_, i) => ({
    row: placement.row + i * dr,
    col: placement.col + i * dc,
  }));
}
