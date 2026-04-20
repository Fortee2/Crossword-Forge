import { Book, BookChapter } from '../types';

const API_BASE = 'http://localhost:8000';

export async function createBook(data: {
  title?: string;
  subtitle?: string;
  author?: string;
  book_type: 'crossword' | 'wordsearch';
  puzzle_ids?: number[];
}): Promise<Book> {
  const response = await fetch(`${API_BASE}/books`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create book');
  return response.json();
}

export async function getBooks(): Promise<Book[]> {
  const response = await fetch(`${API_BASE}/books`);
  if (!response.ok) throw new Error('Failed to fetch books');
  return response.json();
}

export async function getBook(id: number): Promise<Book> {
  const response = await fetch(`${API_BASE}/books/${id}`);
  if (!response.ok) throw new Error('Failed to fetch book');
  return response.json();
}

export async function updateBook(
  id: number,
  data: Partial<{
    title: string;
    subtitle: string;
    author: string;
    puzzle_ids: number[];
    chapters: Pick<BookChapter, 'id' | 'name' | 'description' | 'puzzle_ids'>[];
  }>
): Promise<Book> {
  const response = await fetch(`${API_BASE}/books/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update book');
  return response.json();
}

export async function deleteBook(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/books/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete book');
}

export async function exportBookPdf(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/books/${id}/pdf`);
  if (!response.ok) throw new Error('Failed to export book PDF');

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = response.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1] || 'book.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(downloadUrl);
}
