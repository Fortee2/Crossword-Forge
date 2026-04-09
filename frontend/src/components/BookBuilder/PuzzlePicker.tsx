import { useState, useEffect, useCallback } from 'react';
import { Puzzle, WordSearchPuzzle } from '../../types';
import { getPuzzles } from '../../api/puzzles';
import { getWordSearches } from '../../api/wordSearches';

interface PuzzlePickerProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (ids: number[]) => void;
  bookType: 'crossword' | 'wordsearch';
  existingIds: number[];
}

export function PuzzlePicker({ isOpen, onClose, onAdd, bookType, existingIds }: PuzzlePickerProps) {
  const [items, setItems] = useState<{ id: number; title: string; status: string; updatedAt: string }[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(false);

  const existingSet = new Set(existingIds);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      if (bookType === 'crossword') {
        const data: Puzzle[] = await getPuzzles();
        setItems(data.map(p => ({ id: p.id, title: p.title, status: p.status, updatedAt: p.updated_at })));
      } else {
        const data: WordSearchPuzzle[] = await getWordSearches();
        setItems(data.map(p => ({ id: p.id, title: p.title, status: p.status, updatedAt: p.updated_at })));
      }
    } catch {
      // Server might not be running
    } finally {
      setIsLoading(false);
    }
  }, [bookType]);

  useEffect(() => {
    if (isOpen) {
      load();
      setSelected(new Set());
    }
  }, [isOpen, load]);

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAdd = () => {
    onAdd(Array.from(selected));
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="bb-modal-backdrop" onClick={onClose}>
      <div className="bb-modal" onClick={e => e.stopPropagation()}>
        <div className="bb-modal-header">
          <h3>Add {bookType === 'crossword' ? 'Crossword Puzzles' : 'Word Searches'}</h3>
          <button className="bb-modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="bb-modal-results">
          {isLoading && <p className="bb-loading">Loading...</p>}
          {!isLoading && items.length === 0 && (
            <p className="bb-empty">No {bookType === 'crossword' ? 'puzzles' : 'word searches'} found. Create some first.</p>
          )}
          {items.map(item => {
            const isExisting = existingSet.has(item.id);
            const isSelected = selected.has(item.id);
            return (
              <label key={item.id} className={`bb-picker-item${isExisting ? ' bb-picker-existing' : ''}`}>
                <input
                  type="checkbox"
                  checked={isSelected || isExisting}
                  disabled={isExisting}
                  onChange={() => toggleSelect(item.id)}
                />
                <span className="bb-picker-title">{item.title}</span>
                <span className="bb-picker-meta">
                  {item.status}
                  {' \u00B7 '}
                  {new Date(item.updatedAt).toLocaleDateString()}
                </span>
                {isExisting && <span className="bb-picker-tag">in book</span>}
              </label>
            );
          })}
        </div>

        <div className="bb-modal-footer">
          <span className="bb-selected-count">{selected.size} selected</span>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleAdd} disabled={selected.size === 0}>
            Add Selected
          </button>
        </div>
      </div>
    </div>
  );
}
