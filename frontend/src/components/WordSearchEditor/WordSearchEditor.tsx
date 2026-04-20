import { useState, useEffect, useCallback } from 'react';
import { WordSearchConfig, WordSearchPlacement, WordSearchPuzzle } from '../../types';
import { generateWordSearch } from '../../utils/wordSearchGenerator';
import { createWordSearch, getWordSearches, getWordSearch, updateWordSearch, deleteWordSearch, exportWordSearchPdf } from '../../api/wordSearches';
import { WordSearchGrid } from './WordSearchGrid';
import { WordListPanel } from './WordListPanel';
import { WordSearchConfigPanel } from './WordSearchConfigPanel';
import { WordDbSearchModal } from './WordDbSearchModal';
import './WordSearchEditor.css';

const DEFAULT_CONFIG: WordSearchConfig = {
  rows: 15,
  cols: 15,
  allowedDirections: ['E', 'W', 'N', 'S', 'NE', 'NW', 'SE', 'SW'],
};

export function WordSearchEditor() {
  const [title, setTitle] = useState('Untitled Word Search');
  const [difficulty, setDifficulty] = useState('');
  const [words, setWords] = useState<string[]>([]);
  const [config, setConfig] = useState<WordSearchConfig>(DEFAULT_CONFIG);
  const [grid, setGrid] = useState<string[][]>([]);
  const [placements, setPlacements] = useState<WordSearchPlacement[]>([]);
  const [unplaced, setUnplaced] = useState<string[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [savedPuzzles, setSavedPuzzles] = useState<WordSearchPuzzle[]>([]);
  const [showPuzzleList, setShowPuzzleList] = useState(false);
  const [highlightMode, setHighlightMode] = useState(false);
  const [selectedWord, setSelectedWord] = useState<string | null>(null);
  const [showDbModal, setShowDbModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const loadList = useCallback(async () => {
    try {
      const data = await getWordSearches();
      setSavedPuzzles(data);
    } catch {
      // Server might not be running
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const handleGenerate = () => {
    if (words.length === 0) {
      showMessage('error', 'Add some words before generating.');
      return;
    }
    setIsGenerating(true);
    // Use setTimeout to allow React to render the disabled state first
    setTimeout(() => {
      const result = generateWordSearch(config, words);
      setGrid(result.grid);
      setPlacements(result.placements);
      setUnplaced(result.unplaced);
      setHighlightMode(false);
      setSelectedWord(null);
      setIsGenerating(false);
    }, 10);
  };

  const handleSave = async () => {
    if (grid.length === 0) {
      showMessage('error', 'Generate a puzzle before saving.');
      return;
    }
    setIsSaving(true);
    try {
      if (currentId) {
        await updateWordSearch(currentId, { title, grid, words, placements, config, difficulty_label: difficulty || undefined });
        showMessage('success', 'Saved!');
      } else {
        const created = await createWordSearch({ title, grid, words, placements, config, difficulty_label: difficulty || undefined });
        setCurrentId(created.id);
        showMessage('success', 'Created!');
      }
      loadList();
    } catch {
      showMessage('error', 'Failed to save. Is the server running?');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoad = async (id: number) => {
    setIsLoading(true);
    try {
      const ws = await getWordSearch(id);
      setTitle(ws.title);
      setDifficulty(ws.difficulty_label || '');
      setWords(ws.words);
      setConfig(ws.config);
      setGrid(ws.grid);
      setPlacements(ws.placements as WordSearchPlacement[]);
      setUnplaced([]);
      setCurrentId(ws.id);
      setShowPuzzleList(false);
      setHighlightMode(false);
      setSelectedWord(null);
      showMessage('success', 'Loaded!');
    } catch {
      showMessage('error', 'Failed to load.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this word search?')) return;
    try {
      await deleteWordSearch(id);
      if (currentId === id) handleNew();
      loadList();
      showMessage('success', 'Deleted.');
    } catch {
      showMessage('error', 'Failed to delete.');
    }
  };

  const handleNew = () => {
    setTitle('Untitled Word Search');
    setDifficulty('');
    setWords([]);
    setConfig(DEFAULT_CONFIG);
    setGrid([]);
    setPlacements([]);
    setUnplaced([]);
    setCurrentId(null);
    setHighlightMode(false);
    setSelectedWord(null);
    setShowPuzzleList(false);
  };

  const handleExportPdf = async () => {
    if (!currentId) {
      showMessage('error', 'Save the puzzle first before exporting.');
      return;
    }
    setIsExporting(true);
    try {
      await exportWordSearchPdf(currentId);
      showMessage('success', 'PDF exported!');
    } catch {
      showMessage('error', 'Failed to export PDF.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleAddWordsFromDb = (newWords: string[]) => {
    const size = Math.min(config.rows, config.cols);
    const { min, max } = size <= 10 ? { min: 3, max: 7 } : size <= 15 ? { min: 4, max: 10 } : { min: 5, max: 15 };
    const valid = newWords.filter(w => w.length >= min && w.length <= max);
    const merged = Array.from(new Set([...words, ...valid]));
    setWords(merged);
    if (valid.length < newWords.length) {
      showMessage('error', `${newWords.length - valid.length} word(s) skipped — must be ${min}–${max} letters for a ${config.rows}×${config.cols} grid.`);
    }
  };

  return (
    <div className="ws-editor">
      <div className="ws-toolbar">
        <input
          type="text"
          className="ws-title-input"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Word search title..."
        />
        <select
          className="difficulty-select"
          value={difficulty}
          onChange={e => setDifficulty(e.target.value)}
          title="Difficulty"
        >
          <option value="">Difficulty...</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
          <option value="Expert">Expert</option>
        </select>
        <button className="btn btn-secondary" onClick={handleNew}>New</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : currentId ? 'Save' : 'Create'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => setShowPuzzleList(s => !s)}
        >
          {showPuzzleList ? 'Hide List' : 'Load'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleExportPdf}
          disabled={isExporting || !currentId}
          title={!currentId ? 'Save puzzle first' : 'Export as PDF'}
        >
          {isExporting ? 'Exporting...' : 'Export PDF'}
        </button>
        {grid.length > 0 && (
          <label className="ws-highlight-toggle">
            <input
              type="checkbox"
              checked={highlightMode}
              onChange={e => {
                setHighlightMode(e.target.checked);
                if (!e.target.checked) setSelectedWord(null);
              }}
            />
            Highlight words
          </label>
        )}
      </div>

      {message && (
        <div className={`message message-${message.type}`}>{message.text}</div>
      )}

      {showPuzzleList && (
        <div className="puzzle-list-panel">
          <h3>Saved Word Searches</h3>
          {savedPuzzles.length === 0 ? (
            <p className="no-puzzles">No saved word searches yet.</p>
          ) : (
            <ul className="puzzle-list">
              {savedPuzzles.map(ws => (
                <li key={ws.id} className="puzzle-item">
                  <div className="puzzle-info">
                    <span className="puzzle-name">{ws.title}</span>
                    {ws.difficulty_label && (
                      <span className={`difficulty-badge difficulty-${ws.difficulty_label.toLowerCase()}`}>
                        {ws.difficulty_label}
                      </span>
                    )}
                    <span className="puzzle-date">
                      {new Date(ws.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="puzzle-actions">
                    <button
                      className="btn btn-small"
                      onClick={() => handleLoad(ws.id)}
                      disabled={isLoading}
                    >
                      Load
                    </button>
                    <button
                      className="btn btn-small btn-danger"
                      onClick={() => handleDelete(ws.id)}
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

      <div className="ws-main">
        <div className="ws-sidebar">
          <WordSearchConfigPanel
            config={config}
            onChange={setConfig}
            onGenerate={handleGenerate}
            isGenerating={isGenerating}
            unplacedCount={unplaced.length}
          />
          <WordListPanel
            words={words}
            placements={placements}
            unplaced={unplaced}
            highlightMode={highlightMode}
            selectedWord={selectedWord}
            onWordSelect={setSelectedWord}
            onWordsChange={words => { setWords(words); setPlacements([]); setUnplaced([]); setGrid([]); }}
            onOpenDbSearch={() => setShowDbModal(true)}
            config={config}
          />
        </div>

        <div className="ws-content">
          <WordSearchGrid
            grid={grid}
            placements={placements}
            selectedWord={selectedWord}
            highlightMode={highlightMode}
          />
          {grid.length > 0 && (
            <div className="ws-print-word-list">
              <h3>Find these words:</h3>
              <div className="ws-print-words">
                {words.map(w => (
                  <span key={w} className="ws-print-word">{w}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <WordDbSearchModal
        isOpen={showDbModal}
        onClose={() => setShowDbModal(false)}
        onAddWords={handleAddWordsFromDb}
        existingWords={words}
      />
    </div>
  );
}
