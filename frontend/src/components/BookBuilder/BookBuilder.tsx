import { useState, useEffect, useCallback } from 'react';
import { Book, BookResolvedItem } from '../../types';
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
  const [puzzleIds, setPuzzleIds] = useState<number[]>([]);
  const [resolvedItems, setResolvedItems] = useState<BookResolvedItem[]>([]);

  const [showPicker, setShowPicker] = useState(false);
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
    setPuzzleIds(book.puzzle_ids);
    setResolvedItems(book.resolved_items || []);
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

  const handleSave = async () => {
    if (!editingBook) return;
    setIsSaving(true);
    try {
      const updated = await updateBook(editingBook.id, { title, subtitle: subtitle || undefined, author: author || undefined, puzzle_ids: puzzleIds });
      setEditingBook(updated);
      setResolvedItems(updated.resolved_items || []);
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
    // Save first to persist any pending changes
    setIsExporting(true);
    try {
      await updateBook(editingBook.id, { title, subtitle: subtitle || undefined, author: author || undefined, puzzle_ids: puzzleIds });
      await exportBookPdf(editingBook.id);
      // Refresh to get updated status/exported_at
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

  const handleAddPuzzles = (ids: number[]) => {
    setPuzzleIds(prev => [...prev, ...ids]);
    // We won't know the titles until we save and reload — mark as needing save
  };

  const handleRemove = (index: number) => {
    setPuzzleIds(prev => prev.filter((_, i) => i !== index));
    setResolvedItems(prev => prev.filter((_, i) => i !== index));
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    setPuzzleIds(prev => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next;
    });
    setResolvedItems(prev => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next;
    });
  };

  const handleMoveDown = (index: number) => {
    if (index >= puzzleIds.length - 1) return;
    setPuzzleIds(prev => {
      const next = [...prev];
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
      return next;
    });
    setResolvedItems(prev => {
      const next = [...prev];
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
      return next;
    });
  };

  const handleBack = () => {
    setEditingBook(null);
    loadBooks();
  };

  // Build a lookup for resolved items by id
  const resolvedMap = new Map(resolvedItems.map(r => [r.id, r]));

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
            disabled={isExporting || puzzleIds.length === 0}
            title={puzzleIds.length === 0 ? 'Add puzzles first' : 'Export as PDF'}
          >
            {isExporting ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>

        <div className="bb-main">
          {/* Metadata */}
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
              <span className="bb-label">Puzzles</span>
              <span className="bb-value">{puzzleIds.length}</span>
            </div>
            {editingBook.exported_at && (
              <div className="bb-field">
                <span className="bb-label">Last Exported</span>
                <span className="bb-value">{new Date(editingBook.exported_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>

          {/* Puzzle list */}
          <div className="bb-puzzle-panel">
            <div className="bb-puzzle-header">
              <h3>Puzzles</h3>
              <button className="btn btn-secondary bb-add-btn" onClick={() => setShowPicker(true)}>
                Add Puzzles
              </button>
            </div>

            {puzzleIds.length === 0 ? (
              <p className="bb-empty">No puzzles added yet. Click "Add Puzzles" to get started.</p>
            ) : (
              <div className="bb-puzzle-list">
                {puzzleIds.map((pid, index) => {
                  const resolved = resolvedMap.get(pid);
                  return (
                    <div key={`${pid}-${index}`} className="bb-puzzle-item">
                      <span className="bb-puzzle-num">{index + 1}.</span>
                      <span className="bb-puzzle-title">
                        {resolved ? resolved.title : `Puzzle #${pid}`}
                      </span>
                      {resolved && (
                        <span className={`bb-puzzle-status bb-status-${resolved.status}`}>
                          {resolved.status}
                        </span>
                      )}
                      {!resolved && <span className="bb-puzzle-status bb-status-missing">missing</span>}
                      <div className="bb-puzzle-actions">
                        <button
                          className="bb-move-btn"
                          onClick={() => handleMoveUp(index)}
                          disabled={index === 0}
                          title="Move up"
                        >
                          &#9650;
                        </button>
                        <button
                          className="bb-move-btn"
                          onClick={() => handleMoveDown(index)}
                          disabled={index === puzzleIds.length - 1}
                          title="Move down"
                        >
                          &#9660;
                        </button>
                        <button
                          className="bb-remove-btn"
                          onClick={() => handleRemove(index)}
                          title="Remove"
                        >
                          &times;
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <PuzzlePicker
          isOpen={showPicker}
          onClose={() => setShowPicker(false)}
          onAdd={handleAddPuzzles}
          bookType={editingBook.book_type}
          existingIds={puzzleIds}
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
