import { useState, useEffect, useCallback } from 'react';
import { GridEditor, createEmptyGrid } from './components/GridEditor';
import { GridCell, Puzzle, WordPlacement } from './types';
import { createPuzzle, getPuzzles, getPuzzle, updatePuzzle, deletePuzzle } from './api/puzzles';
import './App.css';

function App() {
  const [grid, setGrid] = useState<GridCell[][]>(createEmptyGrid());
  const [wordPlacements, setWordPlacements] = useState<WordPlacement[]>([]);
  const [initialWordPlacements, setInitialWordPlacements] = useState<WordPlacement[] | undefined>(undefined);
  const [puzzles, setPuzzles] = useState<Puzzle[]>([]);
  const [currentPuzzleId, setCurrentPuzzleId] = useState<number | null>(null);
  const [puzzleTitle, setPuzzleTitle] = useState('Untitled Puzzle');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showPuzzleList, setShowPuzzleList] = useState(false);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const loadPuzzles = useCallback(async () => {
    try {
      const data = await getPuzzles();
      setPuzzles(data);
    } catch {
      // Server might not be running
    }
  }, []);

  useEffect(() => {
    loadPuzzles();
  }, [loadPuzzles]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (currentPuzzleId) {
        await updatePuzzle(currentPuzzleId, {
          title: puzzleTitle,
          grid_data: grid,
          word_placements: wordPlacements,
        });
        showMessage('success', 'Puzzle saved!');
      } else {
        const newPuzzle = await createPuzzle({
          title: puzzleTitle,
          grid_data: grid,
          word_placements: wordPlacements,
        });
        setCurrentPuzzleId(newPuzzle.id);
        showMessage('success', 'Puzzle created!');
      }
      loadPuzzles();
    } catch {
      showMessage('error', 'Failed to save puzzle. Is the server running?');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoad = async (puzzleId: number) => {
    setIsLoading(true);
    try {
      const puzzle = await getPuzzle(puzzleId);
      setGrid(puzzle.grid_data);
      setPuzzleTitle(puzzle.title);
      setCurrentPuzzleId(puzzle.id);
      setInitialWordPlacements(puzzle.word_placements as WordPlacement[] | undefined);
      setShowPuzzleList(false);
      showMessage('success', 'Puzzle loaded!');
    } catch {
      showMessage('error', 'Failed to load puzzle');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (puzzleId: number) => {
    if (!confirm('Are you sure you want to delete this puzzle?')) return;

    try {
      await deletePuzzle(puzzleId);
      if (currentPuzzleId === puzzleId) {
        setCurrentPuzzleId(null);
        setGrid(createEmptyGrid());
        setPuzzleTitle('Untitled Puzzle');
      }
      loadPuzzles();
      showMessage('success', 'Puzzle deleted');
    } catch {
      showMessage('error', 'Failed to delete puzzle');
    }
  };

  const handleNew = () => {
    setGrid(createEmptyGrid());
    setPuzzleTitle('Untitled Puzzle');
    setCurrentPuzzleId(null);
    setInitialWordPlacements(undefined);
    setWordPlacements([]);
    setShowPuzzleList(false);
  };

  const handleGridChange = (newGrid: GridCell[][]) => {
    setGrid(newGrid);
  };

  const handleWordPlacementsChange = useCallback((placements: WordPlacement[]) => {
    setWordPlacements(placements);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>CrosswordForge</h1>
        <div className="header-controls">
          <input
            type="text"
            className="puzzle-title-input"
            value={puzzleTitle}
            onChange={(e) => setPuzzleTitle(e.target.value)}
            placeholder="Puzzle title..."
          />
          <button onClick={handleNew} className="btn btn-secondary">
            New
          </button>
          <button onClick={handleSave} className="btn btn-primary" disabled={isSaving}>
            {isSaving ? 'Saving...' : currentPuzzleId ? 'Save' : 'Create'}
          </button>
          <button
            onClick={() => setShowPuzzleList(!showPuzzleList)}
            className="btn btn-secondary"
          >
            {showPuzzleList ? 'Hide List' : 'Load'}
          </button>
        </div>
      </header>

      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      {showPuzzleList && (
        <div className="puzzle-list-panel">
          <h3>Saved Puzzles</h3>
          {puzzles.length === 0 ? (
            <p className="no-puzzles">No saved puzzles yet.</p>
          ) : (
            <ul className="puzzle-list">
              {puzzles.map((puzzle) => (
                <li key={puzzle.id} className="puzzle-item">
                  <div className="puzzle-info">
                    <span className="puzzle-name">{puzzle.title}</span>
                    <span className="puzzle-date">
                      {new Date(puzzle.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="puzzle-actions">
                    <button
                      onClick={() => handleLoad(puzzle.id)}
                      className="btn btn-small"
                      disabled={isLoading}
                    >
                      Load
                    </button>
                    <button
                      onClick={() => handleDelete(puzzle.id)}
                      className="btn btn-small btn-danger"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <main className="app-main">
        <GridEditor
          initialGrid={grid}
          initialWordPlacements={initialWordPlacements}
          onGridChange={handleGridChange}
          onWordPlacementsChange={handleWordPlacementsChange}
          key={currentPuzzleId}
        />
      </main>
    </div>
  );
}

export default App;
