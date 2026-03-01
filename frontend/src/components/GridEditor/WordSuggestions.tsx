import { useState, useEffect, useCallback, useRef } from 'react';
import { WordSuggestion, WordEntry, ClueInfo, GridCell } from '../../types';
import { suggestWords } from '../../api/answers';
import { getSuggestionsWithCrossings } from '../../api/puzzles';
import './WordSuggestions.css';

interface WordSuggestionsProps {
  selectedWord: WordEntry | null;
  onSelectWord: (word: string) => void;
  onSelectClue?: (clue: ClueInfo) => void;
  grid?: GridCell[][];
}

function getCrossingScoreClass(score: number | undefined): string {
  if (score === undefined) return '';
  if (score === 0) return 'crossing-danger';
  if (score <= 4) return 'crossing-danger';
  if (score <= 19) return 'crossing-tight';
  if (score <= 99) return 'crossing-okay';
  return 'crossing-good';
}

function getCrossingScoreLabel(score: number | undefined): string {
  if (score === undefined) return '';
  if (score >= 99999) return 'unconstrained';
  return `${score} crossings`;
}

export function WordSuggestions({ selectedWord, onSelectWord, onSelectClue, grid }: WordSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<WordSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingCrossings, setIsLoadingCrossings] = useState(false);
  const [expandedWord, setExpandedWord] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  // Track the current request to avoid race conditions
  const requestIdRef = useRef(0);

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

    // Require minimum pattern length
    if (selectedWord.word.length < 2) {
      setSuggestions([]);
      return;
    }

    const currentRequestId = ++requestIdRef.current;
    setIsLoading(true);
    setError(null);

    try {
      // First, load basic suggestions quickly
      const results = await suggestWords({
        pattern: selectedWord.word,
        limit: 30,
      });

      // Check if this request is still current
      if (currentRequestId !== requestIdRef.current) return;

      setSuggestions(results);
      setIsLoading(false);

      // If we have grid data, load crossing analysis in the background
      if (grid && results.length > 0) {
        setIsLoadingCrossings(true);
        try {
          const crossingResults = await getSuggestionsWithCrossings({
            grid_data: grid,
            row: selectedWord.row,
            col: selectedWord.col,
            direction: selectedWord.direction,
            limit: 30,
          });

          // Check if this request is still current
          if (currentRequestId !== requestIdRef.current) return;

          // Update suggestions with crossing data
          setSuggestions(crossingResults.suggestions);
        } catch {
          // Crossing analysis failed, keep basic suggestions
          console.warn('Crossing analysis failed, using basic suggestions');
        } finally {
          if (currentRequestId === requestIdRef.current) {
            setIsLoadingCrossings(false);
          }
        }
      }
    } catch {
      if (currentRequestId === requestIdRef.current) {
        setError('Could not load suggestions');
        setSuggestions([]);
        setIsLoading(false);
      }
    }
  }, [selectedWord, grid]);

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

  const hasCrossingData = suggestions.some(s => s.crossing_score !== undefined);

  return (
    <div className="word-suggestions">
      <h4>
        Word Suggestions
        {hasCrossingData && (
          <span
            className="crossing-help"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            ?
            {showTooltip && (
              <div className="crossing-tooltip">
                <strong>Crossing Score</strong>
                <p>Shows the minimum number of valid words that can fill the crossing slots after placing this word.</p>
                <ul>
                  <li><span className="color-good">Green (100+)</span>: Many options</li>
                  <li><span className="color-okay">Blue (20-99)</span>: Good options</li>
                  <li><span className="color-tight">Yellow (5-19)</span>: Limited</li>
                  <li><span className="color-danger">Red (0-4)</span>: Risky</li>
                </ul>
              </div>
            )}
          </span>
        )}
      </h4>
      <div className="pattern-display">
        Pattern: <span className="pattern">{pattern}</span>
        <span className="word-info">
          ({selectedWord.number} {selectedWord.direction})
        </span>
        {isLoadingCrossings && (
          <span className="crossing-loading">Analyzing crossings...</span>
        )}
      </div>

      {isLoading && <div className="loading">Searching...</div>}

      {error && <div className="error">{error}</div>}

      {!isLoading && !error && suggestions.length === 0 && (
        <div className="no-matches">No matching words in database</div>
      )}

      {!isLoading && suggestions.length > 0 && (
        <ul className="suggestions-list">
          {suggestions.map((suggestion) => {
            const crossingClass = getCrossingScoreClass(suggestion.crossing_score);
            const isUnfillable = suggestion.crossing_score === 0;

            return (
              <li
                key={suggestion.id}
                className={`suggestion-item ${expandedWord === suggestion.id ? 'expanded' : ''} ${isUnfillable ? 'unfillable' : ''}`}
              >
                <div
                  className="suggestion-header"
                  onClick={() => handleWordClick(suggestion)}
                >
                  <div className="suggestion-word-info">
                    <span className={`suggestion-word ${isUnfillable ? 'grayed' : ''}`}>
                      {suggestion.display || suggestion.word}
                    </span>
                    <span className="suggestion-score" title={`Word score: ${suggestion.score || 100}`}>
                      {suggestion.score || 100}
                    </span>
                    {suggestion.crossing_score !== undefined && (
                      <span
                        className={`crossing-score ${crossingClass}`}
                        title={getCrossingScoreLabel(suggestion.crossing_score)}
                      >
                        {isUnfillable && <span className="warning-icon">!</span>}
                        {suggestion.crossing_score >= 99999 ? '\u221e' : suggestion.crossing_score}
                      </span>
                    )}
                    {suggestion.source && suggestion.source !== 'user' && (
                      <span className="suggestion-source">{suggestion.source}</span>
                    )}
                  </div>
                  <div className="suggestion-actions">
                    {suggestion.clues.length > 0 && (
                      <span className="clue-count">
                        {suggestion.clues.length} clue{suggestion.clues.length !== 1 ? 's' : ''}
                      </span>
                    )}
                    <button
                      className={`fill-btn ${isUnfillable ? 'fill-btn-warning' : ''}`}
                      onClick={(e) => handleFillWord(suggestion.word, e)}
                      title={isUnfillable ? 'Warning: No valid crossings' : 'Fill in grid'}
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
            );
          })}
        </ul>
      )}
    </div>
  );
}
