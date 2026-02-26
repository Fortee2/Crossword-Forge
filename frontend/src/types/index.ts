export interface GridCell {
  isBlack: boolean;
  letter: string;
}

export interface WordPlacement {
  word: string;
  clue?: string;
  row: number;
  col: number;
  direction: 'across' | 'down';
  number: number;
}

export interface Puzzle {
  id: number;
  title: string;
  grid_data: GridCell[][];
  word_placements?: WordPlacement[];
  difficulty?: number;
  status: 'draft' | 'complete' | 'published';
  theme?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ValidationWarning {
  type: 'isolated_regions' | 'short_words' | 'broken_symmetry' | 'invalid_size';
  message: string;
  cells?: { row: number; col: number }[];
  words?: { direction: string; row: number; col: number; length: number }[];
}

export interface ValidationResult {
  valid: boolean;
  warnings: ValidationWarning[];
}

export interface WordEntry {
  number: number;
  word: string;
  row: number;
  col: number;
  direction: 'across' | 'down';
}

export interface NumberedCell {
  row: number;
  col: number;
  number: number;
}
