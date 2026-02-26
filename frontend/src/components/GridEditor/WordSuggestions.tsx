import { useState, useEffect, useCallback } from 'react';
import { WordSuggestion, WordEntry, ClueInfo } from '../../types';
import { getWordSuggestions } from '../../api/answers';
import './WordSuggestions.css';

interface WordSuggestionsProps {
  selectedWord: WordEntry | null;
  onSelectWord: (word: string) => void;
  onSelectClue?: (clue: ClueInfo) => void;
}

export function WordSuggestions({ selectedWord, onSelectWord, onSelectClue }: WordSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<WordSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedWord, setExpandedWord] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSuggestions = useCallback(async () => {
    if (!selectedWord || !selectedWord.word.includes('_')) {
      setSuggestions([]);
      return;
    }

    // Don't fetch for completed words
    const hasUnfilled = selectedWord.word.includes('_');
    if (!hasUnfilled) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const results = await getWordSuggestions({
        pattern: selectedWord.word,
        limit: 20,
      });
      setSuggestions(results);
    } catch {
      setError('Could not load suggestions');
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedWord]);

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      loadSuggestions();
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [loadSuggestions]);

  const handleWordClick = (word: WordSuggestion) => {
    if (word.clues.length > 0) {
      setExpandedWord(expandedWord === word.id ? null : word.id);
    } else {
      onSelectWord(word.word);
    }
  };

  const handleFillWord = (word: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectWord(word);
  };

  const handleSelectClue = (clue: ClueInfo, word: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectWord(word);
    onSelectClue?.(clue);
  };

  const renderDifficultyStars = (difficulty: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={`star ${i < difficulty ? 'filled' : ''}`}>
        {i < difficulty ? '\u2605' : '\u2606'}
      </span>
    ));
  };

  if (!selectedWord) {
    return (
      <div className="word-suggestions">
        <h4>Word Suggestions</h4>
        <p className="no-selection">Select a word slot to see suggestions</p>
      </div>
    );
  }

  const pattern = selectedWord.word;
  const hasUnfilled = pattern.includes('_');

  if (!hasUnfilled) {
    return (
      <div className="word-suggestions">
        <h4>Word Suggestions</h4>
        <p className="complete-word">Word is complete: {pattern}</p>
      </div>
    );
  }

  return (
    <div className="word-suggestions">
      <h4>Word Suggestions</h4>
      <div className="pattern-display">
        Pattern: <span className="pattern">{pattern}</span>
        <span className="word-info">
          ({selectedWord.number} {selectedWord.direction})
        </span>
      </div>

      {isLoading && <div className="loading">Searching...</div>}

      {error && <div className="error">{error}</div>}

      {!isLoading && !error && suggestions.length === 0 && (
        <div className="no-matches">No matching words in database</div>
      )}

      {!isLoading && suggestions.length > 0 && (
        <ul className="suggestions-list">
          {suggestions.map((suggestion) => (
            <li
              key={suggestion.id}
              className={`suggestion-item ${expandedWord === suggestion.id ? 'expanded' : ''}`}
            >
              <div
                className="suggestion-header"
                onClick={() => handleWordClick(suggestion)}
              >
                <span className="suggestion-word">{suggestion.word}</span>
                <div className="suggestion-actions">
                  {suggestion.clues.length > 0 && (
                    <span className="clue-count">
                      {suggestion.clues.length} clue{suggestion.clues.length !== 1 ? 's' : ''}
                    </span>
                  )}
                  <button
                    className="fill-btn"
                    onClick={(e) => handleFillWord(suggestion.word, e)}
                    title="Fill in grid"
                  >
                    Fill
                  </button>
                </div>
              </div>

              {expandedWord === suggestion.id && suggestion.clues.length > 0 && (
                <div className="clues-dropdown">
                  {suggestion.clues.map((clue) => (
                    <div
                      key={clue.id}
                      className="clue-option"
                      onClick={(e) => handleSelectClue(clue, suggestion.word, e)}
                    >
                      <div className="clue-text">{clue.clue_text}</div>
                      <div className="clue-meta">
                        <span className="clue-difficulty">
                          {renderDifficultyStars(clue.difficulty)}
                        </span>
                        {clue.tags && (
                          <span className="clue-tags">
                            {clue.tags.split(',').slice(0, 2).map((tag, i) => (
                              <span key={i} className="tag">{tag.trim()}</span>
                            ))}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
