import { Answer, AnswerListItem, ClueInfo, WordSuggestion, ImportResult, GridCell } from '../types';

const API_BASE = 'http://localhost:8000';

// Answer CRUD operations
export async function createAnswer(data: {
  word: string;
  clues?: { clue_text: string; difficulty?: number; tags?: string }[];
}): Promise<Answer> {
  const response = await fetch(`${API_BASE}/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create answer');
  }
  return response.json();
}

export async function getAnswers(params?: {
  skip?: number;
  limit?: number;
  q?: string;
  min_length?: number;
  max_length?: number;
  tag?: string;
}): Promise<AnswerListItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.q) searchParams.set('q', params.q);
  if (params?.min_length) searchParams.set('min_length', params.min_length.toString());
  if (params?.max_length) searchParams.set('max_length', params.max_length.toString());
  if (params?.tag) searchParams.set('tag', params.tag);

  const url = `${API_BASE}/answers${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch answers');
  return response.json();
}

export async function searchAnswers(params: {
  pattern?: string;
  q?: string;
  limit?: number;
}): Promise<Answer[]> {
  const searchParams = new URLSearchParams();
  if (params.pattern) searchParams.set('pattern', params.pattern);
  if (params.q) searchParams.set('q', params.q);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  const response = await fetch(`${API_BASE}/answers/search?${searchParams.toString()}`);
  if (!response.ok) throw new Error('Failed to search answers');
  return response.json();
}

export async function getAnswer(id: number): Promise<Answer> {
  const response = await fetch(`${API_BASE}/answers/${id}`);
  if (!response.ok) throw new Error('Failed to fetch answer');
  return response.json();
}

export async function updateAnswer(id: number, data: { word?: string }): Promise<Answer> {
  const response = await fetch(`${API_BASE}/answers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update answer');
  }
  return response.json();
}

export async function deleteAnswer(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/answers/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete answer');
}

// Clue CRUD operations
export async function createClue(
  answerId: number,
  data: { clue_text: string; difficulty?: number; tags?: string }
): Promise<ClueInfo> {
  const response = await fetch(`${API_BASE}/answers/${answerId}/clues`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create clue');
  return response.json();
}

export async function getClues(answerId: number): Promise<ClueInfo[]> {
  const response = await fetch(`${API_BASE}/answers/${answerId}/clues`);
  if (!response.ok) throw new Error('Failed to fetch clues');
  return response.json();
}

export async function updateClue(
  answerId: number,
  clueId: number,
  data: { clue_text?: string; difficulty?: number; tags?: string }
): Promise<ClueInfo> {
  const response = await fetch(`${API_BASE}/answers/${answerId}/clues/${clueId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update clue');
  return response.json();
}

export async function deleteClue(answerId: number, clueId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/answers/${answerId}/clues/${clueId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete clue');
}

// Bulk import
export async function importAnswers(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/answers/import`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to import answers');
  }
  return response.json();
}

// Word suggestions for grid editor
export async function getWordSuggestions(params: {
  pattern?: string;
  grid_data?: GridCell[][];
  row?: number;
  col?: number;
  direction?: string;
  limit?: number;
}): Promise<WordSuggestion[]> {
  const response = await fetch(`${API_BASE}/puzzles/suggestions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error('Failed to get suggestions');
  return response.json();
}
