import { useRef, useEffect } from 'react';
import { WordEntry } from '../../types';
import './CluePanel.css';

interface CluePanelProps {
  selectedWord: WordEntry | null;
  clues: Map<string, string>;
  onClueChange: (key: string, clue: string) => void;
  onClose: () => void;
}

function getClueKey(word: WordEntry): string {
  return `${word.direction}-${word.number}`;
}

export default function CluePanel({
  selectedWord,
  clues,
  onClueChange,
  onClose,
}: CluePanelProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (selectedWord && inputRef.current) {
      inputRef.current.focus();
    }
  }, [selectedWord]);

  if (!selectedWord) {
    return (
      <div className="clue-panel clue-panel-empty">
        <p>Click a word in the list to add or edit its clue.</p>
      </div>
    );
  }

  const clueKey = getClueKey(selectedWord);
  const currentClue = clues.get(clueKey) || '';

  return (
    <div className="clue-panel">
      <div className="clue-panel-header">
        <div className="clue-word-info">
          <span className="clue-number">{selectedWord.number}</span>
          <span className="clue-direction">
            {selectedWord.direction === 'across' ? 'Across' : 'Down'}
          </span>
        </div>
        <button className="clue-close-btn" onClick={onClose} title="Close">
          ×
        </button>
      </div>
      <div className="clue-word-display">{selectedWord.word}</div>
      <div className="clue-input-container">
        <label htmlFor="clue-input">Clue:</label>
        <textarea
          ref={inputRef}
          id="clue-input"
          className="clue-input"
          value={currentClue}
          onChange={(e) => onClueChange(clueKey, e.target.value)}
          placeholder="Enter clue for this word..."
          rows={3}
        />
      </div>
    </div>
  );
}

export { getClueKey };
