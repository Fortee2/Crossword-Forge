import { Puzzle, GridCell, ValidationResult, WordPlacement, FillabilityResult, CrossingSuggestionsResult } from '../types';

const API_BASE = 'http://localhost:8000';

export async function createPuzzle(data: {
  title: string;
  grid_data: GridCell[][];
  word_placements?: WordPlacement[];
  status?: string;
  theme?: string;
  notes?: string;
}): Promise<Puzzle> {
  const response = await fetch(`${API_BASE}/puzzles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create puzzle');
  return response.json();
}

export async function getPuzzles(): Promise<Puzzle[]> {
  const response = await fetch(`${API_BASE}/puzzles`);
  if (!response.ok) throw new Error('Failed to fetch puzzles');
  return response.json();
}

export async function getPuzzle(id: number): Promise<Puzzle> {
  const response = await fetch(`${API_BASE}/puzzles/${id}`);
  if (!response.ok) throw new Error('Failed to fetch puzzle');
  return response.json();
}

export async function updatePuzzle(
  id: number,
  data: Partial<{
    title: string;
    grid_data: GridCell[][];
    word_placements: WordPlacement[];
    status: string;
    theme: string;
    notes: string;
  }>
): Promise<Puzzle> {
  const response = await fetch(`${API_BASE}/puzzles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update puzzle');
  return response.json();
}

export async function deletePuzzle(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/puzzles/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete puzzle');
}

export async function validateGrid(
  grid_data: GridCell[][],
  symmetry_enabled: boolean = true
): Promise<ValidationResult> {
  const response = await fetch(`${API_BASE}/puzzles/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grid_data, symmetry_enabled }),
  });
  if (!response.ok) throw new Error('Failed to validate grid');
  return response.json();
}

export async function analyzeFillability(grid_data: GridCell[][]): Promise<FillabilityResult> {
  const response = await fetch(`${API_BASE}/puzzles/fillability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grid_data }),
  });
  if (!response.ok) throw new Error('Failed to analyze fillability');
  return response.json();
}

export async function getSuggestionsWithCrossings(params: {
  grid_data: GridCell[][];
  row: number;
  col: number;
  direction: string;
  limit?: number;
}): Promise<CrossingSuggestionsResult> {
  const response = await fetch(`${API_BASE}/puzzles/suggestions-with-crossings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grid_data: params.grid_data,
      row: params.row,
      col: params.col,
      direction: params.direction,
      limit: params.limit || 30,
    }),
  });
  if (!response.ok) throw new Error('Failed to get suggestions with crossings');
  return response.json();
}
