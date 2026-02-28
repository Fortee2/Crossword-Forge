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

// Clue Database types
export interface ClueInfo {
  id: number;
  clue_text: string;
  difficulty: number;
  tags?: string;
  created_at?: string;
}

export interface Answer {
  id: number;
  word: string;
  length: number;
  created_at: string;
  clues: ClueInfo[];
}

export interface AnswerListItem {
  id: number;
  word: string;
  display?: string;
  length: number;
  score?: number;
  source?: string;
  is_phrase?: boolean;
  created_at: string;
  clue_count: number;
}

export interface WordSuggestion {
  id: number;
  word: string;
  display?: string;
  length: number;
  score?: number;
  source?: string;
  is_phrase?: boolean;
  clues: ClueInfo[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface AnswerStats {
  total_answers: number;
  total_clues: number;
  avg_score: number;
  by_source: Record<string, number>;
  by_length: Record<number, number>;
  phrase_count: number;
}

export interface SeedImportResult {
  status: string;
  message: string;
}

// Fillability analysis types
export type FillabilitySeverity = 'good' | 'okay' | 'tight' | 'danger';

export interface SlotFillability {
  number: number;
  direction: 'across' | 'down';
  row: number;
  col: number;
  length: number;
  fill_count: number;
  severity: FillabilitySeverity;
}

export interface FillabilitySummary {
  good: number;
  okay: number;
  tight: number;
  danger: number;
}

export interface FillabilityResult {
  slots: SlotFillability[];
  summary: FillabilitySummary;
}
