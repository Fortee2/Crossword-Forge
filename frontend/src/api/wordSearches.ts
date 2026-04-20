import { WordSearchPuzzle, WordSearchPlacement, WordSearchConfig } from '../types';

const API_BASE = 'http://localhost:8000';

export async function exportWordSearchPdf(id: number, includeAnswerKey: boolean = true): Promise<void> {
  const params = new URLSearchParams();
  if (!includeAnswerKey) params.set('include_answer_key', 'false');
  const url = `${API_BASE}/word-searches/${id}/pdf${params.toString() ? '?' + params.toString() : ''}`;

  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to export PDF');

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = response.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1] || 'word-search.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(downloadUrl);
}

export async function createWordSearch(data: {
  title: string;
  grid: string[][];
  words: string[];
  placements: WordSearchPlacement[];
  config: WordSearchConfig;
  difficulty_label?: string;
  status?: string;
}): Promise<WordSearchPuzzle> {
  const response = await fetch(`${API_BASE}/word-searches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create word search');
  return response.json();
}

export async function getWordSearches(): Promise<WordSearchPuzzle[]> {
  const response = await fetch(`${API_BASE}/word-searches`);
  if (!response.ok) throw new Error('Failed to fetch word searches');
  return response.json();
}

export async function getWordSearch(id: number): Promise<WordSearchPuzzle> {
  const response = await fetch(`${API_BASE}/word-searches/${id}`);
  if (!response.ok) throw new Error('Failed to fetch word search');
  return response.json();
}

export async function updateWordSearch(
  id: number,
  data: Partial<{
    title: string;
    grid: string[][];
    words: string[];
    placements: WordSearchPlacement[];
    config: WordSearchConfig;
    difficulty_label: string;
    status: string;
  }>
): Promise<WordSearchPuzzle> {
  const response = await fetch(`${API_BASE}/word-searches/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update word search');
  return response.json();
}

export async function deleteWordSearch(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/word-searches/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete word search');
}
