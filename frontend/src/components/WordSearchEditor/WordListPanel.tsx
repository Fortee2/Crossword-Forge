import { useState } from 'react';
import { WordSearchConfig, WordSearchPlacement } from '../../types';

function getWordLengthLimits(config: WordSearchConfig): { min: number; max: number } {
  const size = Math.min(config.rows, config.cols);
  if (size <= 10) return { min: 3, max: 7 };
  if (size <= 15) return { min: 4, max: 10 };
  return { min: 5, max: 15 };
}

interface WordListPanelProps {
  words: string[];
  placements: WordSearchPlacement[];
  unplaced: string[];
  highlightMode: boolean;
  selectedWord: string | null;
  onWordSelect: (word: string | null) => void;
  onWordsChange: (words: string[]) => void;
  onOpenDbSearch: () => void;
  config: WordSearchConfig;
}

export function WordListPanel({
  words,
  placements,
  unplaced,
  highlightMode,
  selectedWord,
  onWordSelect,
  onWordsChange,
  onOpenDbSearch,
  config,
}: WordListPanelProps) {
  const [inputText, setInputText] = useState('');
  const [addInput, setAddInput] = useState('');
  const [validationMsg, setValidationMsg] = useState<string | null>(null);

  const placedSet = new Set(placements.map(p => p.word));
  const unplacedSet = new Set(unplaced);
  const { min, max } = getWordLengthLimits(config);

  const showValidation = (msg: string) => {
    setValidationMsg(msg);
    setTimeout(() => setValidationMsg(null), 3000);
  };

  const handleBulkBlur = () => {
    if (!inputText.trim()) return;
    const cleaned = inputText
      .split('\n')
      .map(w => w.trim().toUpperCase().replace(/[^A-Z]/g, ''))
      .filter(w => w.length > 0);
    const valid = cleaned.filter(w => w.length >= min && w.length <= max);
    const skipped = cleaned.length - valid.length;
    const merged = Array.from(new Set([...words, ...valid]));
    onWordsChange(merged);
    setInputText('');
    if (skipped > 0) {
      showValidation(`${skipped} word${skipped !== 1 ? 's' : ''} skipped — must be ${min}–${max} letters for a ${config.rows}×${config.cols} grid.`);
    }
  };

  const handleAdd = () => {
    const word = addInput.trim().toUpperCase().replace(/[^A-Z]/g, '');
    if (!word) return;
    if (word.length < min || word.length > max) {
      showValidation(`"${word}" must be ${min}–${max} letters for a ${config.rows}×${config.cols} grid.`);
      return;
    }
    if (!words.includes(word)) {
      onWordsChange([...words, word]);
    }
    setAddInput('');
  };

  const handleRemove = (word: string) => {
    onWordsChange(words.filter(w => w !== word));
    if (selectedWord === word) onWordSelect(null);
  };

  const handleWordClick = (word: string) => {
    if (!highlightMode) return;
    onWordSelect(selectedWord === word ? null : word);
  };

  return (
    <div className="ws-word-panel">
      <div className="ws-word-panel-header">
        <h3>Word List</h3>
        <span className="ws-word-count">{words.length} word{words.length !== 1 ? 's' : ''}</span>
      </div>

      {validationMsg && (
        <div className="ws-validation-msg">{validationMsg}</div>
      )}

      <div className="ws-add-row">
        <input
          type="text"
          className="ws-add-input"
          placeholder="Add a word..."
          value={addInput}
          onChange={e => setAddInput(e.target.value.toUpperCase())}
          onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button className="btn btn-secondary ws-add-btn" onClick={handleAdd}>Add</button>
        <button className="btn btn-secondary ws-add-btn" onClick={onOpenDbSearch}>From DB</button>
      </div>

      <div className="ws-word-list">
        {words.length === 0 ? (
          <p className="ws-no-words">No words yet. Add some above or paste below.</p>
        ) : (
          words.map(word => {
            const isPlaced = placedSet.has(word);
            const isUnplaced = unplacedSet.has(word);
            const isSelected = selectedWord === word;
            return (
              <div
                key={word}
                className={`ws-word-item${isSelected ? ' ws-word-selected' : ''}${highlightMode ? ' ws-word-clickable' : ''}`}
                onClick={() => handleWordClick(word)}
              >
                <span className="ws-word-text">{word}</span>
                {placements.length > 0 && (
                  <span className={`ws-word-status ${isPlaced ? 'ws-placed' : isUnplaced ? 'ws-unplaced' : 'ws-pending'}`}>
                    {isPlaced ? '✓' : isUnplaced ? '✗' : '·'}
                  </span>
                )}
                <button
                  className="ws-remove-btn"
                  onClick={e => { e.stopPropagation(); handleRemove(word); }}
                  title="Remove word"
                >
                  ×
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="ws-bulk-section">
        <label className="ws-label">Paste multiple words (one per line):</label>
        <textarea
          className="ws-bulk-textarea"
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onBlur={handleBulkBlur}
          placeholder="APPLE&#10;BANANA&#10;CHERRY"
          rows={4}
        />
      </div>
    </div>
  );
}
