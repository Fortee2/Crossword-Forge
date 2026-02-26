import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { GridCell, WordEntry, NumberedCell, ValidationResult, WordPlacement, ClueInfo } from '../../types';
import { validateGrid } from '../../api/puzzles';
import CluePanel, { getClueKey } from './CluePanel';
import { WordSuggestions } from './WordSuggestions';
import './GridEditor.css';

const GRID_SIZE = 15;

function createEmptyGrid(): GridCell[][] {
  return Array(GRID_SIZE)
    .fill(null)
    .map(() =>
      Array(GRID_SIZE)
        .fill(null)
        .map(() => ({ isBlack: false, letter: '' }))
    );
}

function calculateNumberedCells(grid: GridCell[][]): NumberedCell[] {
  const numbered: NumberedCell[] = [];
  let currentNumber = 1;

  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      if (grid[row][col].isBlack) continue;

      const startsAcross =
        (col === 0 || grid[row][col - 1].isBlack) &&
        col < GRID_SIZE - 1 &&
        !grid[row][col + 1].isBlack;

      const startsDown =
        (row === 0 || grid[row - 1][col].isBlack) &&
        row < GRID_SIZE - 1 &&
        !grid[row + 1][col].isBlack;

      if (startsAcross || startsDown) {
        numbered.push({ row, col, number: currentNumber });
        currentNumber++;
      }
    }
  }

  return numbered;
}

function extractWords(
  grid: GridCell[][],
  numberedCells: NumberedCell[]
): { across: WordEntry[]; down: WordEntry[] } {
  const across: WordEntry[] = [];
  const down: WordEntry[] = [];
  const numberMap = new Map<string, number>();

  numberedCells.forEach((nc) => {
    numberMap.set(`${nc.row},${nc.col}`, nc.number);
  });

  for (let row = 0; row < GRID_SIZE; row++) {
    let col = 0;
    while (col < GRID_SIZE) {
      if (grid[row][col].isBlack) {
        col++;
        continue;
      }

      const startCol = col;
      let word = '';
      while (col < GRID_SIZE && !grid[row][col].isBlack) {
        word += grid[row][col].letter || '_';
        col++;
      }

      if (word.length >= 2) {
        const number = numberMap.get(`${row},${startCol}`);
        if (number) {
          across.push({ number, word, row, col: startCol, direction: 'across' });
        }
      }
    }
  }

  for (let col = 0; col < GRID_SIZE; col++) {
    let row = 0;
    while (row < GRID_SIZE) {
      if (grid[row][col].isBlack) {
        row++;
        continue;
      }

      const startRow = row;
      let word = '';
      while (row < GRID_SIZE && !grid[row][col].isBlack) {
        word += grid[row][col].letter || '_';
        row++;
      }

      if (word.length >= 2) {
        const number = numberMap.get(`${startRow},${col}`);
        if (number) {
          down.push({ number, word, row: startRow, col, direction: 'down' });
        }
      }
    }
  }

  return { across, down };
}

interface GridEditorProps {
  initialGrid?: GridCell[][];
  initialWordPlacements?: WordPlacement[];
  onGridChange?: (grid: GridCell[][]) => void;
  onWordPlacementsChange?: (placements: WordPlacement[]) => void;
}

export default function GridEditor({
  initialGrid,
  initialWordPlacements,
  onGridChange,
  onWordPlacementsChange,
}: GridEditorProps) {
  const [grid, setGrid] = useState<GridCell[][]>(initialGrid || createEmptyGrid);
  const [selectedCell, setSelectedCell] = useState<{ row: number; col: number } | null>(null);
  const [direction, setDirection] = useState<'across' | 'down'>('across');
  const [symmetryEnabled, setSymmetryEnabled] = useState(true);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [numberedCells, setNumberedCells] = useState<NumberedCell[]>([]);
  const [words, setWords] = useState<{ across: WordEntry[]; down: WordEntry[] }>({
    across: [],
    down: [],
  });
  const [selectedWord, setSelectedWord] = useState<WordEntry | null>(null);
  const [clues, setClues] = useState<Map<string, string>>(() => {
    const map = new Map<string, string>();
    if (initialWordPlacements) {
      initialWordPlacements.forEach((wp) => {
        if (wp.clue) {
          map.set(`${wp.direction}-${wp.number}`, wp.clue);
        }
      });
    }
    return map;
  });

  const cellRefs = useRef<(HTMLDivElement | null)[][]>(
    Array(GRID_SIZE)
      .fill(null)
      .map(() => Array(GRID_SIZE).fill(null))
  );

  const updateGrid = useCallback(
    (newGrid: GridCell[][]) => {
      setGrid(newGrid);
      const numbered = calculateNumberedCells(newGrid);
      setNumberedCells(numbered);
      setWords(extractWords(newGrid, numbered));
      onGridChange?.(newGrid);
    },
    [onGridChange]
  );

  useEffect(() => {
    const numbered = calculateNumberedCells(grid);
    setNumberedCells(numbered);
    setWords(extractWords(grid, numbered));
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const result = await validateGrid(grid, symmetryEnabled);
        setValidation(result);
      } catch {
        // Validation failed, likely server not running
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [grid, symmetryEnabled]);

  const handleWordClick = useCallback((word: WordEntry) => {
    setSelectedWord(word);
    setSelectedCell({ row: word.row, col: word.col });
    setDirection(word.direction);
    cellRefs.current[word.row][word.col]?.focus();
  }, []);

  const handleClueChange = useCallback(
    (key: string, clue: string) => {
      setClues((prev) => {
        const newClues = new Map(prev);
        if (clue) {
          newClues.set(key, clue);
        } else {
          newClues.delete(key);
        }
        return newClues;
      });
    },
    []
  );

  const handleCloseCluePanel = useCallback(() => {
    setSelectedWord(null);
  }, []);

  // Generate word placements with clues whenever words or clues change
  useEffect(() => {
    const allWords = [...words.across, ...words.down];
    const placements: WordPlacement[] = allWords.map((word) => ({
      word: word.word,
      clue: clues.get(getClueKey(word)) || undefined,
      row: word.row,
      col: word.col,
      direction: word.direction,
      number: word.number,
    }));
    onWordPlacementsChange?.(placements);
  }, [words, clues, onWordPlacementsChange]);

  const toggleBlackSquare = useCallback(
    (row: number, col: number) => {
      const newGrid = grid.map((r) => r.map((c) => ({ ...c })));
      const newIsBlack = !newGrid[row][col].isBlack;
      newGrid[row][col].isBlack = newIsBlack;
      newGrid[row][col].letter = '';

      if (symmetryEnabled) {
        const mirrorRow = GRID_SIZE - 1 - row;
        const mirrorCol = GRID_SIZE - 1 - col;
        newGrid[mirrorRow][mirrorCol].isBlack = newIsBlack;
        newGrid[mirrorRow][mirrorCol].letter = '';
      }

      updateGrid(newGrid);
    },
    [grid, symmetryEnabled, updateGrid]
  );

  const handleCellClick = useCallback(
    (row: number, col: number, e: React.MouseEvent) => {
      if (grid[row][col].isBlack) {
        if (e.shiftKey || e.metaKey) {
          toggleBlackSquare(row, col);
        }
        return;
      }

      if (selectedCell?.row === row && selectedCell?.col === col) {
        setDirection((d) => (d === 'across' ? 'down' : 'across'));
      } else {
        setSelectedCell({ row, col });
      }
      cellRefs.current[row][col]?.focus();
    },
    [grid, selectedCell, toggleBlackSquare]
  );

  const handleCellRightClick = useCallback(
    (row: number, col: number, e: React.MouseEvent) => {
      e.preventDefault();
      toggleBlackSquare(row, col);
    },
    [toggleBlackSquare]
  );

  const moveToNextCell = useCallback(
    (row: number, col: number, forward: boolean = true) => {
      let newRow = row;
      let newCol = col;

      if (direction === 'across') {
        newCol = forward ? col + 1 : col - 1;
      } else {
        newRow = forward ? row + 1 : row - 1;
      }

      if (newRow >= 0 && newRow < GRID_SIZE && newCol >= 0 && newCol < GRID_SIZE) {
        if (!grid[newRow][newCol].isBlack) {
          setSelectedCell({ row: newRow, col: newCol });
          cellRefs.current[newRow][newCol]?.focus();
        }
      }
    },
    [direction, grid]
  );

  const handleKeyDown = useCallback(
    (row: number, col: number, e: React.KeyboardEvent) => {
      if (grid[row][col].isBlack) return;

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (row > 0 && !grid[row - 1][col].isBlack) {
          setSelectedCell({ row: row - 1, col });
          cellRefs.current[row - 1][col]?.focus();
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (row < GRID_SIZE - 1 && !grid[row + 1][col].isBlack) {
          setSelectedCell({ row: row + 1, col });
          cellRefs.current[row + 1][col]?.focus();
        }
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (col > 0 && !grid[row][col - 1].isBlack) {
          setSelectedCell({ row, col: col - 1 });
          cellRefs.current[row][col - 1]?.focus();
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (col < GRID_SIZE - 1 && !grid[row][col + 1].isBlack) {
          setSelectedCell({ row, col: col + 1 });
          cellRefs.current[row][col + 1]?.focus();
        }
      } else if (e.key === 'Backspace') {
        e.preventDefault();
        const newGrid = grid.map((r) => r.map((c) => ({ ...c })));
        if (newGrid[row][col].letter) {
          newGrid[row][col].letter = '';
          updateGrid(newGrid);
        } else {
          moveToNextCell(row, col, false);
        }
      } else if (e.key === 'Delete') {
        e.preventDefault();
        const newGrid = grid.map((r) => r.map((c) => ({ ...c })));
        newGrid[row][col].letter = '';
        updateGrid(newGrid);
      } else if (e.key === 'Tab') {
        e.preventDefault();
        setDirection((d) => (d === 'across' ? 'down' : 'across'));
      } else if (e.key === ' ') {
        e.preventDefault();
        setDirection((d) => (d === 'across' ? 'down' : 'across'));
      } else if (/^[a-zA-Z]$/.test(e.key)) {
        e.preventDefault();
        const newGrid = grid.map((r) => r.map((c) => ({ ...c })));
        newGrid[row][col].letter = e.key.toUpperCase();
        updateGrid(newGrid);
        moveToNextCell(row, col, true);
      }
    },
    [grid, moveToNextCell, updateGrid]
  );

  const getNumberForCell = (row: number, col: number): number | null => {
    const cell = numberedCells.find((nc) => nc.row === row && nc.col === col);
    return cell ? cell.number : null;
  };

  const isHighlighted = (row: number, col: number): boolean => {
    if (!selectedCell || grid[row][col].isBlack) return false;
    if (selectedCell.row === row && selectedCell.col === col) return true;

    if (direction === 'across' && row === selectedCell.row) {
      let startCol = selectedCell.col;
      while (startCol > 0 && !grid[row][startCol - 1].isBlack) startCol--;
      let endCol = selectedCell.col;
      while (endCol < GRID_SIZE - 1 && !grid[row][endCol + 1].isBlack) endCol++;
      return col >= startCol && col <= endCol;
    }

    if (direction === 'down' && col === selectedCell.col) {
      let startRow = selectedCell.row;
      while (startRow > 0 && !grid[startRow - 1][col].isBlack) startRow--;
      let endRow = selectedCell.row;
      while (endRow < GRID_SIZE - 1 && !grid[endRow + 1][col].isBlack) endRow++;
      return row >= startRow && row <= endRow;
    }

    return false;
  };

  const clearGrid = () => {
    updateGrid(createEmptyGrid());
    setSelectedCell(null);
  };

  // Find the current word based on selected cell and direction
  const currentWord = useMemo((): WordEntry | null => {
    if (!selectedCell) return null;

    const { row, col } = selectedCell;
    if (grid[row][col].isBlack) return null;

    const wordList = direction === 'across' ? words.across : words.down;

    // Find the word that contains this cell
    for (const word of wordList) {
      if (direction === 'across') {
        if (word.row === row && col >= word.col && col < word.col + word.word.length) {
          return word;
        }
      } else {
        if (word.col === col && row >= word.row && row < word.row + word.word.length) {
          return word;
        }
      }
    }

    return null;
  }, [selectedCell, direction, words, grid]);

  // Fill in a suggested word
  const handleFillSuggestedWord = useCallback(
    (word: string) => {
      if (!currentWord) return;

      const newGrid = grid.map((r) => r.map((c) => ({ ...c })));

      if (currentWord.direction === 'across') {
        for (let i = 0; i < word.length; i++) {
          const col = currentWord.col + i;
          if (col < GRID_SIZE) {
            newGrid[currentWord.row][col].letter = word[i];
          }
        }
      } else {
        for (let i = 0; i < word.length; i++) {
          const row = currentWord.row + i;
          if (row < GRID_SIZE) {
            newGrid[row][currentWord.col].letter = word[i];
          }
        }
      }

      updateGrid(newGrid);
    },
    [currentWord, grid, updateGrid]
  );

  // Handle selecting a clue from suggestions
  const handleSelectSuggestedClue = useCallback(
    (clue: ClueInfo) => {
      if (!currentWord) return;

      const key = getClueKey(currentWord);
      handleClueChange(key, clue.clue_text);
    },
    [currentWord, handleClueChange]
  );

  return (
    <div className="grid-editor">
      <div className="toolbar">
        <label className="symmetry-toggle">
          <input
            type="checkbox"
            checked={symmetryEnabled}
            onChange={(e) => setSymmetryEnabled(e.target.checked)}
          />
          Rotational Symmetry
        </label>
        <button onClick={clearGrid} className="clear-btn">
          Clear Grid
        </button>
        <span className="direction-indicator">
          Direction: {direction === 'across' ? 'Across →' : 'Down ↓'}
        </span>
      </div>

      <div className="main-content">
        <div className="grid-container">
          <div className="grid">
            {grid.map((row, rowIndex) => (
              <div key={rowIndex} className="grid-row">
                {row.map((cell, colIndex) => {
                  const cellNumber = getNumberForCell(rowIndex, colIndex);
                  const isSelected =
                    selectedCell?.row === rowIndex && selectedCell?.col === colIndex;
                  const highlighted = isHighlighted(rowIndex, colIndex);

                  return (
                    <div
                      key={colIndex}
                      ref={(el) => {
                        cellRefs.current[rowIndex][colIndex] = el;
                      }}
                      className={`grid-cell ${cell.isBlack ? 'black' : ''} ${
                        isSelected ? 'selected' : ''
                      } ${highlighted && !isSelected ? 'highlighted' : ''}`}
                      onClick={(e) => handleCellClick(rowIndex, colIndex, e)}
                      onContextMenu={(e) => handleCellRightClick(rowIndex, colIndex, e)}
                      onKeyDown={(e) => handleKeyDown(rowIndex, colIndex, e)}
                      tabIndex={cell.isBlack ? -1 : 0}
                    >
                      {cellNumber && <span className="cell-number">{cellNumber}</span>}
                      {!cell.isBlack && <span className="cell-letter">{cell.letter}</span>}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {validation && validation.warnings.length > 0 && (
            <div className="validation-warnings">
              <h4>Warnings</h4>
              <ul>
                {validation.warnings.map((warning, index) => (
                  <li key={index} className={`warning-${warning.type}`}>
                    {warning.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="sidebar">
          <div className="word-lists">
            <div className="word-list">
              <h3>Across</h3>
              <ul>
                {words.across.map((entry) => {
                  const hasClue = clues.has(getClueKey(entry));
                  const isActive =
                    selectedWord?.number === entry.number &&
                    selectedWord?.direction === 'across';
                  return (
                    <li
                      key={`across-${entry.number}`}
                      className={`word-item ${hasClue ? 'has-clue' : 'no-clue'} ${isActive ? 'active' : ''}`}
                      onClick={() => handleWordClick(entry)}
                    >
                      <span className="word-number">{entry.number}.</span>
                      <span className="word-text">{entry.word}</span>
                      <span className={`clue-indicator ${hasClue ? 'filled' : ''}`}>
                        {hasClue ? '✓' : '○'}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
            <div className="word-list">
              <h3>Down</h3>
              <ul>
                {words.down.map((entry) => {
                  const hasClue = clues.has(getClueKey(entry));
                  const isActive =
                    selectedWord?.number === entry.number &&
                    selectedWord?.direction === 'down';
                  return (
                    <li
                      key={`down-${entry.number}`}
                      className={`word-item ${hasClue ? 'has-clue' : 'no-clue'} ${isActive ? 'active' : ''}`}
                      onClick={() => handleWordClick(entry)}
                    >
                      <span className="word-number">{entry.number}.</span>
                      <span className="word-text">{entry.word}</span>
                      <span className={`clue-indicator ${hasClue ? 'filled' : ''}`}>
                        {hasClue ? '✓' : '○'}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>

          <CluePanel
            selectedWord={selectedWord}
            clues={clues}
            onClueChange={handleClueChange}
            onClose={handleCloseCluePanel}
          />

          <WordSuggestions
            selectedWord={currentWord}
            onSelectWord={handleFillSuggestedWord}
            onSelectClue={handleSelectSuggestedClue}
          />
        </div>
      </div>

      <div className="instructions">
        <p>
          <strong>Grid:</strong> Click cell to select | Right-click to toggle black | Type letters |
          Arrow keys to navigate | Tab/Space to switch direction
        </p>
        <p>
          <strong>Clues:</strong> Click a word in the list to add or edit its clue
        </p>
      </div>
    </div>
  );
}

export { createEmptyGrid };
