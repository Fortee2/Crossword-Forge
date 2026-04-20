import { useState, useEffect, useCallback } from 'react';
import { Book, BookChapter, BookResolvedItem } from '../../types';
import { createBook, getBooks, getBook, updateBook, deleteBook, exportBookPdf } from '../../api/books';
import { PuzzlePicker } from './PuzzlePicker';
import './BookBuilder.css';

export function BookBuilder() {
  // List mode state
  const [books, setBooks] = useState<Book[]>([]);
  // Edit mode state
  const [editingBook, setEditingBook] = useState<Book | null>(null);
  const [title, setTitle] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [author, setAuthor] = useState('');
  const [chapters, setChapters] = useState<BookChapter[]>([]);

  const [showPicker, setShowPicker] = useState(false);
  const [pickerTargetChapterId, setPickerTargetChapterId] = useState<string | null>(null);
  const [showCreateChoice, setShowCreateChoice] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const loadBooks = useCallback(async () => {
    try {
      const data = await getBooks();
      setBooks(data);
    } catch {
      // Server might not be running
    }
  }, []);

  useEffect(() => {
    loadBooks();
  }, [loadBooks]);

  const handleCreate = async (bookType: 'crossword' | 'wordsearch') => {
    setShowCreateChoice(false);
    try {
      const book = await createBook({ book_type: bookType });
      await loadBooks();
      openEditor(book);
      showMessage('success', 'Book created!');
    } catch {
      showMessage('error', 'Failed to create book');
    }
  };

  const openEditor = (book: Book) => {
    setEditingBook(book);
    setTitle(book.title);
    setSubtitle(book.subtitle || '');
    setAuthor(book.author || '');

    if (book.chapters && book.chapters.length > 0) {
      setChapters(book.chapters);
    } else {
      // Legacy book or new book — start with one default chapter
      setChapters([{
        id: crypto.randomUUID(),
        name: 'Puzzles',
        description: '',
        puzzle_ids: book.puzzle_ids,
        resolved_items: book.resolved_items || [],
      }]);
    }
  };

  const handleLoad = async (bookId: number) => {
    try {
      const book = await getBook(bookId);
      openEditor(book);
    } catch {
      showMessage('error', 'Failed to load book');
    }
  };

  const handleDelete = async (bookId: number) => {
    if (!confirm('Are you sure you want to delete this book?')) return;
    try {
      await deleteBook(bookId);
      if (editingBook?.id === bookId) setEditingBook(null);
      loadBooks();
      showMessage('success', 'Book deleted');
    } catch {
      showMessage('error', 'Failed to delete book');
    }
  };

  const chaptersPayload = () =>
    chapters.map(ch => ({
      id: ch.id,
      name: ch.name,
      description: ch.description || undefined,
      puzzle_ids: ch.puzzle_ids,
    }));

  const handleSave = async () => {
    if (!editingBook) return;
    setIsSaving(true);
    try {
      const updated = await updateBook(editingBook.id, {
        title,
        subtitle: subtitle || undefined,
        author: author || undefined,
        chapters: chaptersPayload(),
      });
      setEditingBook(updated);
      setChapters(updated.chapters && updated.chapters.length > 0 ? updated.chapters : chapters);
      loadBooks();
      showMessage('success', 'Book saved!');
    } catch {
      showMessage('error', 'Failed to save book');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = async () => {
    if (!editingBook) return;
    setIsExporting(true);
    try {
      await updateBook(editingBook.id, {
        title,
        subtitle: subtitle || undefined,
        author: author || undefined,
        chapters: chaptersPayload(),
      });
      await exportBookPdf(editingBook.id);
      const updated = await getBook(editingBook.id);
      setEditingBook(updated);
      loadBooks();
      showMessage('success', 'Book PDF exported!');
    } catch {
      showMessage('error', 'Failed to export PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const handleBack = () => {
    setEditingBook(null);
    loadBooks();
  };

  // --- Chapter management ---

  const addChapter = () => {
    setChapters(prev => [...prev, {
      id: crypto.randomUUID(),
      name: 'New Chapter',
      description: '',
      puzzle_ids: [],
      resolved_items: [],
    }]);
  };

  const updateChapterField = (id: string, field: 'name' | 'description', value: string) => {
    setChapters(prev => prev.map(ch => ch.id === id ? { ...ch, [field]: value } : ch));
  };

  const moveChapterUp = (idx: number) => {
    if (idx === 0) return;
    setChapters(prev => {
      const next = [...prev];
      [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
      return next;
    });
  };

  const moveChapterDown = (idx: number) => {
    if (idx >= chapters.length - 1) return;
    setChapters(prev => {
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  };

  const deleteChapter = (id: string) => {
    setChapters(prev => prev.filter(ch => ch.id !== id));
  };

  // --- Puzzle management within chapters ---

  const openPicker = (chapterId: string) => {
    setPickerTargetChapterId(chapterId);
    setShowPicker(true);
  };

  const handleAddPuzzles = (ids: number[]) => {
    if (!pickerTargetChapterId) return;
    setChapters(prev => prev.map(ch => {
      if (ch.id !== pickerTargetChapterId) return ch;
      return { ...ch, puzzle_ids: [...ch.puzzle_ids, ...ids] };
    }));
  };

  const movePuzzleUp = (chapterId: string, pIdx: number) => {
    if (pIdx === 0) return;
    setChapters(prev => prev.map(ch => {
      if (ch.id !== chapterId) return ch;
      const ids = [...ch.puzzle_ids];
      [ids[pIdx - 1], ids[pIdx]] = [ids[pIdx], ids[pIdx - 1]];
      const res = ch.resolved_items ? [...ch.resolved_items] : [];
      if (res.length > pIdx) [res[pIdx - 1], res[pIdx]] = [res[pIdx], res[pIdx - 1]];
      return { ...ch, puzzle_ids: ids, resolved_items: res };
    }));
  };

  const movePuzzleDown = (chapterId: string, pIdx: number, total: number) => {
    if (pIdx >= total - 1) return;
    setChapters(prev => prev.map(ch => {
      if (ch.id !== chapterId) return ch;
      const ids = [...ch.puzzle_ids];
      [ids[pIdx], ids[pIdx + 1]] = [ids[pIdx + 1], ids[pIdx]];
      const res = ch.resolved_items ? [...ch.resolved_items] : [];
      if (res.length > pIdx + 1) [res[pIdx], res[pIdx + 1]] = [res[pIdx + 1], res[pIdx]];
      return { ...ch, puzzle_ids: ids, resolved_items: res };
    }));
  };

  const removePuzzle = (chapterId: string, pIdx: number) => {
    setChapters(prev => prev.map(ch => {
      if (ch.id !== chapterId) return ch;
      return {
        ...ch,
        puzzle_ids: ch.puzzle_ids.filter((_, i) => i !== pIdx),
        resolved_items: ch.resolved_items?.filter((_, i) => i !== pIdx) || [],
      };
    }));
  };

  // Difficulty sort order
  const DIFFICULTY_ORDER: Record<string, number> = { Easy: 1, Medium: 2, Hard: 3, Expert: 4 };

  const sortChapterByDifficulty = (chapterId: string) => {
    setChapters(prev => prev.map(ch => {
      if (ch.id !== chapterId) return ch;
      const paired = ch.puzzle_ids.map((pid, i) => ({
        pid,
        resolved: (ch.resolved_items || [])[i] as BookResolvedItem | undefined,
      }));
      paired.sort((a, b) => {
        const da = DIFFICULTY_ORDER[a.resolved?.difficulty_label || ''] ?? 99;
        const db = DIFFICULTY_ORDER[b.resolved?.difficulty_label || ''] ?? 99;
        return da - db;
      });
      return {
        ...ch,
        puzzle_ids: paired.map(p => p.pid),
        resolved_items: paired.map(p => p.resolved).filter(Boolean) as BookResolvedItem[],
      };
    }));
  };

  // Build a flat resolved-item lookup across all chapters
  const resolvedMap = new Map<number, BookResolvedItem>();
  chapters.forEach(ch => (ch.resolved_items || []).forEach(r => resolvedMap.set(r.id, r)));

  const allPuzzleIds = chapters.flatMap(ch => ch.puzzle_ids);

  // --- RENDER ---

  if (editingBook) {
    const typeLabel = editingBook.book_type === 'crossword' ? 'Crossword' : 'Word Search';
    return (
      <div className="bb-editor">
        {message && <div className={`message message-${message.type}`}>{message.text}</div>}

        <div className="bb-toolbar">
          <button className="btn btn-secondary" onClick={handleBack}>Back</button>
          <input
            type="text"
            className="bb-title-input"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Book title..."
          />
          <span className="bb-type-badge">{typeLabel}</span>
          <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleExport}
            disabled={isExporting || allPuzzleIds.length === 0}
            title={allPuzzleIds.length === 0 ? 'Add puzzles first' : 'Export as PDF'}
          >
            {isExporting ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>

        <div className="bb-main">
          {/* Metadata sidebar */}
          <div className="bb-meta-panel">
            <h3>Book Details</h3>
            <label className="bb-field">
              <span className="bb-label">Subtitle</span>
              <input
                type="text"
                value={subtitle}
                onChange={e => setSubtitle(e.target.value)}
                placeholder="Optional subtitle..."
                className="bb-input"
              />
            </label>
            <label className="bb-field">
              <span className="bb-label">Author</span>
              <input
                type="text"
                value={author}
                onChange={e => setAuthor(e.target.value)}
                placeholder="Author name..."
                className="bb-input"
              />
            </label>
            <div className="bb-field">
              <span className="bb-label">Trim Size</span>
              <span className="bb-value">8.5" x 11"</span>
            </div>
            <div className="bb-field">
              <span className="bb-label">Chapters</span>
              <span className="bb-value">{chapters.length}</span>
            </div>
            <div className="bb-field">
              <span className="bb-label">Puzzles</span>
              <span className="bb-value">{allPuzzleIds.length}</span>
            </div>
            {editingBook.exported_at && (
              <div className="bb-field">
                <span className="bb-label">Last Exported</span>
                <span className="bb-value">{new Date(editingBook.exported_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>

          {/* Chapter panel */}
          <div className="bb-puzzle-panel">
            <div className="bb-puzzle-header">
              <h3>Chapters</h3>
              <button className="btn btn-secondary bb-add-btn" onClick={addChapter}>
                + Add Chapter
              </button>
            </div>

            {chapters.length === 0 ? (
              <p className="bb-empty">No chapters yet. Click "+ Add Chapter" to get started.</p>
            ) : (
              <div className="bb-chapters">
                {chapters.map((chapter, chIdx) => (
                  <div key={chapter.id} className="bb-chapter">
                    <div className="bb-chapter-header">
                      <span className="bb-chapter-badge">{chIdx + 1}</span>
                      <div className="bb-chapter-meta">
                        <input
                          className="bb-chapter-name"
                          value={chapter.name}
                          onChange={e => updateChapterField(chapter.id, 'name', e.target.value)}
                          placeholder="Chapter name..."
                        />
                        <input
                          className="bb-chapter-desc"
                          value={chapter.description || ''}
                          onChange={e => updateChapterField(chapter.id, 'description', e.target.value)}
                          placeholder="Brief description (optional)..."
                        />
                      </div>
                      <div className="bb-chapter-controls">
                        <button
                          className="bb-move-btn"
                          onClick={() => moveChapterUp(chIdx)}
                          disabled={chIdx === 0}
                          title="Move chapter up"
                        >&#9650;</button>
                        <button
                          className="bb-move-btn"
                          onClick={() => moveChapterDown(chIdx)}
                          disabled={chIdx === chapters.length - 1}
                          title="Move chapter down"
                        >&#9660;</button>
                        <button
                          className="btn btn-secondary bb-add-btn"
                          onClick={() => sortChapterByDifficulty(chapter.id)}
                          title="Sort by difficulty (Easy → Expert)"
                          disabled={chapter.puzzle_ids.length < 2}
                        >
                          Sort
                        </button>
                        <button
                          className="btn btn-secondary bb-add-btn"
                          onClick={() => openPicker(chapter.id)}
                        >
                          Add Puzzles
                        </button>
                        <button
                          className="bb-remove-btn"
                          onClick={() => deleteChapter(chapter.id)}
                          title="Delete chapter"
                        >&times;</button>
                      </div>
                    </div>

                    <div className="bb-chapter-puzzles">
                      {chapter.puzzle_ids.length === 0 ? (
                        <p className="bb-empty bb-chapter-empty">
                          No puzzles in this chapter.
                        </p>
                      ) : (
                        chapter.puzzle_ids.map((pid, pIdx) => {
                          const resolved = resolvedMap.get(pid);
                          return (
                            <div key={`${pid}-${pIdx}`} className="bb-puzzle-item">
                              <span className="bb-puzzle-num">{pIdx + 1}.</span>
                              <span className="bb-puzzle-title">
                                {resolved ? resolved.title : `Puzzle #${pid}`}
                              </span>
                              {resolved?.difficulty_label && (
                                <span className={`difficulty-badge difficulty-${resolved.difficulty_label.toLowerCase()}`}>
                                  {resolved.difficulty_label}
                                </span>
                              )}
                              {resolved && (
                                <span className={`bb-puzzle-status bb-status-${resolved.status}`}>
                                  {resolved.status}
                                </span>
                              )}
                              {!resolved && (
                                <span className="bb-puzzle-status bb-status-missing">missing</span>
                              )}
                              <div className="bb-puzzle-actions">
                                <button
                                  className="bb-move-btn"
                                  onClick={() => movePuzzleUp(chapter.id, pIdx)}
                                  disabled={pIdx === 0}
                                  title="Move up"
                                >&#9650;</button>
                                <button
                                  className="bb-move-btn"
                                  onClick={() => movePuzzleDown(chapter.id, pIdx, chapter.puzzle_ids.length)}
                                  disabled={pIdx === chapter.puzzle_ids.length - 1}
                                  title="Move down"
                                >&#9660;</button>
                                <button
                                  className="bb-remove-btn"
                                  onClick={() => removePuzzle(chapter.id, pIdx)}
                                  title="Remove"
                                >&times;</button>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <PuzzlePicker
          isOpen={showPicker}
          onClose={() => setShowPicker(false)}
          onAdd={handleAddPuzzles}
          bookType={editingBook.book_type}
          existingIds={allPuzzleIds}
        />
      </div>
    );
  }

  // --- LIST MODE ---
  return (
    <div className="bb-list">
      {message && <div className={`message message-${message.type}`}>{message.text}</div>}

      <div className="bb-list-header">
        <h2>Books</h2>
        <div className="bb-list-actions">
          {showCreateChoice ? (
            <div className="bb-create-choice">
              <span className="bb-choice-label">Book type:</span>
              <button className="btn btn-primary" onClick={() => handleCreate('crossword')}>
                Crossword Book
              </button>
              <button className="btn btn-primary" onClick={() => handleCreate('wordsearch')}>
                Word Search Book
              </button>
              <button className="btn btn-secondary" onClick={() => setShowCreateChoice(false)}>
                Cancel
              </button>
            </div>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowCreateChoice(true)}>
              New Book
            </button>
          )}
        </div>
      </div>

      {books.length === 0 ? (
        <div className="bb-no-books">
          <p>No books yet. Create one to start compiling puzzles into a printable book.</p>
        </div>
      ) : (
        <div className="bb-book-grid">
          {books.map(book => (
            <div key={book.id} className="bb-book-card">
              <div className="bb-card-body">
                <h3 className="bb-card-title">{book.title}</h3>
                {book.subtitle && <p className="bb-card-subtitle">{book.subtitle}</p>}
                <div className="bb-card-meta">
                  <span className="bb-type-badge">
                    {book.book_type === 'crossword' ? 'Crossword' : 'Word Search'}
                  </span>
                  <span>{book.puzzle_ids.length} puzzle{book.puzzle_ids.length !== 1 ? 's' : ''}</span>
                  {book.chapters && book.chapters.length > 0 && (
                    <span>{book.chapters.length} chapter{book.chapters.length !== 1 ? 's' : ''}</span>
                  )}
                  <span className={`bb-status-badge bb-status-${book.status}`}>{book.status}</span>
                </div>
                <p className="bb-card-date">
                  Updated {new Date(book.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div className="bb-card-actions">
                <button className="btn btn-small" onClick={() => handleLoad(book.id)}>Open</button>
                <button className="btn btn-small btn-danger" onClick={() => handleDelete(book.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
