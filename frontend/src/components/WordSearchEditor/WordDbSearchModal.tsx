import { useState, useEffect, useCallback } from 'react';
import { AnswerListItem } from '../../types';
import { getAnswers } from '../../api/answers';

interface WordDbSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddWords: (words: string[]) => void;
  existingWords: string[];
}

export function WordDbSearchModal({ isOpen, onClose, onAddWords, existingWords }: WordDbSearchModalProps) {
  const [query, setQuery] = useState('');
  const [minLength, setMinLength] = useState(4);
  const [maxLength, setMaxLength] = useState(15);
  const [results, setResults] = useState<AnswerListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);

  const existingSet = new Set(existingWords);

  const search = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getAnswers({
        q: query || undefined,
        min_length: minLength,
        max_length: maxLength,
        limit: 50,
        sort_by: 'score',
      });
      setResults(data);
    } catch {
      // Server might not be running
    } finally {
      setIsLoading(false);
    }
  }, [query, minLength, maxLength]);

  useEffect(() => {
    if (isOpen) {
      search();
      setSelected(new Set());
    }
  }, [isOpen, search]);

  const toggleSelect = (word: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(word)) next.delete(word);
      else next.add(word);
      return next;
    });
  };

  const handleAdd = () => {
    onAddWords(Array.from(selected));
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="ws-modal-backdrop" onClick={onClose}>
      <div className="ws-modal" onClick={e => e.stopPropagation()}>
        <div className="ws-modal-header">
          <h3>Add Words from Database</h3>
          <button className="ws-modal-close" onClick={onClose}>×</button>
        </div>

        <div className="ws-modal-filters">
          <input
            type="text"
            className="ws-add-input"
            placeholder="Search words..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') search(); }}
          />
          <div className="ws-filter-row">
            <label>
              Min length:
              <input
                type="number"
                min={1}
                max={30}
                value={minLength}
                onChange={e => setMinLength(+e.target.value)}
                className="ws-number-input"
              />
            </label>
            <label>
              Max length:
              <input
                type="number"
                min={1}
                max={30}
                value={maxLength}
                onChange={e => setMaxLength(+e.target.value)}
                className="ws-number-input"
              />
            </label>
            <button className="btn btn-secondary" onClick={search}>Search</button>
          </div>
        </div>

        <div className="ws-modal-results">
          {isLoading && <p className="ws-loading">Loading...</p>}
          {!isLoading && results.length === 0 && <p className="ws-no-words">No results found.</p>}
          {results.map(item => {
            const isExisting = existingSet.has(item.word);
            const isSelected = selected.has(item.word);
            return (
              <label key={item.id} className={`ws-db-item${isExisting ? ' ws-db-existing' : ''}`}>
                <input
                  type="checkbox"
                  checked={isSelected || isExisting}
                  disabled={isExisting}
                  onChange={() => toggleSelect(item.word)}
                />
                <span className="ws-db-word">{item.word}</span>
                <span className="ws-db-meta">{item.length} letters</span>
                {isExisting && <span className="ws-db-tag">already added</span>}
              </label>
            );
          })}
        </div>

        <div className="ws-modal-footer">
          <span className="ws-selected-count">{selected.size} selected</span>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            onClick={handleAdd}
            disabled={selected.size === 0}
          >
            Add Selected
          </button>
        </div>
      </div>
    </div>
  );
}
